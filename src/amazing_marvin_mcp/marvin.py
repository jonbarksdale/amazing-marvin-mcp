# ABOUTME: Business logic layer for Amazing Marvin operations.
# ABOUTME: Provides intent-oriented operations with name resolution, caching, and timezones.

import datetime
from typing import Any, Literal, Self

from amazing_marvin_mcp.client import MarvinClient
from amazing_marvin_mcp.formatting import BackburnerFilter, filter_backburner


class MarvinService:
    """High-level service for Amazing Marvin operations.

    Wraps MarvinClient with caching, fuzzy name resolution, and
    intent-oriented methods. This is the primary interface for the
    MCP server layer.
    """

    def __init__(self, api_token: str) -> None:
        self._client = MarvinClient(api_token=api_token)
        self._categories_cache: list[dict[str, Any]] | None = None
        self._labels_cache: list[dict[str, Any]] | None = None

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._client.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self.close()

    def invalidate_caches(self) -> None:
        """Clear all cached data. Called after mutations that may affect lookups."""
        self._categories_cache = None
        self._labels_cache = None

    async def get_today(self) -> list[dict[str, Any]]:
        """Return tasks and projects scheduled for today."""
        result: list[dict[str, Any]] = await self._client.get("/todayItems")
        return result

    async def get_due(self, backburner: BackburnerFilter = None) -> list[dict[str, Any]]:
        """Return overdue items."""
        result: list[dict[str, Any]] = await self._client.get("/dueItems")
        return filter_backburner(result, backburner)

    async def get_categories(self) -> list[dict[str, Any]]:
        """Return all categories, using cache after first call."""
        if self._categories_cache is not None:
            return self._categories_cache
        result: list[dict[str, Any]] = await self._client.get("/categories")
        self._categories_cache = result
        return result

    async def get_children(
        self,
        parent_id: str | None = None,
        parent_name: str | None = None,
        backburner: BackburnerFilter = None,
    ) -> list[dict[str, Any]]:
        """Return child tasks under a parent category.

        Accepts either parent_id or parent_name (not both).
        If parent_name is given, it is resolved to an ID via fuzzy matching.
        """
        if parent_id and parent_name:
            raise ValueError("Provide parent_id or parent_name, not both.")
        if not parent_id and not parent_name:
            raise ValueError("Provide either parent_id or parent_name.")

        if parent_id:
            resolved_id = parent_id
        else:
            assert parent_name is not None  # guaranteed by validation above  # noqa: S101
            resolved_id = await self._resolve_parent_id(parent_name)
        result: list[dict[str, Any]] = await self._client.get(
            "/children", params={"parentId": resolved_id}
        )
        return filter_backburner(result, backburner)

    async def get_inbox(self, backburner: BackburnerFilter = None) -> list[dict[str, Any]]:
        """Return tasks in the inbox (not assigned to any project or folder)."""
        result: list[dict[str, Any]] = await self._client.get(
            "/children", params={"parentId": "unassigned"}
        )
        return filter_backburner(result, backburner)

    async def get_labels(self) -> list[dict[str, Any]]:
        """Return all labels, using cache after first call."""
        if self._labels_cache is not None:
            return self._labels_cache
        result: list[dict[str, Any]] = await self._client.get("/labels")
        self._labels_cache = result
        return result

    async def get_time_blocks(self) -> list[dict[str, Any]]:
        """Return today's time blocks."""
        result: list[dict[str, Any]] = await self._client.get("/todayTimeBlocks")
        return result

    async def _resolve_parent_id(self, name: str) -> str:
        """Resolve a category name to its ID via case-insensitive matching.

        Prefers an exact (case-insensitive) match. Falls back to the first
        substring match. Raises ValueError if no match is found.
        """
        categories = await self.get_categories()
        name_lower = name.lower()

        # Try exact match first
        for cat in categories:
            if cat.get("title", "").lower() == name_lower:
                return str(cat["_id"])

        # Fall back to substring match
        for cat in categories:
            if name_lower in cat.get("title", "").lower():
                return str(cat["_id"])

        raise ValueError(f"No category matching '{name}' found.")

    async def search(
        self, query: str, max_results: int = 5, backburner: BackburnerFilter = None
    ) -> list[dict[str, Any]]:
        """Search categories by name and return matches with their children.

        Case-insensitive substring match against category titles.
        For each match, fetches children and includes them in the result.
        Limited to max_results to avoid excessive API calls from rate limiting.
        """
        categories = await self.get_categories()
        query_lower = query.lower()

        # Filter categories by title match, then by backburner status
        title_matches = [c for c in categories if query_lower in c.get("title", "").lower()]
        filtered_cats = filter_backburner(title_matches, backburner)

        matches: list[dict[str, Any]] = []
        for cat in filtered_cats:
            cat_id = str(cat["_id"])
            children = await self.get_children(parent_id=cat_id, backburner=backburner)
            matches.append(
                {
                    "_id": cat_id,
                    "title": cat["title"],
                    "type": cat.get("type", ""),
                    "children": children,
                }
            )
            if len(matches) >= max_results:
                break
        return matches

    async def create_task(
        self,
        title: str,
        day: str | None = None,
        due_date: str | None = None,
        parent_id: str | None = None,
        parent_name: str | None = None,
        label_ids: list[str] | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """Create a task. Resolves parent_name to ID if provided."""
        body: dict[str, Any] = {"title": title}
        if day is not None:
            body["day"] = day
        if due_date is not None:
            body["dueDate"] = due_date
        if parent_name is not None:
            parent_id = await self._resolve_parent_id(parent_name)
        if parent_id is not None:
            body["parentId"] = parent_id
        if label_ids is not None:
            body["labelIds"] = label_ids
        if note is not None:
            body["note"] = note

        result: dict[str, Any] = await self._client.post("/addTask", data=body)
        # Invalidate categories cache since a project may have been created
        self.invalidate_caches()
        return result

    async def create_event(
        self,
        title: str,
        start: str,
        duration_minutes: int,
        note: str | None = None,
    ) -> dict[str, Any]:
        """Create a calendar event. Converts duration_minutes to milliseconds."""
        body: dict[str, Any] = {
            "title": title,
            "start": start,
            "length": duration_minutes * 60 * 1000,
        }
        if note is not None:
            body["note"] = note
        result: dict[str, Any] = await self._client.post("/addEvent", data=body)
        return result

    async def update_task(
        self,
        item_id: str,
        setters: dict[str, Any],
    ) -> dict[str, Any]:
        """Update task fields. Converts setters dict to API format."""
        api_setters = [{"key": k, "val": v} for k, v in setters.items()]
        body: dict[str, Any] = {"itemId": item_id, "setters": api_setters}
        result: dict[str, Any] = await self._client.post("/doc/update", data=body)
        return result

    async def mark_done(self, item_id: str) -> dict[str, Any]:
        """Mark a task as done. Auto-detects timezone offset (DST-aware)."""
        utc_offset = datetime.datetime.now(datetime.UTC).astimezone().utcoffset()
        # utcoffset() returns timedelta east of UTC; Marvin expects minutes west of UTC
        offset_minutes = -int(utc_offset.total_seconds()) // 60 if utc_offset else 0
        body: dict[str, Any] = {
            "itemId": item_id,
            "timeZoneOffset": offset_minutes,
        }
        result: dict[str, Any] = await self._client.post("/markDone", data=body)
        return result

    async def delete_task(self, item_id: str) -> dict[str, Any]:
        """Delete a task."""
        body: dict[str, Any] = {"itemId": item_id}
        result: dict[str, Any] = await self._client.post("/doc/delete", data=body)
        # Invalidate categories cache since a project may have been deleted
        self.invalidate_caches()
        return result

    async def track_time(self, task_id: str, action: Literal["START", "STOP"]) -> dict[str, Any]:
        """Start or stop time tracking. action must be 'START' or 'STOP'."""
        if action not in ("START", "STOP"):
            raise ValueError(f"action must be START or STOP, got '{action}'")
        body: dict[str, Any] = {"taskId": task_id, "action": action}
        result: dict[str, Any] = await self._client.post("/track", data=body)
        return result
