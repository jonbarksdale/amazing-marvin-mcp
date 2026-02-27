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


class TestBackburnerFiltering:
    """Verify backburner field is present in API responses and filtering works."""

    @pytest.mark.asyncio
    async def test_backburner_task_filtered_by_default(
        self, service: MarvinService, sandbox_parent_id: str
    ) -> None:
        task = await create_test_task(service, sandbox_parent_id, "MCP Backburner Test")
        task_id = task["_id"]
        try:
            # Move task to backburner
            updated = await service.update_item(task_id, setters={"backburner": True})
            assert updated.get("backburner") is True

            # Default filter should exclude it
            children = await service.get_children(parent_id=sandbox_parent_id)
            ids = [t["_id"] for t in children]
            assert task_id not in ids

            # "include" should return it
            all_children = await service.get_children(
                parent_id=sandbox_parent_id, backburner="include"
            )
            all_ids = [t["_id"] for t in all_children]
            assert task_id in all_ids

            # "only" should return only backburner items
            bb_children = await service.get_children(parent_id=sandbox_parent_id, backburner="only")
            for t in bb_children:
                assert t.get("backburner") is True
        finally:
            await service.delete_item(task_id)


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

            updated = await service.update_item(task_id, setters={"title": "MCP Updated"})
            assert updated is not None
            # /doc/update returns a full task object
            assert updated.get("title") == "MCP Updated"

            done_result = await service.mark_done(task_id)
            assert done_result is not None
        finally:
            await service.delete_item(task_id)

    @pytest.mark.asyncio
    async def test_create_task_with_labels(
        self, service: MarvinService, sandbox_parent_id: str
    ) -> None:
        labels = await service.get_labels()
        if not labels:
            pytest.skip("No labels in account")
        label_name = labels[0]["title"]
        label_id = labels[0]["_id"]

        # Resolve label name to ID via resolve_label_ids, then pass IDs to create_task
        resolved_ids = await service.resolve_label_ids([label_name])
        task = await service.create_task(
            title="MCP Label Test",
            parent_id=sandbox_parent_id,
            label_ids=resolved_ids,
        )
        try:
            assert label_id in task.get("labelIds", [])
        finally:
            await service.delete_item(task["_id"])
