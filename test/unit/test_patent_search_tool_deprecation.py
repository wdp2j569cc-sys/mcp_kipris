"""patent_search was renamed to patent_advanced_search (it wraps KIPRIS's
getAdvancedSearch service, a different endpoint from
patent_application_number_search). The old name is kept registered as a
PatentAdvancedSearchTool subclass for backward compatibility, deprecated at
every layer a consumer might check: a Python DeprecationWarning, the MCP
tool description text, and the tool's metadata. Both tools normalize their
output to the same PascalCase columns so results look consistent regardless
of which one answered.
"""

import pandas as pd
import pytest

from mcp_kipris.kipris.tools.korean.patent_search_tool import (
    PatentAdvancedSearchTool,
    PatentSearchTool,
)

pytestmark = pytest.mark.unit

_RAW_SAMPLE = pd.DataFrame(
    [
        {
            "applicationNumber": "1020230000001",
            "applicationDate": "20230101",
            "inventionTitle": "테스트 발명",
            "applicantName": "삼성전자",
            "registerStatus": "등록",
        }
    ]
)


def test_advanced_search_tool_is_not_deprecated():
    tool = PatentAdvancedSearchTool().get_tool_description()

    assert "DEPRECATED" not in tool.description
    assert not (tool.metadata or {}).get("deprecated")


def test_advanced_search_tool_normalizes_output_columns(monkeypatch):
    tool = PatentAdvancedSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _RAW_SAMPLE)

    result = tool.run_tool({"application_number": "1020230000001"})

    text = result[0].text
    assert "ApplicationNumber" in text
    assert "InventionName" in text
    assert "Applicant" in text
    assert "삼성전자" in text


def test_legacy_tool_instantiation_emits_deprecation_warning():
    with pytest.warns(DeprecationWarning, match="patent_advanced_search"):
        PatentSearchTool()


def test_legacy_tool_description_flags_deprecation():
    tool = PatentSearchTool().get_tool_description()

    assert "DEPRECATED" in tool.description
    assert tool.metadata["deprecated"] is True
    assert tool.metadata["replacement_tool"] == "patent_advanced_search"


def test_legacy_tool_still_works_for_backward_compatibility(monkeypatch):
    tool = PatentSearchTool()
    monkeypatch.setattr(tool.api, "sync_search", lambda **kwargs: _RAW_SAMPLE)

    result = tool.run_tool({"application_number": "1020230000001"})

    assert "삼성전자" in result[0].text


def test_legacy_and_advanced_tools_produce_the_same_output_shape(monkeypatch):
    advanced = PatentAdvancedSearchTool()
    monkeypatch.setattr(advanced.api, "sync_search", lambda **kwargs: _RAW_SAMPLE)
    legacy = PatentSearchTool()
    monkeypatch.setattr(legacy.api, "sync_search", lambda **kwargs: _RAW_SAMPLE)

    advanced_text = advanced.run_tool({"application_number": "1020230000001"})[0].text
    legacy_text = legacy.run_tool({"application_number": "1020230000001"})[0].text

    assert advanced_text == legacy_text
