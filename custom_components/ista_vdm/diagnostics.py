"""Diagnostics support for ista VDM."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import IstaVdmConfigEntry

TO_REDACT = {"password", "email", "street", "housenumber", "door", "postalcode"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: IstaVdmConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    api = coordinator.api

    flats: dict[str, Any] = {}
    for flat_id in coordinator.flat_ids:
        records = (coordinator.data or {}).get(flat_id) or []
        flat_info = coordinator.flat_info.get(flat_id) or {}
        flats[flat_id] = {
            "flat_info": async_redact_data(flat_info, TO_REDACT),
            "months": len(records),
            "has_heating": any(r.heating_consumption is not None for r in records),
            "has_hot_water": any(r.hot_water_consumption is not None for r in records),
            "has_cold_water": any(r.cold_water_consumption is not None for r in records),
        }

    return {
        "entry_data": async_redact_data(entry.data, TO_REDACT),
        "api_status": {
            "authenticated": api.is_authenticated,
            "flat_id": api.flat_id,
            "flat_ids": list(api.flat_ids or []),
        },
        "flats": flats,
    }
