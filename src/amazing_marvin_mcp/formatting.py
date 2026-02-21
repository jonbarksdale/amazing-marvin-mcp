# ABOUTME: Response formatting utilities for Amazing Marvin data.
# ABOUTME: Converts API JSON to markdown and handles response trimming.

from __future__ import annotations

CHARACTER_LIMIT: int = 25_000
NOTES_LIMIT: int = 500

TRUNCATION_MESSAGE = "\n\n[truncated — use filters to narrow results]"


def truncate_response(text: str) -> str:
    """Cut response at nearest newline before CHARACTER_LIMIT and append truncation notice."""
    if len(text) <= CHARACTER_LIMIT:
        return text

    # Find last newline before the limit
    cut = text.rfind("\n", 0, CHARACTER_LIMIT)
    if cut == -1:
        cut = CHARACTER_LIMIT

    return text[:cut] + TRUNCATION_MESSAGE


def trim_notes(notes: str | None) -> str:
    """Cap notes at NOTES_LIMIT characters, appending '[...]' if trimmed."""
    if notes is None:
        return ""
    if len(notes) <= NOTES_LIMIT:
        return notes
    return notes[:NOTES_LIMIT] + "[...]"


def format_task(task: dict[str, object]) -> str:
    """Format a single task as a markdown checklist line with ID and optional fields."""
    done = task.get("done", False)
    checkbox = "[x]" if done else "[ ]"
    title = task.get("title", "Untitled")
    task_id = task.get("_id", "?")

    line = f"- {checkbox} **{title}** (id: {task_id})"

    due = task.get("dueDate")
    if due:
        line += f" — due: {due}"

    day = task.get("day")
    if day:
        line += f" — scheduled: {day}"

    raw_notes = task.get("note")
    if raw_notes:
        trimmed = trim_notes(str(raw_notes))
        line += f"\n  Notes: {trimmed}"

    return line


def format_tasks_list(tasks: list[dict[str, object]], heading: str) -> str:
    """Format a list of tasks under a heading. Shows 'No items' when empty."""
    if not tasks:
        return f"## {heading}\n\nNo items found."

    lines = [f"## {heading}\n"]
    for t in tasks:
        lines.append(format_task(t))

    return truncate_response("\n".join(lines))


def format_categories_tree(categories: list[dict[str, object]]) -> str:
    """Build an indented tree of categories/projects from parentId relationships."""
    # Index by id
    by_id: dict[str, dict[str, object]] = {str(c["_id"]): c for c in categories}

    # Group children by parentId
    children: dict[str | None, list[dict[str, object]]] = {}
    for c in categories:
        pid = c.get("parentId")
        parent_key = str(pid) if pid and str(pid) in by_id else None
        children.setdefault(parent_key, []).append(c)

    lines: list[str] = ["## Categories\n"]

    def _render(parent_key: str | None, depth: int) -> None:
        for cat in children.get(parent_key, []):
            indent = "  " * depth
            cat_type = cat.get("type", "project")
            icon = "📁" if cat_type == "folder" else "📋"
            cat_title = cat.get("title", "Untitled")
            cat_id = cat.get("_id")
            lines.append(f"{indent}- {icon} **{cat_title}** (id: {cat_id})")
            _render(str(cat["_id"]), depth + 1)

    _render(None, 0)

    return truncate_response("\n".join(lines))


def format_time_blocks(blocks: list[dict[str, object]]) -> str:
    """Format time blocks as a markdown list. Shows message when empty."""
    if not blocks:
        return "## Time Blocks\n\nNo time blocks found."

    lines = ["## Time Blocks\n"]
    for b in blocks:
        title = b.get("title", "Untitled")
        start = b.get("start", "?")
        end = b.get("end", "?")
        lines.append(f"- **{title}** {start}–{end}")

    return truncate_response("\n".join(lines))
