"""agent_search wiring regression tests -- same bug class as ipc_search
(see test_ipc_search_tool.py): run_tool called sync_search(docs_count=...,
docs_start=...) but AgentSearchAPI.sync_search's real parameters are
num_of_rows/page_no, so the requested count was silently ignored.
"""

import pandas as pd
import pytest

from mcp_kipris.kipris.tools.korean.agent_search_tool import AgentSearchTool

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
    tool = AgentSearchTool()
    captured = {}

    def _fake_sync_search(**kwargs):
        captured.update(kwargs)
        return _mock_response()

    monkeypatch.setattr(tool.api, "sync_search", _fake_sync_search)

    tool.run_tool({"agent": "김", "docs_count": 5, "docs_start": 1})

    assert captured["num_of_rows"] == 5
    assert captured["page_no"] == 1
    assert "docs_count" not in captured
    assert "docs_start" not in captured


def test_run_tool_reports_total_count_from_response_attrs(monkeypatch):
    tool = AgentSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _mock_response(total_count=1168676))

    text = tool.run_tool({"agent": "김"})[0].text

    assert "1168676건" in text


def test_summary_columns_default_to_empty_when_kipris_omits_them(monkeypatch):
    tool = AgentSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _mock_response())

    result = tool.run_tool({"agent": "김"})

    assert "오류" not in result[0].text
    assert "1020230000001" in result[0].text
