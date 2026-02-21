# ABOUTME: Unit tests for MarvinService business logic with mocked HTTP client.
# ABOUTME: Tests caching, name resolution, validation, and timezone without network calls.

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from amazing_marvin_mcp.marvin import MarvinService


def _make_service() -> tuple[MarvinService, AsyncMock]:
    """Create a MarvinService with a mocked MarvinClient."""
    svc = MarvinService(api_token="fake-token")
    mock_client = AsyncMock()
    svc._client = mock_client
    return svc, mock_client


SAMPLE_CATEGORIES: list[dict[str, Any]] = [
    {"_id": "cat1", "title": "Work", "type": "project"},
    {"_id": "cat2", "title": "Personal", "type": "category"},
    {"_id": "cat3", "title": "Side Projects", "type": "project"},
]

SAMPLE_LABELS: list[dict[str, Any]] = [
    {"_id": "lbl1", "title": "Urgent"},
    {"_id": "lbl2", "title": "Low Priority"},
]


class TestCategoryCaching:
    @pytest.mark.asyncio
    async def test_caches_after_first_call(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_CATEGORIES

        result1 = await svc.get_categories()
        result2 = await svc.get_categories()

        assert result1 == SAMPLE_CATEGORIES
        assert result2 == SAMPLE_CATEGORIES
        mock.get.assert_called_once_with("/categories")

    @pytest.mark.asyncio
    async def test_invalidate_clears_cache(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_CATEGORIES

        await svc.get_categories()
        svc.invalidate_caches()
        await svc.get_categories()

        assert mock.get.call_count == 2


class TestLabelsCaching:
    @pytest.mark.asyncio
    async def test_caches_after_first_call(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_LABELS

        result1 = await svc.get_labels()
        result2 = await svc.get_labels()

        assert result1 == SAMPLE_LABELS
        assert result2 == SAMPLE_LABELS
        mock.get.assert_called_once_with("/labels")


class TestResolveParentId:
    @pytest.mark.asyncio
    async def test_exact_match(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_CATEGORIES

        result = await svc._resolve_parent_id("Work")
        assert result == "cat1"

    @pytest.mark.asyncio
    async def test_case_insensitive_match(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_CATEGORIES

        result = await svc._resolve_parent_id("PERSONAL")
        assert result == "cat2"

    @pytest.mark.asyncio
    async def test_substring_match(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_CATEGORIES

        result = await svc._resolve_parent_id("Side")
        assert result == "cat3"

    @pytest.mark.asyncio
    async def test_exact_preferred_over_substring(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = [
            {"_id": "a", "title": "Work"},
            {"_id": "b", "title": "Homework"},
        ]

        result = await svc._resolve_parent_id("Work")
        assert result == "a"

    @pytest.mark.asyncio
    async def test_exact_match_preferred_when_substring_also_matches(self) -> None:
        """Exact match on first loop should win over substring on second loop."""
        svc, mock = _make_service()
        # "Work" is both an exact match and a substring of "Homework"
        mock.get.return_value = [
            {"_id": "hw", "title": "Homework"},
            {"_id": "w", "title": "Work"},
        ]

        # Should find "Work" via exact match (first loop), not "Homework" via substring
        result = await svc._resolve_parent_id("Work")
        assert result == "w"

    @pytest.mark.asyncio
    async def test_no_match_raises(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_CATEGORIES

        with pytest.raises(ValueError, match="No category matching"):
            await svc._resolve_parent_id("nonexistent")


class TestGetChildrenValidation:
    @pytest.mark.asyncio
    async def test_both_args_raises(self) -> None:
        svc, _ = _make_service()
        with pytest.raises(ValueError, match="not both"):
            await svc.get_children(parent_id="x", parent_name="y")

    @pytest.mark.asyncio
    async def test_no_args_raises(self) -> None:
        svc, _ = _make_service()
        with pytest.raises(ValueError, match="either"):
            await svc.get_children()

    @pytest.mark.asyncio
    async def test_by_id_calls_api(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = [{"_id": "t1", "title": "Task"}]

        result = await svc.get_children(parent_id="cat1")
        assert len(result) == 1
        mock.get.assert_called_once_with("/children", params={"parentId": "cat1"})

    @pytest.mark.asyncio
    async def test_by_name_resolves_then_calls_api(self) -> None:
        svc, mock = _make_service()
        # First call is get_categories (for resolution), second is get_children
        mock.get.side_effect = [
            SAMPLE_CATEGORIES,
            [{"_id": "t1", "title": "Task"}],
        ]

        result = await svc.get_children(parent_name="Work")
        assert len(result) == 1
        assert mock.get.call_args_list[1][1] == {"params": {"parentId": "cat1"}}


class TestTrackTimeValidation:
    @pytest.mark.asyncio
    async def test_invalid_action_raises(self) -> None:
        svc, _ = _make_service()
        with pytest.raises(ValueError, match="START.*STOP"):
            await svc.track_time("x", "PAUSE")

    @pytest.mark.asyncio
    async def test_start_calls_api(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"ok": True}

        await svc.track_time("task1", "START")
        mock.post.assert_called_once_with(
            "/track", data={"taskId": "task1", "action": "START"}
        )


class TestCreateTask:
    @pytest.mark.asyncio
    async def test_basic_create(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"_id": "new1", "title": "Test"}

        result = await svc.create_task(title="Test")
        assert result["_id"] == "new1"
        mock.post.assert_called_once_with("/addTask", data={"title": "Test"})

    @pytest.mark.asyncio
    async def test_create_with_parent_name_resolves(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_CATEGORIES
        mock.post.return_value = {"_id": "new1", "title": "Test"}

        await svc.create_task(title="Test", parent_name="Work")
        call_data = mock.post.call_args[1]["data"]
        assert call_data["parentId"] == "cat1"

    @pytest.mark.asyncio
    async def test_create_invalidates_caches(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_CATEGORIES
        mock.post.return_value = {"_id": "new1", "title": "Test"}

        await svc.get_categories()
        await svc.get_labels()
        assert svc._categories_cache is not None

        await svc.create_task(title="Test")
        assert svc._categories_cache is None
        assert svc._labels_cache is None

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"_id": "new1", "title": "Test"}

        await svc.create_task(
            title="Test",
            day="2026-01-01",
            due_date="2026-01-05",
            parent_id="cat1",
            label_ids=["lbl1"],
            note="A note",
        )
        call_data = mock.post.call_args[1]["data"]
        assert call_data == {
            "title": "Test",
            "day": "2026-01-01",
            "dueDate": "2026-01-05",
            "parentId": "cat1",
            "labelIds": ["lbl1"],
            "note": "A note",
        }


class TestDeleteTask:
    @pytest.mark.asyncio
    async def test_delete_invalidates_caches(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_CATEGORIES
        mock.post.return_value = {}

        await svc.get_categories()
        assert svc._categories_cache is not None

        await svc.delete_task("task1")
        assert svc._categories_cache is None


class TestMarkDone:
    @pytest.mark.asyncio
    async def test_sends_timezone_offset(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"ok": True}

        await svc.mark_done("task1")
        call_data = mock.post.call_args[1]["data"]
        assert "timeZoneOffset" in call_data
        assert isinstance(call_data["timeZoneOffset"], int)
        assert call_data["itemId"] == "task1"

    @pytest.mark.asyncio
    async def test_timezone_offset_is_correct(self) -> None:
        """Verify the offset calculation matches the system timezone."""
        import datetime

        svc, mock = _make_service()
        mock.post.return_value = {"ok": True}

        await svc.mark_done("task1")
        call_data = mock.post.call_args[1]["data"]
        offset = call_data["timeZoneOffset"]

        # Compute expected offset independently
        utc_offset = datetime.datetime.now(datetime.UTC).astimezone().utcoffset()
        assert utc_offset is not None
        expected = -int(utc_offset.total_seconds()) // 60
        assert offset == expected


class TestUpdateTask:
    @pytest.mark.asyncio
    async def test_converts_setters_to_api_format(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"_id": "t1", "title": "Updated"}

        await svc.update_task("t1", setters={"title": "Updated", "day": "2026-01-01"})
        call_data = mock.post.call_args[1]["data"]
        assert call_data["itemId"] == "t1"
        setters = call_data["setters"]
        assert {"key": "title", "val": "Updated"} in setters
        assert {"key": "day", "val": "2026-01-01"} in setters


class TestSearch:
    @pytest.mark.asyncio
    async def test_returns_matches_with_children(self) -> None:
        svc, mock = _make_service()
        children = [{"_id": "t1", "title": "Task A"}]
        mock.get.side_effect = [
            SAMPLE_CATEGORIES,
            children,
        ]

        results = await svc.search("Work")
        assert len(results) == 1
        assert results[0]["title"] == "Work"
        assert results[0]["children"] == children

    @pytest.mark.asyncio
    async def test_no_match_returns_empty(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_CATEGORIES

        results = await svc.search("nonexistent999")
        assert results == []

    @pytest.mark.asyncio
    async def test_caps_at_max_results(self) -> None:
        svc, mock = _make_service()
        many_cats = [{"_id": f"c{i}", "title": f"Match {i}", "type": "project"} for i in range(10)]
        mock.get.side_effect = [
            many_cats,
            *([[] for _ in range(3)]),  # children for first 3 matches
        ]

        results = await svc.search("Match", max_results=3)
        assert len(results) == 3


class TestCreateEvent:
    @pytest.mark.asyncio
    async def test_converts_duration_to_milliseconds(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"_id": "evt1", "title": "Meeting"}

        await svc.create_event(title="Meeting", start="2026-01-01T09:00:00", duration_minutes=30)
        call_data = mock.post.call_args[1]["data"]
        assert call_data["length"] == 30 * 60 * 1000
        assert call_data["start"] == "2026-01-01T09:00:00"

    @pytest.mark.asyncio
    async def test_includes_note_when_provided(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"_id": "evt1", "title": "Meeting"}

        await svc.create_event(
            title="Meeting", start="2026-01-01T09:00:00", duration_minutes=30, note="Agenda items"
        )
        call_data = mock.post.call_args[1]["data"]
        assert call_data["note"] == "Agenda items"

    @pytest.mark.asyncio
    async def test_omits_note_when_none(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"_id": "evt1", "title": "Meeting"}

        await svc.create_event(title="Meeting", start="2026-01-01T09:00:00", duration_minutes=30)
        call_data = mock.post.call_args[1]["data"]
        assert "note" not in call_data
