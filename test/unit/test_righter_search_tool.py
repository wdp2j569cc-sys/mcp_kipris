"""Mocked unit tests for PatentRighterSearchTool covering the totalCount
header added alongside ipc_search/abstract_search/etc (see
test_ipc_search_tool.py) -- this tool already had docs_count/docs_start
wired correctly, so only the totalCount reporting was missing.
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


def test_run_tool_reports_empty_result(monkeypatch):
    tool = PatentRighterSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: pd.DataFrame())

    result = tool.run_tool({"righter_name": "존재하지않는회사"})

    assert "검색 결과가 없습니다" in result[0].text
    assert "0건" in result[0].text


def test_run_tool_reports_total_count_from_response_attrs(monkeypatch):
    tool = PatentRighterSearchTool()

    def _fake_sync_search(**kwargs):
        df = _sample_response()
        df.attrs["total_count"] = 15
        return df

    monkeypatch.setattr(tool.api, "sync_search", _fake_sync_search)

    text = tool.run_tool({"righter_name": "삼성전자"})[0].text

    assert "15건" in text


@pytest.mark.asyncio
async def test_run_tool_async_reports_total_count_from_response_attrs(monkeypatch):
    tool = PatentRighterSearchTool()

    async def _fake_async_search(**kwargs):
        df = _sample_response()
        df.attrs["total_count"] = 3
        return df

    monkeypatch.setattr(tool.api, "async_search", _fake_async_search)

    text = (await tool.run_tool_async({"righter_name": "삼성전자"}))[0].text

    assert "3건" in text
