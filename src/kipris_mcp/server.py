"""KIPRIS 특허 검색 MCP 서버 (Streamable HTTP, Bearer 토큰 인증).

실행:
    uvicorn --factory --app-dir src kipris_mcp.server:create_app --host 0.0.0.0 --port $PORT

필수 환경변수:
    KIPRIS_API_KEY   KIPRIS Plus ServiceKey
    MCP_AUTH_TOKEN   16자 이상. 클라이언트는 `Authorization: Bearer <토큰>` 헤더를 보내야 한다.
선택:
    KIPRIS_BASE_URL  테스트용 API 주소 재정의
"""

from __future__ import annotations

import hmac
import json
import os
import re
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .kipris import DEFAULT_BASE_URL, KiprisClient, KiprisError

MAX_ROWS = 50
LIST_ABSTRACT_CHARS = 500
DETAIL_FIELD_CHARS = 6000
PUBLIC_PATHS = {"/healthz"}


# ---------------------------------------------------------------- 인증 ----
class BearerAuthMiddleware:
    """`Authorization: Bearer <token>` 이 일치하지 않으면 401. /healthz 는 예외."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self._token = token.encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in PUBLIC_PATHS:
            await self.app(scope, receive, send)
            return
        raw = dict(scope["headers"]).get(b"authorization", b"").decode("latin-1")
        scheme, _, credential = raw.partition(" ")
        if scheme.lower() == "bearer" and hmac.compare_digest(credential.strip().encode(), self._token):
            await self.app(scope, receive, send)
            return
        response = JSONResponse(
            {"error": "unauthorized"}, status_code=401, headers={"WWW-Authenticate": "Bearer"}
        )
        await response(scope, receive, send)


# ------------------------------------------------------------ 도구 정의 ----
def _shorten(value: Any, limit: int) -> Any:
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "…(생략)"
    if isinstance(value, dict):
        return {k: _shorten(v, limit) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_shorten(v, limit) for v in value]
    return value


def _clamp_rows(rows: int) -> int:
    return max(1, min(int(rows), MAX_ROWS))


def _list_result(data: dict[str, Any], page: int) -> str:
    items = [_shorten(it, LIST_ABSTRACT_CHARS) for it in data["items"]]
    return json.dumps(
        {"total": data["total"], "page": page, "returned": len(items), "results": items},
        ensure_ascii=False,
    )


def build_mcp(client: KiprisClient) -> FastMCP:
    mcp = FastMCP(
        "kipris-patent",
        instructions=(
            "한국 특허·실용신안을 KIPRIS Plus로 검색한다. 먼저 search_patents 나 "
            "advanced_search_patents 로 후보를 찾고, 관심 있는 출원번호는 get_patent_detail 로 "
            "초록·청구항·서지정보를 확인한다."
        ),
        stateless_http=True,
        json_response=True,
        # Render 등 외부 호스트명으로 접속하므로 localhost 전용 Host 검사는 끈다(인증은 토큰으로 한다).
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    @mcp.custom_route("/healthz", methods=["GET"])
    async def healthz(_: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    @mcp.tool()
    async def search_patents(
        keyword: str,
        page: int = 1,
        rows: int = 10,
        year: int | None = None,
        include_patents: bool = True,
        include_utility_models: bool = True,
    ) -> str:
        """키워드로 한국 특허·실용신안을 검색한다 (선행기술조사의 첫 단계).

        keyword: 검색어. 예: "전익기 측풍 착륙"
        page: 페이지 번호(1부터). rows: 한 페이지 결과 수(최대 50).
        year: 출원 연도로 제한하고 싶을 때만 지정.
        결과에는 출원번호, 발명의 명칭, 출원인, 출원일, 초록(앞부분), IPC 등이 들어 있다.
        """
        page = max(1, int(page))
        data = await client.word_search(
            keyword,
            year=year,
            patent=include_patents,
            utility=include_utility_models,
            page=page,
            rows=_clamp_rows(rows),
        )
        return _list_result(data, page)

    @mcp.tool()
    async def advanced_search_patents(
        invention_title: str | None = None,
        abstract: str | None = None,
        claim: str | None = None,
        ipc: str | None = None,
        applicant: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        rows: int = 10,
        newest_first: bool = True,
    ) -> str:
        """필드를 지정해 한국 특허·실용신안을 검색한다. 최소 한 개 조건은 필요하다.

        invention_title: 발명의 명칭, abstract: 초록, claim: 청구범위, ipc: IPC 분류(예: B64C),
        applicant: 출원인, keyword: 자유 검색어. 결과는 출원일 기준 정렬.
        """
        if not any([invention_title, abstract, claim, ipc, applicant, keyword]):
            raise ValueError("검색 조건을 하나 이상 지정하세요.")
        page = max(1, int(page))
        data = await client.advanced_search(
            word=keyword,
            invention_title=invention_title,
            abstract=abstract,
            claim=claim,
            ipc=ipc,
            applicant=applicant,
            page=page,
            rows=_clamp_rows(rows),
            descending=newest_first,
        )
        return _list_result(data, page)

    @mcp.tool()
    async def get_patent_detail(application_number: str) -> str:
        """출원번호로 서지정보·초록·청구항·IPC·출원인 등 상세 정보를 조회한다.

        application_number: 예 "1020240001234" 또는 "10-2024-0001234" (하이픈 허용).
        """
        number = re.sub(r"[\s-]", "", application_number or "")
        if not (number.isdigit() and 10 <= len(number) <= 13):
            raise ValueError("출원번호는 10~13자리 숫자여야 합니다 (예: 1020240001234).")
        data = await client.detail(number)
        if not data["detail"]:
            return json.dumps({"found": False, "application_number": number}, ensure_ascii=False)
        return json.dumps(
            {"found": True, "application_number": number, "detail": _shorten(data["detail"], DETAIL_FIELD_CHARS)},
            ensure_ascii=False,
        )

    return mcp


# ------------------------------------------------------------ 앱 팩토리 ----
def create_app() -> Starlette:
    token = os.environ.get("MCP_AUTH_TOKEN", "").strip()
    if len(token) < 16:
        raise RuntimeError("MCP_AUTH_TOKEN 환경변수가 없거나 16자 미만입니다. 길고 무작위인 값을 설정하세요.")
    client = KiprisClient(
        os.environ.get("KIPRIS_API_KEY", ""),
        base_url=os.environ.get("KIPRIS_BASE_URL", DEFAULT_BASE_URL),
    )
    app = build_mcp(client).streamable_http_app()
    app.add_middleware(BearerAuthMiddleware, token=token)
    return app


__all__ = ["BearerAuthMiddleware", "KiprisError", "build_mcp", "create_app"]
