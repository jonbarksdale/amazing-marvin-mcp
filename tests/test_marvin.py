# ABOUTME: Tests for the MarvinService business logic layer.
# ABOUTME: Validates intent-oriented operations, caching, and name resolution.

import os

import pytest

from amazing_marvin_mcp.marvin import MarvinService


@pytest.fixture
def service() -> MarvinService:
    token = os.environ.get("MARVIN_API_TOKEN", "")
    if not token:
        pytest.skip("MARVIN_API_TOKEN not set")
    return MarvinService(api_token=token)


class TestGetToday:
    @pytest.mark.asyncio
    async def test_returns_list(self, service: MarvinService) -> None:
        result = await service.get_today()
        assert isinstance(result, list)


class TestGetDue:
    @pytest.mark.asyncio
    async def test_returns_list(self, service: MarvinService) -> None:
        result = await service.get_due()
        assert isinstance(result, list)


class TestGetCategories:
    @pytest.mark.asyncio
    async def test_returns_list(self, service: MarvinService) -> None:
        result = await service.get_categories()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_categories_have_title_and_id(self, service: MarvinService) -> None:
        result = await service.get_categories()
        if result:
            cat = result[0]
            assert "_id" in cat
            assert "title" in cat


class TestGetChildren:
    @pytest.mark.asyncio
    async def test_by_parent_id(self, service: MarvinService) -> None:
        categories = await service.get_categories()
        if not categories:
            pytest.skip("No categories in account")
        parent_id = categories[0]["_id"]
        result = await service.get_children(parent_id=parent_id)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_by_parent_name(self, service: MarvinService) -> None:
        categories = await service.get_categories()
        if not categories:
            pytest.skip("No categories in account")
        name = categories[0]["title"]
        result = await service.get_children(parent_name=name)
        assert isinstance(result, list)


class TestGetLabels:
    @pytest.mark.asyncio
    async def test_returns_list(self, service: MarvinService) -> None:
        result = await service.get_labels()
        assert isinstance(result, list)


class TestGetTimeBlocks:
    @pytest.mark.asyncio
    async def test_returns_list(self, service: MarvinService) -> None:
        result = await service.get_time_blocks()
        assert isinstance(result, list)


class TestCategoryCaching:
    @pytest.mark.asyncio
    async def test_second_call_uses_cache(self, service: MarvinService) -> None:
        result1 = await service.get_categories()
        result2 = await service.get_categories()
        assert result1 == result2
        assert service._categories_cache is not None


class TestGetChildrenValidation:
    @pytest.mark.asyncio
    async def test_both_args_raises(self, service: MarvinService) -> None:
        with pytest.raises(ValueError, match="not both"):
            await service.get_children(parent_id="x", parent_name="y")

    @pytest.mark.asyncio
    async def test_no_args_raises(self, service: MarvinService) -> None:
        with pytest.raises(ValueError, match="either"):
            await service.get_children()

    @pytest.mark.asyncio
    async def test_invalid_name_raises(self, service: MarvinService) -> None:
        with pytest.raises(ValueError, match="No category matching"):
            await service.get_children(parent_name="zzz_nonexistent_zzz_12345")


class TestLabelsCaching:
    @pytest.mark.asyncio
    async def test_second_call_uses_cache(self, service: MarvinService) -> None:
        result1 = await service.get_labels()
        result2 = await service.get_labels()
        assert result1 == result2
        assert service._labels_cache is not None


class TestResolveParentId:
    @pytest.mark.asyncio
    async def test_exact_match(self, service: MarvinService) -> None:
        categories = await service.get_categories()
        if not categories:
            pytest.skip("No categories in account")
        name = categories[0]["title"]
        resolved = await service._resolve_parent_id(name)
        assert resolved == categories[0]["_id"]

    @pytest.mark.asyncio
    async def test_case_insensitive(self, service: MarvinService) -> None:
        categories = await service.get_categories()
        if not categories:
            pytest.skip("No categories in account")
        name = categories[0]["title"].upper()
        resolved = await service._resolve_parent_id(name)
        assert resolved == categories[0]["_id"]

    @pytest.mark.asyncio
    async def test_no_match_raises(self, service: MarvinService) -> None:
        with pytest.raises(ValueError, match="No category"):
            await service._resolve_parent_id("zzz_nonexistent_category_zzz")


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_by_partial_name(self, service: MarvinService) -> None:
        categories = await service.get_categories()
        if not categories:
            pytest.skip("No categories in account")
        query = categories[0]["title"][:4]
        results = await service.search(query)
        assert isinstance(results, list)
        assert len(results) > 0
        assert "title" in results[0]
        assert "children" in results[0]

    @pytest.mark.asyncio
    async def test_search_no_match(self, service: MarvinService) -> None:
        results = await service.search("xyznonexistent999")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, service: MarvinService) -> None:
        categories = await service.get_categories()
        if not categories:
            pytest.skip("No categories in account")
        name = categories[0]["title"]
        upper = await service.search(name.upper())
        lower = await service.search(name.lower())
        assert len(upper) == len(lower)
