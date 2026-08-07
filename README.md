# MCP KIPRIS

[![smithery badge](https://smithery.ai/badge/greennuri/mcp-kipris)](https://smithery.ai/servers/greennuri/mcp-kipris)
[![Test](https://github.com/nuri428/mcp_kipris/actions/workflows/test.yml/badge.svg)](https://github.com/nuri428/mcp_kipris/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/nuri428/mcp_kipris/branch/main/graph/badge.svg)](https://codecov.io/gh/nuri428/mcp_kipris)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**English** | [한국어 →](README.ko.md)

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that gives AI assistants like Claude direct access to **KIPRIS** — South Korea's official patent and trademark database operated by the Korean Intellectual Property Office (KIPO).

---

## Why KIPRIS?

South Korea is one of the **top 5 patent-filing countries** in the world. Companies like Samsung, LG, SK Hynix, Hyundai, and POSCO file tens of thousands of patents every year — all searchable through KIPRIS.

This MCP server lets Claude (or any MCP-compatible AI client) search those patents in natural language, without the user needing to navigate the Korean-language KIPRIS web portal.

**Typical use cases:**
- Prior art search before filing a patent
- Competitive intelligence on Korean technology companies
- Monitoring IPC classifications in a specific technical domain
- Trademark clearance for the Korean market

---

## Quick Start

> **Prerequisites:** Python 3.11+, a free [KIPRIS API key](#getting-a-kipris-api-key)

```bash
# 1. Clone and install
git clone https://github.com/nuri428/mcp_kipris.git
cd mcp_kipris
pip install -e .

# 2. Set your API key
export KIPRIS_API_KEY="your_api_key_here"

# 3. Run the server (stdio mode for Claude Desktop)
python -m mcp_kipris.server
```

Then add the server to Claude Desktop — see [Claude Desktop Configuration](#claude-desktop-configuration).

---

## Getting a KIPRIS API Key

1. Go to [https://plus.kipris.or.kr](https://plus.kipris.or.kr) *(site is in Korean — use a browser translator)*
2. Register for a free account
3. Apply for an Open API key from the developer portal
4. Your key is free for non-commercial use with a daily request quota

---

## Rate Limiting

Outgoing requests to KIPRIS are throttled by an in-process rate limiter capped at **60 requests per minute** (the default in `RateLimiter`, `src/mcp_kipris/kipris/rate_limiter.py`). When the cap is hit, a request waits and retries automatically instead of failing — no action needed on your end. This limit is not currently configurable via an environment variable.

This only governs how fast *this server* calls KIPRIS; it's separate from your API key's own daily request quota on the KIPRIS developer portal.

---

## Features

### Korean Patent Search
| Tool | Description |
|------|-------------|
| `patent_applicant_search` | Search patents by applicant name |
| `patent_free_search` | Free-text keyword search |
| `patent_application_number_search` | Search by application number |
| `patent_righter_search` | Search by rights holder name |
| `patent_detail_search` | Retrieve patent details by application number. Supports a `fields` parameter to pick any combination of ~65 available fields (bibliography, IPC, abstract, claims, applicant/inventor/agent, priority, legal status, R&D funding, ...); omit it for a short default summary |
| `patent_summary_search` | Retrieve patent summary by application number |
| `abstract_search` | Search by abstract / invention summary — *contributed by [@haseo-ai](https://github.com/haseo-ai)* |
| `ipc_search` | Search by IPC classification code — *contributed by [@haseo-ai](https://github.com/haseo-ai)* |
| `agent_search` | Search by patent agent name — *contributed by [@haseo-ai](https://github.com/haseo-ai)* |
| `patent_advanced_search` | Search by application number via KIPRIS's advanced-search service (a different KIPRIS endpoint than `patent_application_number_search`) |
| `patent_search` | ⚠️ **Deprecated** — renamed to `patent_advanced_search`. Kept for backward compatibility; scheduled for removal in a future major version. |

### Trademark Search
| Tool | Description |
|------|-------------|
| `trademark_search` | Search Korean trademarks by keyword — *contributed by [@haseo-ai](https://github.com/haseo-ai)* |

### International Patent Search

Search patents from 13 countries via KIPRIS's international database:

| Tool | Description |
|------|-------------|
| `foreign_patent_applicant_search` | Search foreign patents by applicant |
| `foreign_patent_application_number_search` | Search foreign patents by application number |
| `foreign_patent_free_search` | Free-text search for foreign patents |
| `foreign_international_application_number_search` | Search by PCT international application number |
| `foreign_international_open_number_search` | Search by international publication number |

---

## Installation

### Option 1: Via Smithery (easiest — no local setup required)

Install directly through the [Smithery marketplace](https://smithery.ai/servers/greennuri/mcp-kipris). Smithery handles the setup and prompts you for your KIPRIS API key:

```bash
npx @smithery/cli@latest mcp add greennuri/mcp-kipris
```

Or visit **[smithery.ai/servers/greennuri/mcp-kipris](https://smithery.ai/servers/greennuri/mcp-kipris)** and click **Install**.

### Option 2: From PyPI

```bash
pip install mcp-kipris
```

### Option 3: From Source (development)

```bash
git clone https://github.com/nuri428/mcp_kipris.git
cd mcp_kipris

# Option A — using uv (recommended)
pip install uv
uv sync

# Option B — using pip
pip install -e .
```

### Environment Configuration

```bash
# Shell export (session-scoped)
export KIPRIS_API_KEY="your_api_key_here"

# Or create a .env file at the project root
echo 'KIPRIS_API_KEY=your_api_key_here' > .env
```

---

## Running the Server

### stdio mode — for Claude Desktop and most MCP clients

```bash
# via uv
uv run python -m mcp_kipris.server

# via python directly (if installed with pip install -e .)
python -m mcp_kipris.server
```

### HTTP / SSE mode — for web-based MCP clients

```bash
uv run python -m mcp_kipris.sse_server --http --port 6274 --host 0.0.0.0
```

### Via mcpo proxy (stdio → HTTP bridge)

```bash
uvx mcpo --port 6274 -- uv run python -m mcp_kipris.server
```

### Docker

```bash
bash sse_server_build.sh
```

---

## Claude Desktop Configuration

Add this block to your Claude Desktop `claude_desktop_config.json`
(usually at `~/Library/Application Support/Claude/` on macOS):

```json
{
  "mcpServers": {
    "kipris": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_kipris.server"],
      "cwd": "/absolute/path/to/mcp_kipris",
      "env": {
        "KIPRIS_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

![Claude Settings](assets/Claude-settings.png)

---

## Testing

### Run the Test Suite

`test/` has two kinds of tests:

- **`test/unit/`** — fully mocked, no network access, no `KIPRIS_API_KEY` required. Marked `pytest.mark.unit`.
- **Root-level `test_*.py`** — call the live KIPRIS API and require a valid `KIPRIS_API_KEY`. The one pytest-discoverable case is marked `pytest.mark.integration`; the rest are standalone demo scripts guarded by `if __name__ == "__main__":`.

```bash
# Install
uv sync --group dev

# Unit tests only — fast, no API key needed
pytest test/unit -v

# Everything except the live-API integration test
pytest test/ -m "not integration" -v

# Full suite with coverage (what CI runs — needs KIPRIS_API_KEY)
pytest test/ -v --cov=src/mcp_kipris --cov-report=term-missing
```

Individual demo scripts can also be run directly:

```bash
python test/test_samsung_patents.py
python test/test_patent_keyword_search.py
```

### Lint and Format

```bash
ruff check src/
ruff format src/
```

### Distribution Testing

Before tagging a release, verify the package builds and installs cleanly:

```bash
# 1. Build wheel and sdist
pip install build
python -m build

# 2. Smoke-test the wheel in a clean virtualenv
python -m venv /tmp/kipris-smoke
source /tmp/kipris-smoke/bin/activate
pip install dist/mcp_kipris-*.whl
python -c "import mcp_kipris; print('import OK')"
deactivate
rm -rf /tmp/kipris-smoke

# 3. Verify editable install still works
pip install -e .
pytest test/ -v
```

### CI Matrix

Every push and pull request to `main` / `develop` runs the full pipeline on **Python 3.11 and 3.12**:

| Step | Tool | Notes |
|------|------|-------|
| Lint | `ruff check` | PEP 8 + style rules |
| Format | `ruff format --check` | Enforces consistent formatting |
| Test | `pytest` | Mostly mocked unit tests, plus one live-API integration test; requires `KIPRIS_API_KEY` secret |
| Coverage | Codecov | Report uploaded from Python 3.12 run |

---

## API Usage Examples

These examples use the HTTP/SSE server mode. First, get a session ID:

```bash
# Start the SSE server
uv run python -m mcp_kipris.sse_server --http --port 6274 --host 0.0.0.0

# Get a session ID
curl -N http://localhost:6274/messages/
# → event: endpoint
# → data: /messages/?session_id=<SESSION_ID>
```

### Search patents by applicant — Samsung Electronics

```bash
# "삼성전자" is the Korean name for Samsung Electronics
curl -X POST "http://localhost:6274/messages/?session_id=<SESSION_ID>" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "tool",
    "name": "patent_applicant_search",
    "args": {
      "applicant": "삼성전자",
      "docs_count": 5,
      "desc_sort": true
    }
  }'
```

### List all available tools

```bash
curl http://localhost:6274/tools | jq .
```

### Response Format

All tools return a Markdown table wrapped in this envelope:

```json
[
  {
    "type": "text",
    "text": "| application_number | title | applicant | ...\n|---|---|---|...",
    "metadata": null
  }
]
```

---

## Reference

### Supported Country Codes (International Search)

| Code | Country / Database |
|------|-------------------|
| US | United States |
| EP | European Patent Office |
| WO | PCT / WIPO |
| JP | Japan |
| PJ | Japan (English abstract) |
| CP | China |
| CN | China (English abstract) |
| TW | Taiwan (English abstract) |
| RU | Russia |
| CO | Colombia |
| SE | Sweden |
| ES | Spain |
| IL | Israel |

### Sort Options

| Code | Sort by |
|------|---------|
| PD | Publication date |
| AD | Application date |
| GD | Registration date |
| OPD | Laid-open date |
| FD | International application date |
| FOD | International publication date |
| RD | Priority claim date |

### Patent Status Codes

| Code | Status |
|------|--------|
| A | Published |
| C | Corrected publication |
| F | Granted |
| G | Corrected grant |
| I | Invalidated |
| J | Cancelled |
| R | Re-published |

---

## ClaudeWork Skill

If you use [ClaudeWork](https://claudework.io), this server is also packaged as a ready-to-use skill:

[kipris_skill →](https://github.com/nuri428/kipris_skill)

---

## Known Limitations

All 17 tools were exercised against the live KIPRIS API. 16 of them were verified beyond "returns well-formed output" — their output *field values* were cross-checked, not just their shape:

- **`ipc_search`, `abstract_search`, `agent_search`, `patent_free_search`, `trademark_search`** had a parameter-name mismatch — the tool called its API layer with `docs_count`/`docs_start`, but those methods actually take `num_of_rows`/`page_no`, so the mismatched kwargs went out as query params KIPRIS ignores and the requested count never took effect. Fixed and confirmed live for the first four (requesting N results now returns exactly N); `patent_free_search`'s endpoint turned out to ignore the row-count parameter server-side regardless, so it now trims to N client-side and says so. `trademark_search` got the same fix applied but — see below — couldn't be confirmed live.
- KIPRIS-reported total match counts (`totalCount`) are shown where the endpoint actually provides one (`ipc/abstract/agent_search`, and `trademark_search` once verifiable); the other 9 paginated tools (`patent_applicant_search`, `patent_application_number_search`, `patent_free_search`, `patent_righter_search`, and the 5 foreign tools) call KIPRIS endpoints that never report a total at all, so they now explicitly say so rather than presenting the row count as if it were one.
- Field mappings were spot-checked against a real registered patent (`patent_detail_search`'s 40-field response, cross-referenced against KIPRIS's raw XML) and against each other: `patent_applicant_search`'s publication date/number, and results from `patent_application_number_search`, `patent_righter_search`, and `patent_free_search`, were each re-queried through `patent_detail_search` for the same application and matched exactly; the 5 foreign tools were cross-checked against each other (an applicant-search result looked up again by application number, then by its international application/open number) and returned the same record every time.
- **`patent_righter_search`, `patent_advanced_search`/`patent_search`, and 3 of the 5 foreign tools** (`foreign_patent_applicant_search`, `foreign_international_application_number_search`, `foreign_international_open_number_search`) used to crash at the MCP protocol level on a validation error (a missing required field, an invalid enum value) instead of returning the normal `"입력값 검증 오류: ..."` text every other tool gives — two had no `try`/`except` around `run_tool()` at all, and the other three re-raised from inside their own `except ValidationError` block, which escapes just as completely as not having one. Confirmed live through the actual `server.call_tool()` path both before and after the fix. All 17 tools are now covered by a regression test that calls each with no arguments and asserts none of them raise.

The one tool still unverified:

- **`trademark_search`** — every query against this project's KIPRIS API key returns result code 31 (`DEADLINE_EXPIRED`), regardless of the search term. This looks like the key isn't authorized for `trademarkInfoSearchService` specifically (KIPRIS approves some services separately from general patent search), not a bug in this server — but it also means the parameter-name fix above, and the tool's actual output, still haven't been confirmed against a working key.

Tracking issue: [#9 — trademark_search verification needed](https://github.com/nuri428/mcp_kipris/issues/9). If you have a KIPRIS API key with trademark search access and can share a raw XML response (success or error), please comment there — we'll use it to verify/fix this tool.

---

## Roadmap

- **MCP spec 2026-07-28 upgrade** — the [MCP specification](https://modelcontextprotocol.io/specification/2026-07-28/changelog) released 2026-07-28 is a major protocol redesign (stateless sessions, `server/discover`, Streamable HTTP as the only non-deprecated HTTP transport, deprecation of Roots/Sampling/Logging). This server currently pins `mcp[cli]>=1.6.0` (resolved to `1.9.4`), which predates that revision. We'll upgrade once the `mcp` Python SDK ships support for it, and migrate `sse_server.py` off the legacy HTTP+SSE transport (`SseServerTransport`) to Streamable HTTP at the same time.

---

## Contributing

See [DEVELOPMENT.md](DEVELOPMENT.md) for the full developer guide and CI/CD setup.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'feat: add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

**Before submitting:**
```bash
ruff check src/   # lint
ruff format src/  # format
pytest test/      # tests (requires KIPRIS_API_KEY)
```

The `KIPRIS_API_KEY` for CI is stored as a GitHub Secret — you do not need to commit it.

---

## Acknowledgements

Special thanks to **[@haseo-ai](https://github.com/haseo-ai)** for 5 pull requests that significantly expanded this project:

- **Abstract search** (`AbstractSearchTool`) — search patents by invention abstract
- **IPC code search** (`IpcSearchTool`) — search by international classification code
- **Agent search** (`AgentSearchTool`) — search by registered patent agent name
- **Trademark search** (`TrademarkSearchTool`) — Korean trademark keyword search
- **Improved API error handling** — more robust error management for KIPRIS API responses

---

## License

[MIT License](LICENSE)
