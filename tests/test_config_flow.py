"""Test the ista VDM config flow."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_USER
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.loader import async_get_integration

from custom_components.ista_vdm.config_flow import CannotConnect
from custom_components.ista_vdm.const import DOMAIN
from ista_vdm_api import IstaVdmAuthError, IstaVdmConnectionError


@pytest.fixture(autouse=True)
def mock_setup_entry():
    """Do not set up the entries the flows create; the flow is under test."""
    with patch(
        "custom_components.ista_vdm.async_setup_entry", return_value=True
    ) as setup_entry:
        yield setup_entry


@pytest.fixture
def mock_api():
    """Mock the IstaVdmAPI class."""
    with patch(
        "custom_components.ista_vdm.config_flow.IstaVdmAPI",
        autospec=True,
    ) as mock_api_class:
        api_instance = AsyncMock()
        api_instance.authenticate = AsyncMock(return_value=True)
        api_instance.flat_id = "12345"
        api_instance.user_id = "67890"
        mock_api_class.return_value = api_instance
        yield mock_api_class


async def test_form(hass: HomeAssistant, mock_api) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}


async def test_user_form_success(hass: HomeAssistant, mock_api) -> None:
    """Test successful user form submission."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Ista VDM (test@example.com)"
    assert result["data"] == {
        CONF_EMAIL: "test@example.com",
        CONF_PASSWORD: "test_password",
    }


async def test_invalid_auth(hass: HomeAssistant) -> None:
    """Test we handle invalid auth."""
    with patch(
        "custom_components.ista_vdm.config_flow.IstaVdmAPI.authenticate",
        side_effect=IstaVdmAuthError("Invalid credentials"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "wrong_password",
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    with patch(
        "custom_components.ista_vdm.config_flow.IstaVdmAPI.authenticate",
        side_effect=CannotConnect,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "test_password",
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_portal_outage_is_cannot_connect(hass: HomeAssistant) -> None:
    """A portal outage is reported as cannot_connect, not as a wrong password."""
    with patch(
        "custom_components.ista_vdm.config_flow.IstaVdmAPI.authenticate",
        side_effect=IstaVdmConnectionError("Failed to load login page: 503"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "test_password",
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_no_options_flow(hass: HomeAssistant) -> None:
    """The integration has nothing to configure, so it offers no options flow."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id="test@example.com")
    entry.add_to_hass(hass)
    await async_get_integration(hass, DOMAIN)
    assert entry.supports_options is False


async def test_reauth_flow(hass: HomeAssistant, mock_api) -> None:
    """Test reauthentication flow."""
    # Create an existing entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "old_password",
        },
        unique_id="test@example.com",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": SOURCE_REAUTH,
            "entry_id": entry.entry_id,
        },
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "old_password",
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["description_placeholders"]["email"] == "test@example.com"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PASSWORD: "new_password"},
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"

    assert entry.data[CONF_PASSWORD] == "new_password"


async def test_duplicate_entry(hass: HomeAssistant, mock_api) -> None:
    """Test duplicate entry handling."""
    # Create first entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "password",
        },
        unique_id="test@example.com",
    )
    entry.add_to_hass(hass)

    # Try to create second entry with same email
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "password2",
        },
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
