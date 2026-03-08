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

    @pytest.mark.asyncio
    async def test_create_task_with_attributes(
        self, service: MarvinService, sandbox_parent_id: str
    ) -> None:
        task = await service.create_task(
            title="MCP Attributes Test",
            parent_id=sandbox_parent_id,
            extra_fields={"energyAmount": 2, "focusLevel": 1, "isPhysical": True},
        )
        task_id = task["_id"]
        try:
            children = await service.get_children(parent_id=sandbox_parent_id, backburner="include")
            created = next((t for t in children if t["_id"] == task_id), None)
            assert created is not None, "Created task not found in children"
            assert created.get("energyAmount") == 2
            assert created.get("focusLevel") == 1
            assert created.get("isPhysical") is True
        finally:
            await service.delete_item(task_id)

    @pytest.mark.asyncio
    async def test_update_item_sets_and_clears_attributes(
        self, service: MarvinService, sandbox_parent_id: str
    ) -> None:
        task = await create_test_task(service, sandbox_parent_id, "MCP Update Attributes Test")
        task_id = task["_id"]
        try:
            # Set attributes
            updated = await service.update_item(
                task_id,
                setters={"energyAmount": 2, "isUrgent": 2},
            )
            assert updated.get("energyAmount") == 2
            assert updated.get("isUrgent") == 2

            # Clear one attribute
            cleared = await service.update_item(
                task_id,
                setters={"energyAmount": False},
            )
            # API may omit, return null, or return False for cleared fields
            assert cleared.get("energyAmount") in (False, None, 0)
        finally:
            await service.delete_item(task_id)

    @pytest.mark.asyncio
    async def test_update_item_clears_scheduled_date(
        self, service: MarvinService, sandbox_parent_id: str
    ) -> None:
        task = await create_test_task(
            service, sandbox_parent_id, "MCP Clear Date Test", day="2099-01-01"
        )
        task_id = task["_id"]
        try:
            assert task.get("day") == "2099-01-01"

            cleared = await service.update_item(task_id, setters={"day": False})
            # API may omit or return null/False for a cleared scheduled date
            assert cleared.get("day") in (False, None, "")
        finally:
            await service.delete_item(task_id)

    @pytest.mark.asyncio
    async def test_update_item_clears_due_date(
        self, service: MarvinService, sandbox_parent_id: str
    ) -> None:
        task = await create_test_task(
            service, sandbox_parent_id, "MCP Clear Due Date Test", due_date="2099-01-01"
        )
        task_id = task["_id"]
        try:
            assert task.get("dueDate") == "2099-01-01"

            cleared = await service.update_item(task_id, setters={"dueDate": False})
            # API may omit or return null/False for a cleared due date
            assert cleared.get("dueDate") in (False, None, "")
        finally:
            await service.delete_item(task_id)


class TestProjectLifecycle:
    """Lifecycle tests covering project and category create, update, and delete."""

    @pytest.mark.asyncio
    async def test_project_crud_lifecycle(
        self, service: MarvinService, sandbox_parent_id: str
    ) -> None:
        project = await service.create_project(
            title="MCP Project Test", parent_id=sandbox_parent_id
        )
        project_id = project["_id"]
        try:
            assert "_id" in project
            assert project["title"] == "MCP Project Test"
            assert project.get("type") == "project"

            updated = await service.update_item(
                project_id, setters={"title": "MCP Project Updated"}
            )
            assert updated is not None
            assert updated.get("title") == "MCP Project Updated"
        finally:
            await service.delete_item(project_id)

    @pytest.mark.asyncio
    async def test_category_creation(self, service: MarvinService, sandbox_parent_id: str) -> None:
        category = await service.create_project(
            title="MCP Category Test", type="category", parent_id=sandbox_parent_id
        )
        category_id = category["_id"]
        try:
            assert "_id" in category
            assert category["title"] == "MCP Category Test"
            assert category.get("type") == "category"
        finally:
            await service.delete_item(category_id)
