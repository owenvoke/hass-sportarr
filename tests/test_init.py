"""Tests for Sportarr setup and entities."""

from __future__ import annotations

from http import HTTPStatus

import aiohttp
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.sportarr.const import DOMAIN

from .conftest import URL, mock_sportarr


async def test_entities(
    hass: HomeAssistant, sportarr: AiohttpClientMocker, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    queue = hass.states.get("sensor.sportarr_queue")
    assert queue.state == "2"
    assert queue.attributes["unit_of_measurement"] == "downloads"
    assert hass.states.get("sensor.sportarr_pending_imports").state == "1"
    assert hass.states.get("sensor.sportarr_missing_events").state == "7"
    assert hass.states.get("sensor.sportarr_cutoff_unmet_events").state == "4"
    # The "All health checks passed" result isn't an issue.
    assert hass.states.get("binary_sensor.sportarr_health").state == "off"

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, config_entry.entry_id), config_entry.entry_id
    )
    assert device.sw_version == "4.0.81.140"

    # Paged lists are only asked for their totals.
    missing_call = next(
        call for call in sportarr.mock_calls if call[1].path == "/api/wanted/missing"
    )
    assert dict(missing_call[1].query) == {"page": "1", "pageSize": "1"}


async def test_device_version_follows_sportarr_upgrades(
    hass: HomeAssistant, sportarr: AiohttpClientMocker, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    sportarr.clear_requests()
    mock_sportarr(sportarr, status={"appName": "Sportarr", "version": "4.1.0.1"})
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, config_entry.entry_id), config_entry.entry_id
    )
    assert device.sw_version == "4.1.0.1"


async def test_health_issues(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    issue = {
        "type": 2,
        "level": 3,
        "message": "Download client unavailable",
        "dismissed": False,
    }
    dismissed = {
        "type": 5,
        "level": 2,
        "message": "Update available",
        "dismissed": True,
    }
    mock_sportarr(aioclient_mock, health=[issue, dismissed])
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    health = hass.states.get("binary_sensor.sportarr_health")
    assert health.state == "on"
    assert health.attributes["issues"] == [issue]
    assert hass.states.get("sensor.sportarr_queue").state == "0"


async def test_only_dismissed_issues_are_healthy(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    mock_sportarr(
        aioclient_mock,
        health=[{"type": 5, "level": 2, "message": "x", "dismissed": True}],
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.sportarr_health").state == "off"


async def test_setup_retries_on_network_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    aioclient_mock.get(f"{URL}/api/system/status", exc=aiohttp.ClientConnectionError())
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_retries_on_unexpected_health_response(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    mock_sportarr(aioclient_mock, health={"unexpected": True})
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_auth_failure_starts_reauth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    aioclient_mock.get(f"{URL}/api/system/status", status=HTTPStatus.UNAUTHORIZED)
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == ["reauth"]
