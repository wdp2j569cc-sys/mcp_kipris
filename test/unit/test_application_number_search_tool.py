"""Mocked unit tests for PatentApplicationNumberSearchTool.

applicationNumberSearchInfo (the legacy openapi/rest service family) has no
response.count block -- confirmed live -- so, unlike ipc/abstract/
agent_search, this tool must not present a fabricated total count. An
earlier version echoed len(response) back as "총 검색결과: N건", which
looked like a real total but was really just "however many rows came back
this time" (capped at docs_count); these tests guard against regressing to
that.
"""

import pandas as pd
import pytest

from mcp_kipris.kipris.tools.korean.application_number_search_tool import PatentApplicationNumberSearchTool

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
    tool = PatentApplicationNumberSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _sample_response())

    result = tool.run_tool({"application_number": "1020230000001"})

    assert "삼성전자" in result[0].text
    assert "1020230000001" in result[0].text


def test_run_tool_reports_empty_result(monkeypatch):
    tool = PatentApplicationNumberSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: pd.DataFrame())

    result = tool.run_tool({"application_number": "0000000000000"})

    assert "there is no result" in result[0].text


def test_run_tool_does_not_claim_a_total_count(monkeypatch):
    tool = PatentApplicationNumberSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _sample_response())

    text = tool.run_tool({"application_number": "1020230000001"})[0].text

    assert "총 검색결과" not in text
    assert "totalCount를 제공하지 않아" in text


@pytest.mark.asyncio
async def test_run_tool_async_does_not_claim_a_total_count(monkeypatch):
    tool = PatentApplicationNumberSearchTool()

    async def _fake_async_search(**kwargs):
        return _sample_response()

    monkeypatch.setattr(tool.api, "async_search", _fake_async_search)

    text = (await tool.run_tool_async({"application_number": "1020230000001"}))[0].text

    assert "총 검색결과" not in text
    assert "totalCount를 제공하지 않아" in text
