# ABOUTME: End-to-end tests for the MCP server via STDIO transport.
# ABOUTME: Launches the server as a subprocess and validates core MCP protocol flows.

import os

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# All tools registered on the server
EXPECTED_TOOLS = {
    "get_today",
    "get_due",
    "get_time_blocks",
    "get_labels",
    "get_categories",
    "get_children",
    "get_inbox",
    "search",
    "create_task",
    "create_project",
    "create_event",
    "update_item",
    "delete_item",
    "mark_done",
    "track_time",
}

EXPECTED_PROMPTS = {
    "plan_my_day",
    "weekly_review",
}


def _server_params() -> StdioServerParameters:
    """Build server parameters for connecting to the MCP server subprocess."""
    token = os.environ.get("MARVIN_API_TOKEN", "")
    if not token:
        pytest.skip("MARVIN_API_TOKEN not set")

    return StdioServerParameters(
        command="uv",
        args=["run", "amazing-marvin-mcp"],
        env={**os.environ, "MARVIN_API_TOKEN": token},
    )


def _server_params_no_token() -> StdioServerParameters:
    """Build server parameters without an API token for error path testing."""
    env = {k: v for k, v in os.environ.items() if k != "MARVIN_API_TOKEN"}
    return StdioServerParameters(
        command="uv",
        args=["run", "amazing-marvin-mcp"],
        env=env,
    )


async def _connect_and_run(callback) -> None:
    """Connect to the server and run the callback with the session.

    Each test gets its own server subprocess to avoid anyio cancel scope
    issues with pytest-asyncio fixture teardown across tasks.
    """
    params = _server_params()
    async with (
        stdio_client(params) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        await callback(session)


class TestE2EServer:
    """E2E tests limited to core flows for fast test runs."""

    @pytest.mark.asyncio
    async def test_list_tools_and_prompts(self) -> None:
        """Server should list all registered tools and prompts."""

        async def check(session: ClientSession) -> None:
            tools = await session.list_tools()
            tool_names = {t.name for t in tools.tools}
            assert tool_names == EXPECTED_TOOLS

            prompts = await session.list_prompts()
            prompt_names = {p.name for p in prompts.prompts}
            assert prompt_names == EXPECTED_PROMPTS

        await _connect_and_run(check)

    @pytest.mark.asyncio
    async def test_call_get_today(self) -> None:
        """Calling get_today should return text content."""

        async def check(session: ClientSession) -> None:
            result = await session.call_tool("get_today", {})
            assert len(result.content) > 0
            assert isinstance(result.content[0].text, str)

        await _connect_and_run(check)

    @pytest.mark.asyncio
    async def test_call_get_inbox(self) -> None:
        """Calling get_inbox should return text content."""

        async def check(session: ClientSession) -> None:
            result = await session.call_tool("get_inbox", {})
            assert len(result.content) > 0
            assert isinstance(result.content[0].text, str)

        await _connect_and_run(check)

    @pytest.mark.asyncio
    async def test_server_sends_instructions(self) -> None:
        """Server should include instructions in initialize response."""
        params = _server_params_no_token()
        async with (
            stdio_client(params) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as session,
        ):
            result = await session.initialize()
            assert result.instructions is not None
            assert len(result.instructions) > 0

    @pytest.mark.asyncio
    async def test_invalid_date_returns_actionable_error(self) -> None:
        """Passing an invalid date should return a clear error message."""
        params = _server_params_no_token()
        async with (
            stdio_client(params) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()
            result = await session.call_tool("create_task", {"title": "Test", "day": "not-a-date"})
            text = result.content[0].text
            assert "YYYY-MM-DD" in text
            assert "not-a-date" in text

    @pytest.mark.asyncio
    async def test_missing_token_returns_actionable_error(self) -> None:
        """Calling a tool without MARVIN_API_TOKEN returns an LLM-actionable error."""
        params = _server_params_no_token()
        async with (
            stdio_client(params) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()
            result = await session.call_tool("get_today", {})
            text = result.content[0].text
            assert "MARVIN_API_TOKEN" in text
            assert "amazingmarvin.com" in text
