"""Config flow for Power Watchdog WiFi."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ReadOnlyWatchdogClient, WatchdogAuthError, WatchdogConnectionError
from .const import (
    CONF_ACCOUNT,
    CONF_CONNECT_TYPE,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_NO,
    CONF_FIRMWARE,
    CONF_MCU_FIRMWARE,
    CONF_SOCKET_STATE,
    CONF_START_FROM,
    DOMAIN,
)


class PowerWatchdogConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Power Watchdog WiFi config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._account = ""
        self._password = ""
        self._devices: list[dict[str, Any]] = []

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Collect credentials and discover devices."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._account = user_input[CONF_ACCOUNT].strip()
            self._password = user_input[CONF_PASSWORD]
            client = ReadOnlyWatchdogClient(
                async_get_clientsession(self.hass),
                self._account,
                self._password,
            )
            try:
                self._devices = await client.async_list_devices()
            except WatchdogAuthError:
                errors["base"] = "invalid_auth"
            except WatchdogConnectionError:
                errors["base"] = "cannot_connect"
            else:
                if not self._devices:
                    errors["base"] = "no_devices"
                elif len(self._devices) == 1:
                    return await self._create_for_device(self._devices[0])
                else:
                    return await self.async_step_device()

        schema = vol.Schema(
            {
                vol.Required(CONF_ACCOUNT): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_device(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Select one device when the account has multiple."""
        if user_input is not None:
            selected = user_input[CONF_DEVICE_NO]
            device = next(
                item
                for item in self._devices
                if str(item.get("device_no")) == selected
            )
            return await self._create_for_device(device)

        options = {
            str(item.get("device_no")): str(item.get("name") or item.get("device_no"))
            for item in self._devices
        }
        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {vol.Required(CONF_DEVICE_NO): vol.In(options)}
            ),
        )

    async def _create_for_device(self, device: dict[str, Any]) -> FlowResult:
        device_no = str(device["device_no"])
        await self.async_set_unique_id(device_no)
        self._abort_if_unique_id_configured()

        name = str(device.get("name") or "Power Watchdog")
        return self.async_create_entry(
            title=name,
            data={
                CONF_ACCOUNT: self._account,
                CONF_PASSWORD: self._password,
                CONF_DEVICE_NO: device_no,
                CONF_DEVICE_ID: device.get("id"),
                CONF_DEVICE_NAME: name,
                CONF_FIRMWARE: device.get("version"),
                CONF_MCU_FIRMWARE: device.get("mcu_version"),
                CONF_CONNECT_TYPE: device.get("connect_type"),
                CONF_SOCKET_STATE: device.get("socket_state"),
                CONF_START_FROM: device.get("start_from"),
            },
        )
