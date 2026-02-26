# Block Best Practices Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Apply three best practices from Block's MCP server design playbook: server-level instructions, Literal types for constrained parameters, and date format validation.

**Architecture:** All three changes are in the server adapter layer (`server.py`) and its tests. Task 2 also touches `formatting.py` (the `filter_backburner` signature). Each task is an atomic commit.

**Tech Stack:** Python 3.11+, FastMCP, pytest, ruff, mypy

---

### Task 1: Add server-level instructions to FastMCP

**Files:**
- Modify: `src/amazing_marvin_mcp/server.py:26`
- Modify: `tests/test_server.py` (add test)
- Modify: `tests/test_e2e.py` (add test)

**Step 1: Write the failing unit test**

Add to `tests/test_server.py`:

```python
def test_server_has_instructions(self) -> None:
    assert mcp.instructions is not None
    assert len(mcp.instructions) > 0
```

**Step 2: Run test to verify it fails**

Run: `just check`
Expected: FAIL — `mcp.instructions` is `None`

**Step 3: Add instructions to server.py**

Change line 26 from:
```python
mcp = FastMCP("amazing-marvin")
```
to:
```python
mcp = FastMCP(
    "amazing-marvin",
    instructions=(
        "Amazing Marvin is a personal task manager. "
        "Use get_today for daily planning, get_due for overdue items, "
        "and get_inbox for unassigned tasks. "
        "Use search to find projects by name, then get_children to list their tasks. "
        "The parent parameter on create_task and get_children accepts human-readable "
        "project names — no need to look up IDs first. "
        "Dates use YYYY-MM-DD format. "
        "For time tracking, action must be 'START' or 'STOP'."
    ),
)
```

**Step 4: Run tests to verify they pass**

Run: `just check`
Expected: All PASS

**Step 5: Commit**

```
feat(server): add server-level instructions for LLM guidance

Per Block's MCP playbook, server-level instructions help LLMs
understand the tool ecosystem and common workflows.
```

---

### Task 2: Use Literal types for constrained string parameters

**Files:**
- Modify: `src/amazing_marvin_mcp/server.py` — `backburner` params (lines 106, 126, 138, 170) and `action` param (line 280)
- Modify: `src/amazing_marvin_mcp/formatting.py:62` — `filter_backburner` signature
- Modify: `src/amazing_marvin_mcp/marvin.py` — `backburner` params and `track_time` action param
- Modify: `tests/test_server.py` (add test)

**Step 1: Write the failing test**

Add to `tests/test_server.py`:

```python
def test_backburner_params_use_literal_type(self) -> None:
    """Backburner params should expose allowed values in JSON schema."""
    tools = {t.name: t for t in mcp._tool_manager.list_tools()}
    for name in ("get_due", "get_inbox", "get_children", "search"):
        schema = tools[name].inputSchema
        backburner_prop = schema["properties"]["backburner"]
        # Literal types produce an "enum" key in JSON schema
        assert "enum" in backburner_prop or "anyOf" in backburner_prop, (
            f"{name}: backburner should use Literal type for schema hints"
        )

def test_track_time_action_uses_literal_type(self) -> None:
    """track_time action should expose START/STOP in JSON schema."""
    tools = {t.name: t for t in mcp._tool_manager.list_tools()}
    schema = tools["track_time"].inputSchema
    action_prop = schema["properties"]["action"]
    assert "enum" in action_prop or "anyOf" in action_prop, (
        "track_time: action should use Literal type for schema hints"
    )
```

**Step 2: Run test to verify it fails**

Run: `just check`
Expected: FAIL — current `str | None` produces no `enum` in schema

**Step 3: Update type annotations**

In `server.py`, add to imports:
```python
from typing import Any, Literal
```

Change all `backburner: str | None = None` params in tool functions to:
```python
backburner: Literal["include", "only"] | None = None
```

Change `track_time` `action: str` to:
```python
action: Literal["START", "STOP"]
```

