# ABOUTME: Integration tests for the full Amazing Marvin MCP stack.
# ABOUTME: Tests real API calls through MarvinService with formatted output.

import os

import pytest

from amazing_marvin_mcp.formatting import format_tasks_list, truncate_response
from amazing_marvin_mcp.marvin import MarvinService


@pytest.fixture
def service() -> MarvinService:
    token = os.environ.get("MARVIN_API_TOKEN", "")
    if not token:
        pytest.skip("MARVIN_API_TOKEN not set")
    return MarvinService(api_token=token)


class TestFullWorkflow:
    """Test a complete create → update → done → delete workflow."""

    @pytest.mark.asyncio
    async def test_task_lifecycle(self, service: MarvinService) -> None:
        # Create
        task = await service.create_task(title="Integration Test Task")
        task_id = task["_id"]

        try:
            # Update
            updated = await service.update_task(
                task_id, setters={"title": "Integration Test Updated"}
            )
            assert updated is not None

            # Mark done
            await service.mark_done(task_id)
        finally:
            # Cleanup
            await service.delete_task(task_id)


class TestFormattedOutput:
    """Test that formatted output stays within limits."""

    @pytest.mark.asyncio
    async def test_today_formatted_within_limit(self, service: MarvinService) -> None:
        items = await service.get_today()
        formatted = format_tasks_list(items, "Today's Tasks")
        result = truncate_response(formatted)
        assert len(result) <= 25_100


class TestRateLimiting:
    """Test that rapid calls don't cause 429 errors."""

    @pytest.mark.asyncio
    async def test_rapid_reads_dont_fail(self, service: MarvinService) -> None:
        await service.get_labels()
        await service.get_categories()
        await service.get_time_blocks()
