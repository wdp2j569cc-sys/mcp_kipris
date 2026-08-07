"""trademark_search wiring regression tests -- same bug class as
ipc_search (see test_ipc_search_tool.py): run_tool called
sync_search(docs_count=..., docs_start=...) but TrademarkSearchAPI's real
parameters are num_of_rows/page_no, so the requested count was silently
ignored. This endpoint returns result code 31 for the project's configured
KIPRIS key (see README / issue #9), so this only covers the wiring fix.
"""

import pandas as pd
import pytest

from mcp_kipris.kipris.tools.korean.trademark_search_tool import TrademarkSearchTool

pytestmark = pytest.mark.unit


def _mock_response(total_count=1):
    df = pd.DataFrame(
        [
            {
                "ApplicationNumber": "4020230000001",
                "ApplicationDate": "20230101",
                "TrademarkName": "테스트상표",
                "Applicant": "삼성전자",
            }
        ]
    )
    df.attrs["total_count"] = total_count
    return df


def test_run_tool_sends_num_of_rows_and_page_no_not_docs_count(monkeypatch):
    tool = TrademarkSearchTool()
    captured = {}

    def _fake_sync_search(**kwargs):
        captured.update(kwargs)
        return _mock_response()

    monkeypatch.setattr(tool.api, "sync_search", _fake_sync_search)

    tool.run_tool({"word": "삼성", "docs_count": 5, "docs_start": 1})

    assert captured["num_of_rows"] == 5
    assert captured["page_no"] == 1
    assert "docs_count" not in captured
    assert "docs_start" not in captured


def test_run_tool_reports_total_count_from_response_attrs(monkeypatch):
    tool = TrademarkSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _mock_response(total_count=7))

    text = tool.run_tool({"word": "삼성"})[0].text

    assert "7건" in text
