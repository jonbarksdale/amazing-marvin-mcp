# Amazing Marvin MCP Server — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a 12-tool Python MCP server for Amazing Marvin task management with intent-oriented design, layered architecture, and context-efficient markdown output.

**Architecture:** Four-layer design — thin MCP adapter (`server.py`) delegates to business logic (`marvin.py`), which calls raw HTTP (`client.py`), with shared formatting (`formatting.py`). Category/label caching and name→ID resolution live in `marvin.py`.

**Tech Stack:** Python 3.11+, uv, mcp SDK, httpx (async), ruff, mypy (strict), pytest + pytest-cov

**Design doc:** `docs/plans/2026-02-21-amazing-marvin-mcp-design.md`

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/amazing_marvin_mcp/__init__.py`
- Create: `src/amazing_marvin_mcp/client.py` (stub)
- Create: `src/amazing_marvin_mcp/marvin.py` (stub)
- Create: `src/amazing_marvin_mcp/formatting.py` (stub)
- Create: `src/amazing_marvin_mcp/server.py` (stub)
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "amazing-marvin-mcp"
version = "0.1.0"
description = "MCP server for Amazing Marvin task management"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
]

[project.scripts]
amazing-marvin-mcp = "amazing_marvin_mcp.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "TCH"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.8.0",
    "mypy>=1.13",
]
```

**Step 2: Create stub files**

`src/amazing_marvin_mcp/__init__.py`:
```python
# ABOUTME: Amazing Marvin MCP server package.
# ABOUTME: Provides intent-oriented tools for managing tasks, projects, and events in Amazing Marvin.
```

`src/amazing_marvin_mcp/client.py`:
```python
# ABOUTME: HTTP client for the Amazing Marvin API.
# ABOUTME: Handles authentication, rate limiting, and raw API calls.
```

`src/amazing_marvin_mcp/marvin.py`:
```python
# ABOUTME: Business logic layer for Amazing Marvin operations.
# ABOUTME: Provides intent-oriented operations with name resolution, caching, and timezone detection.
```

`src/amazing_marvin_mcp/formatting.py`:
```python
# ABOUTME: Response formatting utilities for Amazing Marvin data.
# ABOUTME: Converts API JSON to markdown and handles response trimming.
```

`src/amazing_marvin_mcp/server.py`:
```python
# ABOUTME: MCP server entry point for Amazing Marvin.
# ABOUTME: Thin adapter that registers tools and delegates to the marvin business logic layer.
```

`tests/__init__.py`:
```python
```

`tests/conftest.py`:
```python
# ABOUTME: Shared pytest fixtures for Amazing Marvin MCP tests.
# ABOUTME: Provides configured client instances and test data.
```

**Step 3: Install dependencies**

Run: `uv sync`
Expected: Clean install, lock file generated

**Step 4: Verify toolchain**

Run: `uv run ruff check . && uv run mypy src/ && uv run pytest`
Expected: All pass (no code to lint/check yet, 0 tests collected)

**Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/ tests/
git commit -m "chore: scaffold project with uv, ruff, mypy, pytest"
```

---

### Task 2: HTTP Client (`client.py`)

**Files:**
- Modify: `src/amazing_marvin_mcp/client.py`
- Create: `tests/test_client.py`

**Step 1: Write failing tests for MarvinClient**

`tests/test_client.py`:
```python
# ABOUTME: Tests for the MarvinClient HTTP layer.
# ABOUTME: Validates auth headers, rate limiting, error mapping, and raw API calls.

import asyncio
import time

import pytest

from amazing_marvin_mcp.client import MarvinClient, MarvinAPIError


class TestMarvinClientInit:
    """Test client initialization and configuration."""

    def test_requires_api_token(self) -> None:
        """Client raises ValueError if no token provided."""
        with pytest.raises(ValueError, match="MARVIN_API_TOKEN"):
            MarvinClient(api_token="")

    def test_stores_base_url(self) -> None:
        client = MarvinClient(api_token="test-token")
        assert client.base_url == "https://serv.amazingmarvin.com/api"

    def test_does_not_log_token(self) -> None:
        """Token must not appear in repr or str."""
        client = MarvinClient(api_token="secret-token-123")
        assert "secret-token-123" not in repr(client)
        assert "secret-token-123" not in str(client)


