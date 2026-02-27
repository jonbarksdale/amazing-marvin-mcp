# ABOUTME: Tests for response formatting utilities.
# ABOUTME: Validates markdown conversion, truncation, and notes trimming.

import pytest

from amazing_marvin_mcp.formatting import (
    CHARACTER_LIMIT,
    NOTES_LIMIT,
    TRUNCATION_MESSAGE,
    filter_backburner,
    format_categories_tree,
    format_labels,
    format_search_results,
    format_task,
    format_tasks_list,
    format_time_blocks,
    trim_notes,
    truncate_response,
)


class TestTruncateResponse:
    def test_short_response_unchanged(self) -> None:
        text = "Short response"
        assert truncate_response(text) == text

    def test_long_response_truncated_at_newline(self) -> None:
        lines = [f"Line {i}" for i in range(5000)]
        text = "\n".join(lines)
        result = truncate_response(text)
        assert len(result) <= CHARACTER_LIMIT + 100
        assert result.endswith("[truncated — use filters to narrow results]")

    def test_truncation_preserves_complete_lines(self) -> None:
        text = "a" * 24000 + "\n" + "b" * 2000
        result = truncate_response(text)
        # Should not end with partial b's line
        assert not result.rstrip().endswith("bbb")

    def test_exact_character_limit_not_truncated(self) -> None:
        """Text of exactly CHARACTER_LIMIT length should be returned as-is."""
        text = "x" * CHARACTER_LIMIT
        assert truncate_response(text) == text

    def test_one_over_limit_is_truncated(self) -> None:
        """Text one character over CHARACTER_LIMIT should be truncated."""
        text = "x" * (CHARACTER_LIMIT + 1)
        result = truncate_response(text)
        assert result.endswith("[truncated — use filters to narrow results]")

    def test_long_string_no_newlines(self) -> None:
        """When no newline exists, truncation cuts at CHARACTER_LIMIT exactly."""
        text = "x" * (CHARACTER_LIMIT + 500)
        result = truncate_response(text)
        # With no newline, cut should be at CHARACTER_LIMIT
        expected = "x" * CHARACTER_LIMIT + TRUNCATION_MESSAGE
        assert result == expected

    def test_newline_only_at_position_zero(self) -> None:
        """When the only newline is at position 0, rfind should find it."""
        text = "\n" + "x" * (CHARACTER_LIMIT + 500)
        result = truncate_response(text)
        # rfind("\n", 0, CHARACTER_LIMIT) should find the newline at position 0
        # text[:0] is empty, then TRUNCATION_MESSAGE is appended
        assert result == TRUNCATION_MESSAGE


class TestTrimNotes:
    def test_short_notes_unchanged(self) -> None:
        assert trim_notes("Short note") == "Short note"

    def test_long_notes_trimmed(self) -> None:
        long_note = "x" * 1000
        result = trim_notes(long_note)
        assert len(result) <= NOTES_LIMIT + 10
        assert result.endswith("[...]")

    def test_none_notes_returns_empty(self) -> None:
        assert trim_notes(None) == ""

    def test_exact_notes_limit_not_trimmed(self) -> None:
        """Notes of exactly NOTES_LIMIT length should be returned as-is."""
        notes = "y" * NOTES_LIMIT
        assert trim_notes(notes) == notes

    def test_one_over_notes_limit_is_trimmed(self) -> None:
        """Notes one character over NOTES_LIMIT should be trimmed."""
        notes = "y" * (NOTES_LIMIT + 1)
        result = trim_notes(notes)
        assert result == "y" * NOTES_LIMIT + "[...]"


