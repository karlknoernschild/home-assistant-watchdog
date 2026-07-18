"""Power Watchdog WiFi integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ReadOnlyWatchdogClient, WatchdogAuthError, WatchdogConnectionError
from .const import CONF_ACCOUNT, CONF_DEVICE_NO, PLATFORMS
from .coordinator import WatchdogCoordinator


@dataclass(slots=True)
class WatchdogRuntimeData:
    """Runtime data for a config entry."""

    client: ReadOnlyWatchdogClient
    coordinator: WatchdogCoordinator


type WatchdogConfigEntry = ConfigEntry[WatchdogRuntimeData]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WatchdogConfigEntry,
) -> bool:
    """Set up Power Watchdog WiFi from a config entry."""
    client = ReadOnlyWatchdogClient(
        async_get_clientsession(hass),
        entry.data[CONF_ACCOUNT],
        entry.data[CONF_PASSWORD],
    )
    try:
        devices = await client.async_list_devices()
    except WatchdogAuthError as err:
        raise ConfigEntryAuthFailed from err
    except WatchdogConnectionError as err:
        raise ConfigEntryNotReady from err

    device_no = entry.data[CONF_DEVICE_NO]
    if not any(str(device.get("device_no")) == device_no for device in devices):
        raise ConfigEntryNotReady("Configured Watchdog was not returned by the account")

    coordinator = WatchdogCoordinator(hass, client, device_no)
    coordinator.config_entry = entry
    entry.runtime_data = WatchdogRuntimeData(client, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_start()
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: WatchdogConfigEntry,
) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.coordinator.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