class TestMarvinClientHeaders:
    """Test that auth headers are built correctly."""

    def test_headers_include_both_tokens(self) -> None:
        client = MarvinClient(api_token="my-token")
        headers = client._build_headers()
        assert headers["X-API-Token"] == "my-token"
        assert headers["X-Full-Access-Token"] == "my-token"

    def test_headers_include_content_type(self) -> None:
        client = MarvinClient(api_token="my-token")
        headers = client._build_headers()
        assert headers["Content-Type"] == "application/json"


class TestRateLimiting:
    """Test rate limiting between requests."""

    @pytest.mark.asyncio
    async def test_query_rate_limit_delay(self) -> None:
        """Queries must wait at least 3 seconds apart."""
        client = MarvinClient(api_token="test-token")
        # Simulate a recent query
        client._last_query_time = time.monotonic()
        delay = client._calculate_query_delay()
        assert delay > 0
        assert delay <= 3.0

    @pytest.mark.asyncio
    async def test_mutation_rate_limit_delay(self) -> None:
        """Mutations must wait at least 1 second apart."""
        client = MarvinClient(api_token="test-token")
        client._last_mutation_time = time.monotonic()
        delay = client._calculate_mutation_delay()
        assert delay > 0
        assert delay <= 1.0

    def test_no_delay_on_first_request(self) -> None:
        """First request should have zero delay."""
        client = MarvinClient(api_token="test-token")
        assert client._calculate_query_delay() == 0.0
        assert client._calculate_mutation_delay() == 0.0


class TestErrorMapping:
    """Test HTTP status code to error message mapping."""

    def test_401_error(self) -> None:
        error = MarvinAPIError.from_status(401, "test")
        assert "Invalid API token" in str(error)

    def test_403_error(self) -> None:
        error = MarvinAPIError.from_status(403, "test")
        assert "full-access token" in str(error)

    def test_404_error(self) -> None:
        error = MarvinAPIError.from_status(404, "test")
        assert "not found" in str(error).lower()

    def test_429_error(self) -> None:
        error = MarvinAPIError.from_status(429, "test")
        assert "Rate limited" in str(error)

    def test_500_error(self) -> None:
        error = MarvinAPIError.from_status(500, "test")
        assert "server error" in str(error).lower()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_client.py -v`
Expected: FAIL — `MarvinClient` and `MarvinAPIError` not defined

**Step 3: Implement MarvinClient**

`src/amazing_marvin_mcp/client.py`:
```python
# ABOUTME: HTTP client for the Amazing Marvin API.
# ABOUTME: Handles authentication, rate limiting, and raw API calls.

from __future__ import annotations

import time
from typing import Any

import httpx

BASE_URL = "https://serv.amazingmarvin.com/api"
QUERY_RATE_LIMIT_SECONDS = 3.0
MUTATION_RATE_LIMIT_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 30.0