class TestFormatTask:
    def test_basic_task(self) -> None:
        task = {"_id": "abc123", "title": "Buy milk", "done": False}
        result = format_task(task)
        assert "Buy milk" in result
        assert "abc123" in result

    def test_task_with_due_date(self) -> None:
        task = {"_id": "abc123", "title": "Buy milk", "dueDate": "2026-02-25"}
        result = format_task(task)
        assert "2026-02-25" in result

    def test_done_task_shows_checked_box(self) -> None:
        task = {"_id": "abc123", "title": "Buy milk", "done": True}
        result = format_task(task)
        assert "[x]" in result
        assert "[ ]" not in result

    def test_undone_task_shows_unchecked_box(self) -> None:
        task = {"_id": "abc123", "title": "Buy milk", "done": False}
        result = format_task(task)
        assert "[ ]" in result
        assert "[x]" not in result

    def test_task_with_day_shows_scheduled(self) -> None:
        task = {"_id": "abc123", "title": "Buy milk", "day": "2026-02-25"}
        result = format_task(task)
        assert "scheduled: 2026-02-25" in result

    def test_task_with_short_notes(self) -> None:
        task = {"_id": "abc123", "title": "Buy milk", "note": "Get 2%"}
        result = format_task(task)
        assert "Notes: Get 2%" in result

    def test_task_with_long_notes_trimmed(self) -> None:
        task = {"_id": "abc123", "title": "Buy milk", "note": "x" * 1000}
        result = format_task(task)
        assert "[...]" in result

    def test_task_missing_done_key_shows_unchecked(self) -> None:
        """When 'done' key is absent, task should default to unchecked."""
        task = {"_id": "abc123", "title": "Buy milk"}
        result = format_task(task)
        assert "[ ]" in result
        assert "[x]" not in result

    def test_backburner_task_shows_indicator(self) -> None:
        task = {"_id": "abc123", "title": "Someday task", "backburner": True}
        result = format_task(task)
        assert "[backburner]" in result

    def test_non_backburner_task_no_indicator(self) -> None:
        task = {"_id": "abc123", "title": "Active task", "backburner": False}
        result = format_task(task)
        assert "[backburner]" not in result

    def test_missing_backburner_field_no_indicator(self) -> None:
        task = {"_id": "abc123", "title": "Normal task"}
        result = format_task(task)
        assert "[backburner]" not in result

    def test_project_type_shows_indicator(self) -> None:
        task = {"_id": "abc123", "title": "My Project", "type": "project"}
        result = format_task(task)
        assert "[project]" in result

    def test_category_type_shows_indicator(self) -> None:
        task = {"_id": "abc123", "title": "My Folder", "type": "category"}
        result = format_task(task)
        assert "[category]" in result

    def test_task_type_no_indicator(self) -> None:
        task = {"_id": "abc123", "title": "A task", "type": "task"}
        result = format_task(task)
        assert "[task]" not in result

    def test_missing_type_no_indicator(self) -> None:
        task = {"_id": "abc123", "title": "A task"}
        result = format_task(task)
        assert "[project]" not in result
        assert "[category]" not in result


class TestFormatTasksList:
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
    def test_flat_categories(self) -> None:
        categories = [
            {"_id": "1", "title": "Work", "type": "project"},
            {"_id": "2", "title": "Personal", "type": "project"},
        ]
        result = format_categories_tree(categories)
        assert "Work" in result
        assert "Personal" in result

    def test_folder_type_shows_folder_icon(self) -> None:
        categories = [{"_id": "1", "title": "Archive", "type": "folder"}]
        result = format_categories_tree(categories)
        assert "📁" in result
        assert "📋" not in result

    def test_project_type_shows_project_icon(self) -> None:
        categories = [{"_id": "1", "title": "Work", "type": "project"}]
        result = format_categories_tree(categories)
        assert "📋" in result
        assert "📁" not in result

    def test_nested_categories(self) -> None:
        categories = [
            {"_id": "1", "title": "Work", "type": "project"},
            {"_id": "2", "title": "Backend", "type": "project", "parentId": "1"},
        ]
        result = format_categories_tree(categories)
        assert "Work" in result
        assert "Backend" in result
        # Child should be indented more than parent
        lines = result.split("\n")
        work_line = next(line for line in lines if "Work" in line)
        backend_line = next(line for line in lines if "Backend" in line)
        work_indent = len(work_line) - len(work_line.lstrip())
        backend_indent = len(backend_line) - len(backend_line.lstrip())
        assert backend_indent > work_indent

    def test_orphan_parent_id_treated_as_root(self) -> None:
        """Category with parentId pointing to nonexistent ID should be a root item."""
        categories = [
            {"_id": "1", "title": "Root", "type": "project"},
            {"_id": "2", "title": "Orphan", "type": "project", "parentId": "nonexistent"},
        ]
        result = format_categories_tree(categories)
        lines = [line for line in result.split("\n") if line.strip().startswith("-")]
        root_line = next(line for line in lines if "Root" in line)
        orphan_line = next(line for line in lines if "Orphan" in line)
        # Both should be at root level (same indentation)
        root_indent = len(root_line) - len(root_line.lstrip())
        orphan_indent = len(orphan_line) - len(orphan_line.lstrip())
        assert root_indent == orphan_indent

    def test_four_level_nesting_indentation(self) -> None:
        """4 levels of nesting should produce increasing indentation at each level."""
        categories = [
            {"_id": "1", "title": "Level0", "type": "folder"},
            {"_id": "2", "title": "Level1", "type": "project", "parentId": "1"},
            {"_id": "3", "title": "Level2", "type": "project", "parentId": "2"},
            {"_id": "4", "title": "Level3", "type": "project", "parentId": "3"},
        ]
        result = format_categories_tree(categories)
        lines = result.split("\n")

        def indent_of(label: str) -> int:
            line = next(ln for ln in lines if label in ln)
            return len(line) - len(line.lstrip())

        assert indent_of("Level0") == 0
        assert indent_of("Level1") == 2
        assert indent_of("Level2") == 4
        assert indent_of("Level3") == 6

    def test_root_items_have_no_leading_whitespace(self) -> None:
        """Root-level categories should have no indentation."""
        categories = [
            {"_id": "1", "title": "RootItem", "type": "project"},
        ]
        result = format_categories_tree(categories)
        root_line = next(line for line in result.split("\n") if "RootItem" in line)
        assert root_line.startswith("- ")


