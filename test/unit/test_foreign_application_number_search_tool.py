"""Mocked unit tests for ForeignPatentApplicationNumberSearchTool.

Same totalCount caveat as test_foreign_applicant_search_tool.py -- see that
file's module docstring.
"""

import pandas as pd
import pytest

from mcp_kipris.kipris.tools.foreign.application_number_search_tool import ForeignPatentApplicationNumberSearchTool

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
    tool = ForeignPatentApplicationNumberSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _sample_response())

    text = tool.run_tool({"application_number": "US12345", "current_page": 3})[0].text

    assert "totalCount를 제공하지 않아" in text
    assert "페이지: 3" in text


def test_run_tool_empty_result_also_shows_the_note(monkeypatch):
    tool = ForeignPatentApplicationNumberSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: pd.DataFrame())

    text = tool.run_tool({"application_number": "US00000"})[0].text

    assert "totalCount를 제공하지 않아" in text
