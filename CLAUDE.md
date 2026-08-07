# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP KIPRIS is a Model Context Protocol (MCP) server that wraps the Korean Intellectual Property Rights Information Service (KIPRIS) API, enabling AI assistants like Claude to search Korean and foreign patents.

## Environment Setup

```bash
# Required environment variable
export KIPRIS_API_KEY="your_api_key"

# Install dependencies (uses uv)
pip install -e .
# or
uv sync
```

Python 3.11+ required. The project uses `uv` for dependency management and `ruff` for formatting/linting.

## Running the Server

```bash
# stdio mode (for MCP clients like Claude Desktop)
uv run python -m mcp_kipris.server

# HTTP/SSE mode
uv run python -m mcp_kipris.sse_server --http --port 6274 --host 0.0.0.0

# Via mcpo proxy (stdio → HTTP bridge)
uvx mcpo --port 6274 -- uv run python -m mcp_kipris.server

# Docker SSE server
bash sse_server_build.sh
```

## Running Tests

`test/unit/` is fully mocked (no network access, no `KIPRIS_API_KEY` required). The rest of `test/` makes live API calls and requires a valid `KIPRIS_API_KEY`.

```bash
# Mocked unit tests only — no API key needed
pytest test/unit -v

# Everything except live-API integration tests
pytest test/ -m "not integration" -v

# Full suite with coverage (what CI runs — needs KIPRIS_API_KEY)
pytest test/ -v --cov=src/mcp_kipris --cov-report=term-missing
```

## Linting and Formatting

```bash
ruff check src/
ruff format src/
```

## Architecture

### Two-Layer Design

Each tool follows a two-layer pattern:

1. **API layer** (`src/mcp_kipris/kipris/api/`): Calls the KIPRIS HTTP API and parses XML responses into `pd.DataFrame`. All API classes extend `ABSKiprisAPI` which handles URL construction, `accessKey` injection, and async/sync call dispatch. Params are auto-converted to camelCase via `stringcase`.

2. **Tool layer** (`src/mcp_kipris/kipris/tools/`): Wraps the API layer as MCP tools. Each tool extends `ToolHandler` (`kipris/abc.py`) and must implement:
   - `get_tool_description()` → returns `mcp.types.Tool` with name, description, inputSchema, and metadata
   - `run_tool(args)` → sync execution, returns `Sequence[TextContent | ...]`
   - `run_tool_async(args)` → optional async execution using `asyncio.to_thread()`, preferred by the server when present. `ToolHandler` does not declare this method itself — `call_tool` calls it via duck typing and falls back to `run_tool` on `AttributeError`/`NotImplementedError`.

3. **Cross-cutting utilities** (`src/mcp_kipris/kipris/`): `rate_limiter.py` (token-bucket rate limiting for KIPRIS requests), `errors.py` (`KiprisApiError` / `KiprisErrorCode` structured exceptions), `logging_utils.py` (redacts sensitive data such as API keys from log output).

### Server Modes

- **`server.py`**: stdio-only MCP server using `mcp.server.stdio`
- **`sse_server.py`**: Starlette app supporting both SSE (`/sse`) and HTTP POST (`/messages/`) transports, plus a `/tools` JSON endpoint and `/.well-known/mcp` discovery endpoint. Uses uvicorn.

Both servers register all tool handlers at module-level into a `tool_handlers` dict. The `call_tool` handler tries `run_tool_async` first, falling back to `run_tool`.

### Tool Organization

```
kipris/tools/
  korean/    # 11 tools: applicant, free, search (advanced + deprecated alias), righter,
             #   application_number, summary, detail, abstract, ipc, agent, trademark
  foreign/   # 5 tools: applicant, application_number, free, international_application_number, international_open_number
```

All tool classes are exported from `kipris/tools/__init__.py` with `Korean*` and `Foreign*` prefixes.

> `trademark_search` (`KoreanTrademarkSearchTool`) currently returns KIPRIS result code 31 (`DEADLINE_EXPIRED`) for every query against this project's API key — the key doesn't appear to be authorized for `trademarkInfoSearchService`. The tool's actual output is unverified against a working key; see [tracking issue #9](https://github.com/nuri428/mcp_kipris/issues/9) before relying on or extending it.

### Adding a New Tool

1. Create an API class in `kipris/api/korean/` or `kipris/api/foreign/` extending `ABSKiprisAPI`
2. Create a tool class in `kipris/tools/korean/` or `kipris/tools/foreign/` extending `ToolHandler`
3. Export from `kipris/tools/__init__.py`
4. Register in both `server.py` and `sse_server.py` with `add_tool_handler()`

### Utility

`src/mcp_kipris/utils/patent_sim.py` contains experimental patent similarity analysis using TF-IDF + cosine similarity and LangChain/Ollama for keyword extraction. This is not registered as an MCP tool.

## Key Conventions

- All tool args are validated with Pydantic models (`BaseModel`) before use
- API responses are parsed into `pd.DataFrame`; tools format them as markdown tables via `.to_markdown()`
- Parameters passed to KIPRIS API use Python snake_case and are auto-converted to camelCase
- The `KIPRIS_API_KEY` env var is loaded via `python-dotenv`; `.env` file can be placed at project root or `src/`
