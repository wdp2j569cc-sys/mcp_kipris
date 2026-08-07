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
