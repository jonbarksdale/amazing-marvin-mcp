# ABOUTME: End-to-end tests for the MCP server via STDIO transport.
# ABOUTME: Launches the server as a subprocess and communicates via MCP protocol.

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
    "search",
    "create_task",
    "create_event",
    "update_task",
    "delete_task",
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


async def _connect_and_run(callback):
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
    """E2E tests that exercise the MCP server over STDIO transport."""

    @pytest.mark.asyncio
    async def test_list_tools(self) -> None:
        """Server should list all 13 registered tools."""

        async def check(session: ClientSession) -> None:
            result = await session.list_tools()
            tool_names = {t.name for t in result.tools}
            assert tool_names == EXPECTED_TOOLS

        await _connect_and_run(check)

    @pytest.mark.asyncio
    async def test_list_prompts(self) -> None:
        """Server should list all workflow prompts."""

        async def check(session: ClientSession) -> None:
            result = await session.list_prompts()
            prompt_names = {p.name for p in result.prompts}
            assert prompt_names == EXPECTED_PROMPTS

        await _connect_and_run(check)

    @pytest.mark.asyncio
    async def test_call_get_labels(self) -> None:
        """Calling get_labels should return text content."""

        async def check(session: ClientSession) -> None:
            result = await session.call_tool("get_labels", {})
            assert len(result.content) > 0
            text = result.content[0].text
            # Response should contain label-related output
            assert "Labels" in text or "No labels" in text or "label" in text.lower()

        await _connect_and_run(check)

    @pytest.mark.asyncio
    async def test_call_get_today(self) -> None:
        """Calling get_today should return text content about today's tasks."""

        async def check(session: ClientSession) -> None:
            result = await session.call_tool("get_today", {})
            assert len(result.content) > 0
            assert isinstance(result.content[0].text, str)

        await _connect_and_run(check)

    @pytest.mark.asyncio
    async def test_get_prompt(self) -> None:
        """Getting a prompt should return its message content."""

        async def check(session: ClientSession) -> None:
            result = await session.get_prompt("plan_my_day")
            assert len(result.messages) > 0
            assert "plan" in result.messages[0].content.text.lower()

        await _connect_and_run(check)
