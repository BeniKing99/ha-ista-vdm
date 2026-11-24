"""Platform for ista VDM sensor integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ista_vdm_api import ConsumptionData

from . import IstaVdmConfigEntry, flat_device_identifier
from .const import DOMAIN
from .coordinator import IstaVdmDataUpdateCoordinator

# Parallel updates - set to 0 to allow parallel updates
PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "IstaVdmColdWaterSensor",
    "IstaVdmDataUpdateCoordinator",
    "IstaVdmFlatDetailSensor",
    "IstaVdmHeatingSensor",
    "IstaVdmHotWaterSensor",
    "IstaVdmLastUpdatedSensor",
    "create_device_info",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IstaVdmConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ista VDM sensors for every flat of the account."""
    coordinator: IstaVdmDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    multiple_flats = len(coordinator.flat_ids) > 1

    entities: list[IstaVdmBaseSensor] = []
    for flat_id in coordinator.flat_ids:
        device_info = create_device_info(
            coordinator.flat_info.get(flat_id), entry, flat_id, multiple_flats
        )

        entities.extend(
            [
                IstaVdmHeatingSensor(coordinator, entry, device_info, flat_id),
                IstaVdmHotWaterSensor(coordinator, entry, device_info, flat_id),
                IstaVdmLastUpdatedSensor(coordinator, entry, device_info, flat_id),
            ]
        )

        # Only some flats have a cold water meter
        records = (coordinator.data or {}).get(flat_id) or []
        if any(record.cold_water_consumption is not None for record in records):
            entities.append(IstaVdmColdWaterSensor(coordinator, entry, device_info, flat_id))

        # Add flat detail sensors (static info)
        if coordinator.flat_info.get(flat_id):
            entities.extend(
                IstaVdmFlatDetailSensor(coordinator, entry, device_info, flat_id, description)
                for description in FLAT_DETAIL_SENSORS
            )

    async_add_entities(entities)


def _format_address(flat_info: dict[str, Any]) -> str:
    """Return a short address like 'Teststraße 1/4'."""
    address = " ".join(
        str(part) for part in (flat_info.get("street"), flat_info.get("housenumber")) if part
    )
    door = flat_info.get("door")
    if address and door:
        address = f"{address}/{door}"
    return address


def create_device_info(
    flat_info: dict[str, Any] | None,
    entry: ConfigEntry,
    flat_id: str,
    multiple_flats: bool = False,
) -> DeviceInfo:
    """Create the device info of one flat."""
    address = _format_address(flat_info) if flat_info else ""
    if address:
        name = f"Ista VDM - {address}"
    elif multiple_flats:
        name = f"Ista VDM - {flat_id}"
    else:
        name = "Ista VDM"

    return DeviceInfo(
        identifiers={flat_device_identifier(entry, flat_id)},
        name=name,
        manufacturer="ista",
        model="VDM",
        configuration_url="https://ista-vdm.at/",
    )


class IstaVdmBaseSensor(CoordinatorEntity[IstaVdmDataUpdateCoordinator], SensorEntity):
    """Base class for ista VDM sensors of one flat."""

    _attr_has_entity_name = True
    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: IstaVdmDataUpdateCoordinator,
        entry: ConfigEntry,
        device_info: DeviceInfo,
        flat_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._flat_id = flat_id
        self._attr_device_info = device_info
        self._attr_unique_id = f"{entry.entry_id}_{flat_id}_{self.entity_description.key}"

    @property
    def _records(self) -> list[ConsumptionData]:
        """Return the consumption records of this sensor's flat."""
        if not self.coordinator.data:
            return []
        return self.coordinator.data.get(self._flat_id) or []

    @property
    def _flat_info(self) -> dict[str, Any] | None:
        """Return the static details of this sensor's flat."""
        return self.coordinator.flat_info.get(self._flat_id)


