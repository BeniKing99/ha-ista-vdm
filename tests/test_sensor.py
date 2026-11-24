"""Test the ista VDM sensor platform."""

from unittest.mock import MagicMock

import pytest
from homeassistant.const import UnitOfEnergy, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ista_vdm.const import DOMAIN
from custom_components.ista_vdm.sensor import (
    FLAT_DETAIL_SENSORS,
    IstaVdmColdWaterSensor,
    IstaVdmFlatDetailSensor,
    IstaVdmHeatingSensor,
    IstaVdmHotWaterSensor,
    IstaVdmLastUpdatedSensor,
    create_device_info,
)

from .conftest import CONSUMPTION, FLAT_1, FLAT_2, FLAT_INFO, build_api_mock


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Add a config entry for the tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Ista VDM (test@example.com)",
        data={"email": "test@example.com", "password": "password"},
        unique_id="test@example.com",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Create a mock coordinator with two flats."""
    coordinator = MagicMock()
    coordinator.flat_ids = [FLAT_1, FLAT_2]
    coordinator.data = CONSUMPTION
    coordinator.flat_info = FLAT_INFO
    coordinator.last_update_success_time = dt_util.utcnow()
    return coordinator


def _entities(hass: HomeAssistant, entry: MockConfigEntry) -> dict[str, er.RegistryEntry]:
    registry = er.async_get(hass)
    return {
        entity.unique_id: entity
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
    }


async def test_heating_sensor(mock_coordinator: MagicMock, config_entry) -> None:
    """Test heating sensor."""
    sensor = IstaVdmHeatingSensor(mock_coordinator, config_entry, MagicMock(), FLAT_1)

    assert sensor.unique_id == f"{config_entry.entry_id}_{FLAT_1}_heating_consumption"
    assert sensor.device_class == "energy"
    assert sensor.native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR
    assert sensor.state_class == "total"
    assert sensor.native_value == 392.1

    attrs = sensor.extra_state_attributes
    assert attrs["total_months"] == 2
    assert attrs["period_start"] == "2025-12-01"
    assert attrs["history"][0] == {
        "period_start": "2025-12-01",
        "period_end": "2025-12-31",
        "consumption_kwh": 392.1,
    }


async def test_hot_water_sensor(mock_coordinator: MagicMock, config_entry) -> None:
    """Test hot water sensor."""
    sensor = IstaVdmHotWaterSensor(mock_coordinator, config_entry, MagicMock(), FLAT_1)

    assert sensor.device_class == "water"
    assert sensor.native_unit_of_measurement == UnitOfVolume.CUBIC_METERS
    assert sensor.native_value == 0.26
    assert sensor.extra_state_attributes["history"][1]["consumption_m3"] == 0.29


async def test_cold_water_sensor(mock_coordinator: MagicMock, config_entry) -> None:
    """Test cold water sensor reads its own flat."""
    sensor = IstaVdmColdWaterSensor(mock_coordinator, config_entry, MagicMock(), FLAT_2)

    assert sensor.unique_id == f"{config_entry.entry_id}_{FLAT_2}_cold_water_consumption"
    assert sensor.device_class == "water"
    assert sensor.native_unit_of_measurement == UnitOfVolume.CUBIC_METERS
    assert sensor.state_class == "total"
    assert sensor.native_value == 19
    attrs = sensor.extra_state_attributes
    assert attrs["period_start"] == "2026-04-01"
    assert attrs["history"][0]["consumption_m3"] == 19


async def test_sensors_are_per_flat(mock_coordinator: MagicMock, config_entry) -> None:
    """Sensors of different flats read different data."""
    first = IstaVdmHeatingSensor(mock_coordinator, config_entry, MagicMock(), FLAT_1)
    second = IstaVdmHeatingSensor(mock_coordinator, config_entry, MagicMock(), FLAT_2)

    assert first.native_value == 392.1
    assert second.native_value == 17
    assert first.unique_id != second.unique_id


async def test_flat_detail_sensor(mock_coordinator: MagicMock, config_entry) -> None:
    """Test flat detail sensors."""
    door = next(d for d in FLAT_DETAIL_SENSORS if d.key == "flat_door")
    sensor = IstaVdmFlatDetailSensor(mock_coordinator, config_entry, MagicMock(), FLAT_2, door)

    assert sensor.unique_id == f"{config_entry.entry_id}_{FLAT_2}_flat_door"
    assert sensor.native_value == "5"


async def test_last_updated_sensor(mock_coordinator: MagicMock, config_entry) -> None:
    """Test last updated sensor."""
    sensor = IstaVdmLastUpdatedSensor(mock_coordinator, config_entry, MagicMock(), FLAT_1)

    assert sensor.device_class == "timestamp"
    assert sensor.native_value == mock_coordinator.last_update_success_time


async def test_sensor_no_data(config_entry) -> None:
    """Test sensors handle no data gracefully."""
    coordinator = MagicMock()
    coordinator.data = None
    coordinator.flat_info = {}

    sensor = IstaVdmHeatingSensor(coordinator, config_entry, MagicMock(), FLAT_1)
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}


async def test_device_names(config_entry) -> None:
    """Device names include the door so flats in one building can be told apart."""
    info = create_device_info(FLAT_INFO[FLAT_2], config_entry, FLAT_2, True)
    assert info["name"] == "Ista VDM - Test Street 123/5"
    assert info["identifiers"] == {(DOMAIN, f"{config_entry.entry_id}_{FLAT_2}")}

    assert create_device_info(None, config_entry, FLAT_2, True)["name"] == f"Ista VDM - {FLAT_2}"
    assert create_device_info(None, config_entry, FLAT_1, False)["name"] == "Ista VDM"


async def test_setup_single_flat(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_api_single_flat
) -> None:
    """A one-flat account without cold water gets the same sensors as before."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entities = _entities(hass, config_entry)
    sensors = {uid for uid, e in entities.items() if e.domain == "sensor"}
    # 2 consumption + 1 last updated + 6 flat info, no cold water sensor
    assert len(sensors) == 9
    assert f"{config_entry.entry_id}_{FLAT_1}_cold_water_consumption" not in sensors

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), config_entry.entry_id)
    assert len(devices) == 1