class MarvinAPIError(Exception):
    """Error from the Amazing Marvin API with a human-readable message."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)

    @classmethod
    def from_status(cls, status_code: int, endpoint: str) -> MarvinAPIError:
        messages = {
            401: "Invalid API token. Check MARVIN_API_TOKEN.",
            403: "Insufficient permissions. This endpoint requires a full-access token.",
            404: f"Item not found at {endpoint}.",
            429: "Rate limited by Amazing Marvin. Try again shortly.",
        }
        if status_code >= 500:
            msg = "Amazing Marvin server error. Try again later."
        else:
            msg = messages.get(status_code, f"API error {status_code} at {endpoint}.")
        return cls(msg, status_code=status_code)


class MarvinClient:
    """Low-level async HTTP client for the Amazing Marvin API.

    Handles auth headers, rate limiting, and error mapping.
    No business logic — that belongs in marvin.py.
    """

    def __init__(self, api_token: str) -> None:
        if not api_token:
            raise ValueError("MARVIN_API_TOKEN is required but was empty.")
        self._api_token = api_token
        self.base_url = BASE_URL
        self._last_query_time: float = 0.0
        self._last_mutation_time: float = 0.0

    def _build_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-API-Token": self._api_token,
            "X-Full-Access-Token": self._api_token,
        }
        if extra:
            headers.update(extra)
        return headers

    def _calculate_query_delay(self) -> float:
        if self._last_query_time == 0.0:
            return 0.0
        elapsed = time.monotonic() - self._last_query_time
        return max(0.0, QUERY_RATE_LIMIT_SECONDS - elapsed)

    def _calculate_mutation_delay(self) -> float:
        if self._last_mutation_time == 0.0:
            return 0.0
        elapsed = time.monotonic() - self._last_mutation_time
        return max(0.0, MUTATION_RATE_LIMIT_SECONDS - elapsed)

    async def _wait_for_rate_limit(self, is_mutation: bool) -> None:
        import asyncio

        delay = self._calculate_mutation_delay() if is_mutation else self._calculate_query_delay()
        if delay > 0:
            await asyncio.sleep(delay)

    async def get(
        self,
        endpoint: str,
        params: dict[str, str] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        """Make a GET request to the Marvin API."""
        await self._wait_for_rate_limit(is_mutation=False)
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as http:
            response = await http.get(url, headers=self._build_headers(extra_headers), params=params)
        self._last_query_time = time.monotonic()
        if response.status_code != 200:
            raise MarvinAPIError.from_status(response.status_code, endpoint)
        return response.json()

    async def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        """Make a POST request to the Marvin API."""
        await self._wait_for_rate_limit(is_mutation=True)
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as http:
            response = await http.post(
                url, headers=self._build_headers(extra_headers), json=data or {}
            )
        self._last_mutation_time = time.monotonic()
        if response.status_code != 200:
            raise MarvinAPIError.from_status(response.status_code, endpoint)
        return response.json()

    def __repr__(self) -> str:
        return f"MarvinClient(base_url={self.base_url!r})"

    def __str__(self) -> str:
        return f"MarvinClient({self.base_url})"
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_client.py -v`
Expected: All PASS

**Step 5: Run linting and type checking**

Run: `uv run ruff check . && uv run mypy src/amazing_marvin_mcp/client.py`
Expected: Clean

**Step 6: Commit**

```bash
git add src/amazing_marvin_mcp/client.py tests/test_client.py
git commit -m "feat: implement MarvinClient with auth, rate limiting, error mapping"
```

---

### Task 3: Response Formatting (`formatting.py`)

**Files:**
- Modify: `src/amazing_marvin_mcp/formatting.py`
- Create: `tests/test_formatting.py`

**Step 1: Write failing tests**

`tests/test_formatting.py`:
```python
# ABOUTME: Tests for response formatting utilities.
# ABOUTME: Validates markdown conversion, truncation, and notes trimming.

from amazing_marvin_mcp.formatting import (
    truncate_response,
    trim_notes,
    format_task,
    format_tasks_list,
    format_categories_tree,
    format_time_blocks,
    CHARACTER_LIMIT,
    NOTES_LIMIT,
)


class TestTruncateResponse:
    """Test response truncation at character limit."""

    def test_short_response_unchanged(self) -> None:
        text = "Short response"
        assert truncate_response(text) == text

    def test_long_response_truncated_at_newline(self) -> None:
        lines = [f"Line {i}" for i in range(5000)]
        text = "\n".join(lines)
        result = truncate_response(text)
        assert len(result) <= CHARACTER_LIMIT + 100  # allow for truncation message
        assert result.endswith("[truncated — use filters to narrow results]")

    def test_truncation_preserves_complete_lines(self) -> None:
        text = "a" * 24000 + "\n" + "b" * 2000
        result = truncate_response(text)
        assert not result.rstrip().endswith("bbb")  # should cut at the newline


class TestTrimNotes:
    """Test notes field trimming."""

    def test_short_notes_unchanged(self) -> None:
        assert trim_notes("Short note") == "Short note"

    def test_long_notes_trimmed(self) -> None:
        long_note = "x" * 1000
        result = trim_notes(long_note)
        assert len(result) <= NOTES_LIMIT + 10  # allow for [...]
        assert result.endswith("[...]")

    def test_none_notes_returns_empty(self) -> None:
        assert trim_notes(None) == ""


class TestFormatTask:
    """Test single task formatting to markdown."""

    def test_basic_task(self) -> None:
        task = {"_id": "abc123", "title": "Buy milk", "done": False}
        result = format_task(task)
        assert "Buy milk" in result
        assert "abc123" in result

    def test_task_with_due_date(self) -> None:
        task = {"_id": "abc123", "title": "Buy milk", "dueDate": "2026-02-25"}
        result = format_task(task)
        assert "2026-02-25" in result

    def test_task_with_long_notes_trimmed(self) -> None:
        task = {"_id": "abc123", "title": "Buy milk", "note": "x" * 1000}
        result = format_task(task)
        assert "[...]" in result


class TestFormatTasksList:
    """Test formatting a list of tasks."""

    def test_empty_list(self) -> None:
        result = format_tasks_list([], "Today")
        assert "no items" in result.lower() or "empty" in result.lower()

    def test_multiple_tasks(self) -> None:
        tasks = [
            {"_id": "1", "title": "Task A"},
            {"_id": "2", "title": "Task B"},
        ]
        result = format_tasks_list(tasks, "Today")
        assert "Task A" in result
        assert "Task B" in result
        assert "Today" in result


class TestFormatCategoriesTree:
    """Test category hierarchy formatting."""

    def test_flat_categories(self) -> None:
        categories = [
            {"_id": "1", "title": "Work", "type": "project"},
            {"_id": "2", "title": "Personal", "type": "project"},
        ]
        result = format_categories_tree(categories)
        assert "Work" in result
        assert "Personal" in result


class TestFormatTimeBlocks:
    """Test time block formatting."""

    def test_empty_blocks(self) -> None:
        result = format_time_blocks([])
        assert "no time blocks" in result.lower()

    def test_blocks_with_times(self) -> None:
        blocks = [
            {"_id": "1", "title": "Deep Work", "start": "09:00", "end": "11:00"},
        ]
        result = format_time_blocks(blocks)
        assert "Deep Work" in result
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_formatting.py -v`
Expected: FAIL — functions not defined

**Step 3: Implement formatting functions**

Implement `truncate_response`, `trim_notes`, `format_task`, `format_tasks_list`, `format_categories_tree`, `format_time_blocks` in `formatting.py`. Key constants: `CHARACTER_LIMIT = 25_000`, `NOTES_LIMIT = 500`.

The exact formatting will be refined when we see real API responses, but the structure should be:
- Tasks: `- [ ] **Title** (id: abc123) — due: 2026-02-25`
- Categories: indented tree based on parentId relationships
- Time blocks: `| 09:00–11:00 | Deep Work |`

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_formatting.py -v`
Expected: All PASS

**Step 5: Lint and type check**

Run: `uv run ruff check . && uv run mypy src/amazing_marvin_mcp/formatting.py`
Expected: Clean

**Step 6: Commit**

```bash
git add src/amazing_marvin_mcp/formatting.py tests/test_formatting.py
git commit -m "feat: implement response formatting with markdown output and truncation"
```

---

### Task 4: Business Logic — Read Operations (`marvin.py`, part 1)

**Files:**
- Modify: `src/amazing_marvin_mcp/marvin.py`
- Create: `tests/test_marvin.py`

This task implements the read-side of `MarvinService`: `get_today`, `get_due`, `get_categories`, `get_children`, `get_labels`, `get_time_blocks`.

**Step 1: Write failing tests for MarvinService read operations**

`tests/test_marvin.py`:
```python
# ABOUTME: Tests for the MarvinService business logic layer.
# ABOUTME: Validates intent-oriented operations, caching, and name resolution.

import pytest

from amazing_marvin_mcp.marvin import MarvinService


@pytest.fixture
def service() -> MarvinService:
    """MarvinService configured with real API token from env."""
    import os
    token = os.environ.get("MARVIN_API_TOKEN", "")
    if not token:
        pytest.skip("MARVIN_API_TOKEN not set")
    return MarvinService(api_token=token)


class TestGetToday:
    @pytest.mark.asyncio
    async def test_returns_list(self, service: MarvinService) -> None:
        result = await service.get_today()
        assert isinstance(result, list)


class TestGetDue:
    @pytest.mark.asyncio
    async def test_returns_list(self, service: MarvinService) -> None:
        result = await service.get_due()
        assert isinstance(result, list)


class TestGetCategories:
    @pytest.mark.asyncio
    async def test_returns_list(self, service: MarvinService) -> None:
        result = await service.get_categories()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_categories_have_title_and_id(self, service: MarvinService) -> None:
        result = await service.get_categories()
        if result:  # account may have categories
            cat = result[0]
            assert "_id" in cat
            assert "title" in cat


class TestGetChildren:
    @pytest.mark.asyncio
    async def test_by_parent_id(self, service: MarvinService) -> None:
        categories = await service.get_categories()
        if not categories:
            pytest.skip("No categories in account")
        parent_id = categories[0]["_id"]
        result = await service.get_children(parent_id=parent_id)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_by_parent_name(self, service: MarvinService) -> None:
        """Accepts a project name, resolves to ID internally."""
        categories = await service.get_categories()
        if not categories:
            pytest.skip("No categories in account")
        name = categories[0]["title"]
        result = await service.get_children(parent_name=name)
        assert isinstance(result, list)


class TestGetLabels:
    @pytest.mark.asyncio
    async def test_returns_list(self, service: MarvinService) -> None:
        result = await service.get_labels()
        assert isinstance(result, list)


class TestGetTimeBlocks:
    @pytest.mark.asyncio
    async def test_returns_list(self, service: MarvinService) -> None:
        result = await service.get_time_blocks()
        assert isinstance(result, list)


class TestCategoryCaching:
    @pytest.mark.asyncio
    async def test_second_call_uses_cache(self, service: MarvinService) -> None:
        """Second get_categories call should not hit the API again."""
        result1 = await service.get_categories()
        result2 = await service.get_categories()
        assert result1 == result2
        # Verify cache was used (client query count should be 1, not 2)
        assert service._categories_cache is not None
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_marvin.py -v`
Expected: FAIL — `MarvinService` not defined

**Step 3: Implement MarvinService read operations**

Implement `MarvinService` class in `marvin.py` with:
- Constructor takes `api_token`, creates `MarvinClient`
- `_categories_cache` and `_labels_cache` as `list | None` (populated on first access)
- `_resolve_parent_id(name)` — fuzzy matches against cached categories
- Methods: `get_today()`, `get_due()`, `get_categories()`, `get_children(parent_id=None, parent_name=None)`, `get_labels()`, `get_time_blocks()`

**Step 4: Run tests to verify they pass**

Run: `MARVIN_API_TOKEN=<token> uv run pytest tests/test_marvin.py -v`
Expected: All PASS (requires real API token)

**Step 5: Lint and type check**

Run: `uv run ruff check . && uv run mypy src/amazing_marvin_mcp/marvin.py`
Expected: Clean

**Step 6: Commit**

```bash
git add src/amazing_marvin_mcp/marvin.py tests/test_marvin.py
git commit -m "feat: implement MarvinService read operations with category caching"
```

---

### Task 5: Business Logic — Search (`marvin.py`, part 2)

**Files:**
- Modify: `src/amazing_marvin_mcp/marvin.py`
- Modify: `tests/test_marvin.py`

**Step 1: Write failing tests for search**

Add to `tests/test_marvin.py`:
```python
class TestSearch:
    @pytest.mark.asyncio
    async def test_search_by_partial_name(self, service: MarvinService) -> None:
        """Fuzzy match a query against category names and return matches with children."""
        categories = await service.get_categories()
        if not categories:
            pytest.skip("No categories in account")
        # Search for first few characters of a known category
        query = categories[0]["title"][:4]
        results = await service.search(query)
        assert isinstance(results, list)
        assert len(results) > 0
        # Each result should have the category info and its children
        assert "title" in results[0]
        assert "children" in results[0]

    @pytest.mark.asyncio
    async def test_search_no_match(self, service: MarvinService) -> None:
        results = await service.search("xyznonexistent999")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, service: MarvinService) -> None:
        categories = await service.get_categories()
        if not categories:
            pytest.skip("No categories in account")
        name = categories[0]["title"]
        upper = await service.search(name.upper())
        lower = await service.search(name.lower())
        assert len(upper) == len(lower)
```

**Step 2: Run to verify failure**

Run: `MARVIN_API_TOKEN=<token> uv run pytest tests/test_marvin.py::TestSearch -v`
Expected: FAIL — `search` method not defined

**Step 3: Implement search**

Add `search(query: str) -> list[dict]` to `MarvinService`:
- Gets cached categories
- Case-insensitive substring match of `query` against `title` field
- For each match, fetches children via `get_children`
- Returns list of `{"_id": ..., "title": ..., "type": ..., "children": [...]}`

**Step 4: Run tests to verify they pass**

Run: `MARVIN_API_TOKEN=<token> uv run pytest tests/test_marvin.py::TestSearch -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/amazing_marvin_mcp/marvin.py tests/test_marvin.py
git commit -m "feat: implement fuzzy search across categories with children"
```

---

### Task 6: Business Logic — Write Operations (`marvin.py`, part 3)

**Files:**
- Modify: `src/amazing_marvin_mcp/marvin.py`
- Modify: `tests/test_marvin.py`

Implements: `create_task`, `create_event`, `update_task`, `mark_done`, `delete_task`, `track_time`.

**Step 1: Write failing tests for write operations**

Add to `tests/test_marvin.py`:
```python
class TestCreateAndDeleteTask:
    """Tests create, then cleans up by deleting."""

    @pytest.mark.asyncio
    async def test_create_task_basic(self, service: MarvinService) -> None:
        task = await service.create_task(title="MCP Test Task — delete me")
        assert "_id" in task
        assert task["title"] == "MCP Test Task — delete me"
        # Cleanup
        await service.delete_task(task["_id"])

    @pytest.mark.asyncio
    async def test_create_task_with_parent_name(self, service: MarvinService) -> None:
        categories = await service.get_categories()
        if not categories:
            pytest.skip("No categories in account")
        parent_name = categories[0]["title"]
        task = await service.create_task(
            title="MCP Test Task with parent", parent_name=parent_name
        )
        assert "_id" in task
        # Cleanup
        await service.delete_task(task["_id"])

    @pytest.mark.asyncio
    async def test_create_task_with_day_and_due(self, service: MarvinService) -> None:
        task = await service.create_task(
            title="MCP Test Scheduled",
            day="2026-12-31",
            due_date="2026-12-31",
        )
        assert "_id" in task
        await service.delete_task(task["_id"])


class TestMarkDone:
    @pytest.mark.asyncio
    async def test_mark_done(self, service: MarvinService) -> None:
        task = await service.create_task(title="MCP Test Done")
        result = await service.mark_done(task["_id"])
        assert result is not None
        # Cleanup (done tasks may still be deletable)
        await service.delete_task(task["_id"])


class TestUpdateTask:
    @pytest.mark.asyncio
    async def test_update_title(self, service: MarvinService) -> None:
        task = await service.create_task(title="MCP Test Update")
        updated = await service.update_task(
            task["_id"], setters={"title": "MCP Test Updated"}
        )
        assert updated["title"] == "MCP Test Updated"
        await service.delete_task(task["_id"])


class TestTrackTime:
    @pytest.mark.asyncio
    async def test_start_stop(self, service: MarvinService) -> None:
        task = await service.create_task(title="MCP Test Track")
        start_result = await service.track_time(task["_id"], action="START")
        assert start_result is not None
        stop_result = await service.track_time(task["_id"], action="STOP")
        assert stop_result is not None
        await service.delete_task(task["_id"])


class TestCreateEvent:
    @pytest.mark.asyncio
    async def test_create_event(self, service: MarvinService) -> None:
        event = await service.create_event(
            title="MCP Test Event",
            start="2026-12-31T09:00:00",
            duration_minutes=30,
        )
        assert "_id" in event
        # Cleanup
        await service.delete_task(event["_id"])
```

**Step 2: Run to verify failure**

Run: `MARVIN_API_TOKEN=<token> uv run pytest tests/test_marvin.py::TestCreateAndDeleteTask -v`
Expected: FAIL — methods not defined

**Step 3: Implement write operations**

Add to `MarvinService`:
- `create_task(title, day=None, due_date=None, parent_id=None, parent_name=None, label_ids=None, note=None)` — resolves parent_name if provided
- `create_event(title, start, duration_minutes, note=None)` — converts duration to ms
- `update_task(item_id, setters: dict)` — wraps as `/doc/update` format `[{"key": k, "val": v}]`
- `mark_done(item_id)` — auto-detects timezone offset via `time.timezone`
- `delete_task(item_id)` — calls `/doc/delete`
- `track_time(task_id, action)` — validates action is START/STOP

Invalidate category cache after create/delete.

**Step 4: Run tests to verify they pass**

Run: `MARVIN_API_TOKEN=<token> uv run pytest tests/test_marvin.py -v`
Expected: All PASS

**Step 5: Lint and type check**

Run: `uv run ruff check . && uv run mypy src/amazing_marvin_mcp/marvin.py`
Expected: Clean

**Step 6: Commit**

```bash
git add src/amazing_marvin_mcp/marvin.py tests/test_marvin.py
git commit -m "feat: implement write operations — create, update, delete, done, track"
```

---

### Task 7: MCP Server (`server.py`)

**Files:**
- Modify: `src/amazing_marvin_mcp/server.py`
- Create: `tests/test_server.py`

**Step 1: Write failing tests for server tool registration**

`tests/test_server.py`:
```python
# ABOUTME: Tests for the MCP server adapter layer.
# ABOUTME: Validates tool registration, input handling, and formatted output.

import pytest

from amazing_marvin_mcp.server import create_server


class TestServerSetup:
    def test_server_has_expected_tools(self) -> None:
        """Server should register exactly 12 tools."""
        server = create_server()
        tool_names = {tool.name for tool in server.list_tools()}
        expected = {
            "get_today", "get_due", "get_categories", "get_children",
            "get_labels", "get_time_blocks", "search",
            "create_task", "create_event", "update_task",
            "mark_done", "delete_task", "track_time",
        }
        assert tool_names == expected

    def test_server_has_prompts(self) -> None:
        """Server should register workflow prompts."""
        server = create_server()
        prompt_names = {p.name for p in server.list_prompts()}
        assert "plan_my_day" in prompt_names
        assert "weekly_review" in prompt_names
```

Note: The exact test API for listing tools/prompts depends on the `mcp` SDK version. The implementing engineer should check the SDK docs and adjust the assertions to match the actual API (e.g., `server.list_tools()` might be a method on the server or require inspecting registered handlers).

**Step 2: Run to verify failure**

Run: `uv run pytest tests/test_server.py -v`
Expected: FAIL — `create_server` not defined

**Step 3: Implement MCP server**

`server.py` should:
1. `create_server()` — creates MCP `Server` instance, registers all 12 tools and 2 prompts
2. Each tool handler: parse input → call `MarvinService` method → format with `formatting.py` → return
3. `main()` entry point — reads `MARVIN_API_TOKEN` from env, creates server, runs STDIO transport
4. Tool annotations: `readOnlyHint=True` for read tools, `destructiveHint=True` for delete

Keep tool descriptions concise (one sentence each) for context efficiency.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_server.py -v`
Expected: All PASS

**Step 5: Lint and type check**

Run: `uv run ruff check . && uv run mypy src/amazing_marvin_mcp/server.py`
Expected: Clean

**Step 6: Commit**

```bash
git add src/amazing_marvin_mcp/server.py tests/test_server.py
git commit -m "feat: implement MCP server with 12 tools and 2 workflow prompts"
```

---

### Task 8: Integration Testing

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration tests**

These test the full stack: `MarvinService` → `MarvinClient` → real API → formatting.

```python
# ABOUTME: Integration tests for the full Amazing Marvin MCP stack.
# ABOUTME: Tests real API calls through MarvinService with formatted output.

import os

import pytest

from amazing_marvin_mcp.marvin import MarvinService
from amazing_marvin_mcp.formatting import format_tasks_list, truncate_response


@pytest.fixture
def service() -> MarvinService:
    token = os.environ.get("MARVIN_API_TOKEN", "")
    if not token:
        pytest.skip("MARVIN_API_TOKEN not set")
    return MarvinService(api_token=token)


class TestFullWorkflow:
    """Test a complete create → read → update → done → delete workflow."""

    @pytest.mark.asyncio
    async def test_task_lifecycle(self, service: MarvinService) -> None:
        # Create
        task = await service.create_task(title="Integration Test Task")
        task_id = task["_id"]

        try:
            # Read — should appear in today (if scheduled) or via search
            # Update
            updated = await service.update_task(
                task_id, setters={"title": "Integration Test Updated"}
            )
            assert updated["title"] == "Integration Test Updated"

            # Mark done
            await service.mark_done(task_id)
        finally:
            # Cleanup
            await service.delete_task(task_id)


class TestFormattedOutput:
    """Test that formatted output stays within limits."""

    @pytest.mark.asyncio
    async def test_today_formatted_within_limit(self, service: MarvinService) -> None:
        items = await service.get_today()
        formatted = format_tasks_list(items, "Today's Tasks")
        result = truncate_response(formatted)
        assert len(result) <= 25_100  # small buffer for truncation message


class TestRateLimiting:
    """Test that rapid calls don't cause 429 errors."""

    @pytest.mark.asyncio
    async def test_rapid_reads_dont_fail(self, service: MarvinService) -> None:
        """Three rapid reads should succeed (rate limiter handles delays)."""
        await service.get_labels()
        await service.get_categories()
        await service.get_time_blocks()
        # If we get here without MarvinAPIError(429), rate limiting works
