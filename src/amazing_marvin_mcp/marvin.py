# ABOUTME: Business logic layer for Amazing Marvin operations.
# ABOUTME: Provides intent-oriented operations with name resolution, caching, and timezones.

from __future__ import annotations

from typing import Any

from amazing_marvin_mcp.client import MarvinClient


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

    async def get_today(self) -> list[dict[str, Any]]:
        """Return tasks and projects scheduled for today."""
        result: list[dict[str, Any]] = await self._client.get("/todayItems")
        return result

    async def get_due(self) -> list[dict[str, Any]]:
        """Return overdue items."""
        result: list[dict[str, Any]] = await self._client.get("/dueItems")
        return result

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
    ) -> list[dict[str, Any]]:
        """Return child tasks under a parent category.

        Accepts either parent_id or parent_name (not both).
        If parent_name is given, it is resolved to an ID via fuzzy matching.
        """
        if parent_id and parent_name:
            raise ValueError("Provide parent_id or parent_name, not both.")
        if not parent_id and not parent_name:
            raise ValueError("Provide either parent_id or parent_name.")

        resolved_id = parent_id or await self._resolve_parent_id(parent_name)  # type: ignore[arg-type]
        result: list[dict[str, Any]] = await self._client.get(
            "/children", params={"parentId": resolved_id}
        )
        return result

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
                return cat["_id"]  # type: ignore[no-any-return]

        # Fall back to substring match
        for cat in categories:
            if name_lower in cat.get("title", "").lower():
                return cat["_id"]  # type: ignore[no-any-return]

        raise ValueError(f"No category matching '{name}' found.")
