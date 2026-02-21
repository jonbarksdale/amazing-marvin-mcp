# ABOUTME: Integration tests for formatting output with real API data.
# ABOUTME: Validates that formatted responses stay within size limits.

import pytest

from amazing_marvin_mcp.formatting import format_tasks_list, truncate_response
from amazing_marvin_mcp.marvin import MarvinService


class TestFormattedOutput:
    """Test that formatted output stays within limits using real data."""

    @pytest.mark.asyncio
    async def test_today_formatted_within_limit(self, service: MarvinService) -> None:
        items = await service.get_today()
        formatted = format_tasks_list(items, "Today's Tasks")
        result = truncate_response(formatted)
        assert len(result) <= 25_100
