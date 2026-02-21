# ABOUTME: HTTP client for the Amazing Marvin API.
# ABOUTME: Handles authentication, rate limiting, and raw API calls.

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

BASE_URL = "https://serv.amazingmarvin.com/api"
QUERY_RATE_LIMIT_SECONDS = 3.0
MUTATION_RATE_LIMIT_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 30.0


class MarvinAPIError(Exception):
    """Error from the Amazing Marvin API with a human-readable message."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)

    @classmethod
    def from_status(cls, status_code: int, endpoint: str) -> MarvinAPIError:
        messages = {
            401: "Invalid API token. Check MARVIN_API_TOKEN.",
            403: "Insufficient permissions. This endpoint requires a full-access token.",
            404: f"Item not found at {endpoint}.",
            429: "Rate limited by Amazing Marvin. Try again shortly.",
        }
        if status_code >= 500:
            msg = "Amazing Marvin server error. Try again later."
        else:
            msg = messages.get(status_code, f"API error {status_code} at {endpoint}.")
        return cls(msg, status_code=status_code)


class MarvinClient:
    """Low-level async HTTP client for the Amazing Marvin API.

    Handles auth headers, rate limiting, and error mapping.
    No business logic — that belongs in marvin.py.
    """

    def __init__(self, api_token: str) -> None:
        if not api_token:
            raise ValueError("MARVIN_API_TOKEN is required but was empty.")
        self._api_token = api_token
        self.base_url = BASE_URL
        self._last_query_time: float = 0.0
        self._last_mutation_time: float = 0.0

    def _build_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-Full-Access-Token": self._api_token,
        }
        if extra:
            headers.update(extra)
        return headers

    def _calculate_query_delay(self) -> float:
        if self._last_query_time == 0.0:
            return 0.0
        elapsed = time.monotonic() - self._last_query_time
        return max(0.0, QUERY_RATE_LIMIT_SECONDS - elapsed)

    def _calculate_mutation_delay(self) -> float:
        if self._last_mutation_time == 0.0:
            return 0.0
        elapsed = time.monotonic() - self._last_mutation_time
        return max(0.0, MUTATION_RATE_LIMIT_SECONDS - elapsed)

    async def _wait_for_rate_limit(self, is_mutation: bool) -> None:
        delay = self._calculate_mutation_delay() if is_mutation else self._calculate_query_delay()
        if delay > 0:
            await asyncio.sleep(delay)

    async def get(
        self,
        endpoint: str,
        params: dict[str, str] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        """Make a GET request to the Marvin API."""
        await self._wait_for_rate_limit(is_mutation=False)
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as http:
            response = await http.get(
                url, headers=self._build_headers(extra_headers), params=params
            )
        self._last_query_time = time.monotonic()
        if response.status_code != 200:
            raise MarvinAPIError.from_status(response.status_code, endpoint)
        return response.json()

    async def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        """Make a POST request to the Marvin API."""
        await self._wait_for_rate_limit(is_mutation=True)
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as http:
            response = await http.post(
                url, headers=self._build_headers(extra_headers), json=data or {}
            )
        self._last_mutation_time = time.monotonic()
        if response.status_code != 200:
            raise MarvinAPIError.from_status(response.status_code, endpoint)
        return response.json()

    def __repr__(self) -> str:
        return f"MarvinClient(base_url={self.base_url!r})"

    def __str__(self) -> str:
        return f"MarvinClient({self.base_url})"
