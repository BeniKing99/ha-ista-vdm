"""Test the ista VDM integration initialization."""

from unittest.mock import patch
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ista_vdm.const import DOMAIN
from ista_vdm_api import IstaVdmAuthError

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


async def test_setup_entry_auth_failure(hass: HomeAssistant) -> None:
    """Test setup triggers re-authentication on IstaVdmAuthError."""
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
        "custom_components.ista_vdm.IstaVdmAPI.authenticate",
        side_effect=IstaVdmAuthError("Invalid credentials"),
    ) as mock_auth:
        result = await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        
        assert result is False
        mock_auth.assert_called_once()


async def test_setup_entry_auth_failure_triggers_reauth(hass: HomeAssistant) -> None:
    """Test that auth failure triggers the re-authentication flow."""
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
        "custom_components.ista_vdm.IstaVdmAPI.authenticate",
        side_effect=IstaVdmAuthError("Invalid credentials"),
    ):
        with patch.object(
            entry, "async_start_reauth", return_value=None
        ) as mock_reauth:
            result = await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            
            assert result is False
            mock_reauth.assert_called_once_with(hass)


async def test_setup_entry_unexpected_error_triggers_reauth(hass: HomeAssistant) -> None:
    """Test that unexpected errors also trigger re-authentication flow."""
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
        "custom_components.ista_vdm.IstaVdmAPI.authenticate",
        side_effect=Exception("Unexpected network error"),
    ):
        with patch.object(
            entry, "async_start_reauth", return_value=None
        ) as mock_reauth:
            result = await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            
            assert result is False
            mock_reauth.assert_called_once_with(hass)


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
