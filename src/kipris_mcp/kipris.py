"""KIPRIS Plus 특허·실용신안 Open API용 최소 비동기 클라이언트.

- 키 파라미터: ServiceKey
- 응답: XML (response/header, response/count, response/body)
- API 키가 에러 메시지나 로그에 노출되지 않도록 httpx 예외 문자열을 그대로 쓰지 않는다.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import unquote

import httpx

# httpx는 INFO 레벨에서 요청 URL(쿼리의 ServiceKey 포함)을 로그로 남기므로 막는다.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

DEFAULT_BASE_URL = "https://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice"

_RESULT_HINTS = {
    "10": "요청 파라미터가 올바르지 않습니다.",
    "30": "등록되지 않은 API 키입니다. 키를 확인하세요.",
    "31": "이용 기간이 만료되었거나 이 API 상품을 신청하지 않은 키입니다.",
}


class KiprisError(Exception):
    """사용자에게 그대로 보여줘도 안전한 KIPRIS 호출 오류."""


def normalize_key(key: str) -> str:
    """공공데이터포털에서 복사한 percent-encoded 키(%2B 등)를 한 번 풀어준다."""
    key = (key or "").strip()
    return unquote(key) if "%" in key else key


def _to_obj(elem: ET.Element) -> Any:
    children = list(elem)
    if not children:
        text = (elem.text or "").strip()
        return text or None
    out: dict[str, Any] = {}
    for child in children:
        value = _to_obj(child)
        if child.tag in out:
            if not isinstance(out[child.tag], list):
                out[child.tag] = [out[child.tag]]
            out[child.tag].append(value)
        else:
            out[child.tag] = value
    return out


def parse_response(xml_text: str) -> dict[str, Any]:
    """KIPRIS XML을 {"total", "items", "detail"} 로 변환한다. 오류 코드는 KiprisError."""
    try:
        root = ET.fromstring(xml_text.lstrip("﻿").strip())
    except ET.ParseError as exc:
        raise KiprisError("KIPRIS 응답을 해석하지 못했습니다 (XML 형식이 아님).") from exc

    if root.tag == "OpenAPI_ServiceResponse":  # 공공데이터포털식 인증 오류 포맷
        msg = root.findtext(".//returnAuthMsg") or root.findtext(".//errMsg") or "인증 오류"
        raise KiprisError(f"KIPRIS 인증/요청 오류: {msg.strip()}")

    code = (root.findtext("./header/resultCode") or "").strip()
    msg = (root.findtext("./header/resultMsg") or "").strip()
    if code and code != "00":
        if code == "20":  # 검색 결과 없음
            return {"total": 0, "items": [], "detail": None}
        hint = _RESULT_HINTS.get(code, "")
        raise KiprisError(f"KIPRIS 오류 [{code}] {msg} {hint}".strip())

    total_text = (root.findtext("./count/totalCount") or "").strip()
    items = [_to_obj(e) or {} for e in root.findall("./body/items/item")]
    detail_el = root.find("./body/item")
    return {
        "total": int(total_text) if total_text.isdigit() else None,
        "items": items,
        "detail": _to_obj(detail_el) if detail_el is not None else None,
    }


def _fmt(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class KiprisClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        key = normalize_key(api_key)
        if not key:
            raise KiprisError("KIPRIS_API_KEY 환경변수가 설정되지 않았습니다.")
        self._key = key
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport

    async def call(self, operation: str, **params: Any) -> dict[str, Any]:
        query = {k: _fmt(v) for k, v in params.items() if v is not None and v != ""}
        query["ServiceKey"] = self._key
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport, follow_redirects=True
            ) as http:
                resp = await http.get(f"{self._base}/{operation}", params=query)
        except httpx.TimeoutException as exc:
            raise KiprisError("KIPRIS 서버 응답 시간이 초과되었습니다.") from exc
        except httpx.HTTPError as exc:
            # str(exc)에는 ServiceKey가 담긴 URL이 들어갈 수 있어 타입 이름만 쓴다.
            raise KiprisError(f"KIPRIS 서버에 연결하지 못했습니다 ({type(exc).__name__}).") from None
        if resp.status_code != 200:
            raise KiprisError(f"KIPRIS 서버가 HTTP {resp.status_code} 를 반환했습니다.")
        return parse_response(resp.text)

    async def word_search(
        self,
        word: str,
        *,
        year: int | None = None,
        patent: bool = True,
        utility: bool = True,
        page: int = 1,
        rows: int = 10,
    ) -> dict[str, Any]:
        return await self.call(
            "getWordSearch",
            word=word,
            year=year,
            patent=patent,
            utility=utility,
            pageNo=page,
            numOfRows=rows,
        )

    async def advanced_search(
        self,
        *,
        word: str | None = None,
        invention_title: str | None = None,
        abstract: str | None = None,
        claim: str | None = None,
        ipc: str | None = None,
        applicant: str | None = None,
        patent: bool = True,
        utility: bool = True,
        page: int = 1,
        rows: int = 10,
        sort: str = "AD",
        descending: bool = True,
    ) -> dict[str, Any]:
        return await self.call(
            "getAdvancedSearch",
            word=word,
            inventionTitle=invention_title,
            astrtCont=abstract,
            claimScope=claim,
            ipcNumber=ipc,
            applicant=applicant,
            patent=patent,
            utility=utility,
            pageNo=page,
            numOfRows=rows,
            sortSpec=sort,
            descSort=descending,
        )

    async def detail(self, application_number: str) -> dict[str, Any]:
        return await self.call("getBibliographyDetailInfoSearch", applicationNumber=application_number)
