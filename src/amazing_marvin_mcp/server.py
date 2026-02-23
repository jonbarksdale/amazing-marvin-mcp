# ABOUTME: MCP server entry point for Amazing Marvin.
# ABOUTME: Thin adapter that registers tools and delegates to the marvin business logic layer.

import functools
import os
import re
from collections.abc import Callable, Coroutine
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from amazing_marvin_mcp.client import MarvinAPIError
from amazing_marvin_mcp.formatting import (
    format_categories_tree,
    format_labels,
    format_search_results,
    format_task,
    format_tasks_list,
    format_time_blocks,
)
from amazing_marvin_mcp.marvin import MarvinService
from amazing_marvin_mcp.prompts import register_prompts

mcp = FastMCP("amazing-marvin")

_service: MarvinService | None = None

# Pattern matching MongoDB ObjectIDs and UUIDs
_ID_PATTERN = re.compile(r"^[0-9a-fA-F-]{24,}$")


class MissingTokenError(Exception):
    """Raised when MARVIN_API_TOKEN is not set."""


def _get_service() -> MarvinService:
    """Lazily initialize and return the MarvinService singleton.

    The service holds an httpx.AsyncClient for connection pooling.
    For STDIO transport the process exits when the pipe closes, so
    explicit cleanup is not needed. Library consumers should use the
    async context manager for automatic cleanup::

        async with MarvinService(api_token=token) as svc:
            items = await svc.get_today()
    """
    global _service  # noqa: PLW0603
    if _service is None:
        token = os.environ.get("MARVIN_API_TOKEN", "")
        if not token:
            raise MissingTokenError(
                "MARVIN_API_TOKEN environment variable is not set. "
                "Please ask the user to set it with their Amazing Marvin "
                "full-access token from https://app.amazingmarvin.com/pre?api"
            )
        _service = MarvinService(api_token=token)
    return _service


def _looks_like_id(value: str) -> bool:
    """Return True if value looks like a Marvin document ID."""
    return bool(_ID_PATTERN.match(value))


def _handle_errors(
    func: Callable[..., Coroutine[Any, Any, str]],
) -> Callable[..., Coroutine[Any, Any, str]]:
    """Decorator that catches API and transport errors, returning user-safe messages."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            return await func(*args, **kwargs)
        except httpx.TimeoutException:
            return "Error: Request to Amazing Marvin timed out. Try again."
        except httpx.HTTPError as e:
            return f"Error: Could not connect to Amazing Marvin ({type(e).__name__})."
        except (MarvinAPIError, ValueError, MissingTokenError) as e:
            return f"Error: {e}"

    return wrapper


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------


@mcp.tool()
@_handle_errors
async def get_today() -> str:
    """Get tasks and projects scheduled for today."""
    items = await _get_service().get_today()
    return format_tasks_list(items, "Today")


@mcp.tool()
@_handle_errors
async def get_due(backburner: str | None = None) -> str:
    """Get overdue tasks and projects.

    By default excludes backburner items.
    Use backburner='include' to show all, or 'only' for backburner items only.
    """
    items = await _get_service().get_due(backburner=backburner)
    return format_tasks_list(items, "Overdue")


@mcp.tool()
@_handle_errors
async def get_categories() -> str:
    """Get project and folder structure."""
    items = await _get_service().get_categories()
    return format_categories_tree(items)


@mcp.tool()
@_handle_errors
async def get_inbox(backburner: str | None = None) -> str:
    """Get tasks in the inbox (not assigned to any project or folder).

    By default excludes backburner items.
    Use backburner='include' to show all, or 'only' for backburner items only.
    """
    items = await _get_service().get_inbox(backburner=backburner)
    return format_tasks_list(items, "Inbox")


@mcp.tool()
@_handle_errors
async def get_children(parent: str, backburner: str | None = None) -> str:
    """Get child tasks under a project or folder. Accepts name or ID.

    By default excludes backburner items.
    Use backburner='include' to show all, or 'only' for backburner items only.
    """
    svc = _get_service()
    if _looks_like_id(parent):
        items = await svc.get_children(parent_id=parent, backburner=backburner)
    else:
        items = await svc.get_children(parent_name=parent, backburner=backburner)
    return format_tasks_list(items, f"Children of {parent}")


@mcp.tool()
@_handle_errors
async def get_labels() -> str:
    """Get all labels."""
    items = await _get_service().get_labels()
    return format_labels(items)


@mcp.tool()
@_handle_errors
async def get_time_blocks() -> str:
    """Get today's time blocks."""
    items = await _get_service().get_time_blocks()
    return format_time_blocks(items)


