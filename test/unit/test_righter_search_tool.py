"""Mocked unit tests for PatentRighterSearchTool.

This tool's KIPRIS service (openapi/rest legacy family) has no
response.count block -- confirmed live -- so, unlike ipc/abstract/
agent_search, it must not present a fabricated total count. An earlier
version echoed len(response) back as "총 검색결과: N건", which looked
like a real total but was really just "however many rows came back this
time" (capped at docs_count); these tests guard against regressing to
that.
"""

import pandas as pd
import pytest

from mcp_kipris.kipris.tools.korean.righter_search_tool import PatentRighterSearchTool

pytestmark = pytest.mark.unit


def _sample_response() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ApplicationNumber": "1020230000001",
                "ApplicationDate": "20230101",
                "InventionName": "테스트 발명",
                "RegistrationStatus": "등록",
            }
        ]
    )


def test_run_tool_returns_markdown_table_on_success(monkeypatch):
    tool = PatentRighterSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _sample_response())

    result = tool.run_tool({"righter_name": "삼성전자"})

    assert "1020230000001" in result[0].text


def test_run_tool_returns_text_on_missing_required_field_instead_of_raising():
    """run_tool()/run_tool_async() previously had no try/except at all, so a
    ValidationError (e.g. missing righter_name) propagated all the way out
    to server.call_tool(), which re-raises it as a bare RuntimeError instead
    of the graceful TextContent every other tool returns -- confirmed live
    through the actual server.call_tool() path before this fix.
    """
    tool = PatentRighterSearchTool()

    result = tool.run_tool({})

    assert "검증 오류" in result[0].text


@pytest.mark.asyncio
async def test_run_tool_async_returns_text_on_missing_required_field_instead_of_raising():
    tool = PatentRighterSearchTool()

    result = await tool.run_tool_async({})

    assert "검증 오류" in result[0].text


def test_run_tool_reports_empty_result(monkeypatch):
    tool = PatentRighterSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: pd.DataFrame())

    result = tool.run_tool({"righter_name": "존재하지않는회사"})

    assert "검색 결과가 없습니다" in result[0].text


def test_run_tool_does_not_claim_a_total_count(monkeypatch):
    tool = PatentRighterSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _sample_response())

    text = tool.run_tool({"righter_name": "삼성전자"})[0].text

    assert "총 검색결과" not in text
    assert "totalCount를 제공하지 않아" in text


@pytest.mark.asyncio
async def test_run_tool_async_does_not_claim_a_total_count(monkeypatch):
    tool = PatentRighterSearchTool()

    async def _fake_async_search(**kwargs):
        return _sample_response()

    monkeypatch.setattr(tool.api, "async_search", _fake_async_search)

    text = (await tool.run_tool_async({"righter_name": "삼성전자"}))[0].text

    assert "총 검색결과" not in text
    assert "totalCount를 제공하지 않아" in text
