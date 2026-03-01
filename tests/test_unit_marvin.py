# ABOUTME: Unit tests for MarvinService business logic with mocked HTTP client.
# ABOUTME: Tests caching, name resolution, validation, and timezone without network calls.

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

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


class TestServiceLifecycle:
    @pytest.mark.asyncio
    async def test_async_context_manager_delegates_close(self) -> None:
        async with MarvinService(api_token="fake-token") as svc:
            mock_client = AsyncMock()
            svc._client = mock_client
        mock_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_context_manager_closes_on_exception(self) -> None:
        svc = MarvinService(api_token="fake-token")
        mock_client = AsyncMock()
        svc._client = mock_client
        with pytest.raises(RuntimeError, match="boom"):
            async with svc:
                raise RuntimeError("boom")
        mock_client.close.assert_awaited_once()


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


class TestGetDueBackburner:
    @pytest.mark.asyncio
    async def test_excludes_backburner_by_default(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = [
            {"_id": "t1", "title": "Overdue"},
            {"_id": "t2", "title": "Deferred", "backburner": True},
        ]

        result = await svc.get_due()
        assert len(result) == 1
        assert result[0]["title"] == "Overdue"

    @pytest.mark.asyncio
    async def test_backburner_only(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = [
            {"_id": "t1", "title": "Overdue"},
            {"_id": "t2", "title": "Deferred", "backburner": True},
        ]

        result = await svc.get_due(backburner="only")
        assert len(result) == 1
        assert result[0]["title"] == "Deferred"


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

    @pytest.mark.asyncio
    async def test_excludes_backburner_by_default(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = [
            {"_id": "t1", "title": "Active"},
            {"_id": "t2", "title": "Deferred", "backburner": True},
        ]

        result = await svc.get_children(parent_id="cat1")
        assert len(result) == 1
        assert result[0]["title"] == "Active"

    @pytest.mark.asyncio
    async def test_backburner_only(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = [
            {"_id": "t1", "title": "Active"},
            {"_id": "t2", "title": "Deferred", "backburner": True},
        ]

        result = await svc.get_children(parent_id="cat1", backburner="only")
        assert len(result) == 1
        assert result[0]["title"] == "Deferred"


class TestTrackTimeValidation:
    @pytest.mark.asyncio
    async def test_invalid_action_raises(self) -> None:
        svc, _ = _make_service()
        with pytest.raises(ValueError, match=r"START.*STOP"):
            await svc.track_time("x", "PAUSE")

    @pytest.mark.asyncio
    async def test_start_calls_api(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"ok": True}

        await svc.track_time("task1", "START")
        mock.post.assert_called_once_with("/track", data={"taskId": "task1", "action": "START"})


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

    @pytest.mark.asyncio
    async def test_create_with_extra_fields_calls_update(self) -> None:
        svc, mock = _make_service()
        # /addTask returns created task; /doc/update returns updated task
        mock.post.side_effect = [
            {"_id": "new1", "title": "Test"},
            {"_id": "new1", "title": "Test", "energyAmount": 1},
        ]

        result = await svc.create_task(title="Test", extra_fields={"energyAmount": 1})

        assert mock.post.call_count == 2
        # First call: /addTask with no extra fields in body
        first_call = mock.post.call_args_list[0]
        assert first_call[0][0] == "/addTask"
        assert "energyAmount" not in first_call[1]["data"]
        # Second call: /doc/update with setters
        second_call = mock.post.call_args_list[1]
        assert second_call[0][0] == "/doc/update"
        update_body = second_call[1]["data"]
        assert update_body["itemId"] == "new1"
        assert {"key": "energyAmount", "val": 1} in update_body["setters"]
        # Result is from the update call
        assert result["energyAmount"] == 1

    @pytest.mark.asyncio
    async def test_create_without_extra_fields_does_not_call_update(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"_id": "new1", "title": "Test"}

        await svc.create_task(title="Test")

        mock.post.assert_called_once_with("/addTask", data={"title": "Test"})

    @pytest.mark.asyncio
    async def test_create_with_empty_extra_fields_does_not_call_update(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"_id": "new1", "title": "Test"}

        await svc.create_task(title="Test", extra_fields={})

        mock.post.assert_called_once_with("/addTask", data={"title": "Test"})


class TestDeleteItem:
    @pytest.mark.asyncio
    async def test_delete_invalidates_caches(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_CATEGORIES
        mock.post.return_value = {}

        await svc.get_categories()
        assert svc._categories_cache is not None

        await svc.delete_item("task1")
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
    async def test_null_utcoffset_uses_zero(self) -> None:
        """When utcoffset() returns None, offset should default to 0."""
        svc, mock = _make_service()
        mock.post.return_value = {"ok": True}

        # Create a mock datetime whose astimezone().utcoffset() returns None
        mock_dt = MagicMock()
        mock_dt.astimezone.return_value.utcoffset.return_value = None

        with patch("amazing_marvin_mcp.marvin.datetime") as mock_datetime:
            mock_datetime.UTC = __import__("datetime").UTC
            mock_datetime.datetime.now.return_value = mock_dt

            await svc.mark_done("task1")

        call_data = mock.post.call_args[1]["data"]
        assert call_data["timeZoneOffset"] == 0

    @pytest.mark.asyncio
    async def test_timezone_offset_is_correct(self) -> None:
        """Verify the offset calculation for a known non-zero timezone."""
        import datetime

        svc, mock = _make_service()
        mock.post.return_value = {"ok": True}

        # Simulate UTC-7 (e.g., US Mountain Time): utcoffset = -7h = -25200s
        mock_dt = MagicMock()
        mock_dt.astimezone.return_value.utcoffset.return_value = datetime.timedelta(hours=-7)

        with patch("amazing_marvin_mcp.marvin.datetime") as mock_datetime:
            mock_datetime.UTC = datetime.UTC
            mock_datetime.datetime.now.return_value = mock_dt

            await svc.mark_done("task1")

        call_data = mock.post.call_args[1]["data"]
        # -(-25200) // 60 = 420 minutes west of UTC
        assert call_data["timeZoneOffset"] == 420


class TestUpdateItem:
    @pytest.mark.asyncio
    async def test_converts_setters_to_api_format(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"_id": "t1", "title": "Updated"}

        await svc.update_item("t1", setters={"title": "Updated", "day": "2026-01-01"})
        call_data = mock.post.call_args[1]["data"]
        assert call_data["itemId"] == "t1"
        setters = call_data["setters"]
        assert {"key": "title", "val": "Updated"} in setters
        assert {"key": "day", "val": "2026-01-01"} in setters

    @pytest.mark.asyncio
    async def test_update_item_with_attribute_setters(self) -> None:
        """update_item passes attribute setters as API setter objects."""
        svc, mock = _make_service()
        mock.post.return_value = {"_id": "abc", "title": "T", "energyAmount": 2}

        result = await svc.update_item("abc", setters={"energyAmount": 2, "isPhysical": True})
        call_data = mock.post.call_args[1]["data"]
        assert call_data["itemId"] == "abc"
        setters_list = call_data["setters"]
        setters_dict = {s["key"]: s["val"] for s in setters_list}
        assert setters_dict["energyAmount"] == 2
        assert setters_dict["isPhysical"] is True
        assert result == {"_id": "abc", "title": "T", "energyAmount": 2}


class TestUpdateItemBackburner:
    @pytest.mark.asyncio
    async def test_backburner_setter_passed_to_api(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"_id": "t1", "title": "Task", "backburner": True}

        await svc.update_item("t1", setters={"backburner": True})
        call_data = mock.post.call_args[1]["data"]
        assert {"key": "backburner", "val": True} in call_data["setters"]


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

    @pytest.mark.asyncio
    async def test_excludes_backburner_children_by_default(self) -> None:
        svc, mock = _make_service()
        children = [
            {"_id": "t1", "title": "Active"},
            {"_id": "t2", "title": "Deferred", "backburner": True},
        ]
        mock.get.side_effect = [SAMPLE_CATEGORIES, children]

        results = await svc.search("Work")
        assert len(results) == 1
        assert len(results[0]["children"]) == 1
        assert results[0]["children"][0]["title"] == "Active"

    @pytest.mark.asyncio
    async def test_excludes_backburner_categories_by_default(self) -> None:
        svc, mock = _make_service()
        categories = [
            {"_id": "cat1", "title": "Work", "type": "project"},
            {"_id": "cat2", "title": "Work Archive", "type": "project", "backburner": True},
        ]
        # categories call + children for cat1 only (cat2 is filtered before fetch)
        mock.get.side_effect = [categories, [{"_id": "t1", "title": "Task"}]]

        results = await svc.search("Work")
        # Only cat1 ("Work") should appear; cat2 ("Work Archive") is backburner
        assert len(results) == 1
        assert results[0]["title"] == "Work"

    @pytest.mark.asyncio
    async def test_backburner_only_returns_backburner_categories(self) -> None:
        svc, mock = _make_service()
        categories = [
            {"_id": "cat1", "title": "Work", "type": "project"},
            {"_id": "cat2", "title": "Work Archive", "type": "project", "backburner": True},
        ]
        # categories call + children for cat2 only (cat1 should be skipped)
        mock.get.side_effect = [categories, []]

        results = await svc.search("Work", backburner="only")
        assert len(results) == 1
        assert results[0]["title"] == "Work Archive"

    @pytest.mark.asyncio
    async def test_search_backburner_only_filters_categories_and_children(self) -> None:
        """With backburner='only', both categories and children are filtered to backburner items."""
        svc, mock = _make_service()
        categories = [
            {"_id": "cat1", "title": "Work", "type": "project"},
            {"_id": "cat2", "title": "Work Someday", "type": "project", "backburner": True},
        ]
        children = [
            {"_id": "t1", "title": "Active child"},
            {"_id": "t2", "title": "Backburner child", "backburner": True},
        ]
        mock.get.side_effect = [categories, children]

        results = await svc.search("Work", backburner="only")
        # Only cat2 (backburner category) should appear
        assert len(results) == 1
        assert results[0]["title"] == "Work Someday"
        # Only backburner children should be included
        assert len(results[0]["children"]) == 1
        assert results[0]["children"][0]["title"] == "Backburner child"

    @pytest.mark.asyncio
    async def test_default_max_results_is_five(self) -> None:
        """Without explicit max_results, search should return at most 5 matches."""
        svc, mock = _make_service()
        many_cats = [{"_id": f"c{i}", "title": f"Item {i}", "type": "project"} for i in range(10)]
        mock.get.side_effect = [
            many_cats,
            *([[] for _ in range(5)]),  # children for 5 matches
        ]

        results = await svc.search("Item")
        assert len(results) == 5


class TestGetInbox:
    @pytest.mark.asyncio
    async def test_calls_children_with_unassigned(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = [{"_id": "t1", "title": "Inbox Task", "parentId": "unassigned"}]

        result = await svc.get_inbox()
        assert len(result) == 1
        assert result[0]["title"] == "Inbox Task"
        mock.get.assert_called_once_with("/children", params={"parentId": "unassigned"})

    @pytest.mark.asyncio
    async def test_returns_empty_list(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = []

        result = await svc.get_inbox()
        assert result == []

    @pytest.mark.asyncio
    async def test_excludes_backburner_by_default(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = [
            {"_id": "t1", "title": "Active"},
            {"_id": "t2", "title": "Deferred", "backburner": True},
        ]

        result = await svc.get_inbox()
        assert len(result) == 1
        assert result[0]["title"] == "Active"

    @pytest.mark.asyncio
    async def test_backburner_only(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = [
            {"_id": "t1", "title": "Active"},
            {"_id": "t2", "title": "Deferred", "backburner": True},
        ]

        result = await svc.get_inbox(backburner="only")
        assert len(result) == 1
        assert result[0]["title"] == "Deferred"

    @pytest.mark.asyncio
    async def test_backburner_include(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = [
            {"_id": "t1", "title": "Active"},
            {"_id": "t2", "title": "Deferred", "backburner": True},
        ]

        result = await svc.get_inbox(backburner="include")
        assert len(result) == 2


class TestResolveLabelIds:
    @pytest.mark.asyncio
    async def test_exact_match(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_LABELS

        result = await svc.resolve_label_ids(["Urgent"])
        assert result == ["lbl1"]

    @pytest.mark.asyncio
    async def test_case_insensitive_match(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_LABELS

        result = await svc.resolve_label_ids(["urgent"])
        assert result == ["lbl1"]

    @pytest.mark.asyncio
    async def test_case_insensitive_match_uppercase(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_LABELS

        result = await svc.resolve_label_ids(["LOW PRIORITY"])
        assert result == ["lbl2"]

    @pytest.mark.asyncio
    async def test_multiple_labels(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_LABELS

        result = await svc.resolve_label_ids(["Urgent", "Low Priority"])
        assert result == ["lbl1", "lbl2"]

    @pytest.mark.asyncio
    async def test_no_match_raises(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_LABELS

        with pytest.raises(ValueError, match="No label matching 'nonexistent'"):
            await svc.resolve_label_ids(["nonexistent"])

    @pytest.mark.asyncio
    async def test_no_substring_matching(self) -> None:
        """Only exact matches should work, not substring matches."""
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_LABELS

        with pytest.raises(ValueError, match="No label matching 'Urg'"):
            await svc.resolve_label_ids(["Urg"])

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_LABELS

        result = await svc.resolve_label_ids([])
        assert result == []

    @pytest.mark.asyncio
    async def test_uses_labels_cache(self) -> None:
        """Should use cached labels, not fetch every time."""
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_LABELS

        await svc.resolve_label_ids(["Urgent"])
        await svc.resolve_label_ids(["Low Priority"])

        # get_labels caches after first call, so only one GET
        mock.get.assert_called_once_with("/labels")


class TestCreateProject:
    @pytest.mark.asyncio
    async def test_basic_create(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"_id": "proj1", "title": "My Project", "type": "project"}

        result = await svc.create_project(title="My Project")
        assert result["_id"] == "proj1"
        mock.post.assert_called_once_with(
            "/addProject", data={"title": "My Project", "type": "project"}
        )

    @pytest.mark.asyncio
    async def test_create_category(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"_id": "cat1", "title": "My Folder", "type": "category"}

        result = await svc.create_project(title="My Folder", type="category")
        assert result["type"] == "category"
        call_data = mock.post.call_args[1]["data"]
        assert call_data["type"] == "category"

    @pytest.mark.asyncio
    async def test_create_with_parent_name_resolves(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_CATEGORIES
        mock.post.return_value = {"_id": "proj1", "title": "Sub Project", "type": "project"}

        await svc.create_project(title="Sub Project", parent_name="Work")
        call_data = mock.post.call_args[1]["data"]
        assert call_data["parentId"] == "cat1"

    @pytest.mark.asyncio
    async def test_create_invalidates_caches(self) -> None:
        svc, mock = _make_service()
        mock.get.return_value = SAMPLE_CATEGORIES
        mock.post.return_value = {"_id": "proj1", "title": "Test", "type": "project"}

        await svc.get_categories()
        await svc.get_labels()
        assert svc._categories_cache is not None

        await svc.create_project(title="Test")
        assert svc._categories_cache is None
        assert svc._labels_cache is None

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self) -> None:
        svc, mock = _make_service()
        mock.post.return_value = {"_id": "proj1", "title": "Full Project", "type": "project"}

        await svc.create_project(
            title="Full Project",
            type="project",
            parent_id="cat1",
            day="2026-01-01",
            due_date="2026-01-05",
            label_ids=["lbl1"],
            note="A note",
            priority="high",
        )
        call_data = mock.post.call_args[1]["data"]
        assert call_data == {
            "title": "Full Project",
            "type": "project",
            "parentId": "cat1",
            "day": "2026-01-01",
            "dueDate": "2026-01-05",
            "labelIds": ["lbl1"],
            "note": "A note",
            "priority": "high",
        }


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
