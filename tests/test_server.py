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
        assert len(tools) == 13  # 7 read + 6 write
