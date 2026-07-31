"""patent_detail_search wraps a deeply nested KIPRIS response
(getBibliographyDetailInfoSearch) that previously got dumped to markdown
unfiltered — its raw DataFrame columns are opaque array-wrapper names like
"biblioSummaryInfoArray", each cell holding a nested dict/list, so the old
`response.to_markdown()` output was close to unusable. These tests cover
the new `fields` parameter: default summary fields when omitted/empty, an
arbitrary combination of the full field set on request, validation of
unknown field names, and that repeated entries (IPC codes, claims) join
correctly regardless of whether xmltodict handed back a dict (single
entry) or a list (multiple entries).
"""

import pandas as pd
import pytest

from mcp_kipris.kipris.tools.korean.patent_detail_search_tool import (
    _ALL_FIELDS,
    _DEFAULT_FIELDS,
    _extract_field,
    _item_has_data,
    PatentDetailSearchTool,
)

pytestmark = pytest.mark.unit

_SAMPLE_ITEM = {
    "biblioSummaryInfoArray": {
        "biblioSummaryInfo": {
            "applicationDate": "20230101",
            "applicationNumber": "1020230000001",
            "inventionTitle": "테스트 발명",
            "registerStatus": "등록",
        }
    },
    "ipcInfoArray": {
        "ipcInfo": [
            {"ipcNumber": "H01L21/00", "ipcDate": "20230101"},
            {"ipcNumber": "H01L29/00", "ipcDate": "20230101"},
        ]
    },
    "abstractInfoArray": {"abstractInfo": {"astrtCont": "이 발명은 테스트를 위한 것입니다."}},
    "applicantInfoArray": {"applicantInfo": {"name": "삼성전자", "country": "KR"}},
    "claimInfoArray": {"claimInfo": [{"claim": "청구항 1"}, {"claim": "청구항 2"}]},
}


def _mock_response() -> pd.DataFrame:
    return pd.DataFrame([_SAMPLE_ITEM])


# --- _extract_field: the pure nested-extraction helper ---------------------


def test_extract_field_reads_a_singleton_dict_entry():
    value = _extract_field(_SAMPLE_ITEM, "applicantInfoArray", "applicantInfo", "name", ", ")
    assert value == "삼성전자"


def test_extract_field_joins_a_list_of_entries():
    value = _extract_field(_SAMPLE_ITEM, "ipcInfoArray", "ipcInfo", "ipcNumber", ", ")
    assert value == "H01L21/00, H01L29/00"


def test_extract_field_returns_none_when_group_absent():
    assert _extract_field(_SAMPLE_ITEM, "rndInfoArray", "rndInfo", "rndProjectName", ", ") is None


def test_extract_field_returns_none_when_source_field_absent():
    assert _extract_field(_SAMPLE_ITEM, "applicantInfoArray", "applicantInfo", "engName", ", ") is None


def test_item_has_data_true_for_a_real_item():
    assert _item_has_data(_SAMPLE_ITEM) is True


def test_item_has_data_false_when_biblio_summary_is_null():
    assert _item_has_data({"biblioSummaryInfoArray": None, "ipcInfoArray": None}) is False


# --- tool-level behavior -----------------------------------------------


def test_default_fields_used_when_fields_omitted(monkeypatch):
    tool = PatentDetailSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _mock_response())

    text = tool.run_tool({"application_number": "1020230000001"})[0].text

    for field in _DEFAULT_FIELDS:
        assert field in text
    assert "삼성전자" in text
    assert "H01L21/00, H01L29/00" in text
    assert "astrtCont" not in text


def test_default_fields_used_when_fields_is_empty_list(monkeypatch):
    tool = PatentDetailSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _mock_response())

    text = tool.run_tool({"application_number": "1020230000001", "fields": []})[0].text

    for field in _DEFAULT_FIELDS:
        assert field in text


def test_custom_field_combination_returns_only_requested_fields(monkeypatch):
    tool = PatentDetailSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _mock_response())

    text = tool.run_tool({"application_number": "1020230000001", "fields": ["astrtCont", "claim"]})[0].text

    assert "이 발명은 테스트를 위한 것입니다" in text
    assert "청구항 1" in text and "청구항 2" in text
    assert "applicationNumber" not in text
    assert "registerStatus" not in text


def test_unknown_field_returns_validation_error(monkeypatch):
    tool = PatentDetailSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _mock_response())

    text = tool.run_tool({"application_number": "1020230000001", "fields": ["not_a_real_field"]})[0].text

    assert "검증 오류" in text
    assert "not_a_real_field" in text


def test_field_missing_from_response_renders_as_empty_not_a_crash(monkeypatch):
    tool = PatentDetailSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _mock_response())

    result = tool.run_tool({"application_number": "1020230000001", "fields": ["claimCount", "applicationNumber"]})

    assert "claimCount" in result[0].text
    assert "1020230000001" in result[0].text


def test_empty_response_returns_no_result_message(monkeypatch):
    tool = PatentDetailSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: pd.DataFrame())

    result = tool.run_tool({"application_number": "1020230000001"})

    assert result[0].text == "there is no result"


def test_unrecognized_application_number_returns_no_result_message(monkeypatch):
    """For an application number KIPRIS doesn't recognize, the live API
    returns HTTP 200 / resultCode 00 with every group under item set to
    null rather than an error — parse_response turns that into a non-empty
    1-row DataFrame, so `response.empty` alone doesn't catch it (confirmed
    against the real API). Without this check the tool used to render an
    all-blank table instead of reporting no result.
    """
    tool = PatentDetailSearchTool()
    all_null_item = {
        "biblioSummaryInfoArray": None,
        "ipcInfoArray": None,
        "abstractInfoArray": None,
        "applicantInfoArray": None,
        "claimInfoArray": None,
    }
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: pd.DataFrame([all_null_item]))

    result = tool.run_tool({"application_number": "9999999999999"})

    assert result[0].text == "there is no result"


def test_multi_value_fields_join_without_embedding_raw_newlines(monkeypatch):
    """A joined multi-entry field (claim, astrtCont) must not contain a
    literal newline: pandas/tabulate's to_markdown() renders an embedded
    newline as extra, misaligned table rows instead of keeping it in one
    cell — confirmed against a real patent with 7 claims, where the old
    "\\n\\n" separator broke the table into 13 garbled rows.
    """
    tool = PatentDetailSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _mock_response())

    text = tool.run_tool({"application_number": "1020230000001", "fields": ["claim"]})[0].text

    # header + separator + exactly one data row == 3 lines; any more means
    # the joined value leaked a newline into the table body.
    assert len(text.strip().splitlines()) == 3
    assert "청구항 1 청구항 2" in text


def test_tool_description_advertises_the_full_field_set():
    tool = PatentDetailSearchTool().get_tool_description()

    fields_schema = tool.inputSchema["properties"]["fields"]
    assert set(fields_schema["items"]["enum"]) == set(_ALL_FIELDS)


@pytest.mark.asyncio
async def test_run_tool_async_supports_field_selection_too(monkeypatch):
    tool = PatentDetailSearchTool()

    async def _async_search(**kwargs):
        return _mock_response()

    monkeypatch.setattr(tool.api, "async_search", _async_search)

    text = (await tool.run_tool_async({"application_number": "1020230000001", "fields": ["astrtCont"]}))[0].text

    assert "이 발명은 테스트를 위한 것입니다" in text
    assert "applicationNumber" not in text
