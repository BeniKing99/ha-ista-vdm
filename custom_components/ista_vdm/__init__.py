"""The Ista VDM integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from ista_vdm_api import IstaVdmAPI
from .const import DOMAIN, PLATFORMS, SENSOR_KEYS
from .coordinator import IstaVdmDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


type IstaVdmConfigEntry = ConfigEntry[IstaVdmDataUpdateCoordinator]


def flat_device_identifier(entry: ConfigEntry, flat_id: str) -> tuple[str, str]:
    """Return the device registry identifier of a flat."""
    return (DOMAIN, f"{entry.entry_id}_{flat_id}")


@callback
def _async_migrate_to_flat_ids(
    hass: HomeAssistant, entry: ConfigEntry, flat_id: str
) -> None:
    """Move entities and device of the single-flat layout (<= 1.0.4) to the given flat.

    Older versions only supported the first flat of an account and used unique IDs
    without a flat ID. Re-keying them keeps entity IDs and history intact.
    """
    legacy_prefix = f"{entry.entry_id}_"
    new_prefix = f"{entry.entry_id}_{flat_id}_"

    ent_reg = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if entity.domain != Platform.SENSOR or not entity.unique_id.startswith(legacy_prefix):
            continue
        key = entity.unique_id.removeprefix(legacy_prefix)
        if key not in SENSOR_KEYS:
            continue
        new_unique_id = f"{new_prefix}{key}"
        if ent_reg.async_get_entity_id(Platform.SENSOR, DOMAIN, new_unique_id):
            continue
        _LOGGER.debug("Migrating %s to unique ID %s", entity.entity_id, new_unique_id)
        ent_reg.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)

    dev_reg = dr.async_get(hass)
    new_identifier = flat_device_identifier(entry, flat_id)
    legacy_device = dev_reg.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    if legacy_device and not dev_reg.async_get_device(identifiers={new_identifier}):
        _LOGGER.debug("Migrating device %s to flat %s", legacy_device.id, flat_id)
        dev_reg.async_update_device(legacy_device.id, new_identifiers={new_identifier})


async def async_setup_entry(hass: HomeAssistant, entry: IstaVdmConfigEntry) -> bool:
    """Set up ista VDM from a config entry."""
    api = IstaVdmAPI(entry.data["email"], entry.data["password"])

    # The first refresh logs in. A rejected password raises ConfigEntryAuthFailed
    # (Home Assistant starts the reauth flow), any other error raises
    # ConfigEntryNotReady (Home Assistant retries the setup later).
    coordinator = IstaVdmDataUpdateCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()

    # The first flat of the account is the one older versions created entities for
    if coordinator.flat_ids:
        _async_migrate_to_flat_ids(hass, entry, coordinator.flat_ids[0])

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: IstaVdmConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