async def test_setup_multiple_flats(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_api
) -> None:
    """Every flat of the account gets its own device and sensors."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entities = _entities(hass, config_entry)
    prefix = config_entry.entry_id
    # Flat 1: 9 sensors, flat 2: 9 sensors + cold water
    assert len([e for e in entities.values() if e.domain == "sensor"]) == 19
    assert f"{prefix}_{FLAT_2}_cold_water_consumption" in entities
    assert f"{prefix}_{FLAT_1}_cold_water_consumption" not in entities

    device_registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(device_registry, config_entry.entry_id)
    assert sorted(d.name for d in devices) == [
        "Ista VDM - Test Street 123/4",
        "Ista VDM - Test Street 123/5",
    ]

    cold_water = entities[f"{prefix}_{FLAT_2}_cold_water_consumption"]
    assert hass.states.get(cold_water.entity_id).state == "19"
    heating_2 = entities[f"{prefix}_{FLAT_2}_heating_consumption"]
    assert hass.states.get(heating_2.entity_id).state == "17"
    heating_1 = entities[f"{prefix}_{FLAT_1}_heating_consumption"]
    assert hass.states.get(heating_1.entity_id).state == "392.1"
    assert heating_1.device_id != heating_2.device_id


async def test_one_failing_flat_does_not_break_others(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_api
) -> None:
    """An error for one flat leaves the other flats working."""
    from ista_vdm_api import IstaVdmError

    working = mock_api.get_consumption_data.side_effect

    async def get_consumption_data(flat_id=None):
        if flat_id == FLAT_2:
            raise IstaVdmError("Export URL not found in flat details")
        return await working(flat_id)

    mock_api.get_consumption_data.side_effect = get_consumption_data

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entities = _entities(hass, config_entry)
    heating_1 = entities[f"{config_entry.entry_id}_{FLAT_1}_heating_consumption"]
    assert hass.states.get(heating_1.entity_id).state == "392.1"
    heating_2 = entities[f"{config_entry.entry_id}_{FLAT_2}_heating_consumption"]
    assert hass.states.get(heating_2.entity_id).state == "unknown"


async def test_migrate_single_flat_entities(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Entities and device of versions <= 1.0.4 move to the first flat, keeping entity IDs."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    legacy_device = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, config_entry.entry_id)},
        name="Ista VDM - Test Street 123",
    )
    legacy_heating = entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{config_entry.entry_id}_heating_consumption",
        config_entry=config_entry,
        device_id=legacy_device.id,
        suggested_object_id="ista_vdm_heating_consumption",
    )
    legacy_button = entity_registry.async_get_or_create(
        "button",
        DOMAIN,
        f"{config_entry.entry_id}_refresh",
        config_entry=config_entry,
        device_id=legacy_device.id,
    )

    api = build_api_mock([FLAT_1, FLAT_2])
    from unittest.mock import patch

    with patch("custom_components.ista_vdm.IstaVdmAPI", return_value=api):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    migrated = entity_registry.async_get(legacy_heating.entity_id)
    assert migrated is not None
    assert migrated.unique_id == f"{config_entry.entry_id}_{FLAT_1}_heating_consumption"
    assert hass.states.get(legacy_heating.entity_id).state == "392.1"

    # No duplicate entity was created for the first flat
    heating_ids = [
        e.entity_id
        for e in er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)
        if e.unique_id.endswith(f"{FLAT_1}_heating_consumption")
    ]
    assert heating_ids == [legacy_heating.entity_id]

    # The existing device now belongs to the first flat
    device = device_registry.async_get(legacy_device.id)
    assert device is not None
    assert device.identifiers == {(DOMAIN, f"{config_entry.entry_id}_{FLAT_1}")}
    assert migrated.device_id == legacy_device.id

    # The refresh button keeps its unique ID and stays on that device
    button = entity_registry.async_get(legacy_button.entity_id)
    assert button is not None
    assert button.unique_id == f"{config_entry.entry_id}_refresh"
    assert button.device_id == legacy_device.id
