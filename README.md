# Amazing Marvin MCP Server

An MCP server that provides intent-oriented tools for managing tasks, projects, events, and time tracking in [Amazing Marvin](https://amazingmarvin.com). Designed for Claude Code and Claude Desktop.

## Setup

```bash
uv sync
export MARVIN_API_TOKEN='your-full-access-token'
```

Get your full-access token from [app.amazingmarvin.com/pre?api](https://app.amazingmarvin.com/pre?api).

## Usage

### Claude Code

```bash
claude mcp add amazing-marvin -- uv run --directory /path/to/amazing-marvin-mcp amazing-marvin-mcp
```

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "amazing-marvin": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/amazing-marvin-mcp", "amazing-marvin-mcp"],
      "env": {
        "MARVIN_API_TOKEN": "your-full-access-token"
      }
    }
  }
}
```

## Tools (13)

| Tool | Description |
|------|-------------|
| `get_today` | Get tasks and projects scheduled for today |
| `get_due` | Get overdue tasks and projects |
| `get_categories` | Get project and folder structure |
| `get_children` | Get child tasks under a project (accepts name or ID) |
| `get_labels` | Get all labels |
| `get_time_blocks` | Get today's time blocks |
| `search` | Search projects and folders by name |
| `create_task` | Create a task (with optional project, dates, notes) |
| `create_event` | Create a calendar event |
| `update_task` | Update task fields (title, dates, notes) |
| `mark_done` | Mark a task as complete |
| `delete_task` | Delete a task |
| `track_time` | Start or stop time tracking |

## Prompts (2)

| Prompt | Description |
|--------|-------------|
| `plan_my_day` | Review today's tasks, overdue items, and time blocks |
| `weekly_review` | Review overdue items and suggest cleanup |

## Library Usage

`MarvinService` and `MarvinClient` support async context managers for automatic connection cleanup:

```python
from amazing_marvin_mcp.marvin import MarvinService

async with MarvinService(api_token="your-token") as svc:
    tasks = await svc.get_today()
    await svc.create_task(title="New task", parent_name="Work")
```

Without a context manager, call `close()` explicitly to release connections.

## Development

```bash
uv sync
uv run ruff check .
uv run mypy src/
uv run pytest tests/ -v
```

Integration and E2E tests require `MARVIN_API_TOKEN` to be set.

## Architecture

```
server.py  →  marvin.py  →  client.py  →  Amazing Marvin API
(MCP)         (logic)       (HTTP)
```

- **`server.py`**: Thin MCP adapter — registers tools, delegates to business logic
- **`marvin.py`**: Intent-oriented operations — name resolution, caching, timezone detection
- **`client.py`**: Raw HTTP — auth headers, rate limiting, error mapping
- **`formatting.py`**: Markdown conversion and response trimming
