# ABOUTME: Tests for the MCP server adapter layer.
# ABOUTME: Validates tool registration and prompt registration.

import pytest

from amazing_marvin_mcp.server import (
    _build_attribute_setters,
    _looks_like_id,
    _validate_date,
    _validate_datetime,
    mcp,
)


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
            "create_project",
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
        assert len(tools) == 15  # 8 read + 7 write

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
            "create_project",
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


class TestLooksLikeId:
    def test_mongo_object_id(self) -> None:
        assert _looks_like_id("42c312949028ab5b371a608847cef9a6") is True

    def test_uuid(self) -> None:
        assert _looks_like_id("980d7516-a0ce-4903-91f5-b37bc8180ca5") is True

    def test_short_hex_is_not_id(self) -> None:
        assert _looks_like_id("abc123") is False

    def test_human_readable_name_is_not_id(self) -> None:
        assert _looks_like_id("Urgent") is False

    def test_empty_string_is_not_id(self) -> None:
        assert _looks_like_id("") is False

    def test_mixed_case_hex_is_id(self) -> None:
        assert _looks_like_id("42C312949028AB5B371A608847CEF9A6") is True


class TestBuildAttributeSetters:
    def test_all_none_returns_empty(self) -> None:
        result = _build_attribute_setters(None, None, None, None, None, None)
        assert result == {}

    def test_energy_low(self) -> None:
        result = _build_attribute_setters("low", None, None, None, None, None)
        assert result == {"energyAmount": 1}

    def test_energy_high(self) -> None:
        result = _build_attribute_setters("high", None, None, None, None, None)
        assert result == {"energyAmount": 2}

    def test_energy_unset(self) -> None:
        result = _build_attribute_setters("unset", None, None, None, None, None)
        assert result == {"energyAmount": False}

    def test_focus_low(self) -> None:
        result = _build_attribute_setters(None, "low", None, None, None, None)
        assert result == {"focusLevel": 1}

    def test_focus_high(self) -> None:
        result = _build_attribute_setters(None, "high", None, None, None, None)
        assert result == {"focusLevel": 2}

    def test_focus_unset(self) -> None:
        result = _build_attribute_setters(None, "unset", None, None, None, None)
        assert result == {"focusLevel": False}

    def test_mental_weight_weighing(self) -> None:
        result = _build_attribute_setters(None, None, "weighing", None, None, None)
        assert result == {"mentalWeight": 2}

    def test_mental_weight_crushing(self) -> None:
        result = _build_attribute_setters(None, None, "crushing", None, None, None)
        assert result == {"mentalWeight": 4}

    def test_mental_weight_unset(self) -> None:
        result = _build_attribute_setters(None, None, "unset", None, None, None)
        assert result == {"mentalWeight": False}

    def test_is_physical_true(self) -> None:
        result = _build_attribute_setters(None, None, None, True, None, None)
        assert result == {"isPhysical": True}

    def test_is_physical_false_clears(self) -> None:
        result = _build_attribute_setters(None, None, None, False, None, None)
        assert result == {"isPhysical": False}

    def test_urgency_urgent(self) -> None:
        result = _build_attribute_setters(None, None, None, None, "urgent", None)
        assert result == {"isUrgent": 2}

    def test_urgency_fire(self) -> None:
        result = _build_attribute_setters(None, None, None, None, "fire", None)
        assert result == {"isUrgent": 4}

    def test_urgency_unset(self) -> None:
        result = _build_attribute_setters(None, None, None, None, "unset", None)
        assert result == {"isUrgent": False}

    def test_importance_important(self) -> None:
        result = _build_attribute_setters(None, None, None, None, None, "important")
        assert result == {"isStarred": 1}

    def test_importance_low(self) -> None:
        result = _build_attribute_setters(None, None, None, None, None, "low")
        assert result == {"isStarred": -1}

    def test_importance_unset(self) -> None:
        result = _build_attribute_setters(None, None, None, None, None, "unset")
        assert result == {"isStarred": False}

    def test_multiple_fields_combined(self) -> None:
        result = _build_attribute_setters("high", "low", None, True, "urgent", None)
        assert result == {
            "energyAmount": 2,
            "focusLevel": 1,
            "isPhysical": True,
            "isUrgent": 2,
        }
