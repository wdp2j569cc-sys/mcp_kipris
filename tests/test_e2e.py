"""실제 uvicorn 서버 + 실제 MCP 클라이언트(Streamable HTTP) + 가짜 KIPRIS 서버로 끝까지 확인한다."""

import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from kipris_mcp.server import create_app

from .samples import DETAIL_XML, LIST_XML

TOKEN = "e2e-token-" + "x" * 24
API_KEY = "E2E_SERVICE_KEY"
seen_requests: list[dict] = []


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class FakeKipris(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        url = urlparse(self.path)
        seen_requests.append({"path": url.path, "query": {k: v[0] for k, v in parse_qs(url.query).items()}})
        xml = DETAIL_XML if url.path.endswith("getBibliographyDetailInfoSearch") else LIST_XML.format(abstract="초록")
        body = xml.encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/xml; charset=UTF-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def mcp_url():
    kipris_port, mcp_port = free_port(), free_port()
    fake = HTTPServer(("127.0.0.1", kipris_port), FakeKipris)
    threading.Thread(target=fake.serve_forever, daemon=True).start()

    mp = pytest.MonkeyPatch()
    mp.setenv("KIPRIS_API_KEY", API_KEY)
    mp.setenv("MCP_AUTH_TOKEN", TOKEN)
    mp.setenv("KIPRIS_BASE_URL", f"http://127.0.0.1:{kipris_port}/kipo-api/kipi/patUtiModInfoSearchSevice")
    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=mcp_port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started, "uvicorn did not start"
    yield f"http://127.0.0.1:{mcp_port}/mcp"
    server.should_exit = True
    thread.join(timeout=5)
    fake.shutdown()
    mp.undo()


async def test_real_client_full_flow(mcp_url):
    async with streamablehttp_client(mcp_url, headers={"Authorization": f"Bearer {TOKEN}"}) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {t.name for t in tools.tools} == {
                "search_patents",
                "advanced_search_patents",
                "get_patent_detail",
            }

            result = await session.call_tool("search_patents", {"keyword": "전익기", "rows": 3})
            assert not result.isError
            payload = json.loads(result.content[0].text)
            assert payload["total"] == 42

            detail = await session.call_tool("get_patent_detail", {"application_number": "1020230034567"})
            assert json.loads(detail.content[0].text)["found"] is True

    # 서버가 KIPRIS로 보낸 요청: 키는 ServiceKey로, 검색어는 word로 전달돼야 한다.
    search_req = next(q for q in seen_requests if q["path"].endswith("getWordSearch"))
    assert search_req["query"]["ServiceKey"] == API_KEY
    assert search_req["query"]["word"] == "전익기" and search_req["query"]["numOfRows"] == "3"
    detail_req = next(q for q in seen_requests if q["path"].endswith("getBibliographyDetailInfoSearch"))
    assert detail_req["query"]["applicationNumber"] == "1020230034567"


async def test_real_client_without_token_is_refused(mcp_url):
    with pytest.raises(BaseException) as exc:  # anyio ExceptionGroup 등으로 감싸져 올라온다
        async with streamablehttp_client(mcp_url) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
    assert "401" in repr(exc.value) or "Unauthorized" in repr(exc.value)
