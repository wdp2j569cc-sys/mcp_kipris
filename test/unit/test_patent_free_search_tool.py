"""patent_free_search regression tests covering two related fixes.

1. run_tool called sync_search(docs_count=..., docs_start=...) but
   PatentFreeSearchAPI's real parameters are num_of_rows/page_no, so the
   requested count was silently ignored (same bug class as ipc_search, see
   test_ipc_search_tool.py).
2. Live verification (with a correctly configured KIPRIS key) showed that
   even after fixing #1, this specific endpoint (freeSearchInfo) ignores
   numOfRows/pageNo server-side and always returns a fixed batch of rows,
   with no response.count block to report a real total from. So this tool
   now trims the response to docs_count itself rather than passing through
   more rows than the caller asked for.
"""

import pandas as pd
import pytest

from mcp_kipris.kipris.tools.korean.patent_free_search_tool import PatentFreeSearchTool

pytestmark = pytest.mark.unit


def _mock_response(row_count=1):
    rows = [
        {
            "ApplicationNumber": f"102023000000{i}",
            "ApplicationDate": "20230101",
            "InventionName": "테스트 발명",
            "Applicant": "삼성전자",
        }
        for i in range(row_count)
    ]
    return pd.DataFrame(rows)


def test_run_tool_sends_num_of_rows_and_page_no_not_docs_count(monkeypatch):
    tool = PatentFreeSearchTool()
    captured = {}

    def _fake_sync_search(**kwargs):
        captured.update(kwargs)
        return _mock_response()

    monkeypatch.setattr(tool.api, "sync_search", _fake_sync_search)

    tool.run_tool({"word": "반도체", "docs_count": 5, "docs_start": 1})

    assert captured["num_of_rows"] == 5
    assert captured["page_no"] == 1
    assert "docs_count" not in captured
    assert "docs_start" not in captured


def test_run_tool_trims_to_docs_count_when_kipris_ignores_the_limit(monkeypatch):
    # freeSearchInfo always sends back a fixed batch regardless of
    # numOfRows -- simulate KIPRIS returning 30 rows for a docs_count=5
    # request and assert the tool only displays 5.
    tool = PatentFreeSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _mock_response(row_count=30))

    text = tool.run_tool({"word": "반도체", "docs_count": 5})[0].text

    assert "30건 중 5건 표시" in text
    assert text.count("1020230000000") == 1  # only row 0 of the 5 kept


def test_run_tool_reports_returned_count_when_within_docs_count(monkeypatch):
    tool = PatentFreeSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _mock_response(row_count=3))

    text = tool.run_tool({"word": "반도체", "docs_count": 10})[0].text

    assert "3건 중 3건 표시" in text
