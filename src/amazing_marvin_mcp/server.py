# ABOUTME: MCP server entry point for Amazing Marvin.
# ABOUTME: Thin adapter that registers tools and delegates to the marvin business logic layer.

from __future__ import annotations

import os
import re
from typing import Any

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


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_today() -> str:
    """Get tasks and projects scheduled for today."""
    try:
        items = await _get_service().get_today()
        return format_tasks_list(items, "Today")
    except (MarvinAPIError, ValueError, MissingTokenError) as e:
        return f"Error: {e}"


@mcp.tool()
async def get_due() -> str:
    """Get overdue tasks and projects."""
    try:
        items = await _get_service().get_due()
        return format_tasks_list(items, "Overdue")
    except (MarvinAPIError, ValueError, MissingTokenError) as e:
        return f"Error: {e}"


@mcp.tool()
async def get_categories() -> str:
    """Get project and folder structure."""
    try:
        items = await _get_service().get_categories()
        return format_categories_tree(items)
    except (MarvinAPIError, ValueError, MissingTokenError) as e:
        return f"Error: {e}"


@mcp.tool()
async def get_children(parent: str) -> str:
    """Get child tasks under a project or folder. Accepts name or ID."""
    try:
        svc = _get_service()
        if _looks_like_id(parent):
            items = await svc.get_children(parent_id=parent)
        else:
            items = await svc.get_children(parent_name=parent)
        return format_tasks_list(items, f"Children of {parent}")
    except (MarvinAPIError, ValueError, MissingTokenError) as e:
        return f"Error: {e}"


@mcp.tool()
async def get_labels() -> str:
    """Get all labels."""
    try:
        items = await _get_service().get_labels()
        return format_labels(items)
    except (MarvinAPIError, ValueError, MissingTokenError) as e:
        return f"Error: {e}"


@mcp.tool()
async def get_time_blocks() -> str:
    """Get today's time blocks."""
    try:
        items = await _get_service().get_time_blocks()
        return format_time_blocks(items)
    except (MarvinAPIError, ValueError, MissingTokenError) as e:
        return f"Error: {e}"


@mcp.tool()
async def search(query: str) -> str:
    """Search projects and folders by name. Returns matches with their tasks."""
    try:
        matches = await _get_service().search(query)
        return format_search_results(query, matches)
    except (MarvinAPIError, ValueError, MissingTokenError) as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Write tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def create_task(
    title: str,
    day: str | None = None,
    due_date: str | None = None,
    parent: str | None = None,
    note: str | None = None,
    label_ids: list[str] | None = None,
) -> str:
    """Create a task. 'parent' can be a project name or ID. Dates use YYYY-MM-DD."""
    try:
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
    except (MarvinAPIError, ValueError, MissingTokenError) as e:
        return f"Error: {e}"


@mcp.tool()
async def create_event(
    title: str,
    start: str,
    duration_minutes: int,
    note: str | None = None,
) -> str:
    """Create a calendar event. 'start' is ISO datetime (e.g. 2026-02-21T09:30:00)."""
    try:
        result = await _get_service().create_event(
            title=title, start=start, duration_minutes=duration_minutes, note=note
        )
        return f"Created event: **{result.get('title', title)}** (id: {result.get('_id', '?')})"
    except (MarvinAPIError, ValueError, MissingTokenError) as e:
        return f"Error: {e}"


@mcp.tool()
async def update_task(
    item_id: str,
    title: str | None = None,
    day: str | None = None,
    due_date: str | None = None,
    note: str | None = None,
) -> str:
    """Update task fields. Pass only the fields you want to change."""
    try:
        setters: dict[str, Any] = {}
        if title is not None:
            setters["title"] = title
        if day is not None:
            setters["day"] = day
        if due_date is not None:
            setters["dueDate"] = due_date
        if note is not None:
            setters["note"] = note
        if not setters:
            return "Error: No fields provided to update."
        result = await _get_service().update_task(item_id, setters)
        return f"Updated: {format_task(result)}"
    except (MarvinAPIError, ValueError, MissingTokenError) as e:
        return f"Error: {e}"


@mcp.tool()
async def mark_done(item_id: str) -> str:
    """Mark a task as complete."""
    try:
        await _get_service().mark_done(item_id)
        return f"Marked task {item_id} as done."
    except (MarvinAPIError, ValueError, MissingTokenError) as e:
        return f"Error: {e}"


@mcp.tool()
async def delete_task(item_id: str) -> str:
    """Delete a task."""
    try:
        await _get_service().delete_task(item_id)
        return f"Deleted task {item_id}."
    except (MarvinAPIError, ValueError, MissingTokenError) as e:
        return f"Error: {e}"


@mcp.tool()
async def track_time(task_id: str, action: str) -> str:
    """Start or stop time tracking on a task. action must be 'START' or 'STOP'."""
    try:
        await _get_service().track_time(task_id, action)
        verb = "started" if action == "START" else "stopped"
        return f"Time tracking {verb} for task {task_id}."
    except (MarvinAPIError, ValueError, MissingTokenError) as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt()
def plan_my_day() -> str:
    """Plan your day by reviewing today's tasks, overdue items, and time blocks."""
    return (
        "Help me plan my day. Please:\n"
        "1. Call get_today to see what's scheduled\n"
        "2. Call get_due to check for overdue items\n"
        "3. Call get_time_blocks to see my schedule structure\n"
        "4. Suggest how to organize my day based on what you find"
    )


@mcp.prompt()
def weekly_review() -> str:
    """Review the week — check overdue items and suggest cleanup."""
    return (
        "Help me do a weekly review. Please:\n"
        "1. Call get_due to find all overdue items\n"
        "2. For each overdue item, suggest: reschedule, mark done, or delete\n"
        "3. Summarize what needs attention"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server over stdio transport."""
    mcp.run(transport="stdio")
