# ABOUTME: Tests for markdown-based prompt loading and registration.
# ABOUTME: Validates parsing, registration with FastMCP, and error handling.

from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP

from amazing_marvin_mcp.prompts import load_prompt, register_prompts

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "src" / "amazing_marvin_mcp" / "prompts"


class TestLoadPrompt:
    def test_parses_description_from_first_line(self) -> None:
        desc, _body = load_prompt(PROMPTS_DIR / "plan_my_day.md")
        assert desc == "Plan your day by reviewing today's tasks, overdue items, and time blocks."

    def test_parses_body_after_blank_line(self) -> None:
        _, body = load_prompt(PROMPTS_DIR / "plan_my_day.md")
        assert body.startswith("Help me plan my day.")

    def test_body_does_not_include_description(self) -> None:
        desc, body = load_prompt(PROMPTS_DIR / "plan_my_day.md")
        assert desc not in body

    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_prompt(Path("/nonexistent/prompt.md"))

    def test_missing_blank_line_raises(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "no_separator.md"
        bad_file.write_text("Description only\nNo blank line before body")
        with pytest.raises(ValueError, match="blank line"):
            load_prompt(bad_file)


class TestRegisterPrompts:
    def test_registers_expected_prompts(self) -> None:
        app = FastMCP("test")
        register_prompts(app)
        prompt_names = {p.name for p in app._prompt_manager.list_prompts()}
        assert "plan_my_day" in prompt_names
        assert "weekly_review" in prompt_names

    @pytest.mark.asyncio
    async def test_prompt_body_matches_file_content(self) -> None:
        app = FastMCP("test")
        register_prompts(app)
        messages = await app._prompt_manager.render_prompt("plan_my_day", {})
        text = messages[0].content.text
        assert "Call get_today" in text
        assert "Call get_due" in text

    @pytest.mark.asyncio
    async def test_weekly_review_body_includes_inbox(self) -> None:
        app = FastMCP("test")
        register_prompts(app)
        messages = await app._prompt_manager.render_prompt("weekly_review", {})
        text = messages[0].content.text
        assert "get_inbox" in text

    def test_prompt_descriptions_are_set(self) -> None:
        app = FastMCP("test")
        register_prompts(app)
        prompts = {p.name: p for p in app._prompt_manager.list_prompts()}
        assert prompts["plan_my_day"].description is not None
        assert len(prompts["plan_my_day"].description) > 0
