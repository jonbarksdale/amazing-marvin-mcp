# Amazing Marvin MCP Server — Design Document

## Executive Summary

A Python MCP server exposing 12 intent-oriented tools for managing tasks, projects, events, and time tracking in Amazing Marvin. Designed for use with Claude Code and Claude Desktop via STDIO transport. Prioritizes context efficiency (trimmed markdown responses), minimal tool count, and internal name resolution to reduce LLM call chains.

## Purpose

Provide a portable, structured interface between LLMs and Amazing Marvin that covers daily task management workflows without the bloat of existing solutions (47 tools) or the gaps of minimal ones (no update/delete/calendar).

## Problem Statement

Existing Amazing Marvin MCP servers fall into two camps:
- **Too many tools** (logical-luke, 47 tools): bloats LLM context, returns raw untrimmed JSON
- **Too few tools** (lucadeleo, 9 tools): good formatting but lacks update, delete, calendar, time tracking

We need a middle ground: ~12 focused tools with rich formatting and smart internal logic.

## Requirements

1. **Portability** — works in any MCP-compatible client (Claude Code, Claude Desktop)
2. **Context efficiency** — markdown output, 25K char limit, notes trimmed to 500 chars
3. **Intent-oriented** — tools resolve names internally, don't require callers to chain lookups
4. **Security** — API token only in headers to amazingmarvin.com over HTTPS, never logged
5. **Rate limiting** — 1s between mutations, 3s between queries, matching Marvin's documented limits
6. **Testable** — unit, integration, and E2E tests against real API

## Architecture

### Project Structure

```
amazing-marvin-mcp/
├── pyproject.toml
├── src/
│   └── amazing_marvin_mcp/
│       ├── __init__.py
│       ├── server.py        # Thin MCP adapter — tool registration, delegates to marvin
│       ├── client.py        # HTTP client — auth, rate limiting, raw API calls
│       ├── marvin.py        # Business logic — name resolution, caching, smart operations
│       └── formatting.py    # Response trimming, markdown conversion
└── tests/
    ├── conftest.py
    ├── test_client.py
    ├── test_marvin.py
    ├── test_formatting.py
    └── test_server.py
```

### Layer Responsibilities

```
server.py  →  marvin.py  →  client.py  →  Amazing Marvin API
(MCP)         (logic)       (HTTP)
```

- **`client.py`**: Raw API calls, auth headers, rate limiting. No business logic.
- **`marvin.py`**: Intent-oriented operations — name→ID resolution, category caching, timezone detection, fuzzy search. Importable by any consumer (MCP server, future CLI, library).
- **`server.py`**: Thin MCP adapter — registers tools, parses inputs, calls `marvin.py`, formats output via `formatting.py`. No business logic.
- **`formatting.py`**: Markdown conversion, response trimming. Used by `server.py` and any future consumer that wants formatted output.

This layering means a future CLI or library imports `marvin.py` and `formatting.py` directly, without any MCP dependency.

### Toolchain

| Category | Tool |
|----------|------|
| Package Manager | uv |
| Linting/Formatting | ruff |
| Type Checking | mypy (strict) |
| Testing | pytest + pytest-cov |
| HTTP Client | httpx (async) |
| MCP SDK | mcp |

### Authentication

Single environment variable: `MARVIN_API_TOKEN` (full-access token).

Sent as `X-Full-Access-Token` header only. The API rejects requests that include `X-API-Token` with a full-access token value — sending both headers causes auth failure. The full-access token covers all endpoints including `/doc/update`, `/doc/create`, `/doc/delete`, and `/doc`.

Token is read once at startup, never logged at any level.

### Rate Limiting

Built into `MarvinClient` using `asyncio` timestamps:
- Minimum 1 second between create/mutate calls
- Minimum 3 seconds between read/query calls
- `await asyncio.sleep(remaining)` if a request arrives too fast
- Marvin's daily limit: 1,440 queries (tracked but not enforced — hitting it is unlikely in normal use)

### Response Formatting

- **Format**: Markdown (not raw JSON)
- **Character limit**: 25,000 characters per response
- **Truncation**: Cut at nearest newline, append `[truncated — use filters to narrow results]`
- **Notes trimming**: Task notes capped at 500 characters with `[...]`
- **IDs always included**: Every item in output includes its ID so follow-up actions don't need lookups

### Category/Label Caching

`MarvinClient` caches `/categories` and `/labels` responses in memory (they change rarely). Cache is refreshed:
- On first access
- When a create/update/delete operation might invalidate it
- On explicit request

This avoids redundant API calls when tools like `create_task` or `search` need to resolve names to IDs.

## Tool Set (12 Tools)

### Read Tools

| Tool | Intent | API Calls |
|---|---|---|
| `get_today` | "What's on my plate today?" | `GET /todayItems` |
| `get_due` | "What's overdue?" | `GET /dueItems` |
| `get_categories` | "Show my project/folder structure" | `GET /categories` |
| `get_children` | "What's inside this project?" (accepts name or ID) | `GET /categories` (if name) → `GET /children` |
| `get_labels` | "What labels do I have?" | `GET /labels` |
| `get_time_blocks` | "What's my schedule?" | `GET /todayTimeBlocks` |
| `search` | "What's next on my transition project?" | `GET /categories` + `GET /children` (fuzzy match query against names) |

### Write Tools

| Tool | Intent | API Calls |
|---|---|---|
| `create_task` | "Add X to project Y, due Friday" | `GET /categories` (resolve name) → `POST /addTask` |
| `create_event` | "Block 9:30-10am for standup" | `POST /addEvent` |
| `update_task` | "Reschedule X to Monday" / "Rename X" | `POST /doc/update` |
| `mark_done` | "I finished X" (auto timezone detection) | `POST /markDone` |
| `delete_task` | "Remove X" | `POST /doc/delete` |
| `track_time` | "Start/stop tracking X" | `POST /track` |

### Design Principles

1. **Intent-oriented, not API-mirror** — tools map to user goals, not endpoints
2. **Internal resolution** — `create_task` accepts project name, resolves to ID internally
3. **Auto timezone** — `mark_done` detects system timezone, no user input needed
4. **Rich output** — all list responses include IDs for follow-up actions
5. **Flexible input** — `create_event` accepts human-friendly times ("9:30am"), not just ISO timestamps

## MCP Prompts

Two workflow prompts shipped with the server:

| Prompt | Purpose |
|---|---|
| `plan_my_day` | Calls `get_today` + `get_due` + `get_time_blocks`, suggests a schedule |
| `weekly_review` | Reviews overdue items, suggests reschedule or mark done |

## Error Handling

`MarvinClient` maps HTTP status codes to clear messages:
- 401 → "Invalid API token. Check MARVIN_API_TOKEN."
- 403 → "Insufficient permissions. This endpoint requires a full-access token."
- 404 → "Item not found."
- 429 → "Rate limited by Amazing Marvin. Try again shortly."
- 5xx → "Amazing Marvin server error. Try again later."

Connection failures return a clear "Cannot reach Amazing Marvin API" message.

## Future Considerations

- **Claude Code plugin layer**: Skills and commands can be added in a `plugin/` directory to provide richer workflow guidance on top of the MCP tools
- **`get_unfinished` tool**: If auto-rollover doesn't fully cover past scheduled tasks, add a tool that queries `/todayItems` across a date range
- **Spotlight strategy**: Currently app-only; add API support if/when Amazing Marvin exposes it