In `formatting.py`, update `filter_backburner` signature:
```python
from typing import Literal

def filter_backburner(
    tasks: list[dict[str, object]], backburner: Literal["include", "only"] | None
) -> list[dict[str, object]]:
```

In `marvin.py`, update all method signatures with `backburner` to use `Literal["include", "only"] | None`, and `track_time` action to `Literal["START", "STOP"]`. Add `Literal` to the typing import.

**Step 4: Run tests to verify they pass**

Run: `just check`
Expected: All PASS

**Step 5: Commit**

```
feat(server): use Literal types for constrained parameters

Backburner and track_time action params now use Literal types,
exposing allowed values in the JSON schema for better LLM hints.
```

---

### Task 3: Add date format validation in the server layer

**Files:**
- Modify: `src/amazing_marvin_mcp/server.py` — add `_validate_date` and `_validate_datetime` helpers, call in `create_task`, `update_task`, `create_event`
- Modify: `tests/test_server.py` (add tests for validation)

**Step 1: Write the failing tests**

Add to `tests/test_server.py` a new class:

```python
import pytest
from amazing_marvin_mcp.server import _validate_date, _validate_datetime


class TestDateValidation:
    def test_valid_date(self) -> None:
        assert _validate_date("2026-01-15") == "2026-01-15"

    def test_invalid_date_raises(self) -> None:
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            _validate_date("01-15-2026")

    def test_none_date_passes_through(self) -> None:
        assert _validate_date(None) is None

    def test_valid_datetime(self) -> None:
        assert _validate_datetime("2026-01-15T09:30:00") == "2026-01-15T09:30:00"

    def test_invalid_datetime_raises(self) -> None:
        with pytest.raises(ValueError, match="ISO datetime"):
            _validate_datetime("not-a-datetime")

    def test_none_datetime_passes_through(self) -> None:
        assert _validate_datetime(None) is None
```

**Step 2: Run test to verify it fails**

Run: `just check`
Expected: FAIL — `_validate_date` and `_validate_datetime` do not exist

**Step 3: Add validation helpers to server.py**

Add after the `_looks_like_id` function:

```python
import datetime as _dt


def _validate_date(value: str | None) -> str | None:
    """Validate that a date string is YYYY-MM-DD format. Returns the value or raises ValueError."""
    if value is None:
        return None
    try:
        _dt.date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"Invalid date '{value}'. Expected YYYY-MM-DD format.") from None
    return value


def _validate_datetime(value: str | None) -> str | None:
    """Validate that a datetime string is ISO format. Returns the value or raises ValueError."""
    if value is None:
        return None
    try:
        _dt.datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(
            f"Invalid datetime '{value}'. Expected ISO datetime format (e.g. 2026-01-15T09:30:00)."
        ) from None
    return value
```

Then wire them in to the tool functions:

In `create_task`, add before the `svc = _get_service()` line:
```python
_validate_date(day)
_validate_date(due_date)
```

In `update_task`, add inside the `if day is not None:` block:
```python
_validate_date(day)
```
And inside the `if due_date is not None:` block:
```python
_validate_date(due_date)
```

In `create_event`, add before the service call:
```python
_validate_datetime(start)
```

**Step 4: Run tests to verify they pass**

Run: `just check`
Expected: All PASS

**Step 5: Run mutation testing**

Run: `just mutate`
Expected: Mutation scores within thresholds

**Step 6: Commit**

```
feat(server): add date format validation for task and event inputs

Validates day/due_date (YYYY-MM-DD) and event start (ISO datetime)
at the server layer, giving LLMs actionable errors before hitting
the API.
```

---

### Task 4: Create Marvin task for read tool consolidation evaluation

**Action:** Use the Amazing Marvin MCP to create a task in the "Marvin MCP" category.

**Title:** "Evaluate consolidating read-only MCP tools"
**Note:** "Per Block's MCP playbook: consider whether get_today, get_due, get_inbox could be consolidated into a single get_tasks tool with a view parameter. Weigh reduced tool surface vs clarity of individual tools. Current count (14) is manageable but worth evaluating."

No code changes — just create the Marvin task.
