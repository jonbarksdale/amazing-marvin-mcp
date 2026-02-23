# ABOUTME: Integration tests for MarvinService against the real Amazing Marvin API.
# ABOUTME: Validates real API endpoints. Business logic is in test_unit_marvin.py.

import pytest

from amazing_marvin_mcp.marvin import MarvinService
from tests.conftest import create_test_task


class TestReadEndpoints:
    """Verify each read endpoint returns valid data from the real API."""

    @pytest.mark.asyncio
    async def test_get_today(self, service: MarvinService) -> None:
        result = await service.get_today()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_due(self, service: MarvinService) -> None:
        result = await service.get_due()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_categories(self, service: MarvinService) -> None:
        result = await service.get_categories()
        assert isinstance(result, list)
        if result:
            assert "_id" in result[0]
            assert "title" in result[0]

    @pytest.mark.asyncio
    async def test_get_labels(self, service: MarvinService) -> None:
        result = await service.get_labels()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_inbox(self, service: MarvinService) -> None:
        result = await service.get_inbox()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_time_blocks(self, service: MarvinService) -> None:
        result = await service.get_time_blocks()
        assert isinstance(result, list)


class TestWriteLifecycle:
    """Lifecycle tests covering create, update, done, and delete."""

    @pytest.mark.asyncio
    async def test_task_crud_lifecycle(
        self, service: MarvinService, sandbox_parent_id: str
    ) -> None:
        task = await create_test_task(service, sandbox_parent_id, "MCP Integration Lifecycle")
        task_id = task["_id"]
        try:
            assert "_id" in task

            updated = await service.update_task(task_id, setters={"title": "MCP Updated"})
            assert updated is not None
            # /doc/update returns a full task object
            assert updated.get("title") == "MCP Updated"

            done_result = await service.mark_done(task_id)
            assert done_result is not None
        finally:
            await service.delete_task(task_id)

    @pytest.mark.asyncio
    async def test_create_task_with_labels(
        self, service: MarvinService, sandbox_parent_id: str
    ) -> None:
        labels = await service.get_labels()
        if not labels:
            pytest.skip("No labels in account")
        label_id = labels[0]["_id"]

        task = await service.create_task(
            title="MCP Label Test",
            parent_id=sandbox_parent_id,
            label_ids=[label_id],
        )
        try:
            assert label_id in task.get("labelIds", [])
        finally:
            await service.delete_task(task["_id"])
