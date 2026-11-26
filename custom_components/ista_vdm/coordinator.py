"""Data update coordinator for the ista VDM integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from ista_vdm_api import ConsumptionData, IstaVdmAPI, IstaVdmAuthError, IstaVdmError

from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class IstaVdmDataUpdateCoordinator(DataUpdateCoordinator[dict[str, list[ConsumptionData]]]):
    """Fetch consumption data for every flat of an ista VDM account.

    ``data`` maps each flat ID to its list of monthly consumption records.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api: IstaVdmAPI,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.api = api
        self.entry = entry
        self.flat_ids: list[str] = []
        self.flat_info: dict[str, dict[str, Any] | None] = {}
        self.last_update_success_time: datetime | None = None

    def _discover_flat_ids(self) -> list[str]:
        """Return the flat IDs of the account (first one is the default flat)."""
        flat_ids = list(self.api.flat_ids or [])
        if not flat_ids and self.api.flat_id:
            flat_ids = [self.api.flat_id]
        return flat_ids

    async def _async_update_data(self) -> dict[str, list[ConsumptionData]]:
        """Fetch data from ista VDM API."""
        _LOGGER.debug("Starting data update for %s", self.entry.title)
        try:
            async with self.api:
                if not self.api.is_authenticated:
                    _LOGGER.debug("API not authenticated, authenticating...")
                    await self.api.authenticate()

                flat_ids = self._discover_flat_ids()
                if not flat_ids:
                    raise IstaVdmError("No flats found for this account")
                if flat_ids != self.flat_ids:
                    _LOGGER.debug("Flats of %s: %s", self.entry.title, flat_ids)
                    self.flat_ids = flat_ids

                previous = self.data or {}
                data: dict[str, list[ConsumptionData]] = {}
                errors: list[str] = []

                for flat_id in flat_ids:
                    try:
                        # Flat details are static, fetch them only once
                        if self.flat_info.get(flat_id) is None:
                            self.flat_info[flat_id] = await self.api.get_flat_info(flat_id)
                            _LOGGER.debug(
                                "Flat info for %s: %s", flat_id, self.flat_info[flat_id]
                            )

                        records = await self.api.get_consumption_data(flat_id)
                    except IstaVdmAuthError:
                        raise
                    except IstaVdmError as err:
                        # One failing flat must not take down the others
                        _LOGGER.warning(
                            "Could not update flat %s of %s: %s", flat_id, self.entry.title, err
                        )
                        errors.append(f"{flat_id}: {err}")
                        if flat_id in previous:
                            data[flat_id] = previous[flat_id]
                        continue

                    _LOGGER.debug(
                        "Retrieved %d consumption records for flat %s", len(records), flat_id
                    )
                    if records:
                        latest = max(records, key=lambda x: x.period_end)
                        _LOGGER.debug(
                            "Latest data for flat %s: period=%s to %s, heating=%s kWh, "
                            "hot_water=%s m³, cold_water=%s m³",
                            flat_id,
                            latest.period_start,
                            latest.period_end,
                            latest.heating_consumption,
                            latest.hot_water_consumption,
                            latest.cold_water_consumption,
                        )
                    data[flat_id] = records

                if len(errors) == len(flat_ids):
                    raise IstaVdmError("; ".join(errors))

                self.last_update_success_time = dt_util.utcnow()
                return data

        except IstaVdmAuthError as err:
            _LOGGER.error(
                "Authentication failed for %s: %s. Triggering re-authentication.",
                self.entry.title,
                err,
            )
            raise ConfigEntryAuthFailed from err
        except IstaVdmError as err:
            _LOGGER.error("Ista VDM error for %s: %s", self.entry.title, err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error updating data for %s: %s", self.entry.title, err)
            raise UpdateFailed(f"Unexpected error: {err}") from err
