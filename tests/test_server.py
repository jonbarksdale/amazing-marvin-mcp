# ABOUTME: Tests for the MCP server adapter layer.
# ABOUTME: Validates tool registration and prompt registration.

import pytest

from amazing_marvin_mcp.server import _validate_date, _validate_datetime, mcp


class TestServerSetup:
    def test_server_has_expected_tools(self) -> None:
        tool_names = {t.name for t in mcp._tool_manager.list_tools()}
        expected = {
            "get_today",
            "get_due",
            "get_categories",
            "get_children",
            "get_inbox",
            "get_labels",
            "get_time_blocks",
            "search",
            "create_task",
            "create_event",
            "update_item",
            "mark_done",
            "delete_item",
            "track_time",
        }
        missing = expected - tool_names
        extra = tool_names - expected
        assert tool_names == expected, f"Missing: {missing}, Extra: {extra}"

    def test_server_has_prompts(self) -> None:
        prompt_names = {p.name for p in mcp._prompt_manager.list_prompts()}
        assert "plan_my_day" in prompt_names
        assert "weekly_review" in prompt_names

    def test_tool_count(self) -> None:
        tools = mcp._tool_manager.list_tools()
        assert len(tools) == 14  # 8 read + 6 write

    def test_read_tools_have_read_only_annotation(self) -> None:
        read_tools = {
            "get_today",
            "get_due",
            "get_categories",
            "get_children",
            "get_inbox",
            "get_labels",
            "get_time_blocks",
            "search",
        }
        tools = {t.name: t for t in mcp._tool_manager.list_tools()}
        for name in read_tools:
            ann = tools[name].annotations
            assert ann is not None, f"{name} missing annotations"
            assert ann.readOnlyHint is True, f"{name} should be readOnly"
            assert ann.destructiveHint is False, f"{name} should not be destructive"

    def test_write_tools_have_write_annotation(self) -> None:
        write_tools = {
            "create_task",
            "create_event",
            "track_time",
        }
        tools = {t.name: t for t in mcp._tool_manager.list_tools()}
        for name in write_tools:
            ann = tools[name].annotations
            assert ann is not None, f"{name} missing annotations"
            assert ann.readOnlyHint is False, f"{name} should not be readOnly"
            assert ann.destructiveHint is False, f"{name} should not be destructive"
            assert ann.idempotentHint is None, f"{name} should not be idempotent"

    def test_idempotent_tools_have_idempotent_annotation(self) -> None:
        idempotent_tools = {"update_item", "mark_done"}
        tools = {t.name: t for t in mcp._tool_manager.list_tools()}
        for name in idempotent_tools:
            ann = tools[name].annotations
            assert ann is not None, f"{name} missing annotations"
            assert ann.readOnlyHint is False, f"{name} should not be readOnly"
            assert ann.destructiveHint is False, f"{name} should not be destructive"
            assert ann.idempotentHint is True, f"{name} should be idempotent"

    def test_server_has_instructions(self) -> None:
        assert mcp.instructions is not None
        assert len(mcp.instructions) > 0

    def test_backburner_params_use_literal_type(self) -> None:
        """Backburner params should expose allowed values in JSON schema."""
        tools = {t.name: t for t in mcp._tool_manager.list_tools()}
        for name in ("get_due", "get_inbox", "get_children", "search"):
            schema = tools[name].parameters
            backburner_prop = schema["properties"]["backburner"]
            # Literal types produce an "enum" key in JSON schema (possibly nested in anyOf)
            any_of = backburner_prop.get("anyOf", [])
            has_enum = "enum" in backburner_prop or any(
                "enum" in item for item in any_of if isinstance(item, dict)
            )
            assert has_enum, f"{name}: backburner should use Literal type for schema hints"

    def test_track_time_action_uses_literal_type(self) -> None:
        """track_time action should expose START/STOP in JSON schema."""
        tools = {t.name: t for t in mcp._tool_manager.list_tools()}
        schema = tools["track_time"].parameters
        action_prop = schema["properties"]["action"]
        has_enum = "enum" in action_prop or any(
            "enum" in item for item in action_prop.get("anyOf", []) if isinstance(item, dict)
        )
        assert has_enum, "track_time: action should use Literal type for schema hints"

    def test_destructive_tools_have_destructive_annotation(self) -> None:
        tools = {t.name: t for t in mcp._tool_manager.list_tools()}
        ann = tools["delete_item"].annotations
        assert ann is not None, "delete_item missing annotations"
        assert ann.readOnlyHint is False
        assert ann.destructiveHint is True


class TestDateValidation:
    def test_valid_date(self) -> None:
        assert _validate_date("2026-01-15") == "2026-01-15"

    def test_invalid_date_raises(self) -> None:
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            _validate_date("01-15-2026")

    def test_none_date_passes_through(self) -> None:
        assert _validate_date(None) is None

    def test_valid_datetime(self) -> None:
        assert _validate_datetime("2026-01-15T09:30:00") == "2026-01-15T09:30:00"

    def test_invalid_datetime_raises(self) -> None:
        with pytest.raises(ValueError, match="ISO datetime"):
            _validate_datetime("not-a-datetime")

    def test_none_datetime_passes_through(self) -> None:
        assert _validate_datetime(None) is None
