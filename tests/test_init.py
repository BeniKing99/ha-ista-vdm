"""Test the ista VDM integration initialization."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ista_vdm.const import DOMAIN
from ista_vdm_api import IstaVdmAuthError, IstaVdmConnectionError, IstaVdmError

from .conftest import FLAT_1, build_api_mock


async def test_setup_entry(hass: HomeAssistant) -> None:
    """Test setting up the integration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "email": "test@example.com",
            "password": "password",
        },
        unique_id="test@example.com",
    )
    entry.add_to_hass(hass)
    
    with patch(
        "custom_components.ista_vdm.IstaVdmAPI",
        return_value=build_api_mock([FLAT_1]),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        
        assert entry.state == ConfigEntryState.LOADED


def _failing_login_api(error: Exception):
    """Return a mocked API whose login raises the given error."""
    api = build_api_mock([FLAT_1])
    api.is_authenticated = False
    api.authenticate = AsyncMock(side_effect=error)
    return api


def _reauth_flows(hass: HomeAssistant) -> list:
    return [
        flow
        for flow in hass.config_entries.flow.async_progress()
        if flow["handler"] == DOMAIN and flow["context"]["source"] == SOURCE_REAUTH
    ]


async def test_setup_entry_auth_failure_starts_reauth(hass: HomeAssistant) -> None:
    """A rejected password fails the setup and asks for the password."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "email": "test@example.com",
            "password": "wrong_password",
        },
        unique_id="test@example.com",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.ista_vdm.IstaVdmAPI",
        return_value=_failing_login_api(IstaVdmAuthError("Invalid credentials")),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert len(_reauth_flows(hass)) == 1


@pytest.mark.parametrize(
    "error",
    [
        IstaVdmConnectionError("Network error during authentication"),
        IstaVdmError("Login form not found on page"),
        Exception("Unexpected error"),
    ],
)
async def test_setup_entry_outage_retries_without_reauth(
    hass: HomeAssistant, error: Exception
) -> None:
    """A portal or network outage retries the setup later without asking for the password."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "email": "test@example.com",
            "password": "password",
        },
        unique_id="test@example.com",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.ista_vdm.IstaVdmAPI",
        return_value=_failing_login_api(error),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert _reauth_flows(hass) == []


async def test_unload_entry(hass: HomeAssistant) -> None:
    """Test unloading the integration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "email": "test@example.com",
            "password": "password",
        },
        unique_id="test@example.com",
    )
    entry.add_to_hass(hass)
    
    with patch(
        "custom_components.ista_vdm.IstaVdmAPI",
        return_value=build_api_mock([FLAT_1]),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        
        assert entry.state == ConfigEntryState.LOADED
        
        # Unload the entry
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        
        assert entry.state == ConfigEntryState.NOT_LOADED


async def test_reload_entry(hass: HomeAssistant) -> None:
    """Test reloading the integration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "email": "test@example.com",
            "password": "password",
        },
        unique_id="test@example.com",
    )
    entry.add_to_hass(hass)
    
    with patch(
        "custom_components.ista_vdm.IstaVdmAPI",
        return_value=build_api_mock([FLAT_1]),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        
        assert entry.state == ConfigEntryState.LOADED
        
        # Reload the entry
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        
        assert entry.state == ConfigEntryState.LOADED
