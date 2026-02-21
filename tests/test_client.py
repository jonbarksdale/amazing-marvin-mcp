# ABOUTME: Tests for the MarvinClient HTTP layer.
# ABOUTME: Validates auth headers, rate limiting, error mapping, and raw API calls.

import time

import pytest

from amazing_marvin_mcp.client import MarvinAPIError, MarvinClient


class TestMarvinClientInit:
    """Test client initialization and configuration."""

    def test_requires_api_token(self) -> None:
        with pytest.raises(ValueError, match="MARVIN_API_TOKEN"):
            MarvinClient(api_token="")

    def test_stores_base_url(self) -> None:
        client = MarvinClient(api_token="test-token")
        assert client.base_url == "https://serv.amazingmarvin.com/api"

    def test_does_not_log_token(self) -> None:
        client = MarvinClient(api_token="secret-token-123")
        assert "secret-token-123" not in repr(client)
        assert "secret-token-123" not in str(client)


class TestMarvinClientHeaders:
    def test_headers_include_full_access_token(self) -> None:
        client = MarvinClient(api_token="my-token")
        headers = client._build_headers()
        assert headers["X-Full-Access-Token"] == "my-token"
        assert "X-API-Token" not in headers

    def test_headers_include_content_type(self) -> None:
        client = MarvinClient(api_token="my-token")
        headers = client._build_headers()
        assert headers["Content-Type"] == "application/json"


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_query_rate_limit_delay(self) -> None:
        client = MarvinClient(api_token="test-token")
        client._last_query_time = time.monotonic()
        delay = client._calculate_query_delay()
        assert delay > 0
        assert delay <= 3.0

    @pytest.mark.asyncio
    async def test_mutation_rate_limit_delay(self) -> None:
        client = MarvinClient(api_token="test-token")
        client._last_mutation_time = time.monotonic()
        delay = client._calculate_mutation_delay()
        assert delay > 0
        assert delay <= 1.0

    def test_no_delay_on_first_request(self) -> None:
        client = MarvinClient(api_token="test-token")
        assert client._calculate_query_delay() == 0.0
        assert client._calculate_mutation_delay() == 0.0


class TestErrorMapping:
    def test_401_error(self) -> None:
        error = MarvinAPIError.from_status(401, "test")
        assert "Invalid API token" in str(error)

    def test_403_error(self) -> None:
        error = MarvinAPIError.from_status(403, "test")
        assert "full-access token" in str(error)

    def test_404_error(self) -> None:
        error = MarvinAPIError.from_status(404, "test")
        assert "not found" in str(error).lower()

    def test_429_error(self) -> None:
        error = MarvinAPIError.from_status(429, "test")
        assert "Rate limited" in str(error)

    def test_500_error(self) -> None:
        error = MarvinAPIError.from_status(500, "test")
        assert "server error" in str(error).lower()
