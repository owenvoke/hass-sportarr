"""A minimal client for the Sportarr API."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

REQUEST_TIMEOUT = 10

# Sportarr's HealthCheckLevel.Ok. With nothing wrong, the health endpoint
# returns a single "All health checks passed" result at this level.
HEALTH_LEVEL_OK = 0


class SportarrError(Exception):
    """Base exception for Sportarr API errors."""


class SportarrConnectionError(SportarrError):
    """Raised when the Sportarr instance cannot be reached."""


class SportarrAuthError(SportarrError):
    """Raised when the API key is invalid."""


class SportarrClient:
    """Client for a Sportarr instance's API."""

    def __init__(self, session: aiohttp.ClientSession, url: str, api_key: str) -> None:
        """Initialise the client."""
        self._session = session
        self._base_url = url.rstrip("/")
        self._api_key = api_key

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self._session.get(
                    f"{self._base_url}/api{path}",
                    headers={"X-Api-Key": self._api_key},
                    params=params,
                )
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SportarrConnectionError(str(err) or type(err).__name__) from err

        async with response:
            if response.status in (401, 403):
                raise SportarrAuthError(f"Unauthorized ({response.status})")
            if response.status >= 400:
                raise SportarrError(f"Unexpected response ({response.status})")
            try:
                return await response.json()
            except (aiohttp.ContentTypeError, ValueError) as err:
                raise SportarrError("Invalid response from Sportarr") from err

    async def _get_dict(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data = await self._get(path, params)
        if not isinstance(data, dict):
            raise SportarrError("Invalid response from Sportarr")
        return data

    async def version(self) -> str:
        """Return the Sportarr version, checking this is a Sportarr instance."""
        status = await self._get_dict("/system/status")
        if status.get("appName") != "Sportarr" or "version" not in status:
            raise SportarrError("Not a Sportarr instance")
        return status["version"]

    async def activity_counts(self) -> dict[str, Any]:
        """Return the counts shown in Sportarr's activity badges."""
        return await self._get_dict("/activity/counts")

    async def _total_records(self, path: str) -> int:
        """Return the total of a paged list, fetching as little as possible."""
        data = await self._get_dict(path, {"page": 1, "pageSize": 1})
        return int(data.get("totalRecords") or 0)

    async def missing_count(self) -> int:
        """Return how many monitored, aired events have no file."""
        return await self._total_records("/wanted/missing")

    async def cutoff_unmet_count(self) -> int:
        """Return how many events have a file below the quality cutoff."""
        return await self._total_records("/wanted/cutoff-unmet")

    async def health(self) -> list[dict[str, Any]]:
        """Return the current health issues, leaving out dismissed ones."""
        data = await self._get("/system/health")
        if not isinstance(data, list):
            raise SportarrError("Invalid response from Sportarr")
        return [
            issue
            for issue in data
            if isinstance(issue, dict)
            and issue.get("level") not in (HEALTH_LEVEL_OK, "Ok")
            and not issue.get("dismissed")
        ]
