# ABOUTME: Shared pytest fixtures for Amazing Marvin MCP tests.
# ABOUTME: Provides configured MarvinService and test sandbox parent category.

from __future__ import annotations

import os
from typing import Any

import pytest

from amazing_marvin_mcp.marvin import MarvinService

# Test tasks are created inside this category for easy cleanup.
TEST_SANDBOX_PARENT = "MCP Test"


@pytest.fixture
def service() -> MarvinService:
    """MarvinService configured with real API token from env."""
    token = os.environ.get("MARVIN_API_TOKEN", "")
    if not token:
        pytest.skip("MARVIN_API_TOKEN not set")
    return MarvinService(api_token=token)


@pytest.fixture
async def sandbox_parent_id(service: MarvinService) -> str:
    """Resolve the test sandbox parent ID, skip if not found."""
    categories = await service.get_categories()
    for cat in categories:
        if cat.get("title") == TEST_SANDBOX_PARENT:
            return str(cat["_id"])
    pytest.skip(f"Test sandbox parent '{TEST_SANDBOX_PARENT}' not found in Marvin account")
    return ""  # unreachable, satisfies mypy


async def create_test_task(
    service: MarvinService,
    sandbox_id: str,
    title: str = "MCP Test Task",
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a task inside the test sandbox for easy cleanup."""
    return await service.create_task(title=title, parent_id=sandbox_id, **kwargs)
