"""ipc_search regression tests for two bugs found via live user testing.

1. run_tool called self.api.sync_search(docs_count=..., docs_start=...), but
   IpcSearchAPI.sync_search's real parameters are num_of_rows/page_no.
   docs_count/docs_start fell into **kwargs and went out as query params
   KIPRIS doesn't recognize (docsCount/docsStart), while num_of_rows kept
   its hardcoded default of 10 -- so a requested docs_count of 5 always
   came back as 10 rows.
2. totalCount (needed for any aggregation across pages) was never surfaced
   anywhere in the tool's output.
"""

import pandas as pd
import pytest

from mcp_kipris.kipris.errors import KiprisTimeoutError
from mcp_kipris.kipris.tools.korean.ipc_search_tool import IpcSearchTool

pytestmark = pytest.mark.unit


def _mock_response(total_count=1, **extra_columns):
    row = {
        "applicationNumber": "1020230000001",
        "applicationDate": "20230101",
        "inventionTitle": "테스트 발명",
        "applicantName": "삼성전자",
    }
    row.update(extra_columns)
    df = pd.DataFrame([row])
    df.attrs["total_count"] = total_count
    return df


def test_run_tool_sends_num_of_rows_and_page_no_not_docs_count(monkeypatch):
    tool = IpcSearchTool()
    captured = {}

    def _fake_sync_search(**kwargs):
        captured.update(kwargs)
        return _mock_response()

    monkeypatch.setattr(tool.api, "sync_search", _fake_sync_search)

    tool.run_tool({"ipc_number": "H01L", "docs_count": 5, "docs_start": 1})

    assert captured["num_of_rows"] == 5
    assert captured["page_no"] == 1
    assert "docs_count" not in captured
    assert "docs_start" not in captured


def test_run_tool_translates_docs_start_offset_to_a_page_number(monkeypatch):
    tool = IpcSearchTool()
    captured = {}

    def _fake_sync_search(**kwargs):
        captured.update(kwargs)
        return _mock_response()

    monkeypatch.setattr(tool.api, "sync_search", _fake_sync_search)

    # docs_start=11 with docs_count=10 means "the second page of 10"
    tool.run_tool({"ipc_number": "H01L", "docs_count": 10, "docs_start": 11})

    assert captured["page_no"] == 2


def test_run_tool_reports_total_count_from_response_attrs(monkeypatch):
    tool = IpcSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _mock_response(total_count=137))

    text = tool.run_tool({"ipc_number": "H01L"})[0].text

    assert "137건" in text


def test_summary_includes_open_and_register_fields_when_present(monkeypatch):
    tool = IpcSearchTool()
    monkeypatch.setattr(
        tool.api,
        "sync_search",
        lambda **kwargs: _mock_response(
            openNumber="1020230000002", openDate="20230601", registerDate="20240101", ipcNumber="H01L21/00"
        ),
    )

    text = tool.run_tool({"ipc_number": "H01L"})[0].text

    assert "1020230000002" in text
    assert "20230601" in text
    assert "20240101" in text
    assert "H01L21/00" in text


def test_summary_columns_default_to_empty_when_kipris_omits_them(monkeypatch):
    """openDate/openNumber/registerDate are absent for a not-yet-published
    application -- selecting them must not raise KeyError."""
    tool = IpcSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _mock_response())

    result = tool.run_tool({"ipc_number": "H01L"})

    assert "오류" not in result[0].text
    assert "1020230000001" in result[0].text


def test_empty_response_reports_zero_total_count(monkeypatch):
    empty = pd.DataFrame()
    empty.attrs["total_count"] = 0
    tool = IpcSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: empty)

    text = tool.run_tool({"ipc_number": "H01L"})[0].text

    assert "0건" in text


def test_network_failure_is_reported_as_an_error_not_as_no_result(monkeypatch):
    """get_response() used to swallow timeouts/connection errors into an
    empty {}, which parse_response() then read as "0 matches" -- a real
    KIPRIS timeout looked identical to "this search genuinely has no
    results". Now that get_response() raises KiprisTimeoutError instead
    (see test_api_utils_errors.py), this must surface as an actual error
    message here, not "there is no result".
    """
    tool = IpcSearchTool()

    def _raise_timeout(**kwargs):
        raise KiprisTimeoutError(timeout_seconds=600)

    monkeypatch.setattr(tool.api, "sync_search", _raise_timeout)

    text = tool.run_tool({"ipc_number": "H01L"})[0].text

    assert "오류가 발생했습니다" in text
    assert "timeout" in text.lower()
    assert "there is no result" not in text
