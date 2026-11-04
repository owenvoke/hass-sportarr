"""Fixtures for Sportarr tests."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.const import CONF_API_KEY, CONF_URL
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.sportarr.const import DOMAIN

URL = "http://sportarr.local:1867"
DATA = {CONF_URL: URL, CONF_API_KEY: "key"}

STATUS = {"appName": "Sportarr", "version": "4.0.81.140"}
HEALTHY = [
    {
        "type": 0,
        "level": 0,
        "message": "All health checks passed",
        "details": "System is healthy and operating normally",
        "dismissed": False,
    }
]


def mock_sportarr(
    aioclient_mock: AiohttpClientMocker,
    url: str = URL,
    *,
    status: dict[str, Any] = STATUS,
    counts: dict[str, Any] | None = None,
    missing: int = 0,
    cutoff_unmet: int = 0,
    health: list[dict[str, Any]] = HEALTHY,
) -> None:
    """Register responses for every endpoint the integration polls."""
    aioclient_mock.get(f"{url}/api/system/status", json=status)
    aioclient_mock.get(f"{url}/api/activity/counts", json=counts or {})
    aioclient_mock.get(
        f"{url}/api/wanted/missing", json={"events": [], "totalRecords": missing}
    )
    aioclient_mock.get(
        f"{url}/api/wanted/cutoff-unmet",
        json={"events": [], "totalRecords": cutoff_unmet},
    )
    aioclient_mock.get(f"{url}/api/system/health", json=health)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in every test."""


@pytest.fixture
def sportarr(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Mock a healthy Sportarr instance."""
    mock_sportarr(
        aioclient_mock,
        counts={"queueCount": 2, "pendingImportCount": 1, "blocklistCount": 5},
        missing=7,
        cutoff_unmet=4,
    )
    return aioclient_mock


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A configured Sportarr entry."""
    return MockConfigEntry(domain=DOMAIN, title="Sportarr (sportarr.local)", data=DATA)