@mcp.tool()
@_handle_errors
async def search(query: str, backburner: str | None = None) -> str:
    """Search projects and folders by name. Returns matches with their tasks.

    By default excludes backburner items.
    Use backburner='include' to show all, or 'only' for backburner items only.
    """
    matches = await _get_service().search(query, backburner=backburner)
    return format_search_results(query, matches)


# ---------------------------------------------------------------------------
# Write tools
# ---------------------------------------------------------------------------


@mcp.tool()
@_handle_errors
async def create_task(
    title: str,
    day: str | None = None,
    due_date: str | None = None,
    parent: str | None = None,
    note: str | None = None,
    label_ids: list[str] | None = None,
) -> str:
    """Create a task. 'parent' can be a project name or ID. Dates use YYYY-MM-DD."""
    svc = _get_service()
    kwargs: dict[str, Any] = {"title": title}
    if day is not None:
        kwargs["day"] = day
    if due_date is not None:
        kwargs["due_date"] = due_date
    if note is not None:
        kwargs["note"] = note
    if label_ids is not None:
        kwargs["label_ids"] = label_ids
    if parent is not None:
        if _looks_like_id(parent):
            kwargs["parent_id"] = parent
        else:
            kwargs["parent_name"] = parent
    result = await svc.create_task(**kwargs)
    return f"Created: {format_task(result)}"


@mcp.tool()
@_handle_errors
async def create_event(
    title: str,
    start: str,
    duration_minutes: int,
    note: str | None = None,
) -> str:
    """Create a calendar event. 'start' is ISO datetime (e.g. 2026-02-21T09:30:00)."""
    result = await _get_service().create_event(
        title=title, start=start, duration_minutes=duration_minutes, note=note
    )
    return f"Created event: **{result.get('title', title)}** (id: {result.get('_id', '?')})"


@mcp.tool()
@_handle_errors
async def update_task(
    item_id: str,
    title: str | None = None,
    day: str | None = None,
    due_date: str | None = None,
    note: str | None = None,
    backburner: bool | None = None,
) -> str:
    """Update task fields. Pass only the fields you want to change.

    Set backburner=true to move a task to the backburner,
    or backburner=false to restore it.
    """
    setters: dict[str, Any] = {}
    if title is not None:
        setters["title"] = title
    if day is not None:
        setters["day"] = day
    if due_date is not None:
        setters["dueDate"] = due_date
    if note is not None:
        setters["note"] = note
    if backburner is not None:
        setters["backburner"] = backburner
    if not setters:
        return "Error: No fields provided to update."
    result = await _get_service().update_task(item_id, setters)
    return f"Updated: {format_task(result)}"


@mcp.tool()
@_handle_errors
async def mark_done(item_id: str) -> str:
    """Mark a task as complete."""
    await _get_service().mark_done(item_id)
    return f"Marked task {item_id} as done."


@mcp.tool()
@_handle_errors
async def delete_task(item_id: str) -> str:
    """Delete a task."""
    await _get_service().delete_task(item_id)
    return f"Deleted task {item_id}."


@mcp.tool()
@_handle_errors
async def track_time(task_id: str, action: str) -> str:
    """Start or stop time tracking on a task. action must be 'START' or 'STOP'."""
    await _get_service().track_time(task_id, action)
    verb = "started" if action == "START" else "stopped"
    return f"Time tracking {verb} for task {task_id}."


# ---------------------------------------------------------------------------
# Prompts — loaded from markdown files in prompts/
# ---------------------------------------------------------------------------

register_prompts(mcp)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server over stdio transport."""
    mcp.run(transport="stdio")
