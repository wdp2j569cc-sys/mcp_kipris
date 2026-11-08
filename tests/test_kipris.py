import httpx
import pytest

from kipris_mcp.kipris import KiprisClient, KiprisError, normalize_key, parse_response

from .samples import DETAIL_XML, EMPTY_XML, KEY_ERROR_XML, LIST_XML, PORTAL_ERROR_XML

KEY = "SECRETKEY1234567890abcdefghijklmnop"


def make_client(handler):
    return KiprisClient(KEY, transport=httpx.MockTransport(handler))


def test_parse_list():
    data = parse_response(LIST_XML.format(abstract="초록"))
    assert data["total"] == 42
    assert len(data["items"]) == 2
    assert data["items"][0]["applicationNumber"] == "1020230034567"
    assert data["items"][1]["ipcNumber"] is None  # 빈 태그는 None


def test_parse_no_result_is_empty_not_error():
    assert parse_response(EMPTY_XML) == {"total": 0, "items": [], "detail": None}


def test_parse_key_error_has_hint():
    with pytest.raises(KiprisError, match=r"\[30\].*등록되지 않은 API 키"):
        parse_response(KEY_ERROR_XML)


def test_parse_portal_style_error():
    with pytest.raises(KiprisError, match="SERVICE_KEY_IS_NOT_REGISTERED_ERROR"):
        parse_response(PORTAL_ERROR_XML)


def test_parse_non_xml():
    with pytest.raises(KiprisError, match="해석"):
        parse_response("<html><body>502 Bad Gateway")


def test_parse_detail_groups_repeated_tags_into_list():
    detail = parse_response(DETAIL_XML)["detail"]
    claims = detail["claimInfoArray"]["claimInfo"]
    assert isinstance(claims, list) and len(claims) == 2
    assert detail["abstractInfoArray"]["abstractInfo"]["astrtCont"] == "상세 초록입니다."


def test_normalize_key_decodes_percent_once():
    assert normalize_key(" abc%2Bdef%3D ") == "abc+def="
    assert normalize_key("plainkey") == "plainkey"


def test_empty_key_rejected():
    with pytest.raises(KiprisError, match="KIPRIS_API_KEY"):
        KiprisClient("   ")


async def test_word_search_sends_expected_request():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["query"] = dict(request.url.params)
        return httpx.Response(200, text=LIST_XML.format(abstract="x"))

    data = await make_client(handler).word_search("전익기", year=2023, page=2, rows=5)
    assert seen["path"].endswith("/getWordSearch")
    assert seen["query"] == {
        "word": "전익기",
        "year": "2023",
        "patent": "true",
        "utility": "true",
        "pageNo": "2",
        "numOfRows": "5",
        "ServiceKey": KEY,
    }
    assert data["total"] == 42


async def test_advanced_search_maps_field_names_and_skips_empty():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["query"] = dict(request.url.params)
        return httpx.Response(200, text=EMPTY_XML)

    await make_client(handler).advanced_search(abstract="측풍", claim="디크랩", ipc="B64C", descending=False)
    q = seen["query"]
    assert seen["path"].endswith("/getAdvancedSearch")
    assert (q["astrtCont"], q["claimScope"], q["ipcNumber"], q["descSort"]) == ("측풍", "디크랩", "B64C", "false")
    assert "applicant" not in q and "word" not in q and "inventionTitle" not in q


async def test_percent_encoded_key_is_sent_decoded_once():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["key"] = request.url.params["ServiceKey"]
        return httpx.Response(200, text=EMPTY_XML)

    client = KiprisClient("a%2Bb%3D", transport=httpx.MockTransport(handler))
    await client.word_search("x")
    assert seen["key"] == "a+b="


async def test_network_error_does_not_leak_key():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {request.url}")

    with pytest.raises(KiprisError) as exc:
        await make_client(handler).word_search("x")
    assert KEY not in str(exc.value)
    assert "ConnectError" in str(exc.value)


async def test_timeout_message():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(KiprisError, match="시간이 초과"):
        await make_client(handler).word_search("x")


async def test_http_error_status():
    with pytest.raises(KiprisError, match="HTTP 503"):
        await make_client(lambda r: httpx.Response(503, text="down")).word_search("x")