class TestFormatTimeBlocks:
    def test_empty_blocks(self) -> None:
        result = format_time_blocks([])
        assert "no time blocks" in result.lower()

    def test_blocks_with_times(self) -> None:
        blocks = [
            {"_id": "1", "title": "Deep Work", "start": "09:00", "end": "11:00"},
        ]
        result = format_time_blocks(blocks)
        assert "Deep Work" in result


class TestFormatLabels:
    def test_empty_labels(self) -> None:
        result = format_labels([])
        assert "no labels" in result.lower()

    def test_labels_with_data(self) -> None:
        labels = [
            {"_id": "l1", "title": "Urgent"},
            {"_id": "l2", "title": "Low Priority"},
        ]
        result = format_labels(labels)
        assert "Urgent" in result
        assert "l1" in result
        assert "Low Priority" in result


class TestFormatSearchResults:
    def test_no_results(self) -> None:
        result = format_search_results("foo", [])
        assert "No results" in result
        assert "foo" in result

    def test_results_with_children(self) -> None:
        matches = [
            {
                "_id": "cat1",
                "title": "Work",
                "children": [
                    {"_id": "t1", "title": "Task A"},
                ],
            },
        ]
        result = format_search_results("work", matches)
        assert "Work" in result
        assert "Task A" in result
        assert "cat1" in result

    def test_results_no_children(self) -> None:
        matches = [{"_id": "cat1", "title": "Empty Project", "children": []}]
        result = format_search_results("empty", matches)
        assert "No child tasks" in result

    def test_children_not_a_list_shows_no_children(self) -> None:
        matches = [{"_id": "cat1", "title": "Weird", "children": "not-a-list"}]
        result = format_search_results("weird", matches)
        assert "No child tasks" in result

    def test_non_dict_children_skipped(self) -> None:
        children = ["string", {"_id": "t1", "title": "Real"}]
        matches = [{"_id": "cat1", "title": "Mixed", "children": children}]
        result = format_search_results("mixed", matches)
        assert "Real" in result
        assert "string" not in result.split("Mixed")[1]  # "string" shouldn't appear as a task


class TestFilterBackburner:
    def test_default_excludes_backburner(self) -> None:
        tasks: list[dict[str, object]] = [
            {"_id": "1", "title": "Active"},
            {"_id": "2", "title": "Deferred", "backburner": True},
        ]
        result = filter_backburner(tasks, None)
        assert len(result) == 1
        assert result[0]["title"] == "Active"

    def test_only_returns_backburner_items(self) -> None:
        tasks: list[dict[str, object]] = [
            {"_id": "1", "title": "Active"},
            {"_id": "2", "title": "Deferred", "backburner": True},
        ]
        result = filter_backburner(tasks, "only")
        assert len(result) == 1
        assert result[0]["title"] == "Deferred"

    def test_include_returns_all(self) -> None:
        tasks: list[dict[str, object]] = [
            {"_id": "1", "title": "Active"},
            {"_id": "2", "title": "Deferred", "backburner": True},
        ]
        result = filter_backburner(tasks, "include")
        assert len(result) == 2

    def test_default_keeps_items_without_backburner_field(self) -> None:
        tasks: list[dict[str, object]] = [{"_id": "1", "title": "Normal"}]
        result = filter_backburner(tasks, None)
        assert len(result) == 1

    def test_default_excludes_backburner_false(self) -> None:
        """Items with backburner=False should NOT be excluded."""
        tasks: list[dict[str, object]] = [{"_id": "1", "title": "Active", "backburner": False}]
        result = filter_backburner(tasks, None)
        assert len(result) == 1

    def test_invalid_value_raises(self) -> None:
        tasks: list[dict[str, object]] = [{"_id": "1", "title": "Task"}]
        with pytest.raises(ValueError, match="backburner"):
            filter_backburner(tasks, "foo")
