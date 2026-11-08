import json

import httpx
import pytest
from starlette.testclient import TestClient

from kipris_mcp.kipris import KiprisClient
from kipris_mcp.server import BearerAuthMiddleware, build_mcp, create_app

from .samples import DETAIL_XML, EMPTY_XML, LIST_XML

TOKEN = "t" * 32
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}
LONG_ABSTRACT = "가" * 2000


def fake_kipris(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("getBibliographyDetailInfoSearch"):
        return httpx.Response(200, text=DETAIL_XML)
    if request.url.params.get("word") == "없는검색어":
        return httpx.Response(200, text=EMPTY_XML)
    return httpx.Response(200, text=LIST_XML.format(abstract=LONG_ABSTRACT))


@pytest.fixture
def client():
    kipris = KiprisClient("key", transport=httpx.MockTransport(fake_kipris))
    app = build_mcp(kipris).streamable_http_app()
    app.add_middleware(BearerAuthMiddleware, token=TOKEN)
    # 배포 환경처럼 localhost가 아닌 Host 로 접속해도 동작해야 한다.
    with TestClient(app, base_url="https://kipris-patent-mcp.onrender.com") as c:
        yield c


def rpc(client, method, params=None, headers=HEADERS, id_=1):
    body = {"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}}
    return client.post("/mcp", json=body, headers=headers)


def test_healthz_is_public(client):
    r = client.get("/healthz")
    assert (r.status_code, r.text) == (200, "ok")


@pytest.mark.parametrize(
    "auth",
    [None, "Bearer wrong-token", "Basic " + TOKEN, TOKEN, "Bearer", "Bearer "],
)
def test_mcp_rejects_bad_credentials(client, auth):
    headers = {k: v for k, v in HEADERS.items() if k != "Authorization"}
    if auth is not None:
        headers["Authorization"] = auth
    r = rpc(client, "tools/list", headers=headers)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


def test_mcp_initialize_and_list_tools(client):
    init = rpc(
        client,
        "initialize",
        {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}},
    )
    assert init.status_code == 200
    assert init.json()["result"]["serverInfo"]["name"] == "kipris-patent"
    tools = rpc(client, "tools/list", id_=2).json()["result"]["tools"]
    assert {t["name"] for t in tools} == {"search_patents", "advanced_search_patents", "get_patent_detail"}


def call(client, name, arguments):
    r = rpc(client, "tools/call", {"name": name, "arguments": arguments})
    assert r.status_code == 200
    return r.json()["result"]


def test_search_patents_truncates_long_abstract(client):
    result = call(client, "search_patents", {"keyword": "전익기", "rows": 999})
    assert not result.get("isError")
    payload = json.loads(result["content"][0]["text"])
    assert payload["total"] == 42 and payload["returned"] == 2
    first = payload["results"][0]
    assert first["inventionTitle"] == "전익기의 측풍 착륙 제어 방법"
    assert len(first["astrtCont"]) < 600 and first["astrtCont"].endswith("(생략)")


def test_search_no_results(client):
    payload = json.loads(call(client, "search_patents", {"keyword": "없는검색어"})["content"][0]["text"])
    assert payload["total"] == 0 and payload["results"] == []


def test_advanced_search_requires_a_condition(client):
    result = call(client, "advanced_search_patents", {})
    assert result["isError"] is True
    assert "하나 이상" in result["content"][0]["text"]


def test_advanced_search_ok(client):
    result = call(client, "advanced_search_patents", {"abstract": "측풍"})
    assert not result.get("isError")


def test_detail_accepts_hyphenated_number(client):
    result = call(client, "get_patent_detail", {"application_number": "10-2023-0034567"})
    payload = json.loads(result["content"][0]["text"])
    assert payload["found"] is True and payload["application_number"] == "1020230034567"
    assert len(payload["detail"]["claimInfoArray"]["claimInfo"]) == 2


def test_detail_rejects_garbage_number(client):
    result = call(client, "get_patent_detail", {"application_number": "abc"})
    assert result["isError"] is True


def test_create_app_requires_strong_token(monkeypatch):
    monkeypatch.setenv("KIPRIS_API_KEY", "key")
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="MCP_AUTH_TOKEN"):
        create_app()
    monkeypatch.setenv("MCP_AUTH_TOKEN", "short")
    with pytest.raises(RuntimeError, match="MCP_AUTH_TOKEN"):
        create_app()
