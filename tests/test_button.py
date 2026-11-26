"""Test the ista VDM button platform."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ista_vdm.button import IstaVdmRefreshButton
from custom_components.ista_vdm.const import DOMAIN
from ista_vdm_api import IstaVdmAuthError

from .conftest import FLAT_1


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.async_refresh = AsyncMock()
    coordinator.hass = MagicMock()
    return coordinator


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.title = "Ista VDM"
    entry.async_start_reauth = MagicMock()
    return entry


@pytest.fixture
def mock_device_info():
    """Create mock device info."""
    return MagicMock()


async def test_refresh_button(hass: HomeAssistant, mock_coordinator, mock_entry, mock_device_info) -> None:
    """Test refresh button."""
    button = IstaVdmRefreshButton(mock_coordinator, mock_entry, mock_device_info)
    
    assert button.name == "Refresh Data"
    assert button.icon == "mdi:refresh"
    
    await button.async_press()
    
    mock_coordinator.async_refresh.assert_called_once()


async def test_refresh_button_rejected_password_starts_reauth(
    hass: HomeAssistant, mock_api
) -> None:
    """Pressing the button with a rejected password starts the reauth flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"email": "test@example.com", "password": "password"},
        unique_id="test@example.com",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    mock_api.get_consumption_data.side_effect = IstaVdmAuthError("Invalid credentials")
    button_id = next(
        e.entity_id
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if e.domain == "button"
    )
    await hass.services.async_call(
        "button", "press", {"entity_id": button_id}, blocking=True
    )
    await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows if f["handler"] == DOMAIN] == ["reauth"]


async def test_async_setup_entry(hass: HomeAssistant, mock_api) -> None:
    """The refresh button is created once, on the device of the first flat."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "email": "test@example.com",
            "password": "password",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    buttons = [
        e
        for e in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
        if e.domain == "button"
    ]
    assert len(buttons) == 1
    assert buttons[0].unique_id == f"{entry.entry_id}_refresh"

    device = dr.async_get(hass).async_get(buttons[0].device_id)
    assert device is not None
    assert device.identifiers == {(DOMAIN, f"{entry.entry_id}_{FLAT_1}")}