class IstaVdmLastUpdatedSensor(IstaVdmBaseSensor):
    """Sensor for last updated timestamp."""

    entity_description = SensorEntityDescription(
        key="last_updated",
        name="Last Updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    @property
    def native_value(self) -> datetime | None:
        """Return the last update timestamp."""
        return self.coordinator.last_update_success_time


class IstaVdmConsumptionSensor(IstaVdmBaseSensor):
    """Monthly consumption of one type, with the history in its attributes."""

    # Name of the ConsumptionData field and of the value key in the history attribute
    _value_field: str
    _history_key: str

    def _value(self, record: ConsumptionData) -> float | None:
        value: float | None = getattr(record, self._value_field)
        return value

    @property
    def native_value(self) -> float | None:
        """Return the latest consumption value."""
        if self._records:
            latest = max(self._records, key=lambda x: x.period_end)
            return self._value(latest)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return historical data in attributes."""
        attrs: dict[str, Any] = {}

        if self._records:
            sorted_data = sorted(self._records, key=lambda x: x.period_start, reverse=True)

            latest = sorted_data[0]
            attrs["period_start"] = latest.period_start.isoformat()
            attrs["period_end"] = latest.period_end.isoformat()

            history = [
                {
                    "period_start": c.period_start.isoformat(),
                    "period_end": c.period_end.isoformat(),
                    self._history_key: self._value(c),
                }
                for c in sorted_data
            ]
            attrs["history"] = history
            attrs["total_months"] = len(history)

        return attrs


class IstaVdmHeatingSensor(IstaVdmConsumptionSensor):
    """Sensor for heating consumption."""

    entity_description = SensorEntityDescription(
        key="heating_consumption",
        name="Heating Consumption",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:radiator",
    )
    _value_field = "heating_consumption"
    _history_key = "consumption_kwh"


class IstaVdmHotWaterSensor(IstaVdmConsumptionSensor):
    """Sensor for hot water consumption."""

    entity_description = SensorEntityDescription(
        key="hot_water_consumption",
        name="Hot Water Consumption",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:water-boiler",
    )
    _value_field = "hot_water_consumption"
    _history_key = "consumption_m3"


class IstaVdmColdWaterSensor(IstaVdmConsumptionSensor):
    """Sensor for cold water consumption."""

    entity_description = SensorEntityDescription(
        key="cold_water_consumption",
        name="Cold Water Consumption",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:water",
    )
    _value_field = "cold_water_consumption"
    _history_key = "consumption_m3"


# Flat detail sensors (static information, diagnostic category)


@dataclass(frozen=True, kw_only=True)
class IstaVdmFlatSensorEntityDescription(SensorEntityDescription):
    """Describes a static flat detail sensor."""

    field: str


FLAT_DETAIL_SENSORS: tuple[IstaVdmFlatSensorEntityDescription, ...] = (
    IstaVdmFlatSensorEntityDescription(
        key="flat_city",
        field="city",
        name="City",
        icon="mdi:city",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    IstaVdmFlatSensorEntityDescription(
        key="flat_street",
        field="street",
        name="Street",
        icon="mdi:road",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    IstaVdmFlatSensorEntityDescription(
        key="flat_housenumber",
        field="housenumber",
        name="House Number",
        icon="mdi:numeric",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    IstaVdmFlatSensorEntityDescription(
        key="flat_door",
        field="door",
        name="Door",
        icon="mdi:door",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    IstaVdmFlatSensorEntityDescription(
        key="flat_squaremeter",
        field="squaremeter",
        name="Square Meters",
        icon="mdi:ruler-square",
        native_unit_of_measurement="m²",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    IstaVdmFlatSensorEntityDescription(
        key="flat_postalcode",
        field="postalcode",
        name="Postal Code",
        icon="mdi:mailbox",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


class IstaVdmFlatDetailSensor(IstaVdmBaseSensor):
    """Sensor for one static detail of a flat (city, street, ...)."""

    entity_description: IstaVdmFlatSensorEntityDescription

    def __init__(
        self,
        coordinator: IstaVdmDataUpdateCoordinator,
        entry: ConfigEntry,
        device_info: DeviceInfo,
        flat_id: str,
        description: IstaVdmFlatSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        super().__init__(coordinator, entry, device_info, flat_id)

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self._flat_info:
            return self._flat_info.get(self.entity_description.field)
        return None
