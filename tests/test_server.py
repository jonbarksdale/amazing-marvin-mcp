# ABOUTME: Tests for the MCP server adapter layer.
# ABOUTME: Validates tool registration and prompt registration.

from amazing_marvin_mcp.server import mcp


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
            "update_task",
            "mark_done",
            "delete_task",
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
        idempotent_tools = {"update_task", "mark_done"}
        tools = {t.name: t for t in mcp._tool_manager.list_tools()}
        for name in idempotent_tools:
            ann = tools[name].annotations
            assert ann is not None, f"{name} missing annotations"
            assert ann.readOnlyHint is False, f"{name} should not be readOnly"
            assert ann.destructiveHint is False, f"{name} should not be destructive"
            assert ann.idempotentHint is True, f"{name} should be idempotent"

    def test_destructive_tools_have_destructive_annotation(self) -> None:
        tools = {t.name: t for t in mcp._tool_manager.list_tools()}
        ann = tools["delete_task"].annotations
        assert ann is not None, "delete_task missing annotations"
        assert ann.readOnlyHint is False
        assert ann.destructiveHint is True
