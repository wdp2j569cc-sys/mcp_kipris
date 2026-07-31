"""Regression tests guarding tool registration parity between server.py and
sse_server.py. mcp_kipris previously shipped with sse_server.py missing four
tools that server.py registered, silently making them unreachable over
HTTP/SSE. See CLAUDE.md's "Adding a New Tool" checklist, which requires
registering every tool in both entry points.
"""

import pytest

pytestmark = pytest.mark.unit


def _import_handlers(module_path):
    import importlib

    module = importlib.import_module(module_path)
    return module.tool_handlers


def test_stdio_and_sse_servers_register_the_same_tools():
    stdio_handlers = _import_handlers("mcp_kipris.server")
    sse_handlers = _import_handlers("mcp_kipris.sse_server")

    assert set(stdio_handlers.keys()) == set(sse_handlers.keys())


def test_stdio_server_registers_at_least_the_known_tool_set():
    stdio_handlers = _import_handlers("mcp_kipris.server")

    expected_minimum = {
        "patent_applicant_search",
        "patent_search",  # deprecated alias of patent_advanced_search, kept for backward compatibility
        "patent_advanced_search",
        "patent_righter_search",
        "patent_application_number_search",
        "patent_summary_search",
        "patent_detail_search",
        "patent_free_search",
        "abstract_search",
        "ipc_search",
        "agent_search",
        "trademark_search",
        "foreign_patent_applicant_search",
        "foreign_patent_application_number_search",
        "foreign_patent_free_search",
        "foreign_international_application_number_search",
        "foreign_international_open_number_search",
    }

    assert expected_minimum.issubset(stdio_handlers.keys())


def test_every_registered_tool_has_a_well_formed_description():
    stdio_handlers = _import_handlers("mcp_kipris.server")

    for name, handler in stdio_handlers.items():
        tool = handler.get_tool_description()
        assert tool.name == name
        assert tool.description
        assert tool.inputSchema.get("type") == "object"
        assert "properties" in tool.inputSchema
