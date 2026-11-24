"""Shared fixtures for the ista VDM tests."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ista_vdm_api import ConsumptionData

FLAT_1 = "111"
FLAT_2 = "222"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load the integration from custom_components in every test."""


def make_record(
    year: int,
    month: int,
    heating: float | None = None,
    hot_water: float | None = None,
    cold_water: float | None = None,
) -> ConsumptionData:
    """Build one monthly consumption record."""
    end = date(year + (month == 12), month % 12 + 1, 1)
    return ConsumptionData(
        period_start=date(year, month, 1),
        period_end=date.fromordinal(end.toordinal() - 1),
        heating_consumption=heating,
        heating_cost=None,
        hot_water_consumption=hot_water,
        hot_water_cost=None,
        cold_water_consumption=cold_water,
        cold_water_cost=None,
    )


FLAT_INFO = {
    FLAT_1: {
        "id": FLAT_1,
        "city": "Vienna",
        "street": "Test Street",
        "housenumber": "123",
        "door": "4",
        "squaremeter": 56.9,
        "postalcode": "1010",
    },
    FLAT_2: {
        "id": FLAT_2,
        "city": "Vienna",
        "street": "Test Street",
        "housenumber": "123",
        "door": "5",
        "squaremeter": 36.57,
        "postalcode": "1010",
    },
}

CONSUMPTION = {
    # Heating + hot water, no cold water meter
    FLAT_1: [
        make_record(2025, 11, heating=327.8, hot_water=0.29),
        make_record(2025, 12, heating=392.1, hot_water=0.26),
    ],
    # Heating + cold water, no hot water meter
    FLAT_2: [
        make_record(2026, 3, heating=16, cold_water=18),
        make_record(2026, 4, heating=17, cold_water=19),
    ],
}


def build_api_mock(flat_ids: list[str]) -> MagicMock:
    """Return a mocked IstaVdmAPI serving the given flats."""
    api = MagicMock()
    api.authenticate = AsyncMock(return_value=True)
    api.is_authenticated = True
    api.flat_ids = flat_ids
    api.flat_id = flat_ids[0] if flat_ids else None

    async def get_flat_info(flat_id: str | None = None) -> dict[str, Any] | None:
        return FLAT_INFO.get(flat_id or flat_ids[0])

    async def get_consumption_data(flat_id: str | None = None) -> list[ConsumptionData]:
        return CONSUMPTION[flat_id or flat_ids[0]]

    api.get_flat_info = AsyncMock(side_effect=get_flat_info)
    api.get_consumption_data = AsyncMock(side_effect=get_consumption_data)
    return api


@pytest.fixture
def mock_api() -> Generator[MagicMock]:
    """Patch the API client used by the integration with a two-flat account."""
    api = build_api_mock([FLAT_1, FLAT_2])
    with patch("custom_components.ista_vdm.IstaVdmAPI", return_value=api):
        yield api


@pytest.fixture
def mock_api_single_flat() -> Generator[MagicMock]:
    """Patch the API client used by the integration with a one-flat account."""
    api = build_api_mock([FLAT_1])
    with patch("custom_components.ista_vdm.IstaVdmAPI", return_value=api):
        yield api
