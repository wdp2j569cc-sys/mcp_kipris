"""Mocked unit tests for ForeignPatentInternationalApplicationNumberSearchTool.

Same totalCount caveat as test_foreign_applicant_search_tool.py -- see that
file's module docstring.
"""

import pandas as pd
import pytest

from mcp_kipris.kipris.tools.foreign.international_application_number_search_tool import (
    ForeignPatentInternationalApplicationNumberSearchTool,
)

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
    tool = ForeignPatentInternationalApplicationNumberSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _sample_response())

    text = tool.run_tool({"international_application_number": "PCT/US2023/000001", "current_page": 2})[0].text

    assert "totalCount를 제공하지 않아" in text
    assert "페이지: 2" in text


def test_run_tool_empty_result_also_shows_the_note(monkeypatch):
    tool = ForeignPatentInternationalApplicationNumberSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: pd.DataFrame())

    text = tool.run_tool({"international_application_number": "PCT/US2023/999999"})[0].text

    assert "totalCount를 제공하지 않아" in text
