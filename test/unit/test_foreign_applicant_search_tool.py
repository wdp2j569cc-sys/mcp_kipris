"""Mocked unit tests for ForeignPatentApplicantSearchTool.

This tool's KIPRIS service (openapi/rest/ForeignPatentAdvencedSearchService,
shared by all 5 foreign tools) has no response.count block and no
page-size parameter -- confirmed live, it always returns a fixed batch per
current_page -- so it must not claim a total-match count, only report
which page is shown.
"""

import pandas as pd
import pytest

from mcp_kipris.kipris.tools.foreign.applicant_search_tool import ForeignPatentApplicantSearchTool

pytestmark = pytest.mark.unit


def _sample_response() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "applicationNo": "US12345",
                "applicationDate": "20230101",
                "inventionName": "Test Invention",
                "applicant": "Samsung",
            }
        ]
    )


def test_run_tool_shows_no_total_count_note(monkeypatch):
    tool = ForeignPatentApplicantSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _sample_response())

    text = tool.run_tool({"applicant": "Samsung", "current_page": 2})[0].text

    assert "totalCount를 제공하지 않아" in text
    assert "페이지: 2" in text
    assert "Samsung" in text


def test_run_tool_empty_result_also_shows_the_note(monkeypatch):
    tool = ForeignPatentApplicantSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: pd.DataFrame())

    text = tool.run_tool({"applicant": "존재하지않는회사"})[0].text

    assert "totalCount를 제공하지 않아" in text


def test_run_tool_returns_text_on_missing_required_field_instead_of_raising():
    """The ValidationError handler used to `raise ValueError(...)` for each
    known field instead of returning a TextContent, which bypassed this
    tool's own try/except entirely and propagated out to server.call_tool()
    as a bare RuntimeError -- confirmed live before this fix.
    """
    tool = ForeignPatentApplicantSearchTool()

    result = tool.run_tool({})

    assert "검증 오류" in result[0].text
    assert "출원인명" in result[0].text


def test_run_tool_returns_text_on_invalid_collection_values():
    tool = ForeignPatentApplicantSearchTool()

    result = tool.run_tool({"applicant": "Samsung", "collection_values": "ZZ"})

    assert "검증 오류" in result[0].text
    assert "국가 코드" in result[0].text
