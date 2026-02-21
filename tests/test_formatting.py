# ABOUTME: Tests for response formatting utilities.
# ABOUTME: Validates markdown conversion, truncation, and notes trimming.

from amazing_marvin_mcp.formatting import (
    CHARACTER_LIMIT,
    NOTES_LIMIT,
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

    def test_task_with_long_notes_trimmed(self) -> None:
        task = {"_id": "abc123", "title": "Buy milk", "note": "x" * 1000}
        result = format_task(task)
        assert "[...]" in result


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
