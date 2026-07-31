"""Mocked unit tests for PatentApplicantSearchTool. The KIPRIS HTTP layer is
never touched — self.api.sync_search/async_search are monkeypatched with
canned DataFrames so these tests run offline and deterministically.
"""

import pandas as pd
import pytest

from mcp_kipris.kipris.tools.korean.applicant_search_tool import PatentApplicantSearchTool

pytestmark = pytest.mark.unit


def _sample_response() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ApplicationNumber": "1020230000001",
                "ApplicationDate": "20230101",
                "InventionName": "테스트 발명",
                "Applicant": "삼성전자",
            }
        ]
    )


def test_run_tool_returns_markdown_table_on_success(monkeypatch):
    tool = PatentApplicantSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _sample_response())

    result = tool.run_tool({"applicant": "삼성전자"})

    assert len(result) == 1
    assert "삼성전자" in result[0].text
    assert "1020230000001" in result[0].text


def test_run_tool_reports_empty_result(monkeypatch):
    tool = PatentApplicantSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: pd.DataFrame())

    result = tool.run_tool({"applicant": "존재하지않는회사"})

    assert result[0].text == "there is no result"


def test_run_tool_rejects_missing_required_field():
    tool = PatentApplicantSearchTool()

    result = tool.run_tool({})

    assert "검증 오류" in result[0].text


def test_run_tool_wraps_api_exceptions(monkeypatch):
    tool = PatentApplicantSearchTool()

    def _raise(**kwargs):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(tool.api, "sync_search", _raise)

    result = tool.run_tool({"applicant": "삼성전자"})

    assert "오류가 발생했습니다" in result[0].text
    assert "connection reset" in result[0].text


@pytest.mark.asyncio
async def test_run_tool_async_returns_markdown_table_on_success(monkeypatch):
    tool = PatentApplicantSearchTool()

    async def _async_search(**kwargs):
        return _sample_response()

    monkeypatch.setattr(tool.api, "async_search", _async_search)

    result = await tool.run_tool_async({"applicant": "삼성전자"})

    assert "삼성전자" in result[0].text