```

**Step 2: Run integration tests**

Run: `MARVIN_API_TOKEN=<token> uv run pytest tests/test_integration.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for full task lifecycle and rate limiting"
```

---

### Task 9: E2E Test — MCP Server via STDIO

**Files:**
- Create: `tests/test_e2e.py`

**Step 1: Write E2E test**

Test the server as an MCP client would see it — launch it as a subprocess, send JSON-RPC over STDIO, validate responses.

```python
# ABOUTME: End-to-end tests for the MCP server via STDIO transport.
# ABOUTME: Launches the server as a subprocess and communicates via JSON-RPC.

import json
import os
import subprocess
import sys

import pytest


@pytest.fixture
def server_process():
    """Launch the MCP server as a subprocess."""
    token = os.environ.get("MARVIN_API_TOKEN", "")
    if not token:
        pytest.skip("MARVIN_API_TOKEN not set")
    proc = subprocess.Popen(
        [sys.executable, "-m", "amazing_marvin_mcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "MARVIN_API_TOKEN": token},
    )
    yield proc
    proc.terminate()
    proc.wait(timeout=5)


class TestE2EServer:
    def test_server_responds_to_initialize(self, server_process) -> None:
        """Server should respond to MCP initialize request."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0.1.0"},
            },
        }
        server_process.stdin.write(json.dumps(request).encode() + b"\n")
        server_process.stdin.flush()
        # Read response (may need content-length framing depending on MCP SDK)
        # The implementing engineer should adjust based on the actual transport format
```

Note: The exact STDIO framing depends on the MCP SDK version. The implementing engineer should consult the `mcp` SDK docs for the correct request/response format and adjust accordingly. The MCP SDK may provide a test client utility that simplifies this.

**Step 2: Run E2E test**

Run: `MARVIN_API_TOKEN=<token> uv run pytest tests/test_e2e.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_e2e.py
git commit -m "test: add E2E test for MCP server STDIO communication"
```

---

### Task 10: Documentation and Final Checks

**Files:**
- Create: `README.md`
- Modify: `pyproject.toml` (if needed)

**Step 1: Write README**

Include:
- What this is (one paragraph)
- Setup: `uv sync`, set `MARVIN_API_TOKEN`
- Usage with Claude Code: `claude mcp add` command
- Usage with Claude Desktop: JSON config snippet
- Available tools table (name + one-line description)
- Available prompts

**Step 2: Run full test suite**

Run: `MARVIN_API_TOKEN=<token> uv run pytest --cov=src -v`
Expected: All PASS, coverage ≥ 90%

**Step 3: Run all quality checks**

Run: `uv run ruff check . && uv run ruff format --check . && uv run mypy src/`
Expected: All clean

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup, usage, and tool reference"
```

---

## Task Dependency Graph

```
Task 1 (scaffold)
  ├── Task 2 (client.py)
  │     └── Task 4 (marvin.py reads)
  │           ├── Task 5 (search)
  │           └── Task 6 (marvin.py writes)
  │                 └── Task 7 (server.py)
  │                       ├── Task 8 (integration tests)
  │                       └── Task 9 (E2E tests)
  └── Task 3 (formatting.py)
        └── Task 7 (server.py)

Task 10 (docs) — after all others
```

## Notes for the Implementing Engineer

1. **Real API required**: All tests beyond Task 2 and Task 3 require `MARVIN_API_TOKEN` env var set. Get your token from `app.amazingmarvin.com/pre?api`.

2. **Rate limiting in tests**: The integration/E2E tests hit a real API with rate limits. If tests fail with 429s, the rate limiter needs tuning. Tests should pass without adding `time.sleep` in test code — the client should handle it.

3. **MCP SDK API**: The `mcp` Python SDK is evolving. Check the latest docs for:
   - How to register tools (`@server.tool()` decorator or `server.add_tool()`)
   - How to register prompts
   - STDIO transport setup
   - Tool annotation schema

4. **Test cleanup**: Write tests create real tasks and delete them. If a test fails mid-way, orphaned tasks may remain. The test tasks are prefixed with "MCP Test" or "Integration Test" for easy manual cleanup.

5. **Formatting refinement**: The exact markdown format for tasks/categories will need tuning once you see real API response shapes. The tests in Task 3 define the contract; adjust implementation to match.
