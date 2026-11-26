"""Platform for ista VDM button integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IstaVdmConfigEntry
from .coordinator import IstaVdmDataUpdateCoordinator
from .sensor import create_device_info

PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IstaVdmConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ista VDM button based on a config entry."""
    coordinator = entry.runtime_data
    if not coordinator.flat_ids:
        return
    
    # The button refreshes the whole account; it lives on the device of the first flat
    flat_id = coordinator.flat_ids[0]
    device_info = create_device_info(
        coordinator.flat_info.get(flat_id),
        entry,
        flat_id,
        len(coordinator.flat_ids) > 1,
    )
    
    async_add_entities([
        IstaVdmRefreshButton(coordinator, entry, device_info),
    ])


class IstaVdmRefreshButton(ButtonEntity):
    """Button to manually refresh ista VDM data."""

    entity_description = ButtonEntityDescription(
        key="refresh",
        name="Refresh Data",
        icon="mdi:refresh",
        entity_category=EntityCategory.CONFIG,
    )

    def __init__(
        self,
        coordinator: IstaVdmDataUpdateCoordinator,
        entry: ConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the button."""
        self._entry = entry
        self._coordinator = coordinator
        self._attr_device_info = device_info
        self._attr_unique_id = f"{entry.entry_id}_refresh"

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.debug("Manual refresh triggered for %s", self._entry.title)
        # The coordinator logs in again when needed and starts the reauth flow
        # itself if the portal rejects the stored password.
        await self._coordinator.async_refresh()
