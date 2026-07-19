"""Power Watchdog WiFi integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ReadOnlyWatchdogClient, WatchdogAuthError, WatchdogConnectionError
from .const import (
    CONF_ACCOUNT,
    CONF_CONNECTION_MODE,
    CONF_CONNECT_TYPE,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_NO,
    CONF_FIRMWARE,
    CONF_MCU_FIRMWARE,
    CONF_LOG_LEVEL,
    CONF_POLL_INTERVAL_MINUTES,
    CONF_SOCKET_STATE,
    CONF_START_FROM,
    DEFAULT_CONNECTION_MODE,
    DEFAULT_LOG_LEVEL,
    DEFAULT_POLL_INTERVAL_MINUTES,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import WatchdogCoordinator
from .logging_utils import apply_package_log_level
from .models import metadata_from_device_row
from .repairs import (
    ISSUE_DEVICE_MAPPING_UNSUPPORTED,
    clear_issue,
    clear_runtime_issues,
    create_auth_failed_issue,
    create_cannot_connect_issue,
    create_device_mapping_unsupported_issue,
)

_LOGGER = logging.getLogger(__name__)


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
    applied_log_level = apply_package_log_level(
        str(entry.options.get(CONF_LOG_LEVEL, DEFAULT_LOG_LEVEL))
    )
    _LOGGER.info(
        "Setting up %s entry_id=%s device_no=%s connection_mode=%s poll_interval=%s min log_level=%s",
        DOMAIN,
        entry.entry_id,
        entry.data.get(CONF_DEVICE_NO, "unknown"),
        entry.options.get(CONF_CONNECTION_MODE, DEFAULT_CONNECTION_MODE),
        entry.options.get(CONF_POLL_INTERVAL_MINUTES, DEFAULT_POLL_INTERVAL_MINUTES),
        applied_log_level,
    )

    # Setup is intentionally front-loaded with a device-list check so we can
    # fail fast on auth/connectivity/mapping problems before entity platforms
    # are created.
    client = ReadOnlyWatchdogClient(
        async_get_clientsession(hass),
        entry.data[CONF_ACCOUNT],
        entry.data[CONF_PASSWORD],
    )
    try:
        devices = await client.async_list_devices()
    except WatchdogAuthError as err:
        _LOGGER.error("Initial cloud authentication failed for entry_id=%s", entry.entry_id)
        create_auth_failed_issue(hass, entry.entry_id)
        raise ConfigEntryAuthFailed from err
    except WatchdogConnectionError as err:
        _LOGGER.warning(
            "Initial cloud device-list request failed for entry_id=%s: %s",
            entry.entry_id,
            err,
        )
        create_cannot_connect_issue(hass, entry.entry_id)
        raise ConfigEntryNotReady from err

    device_no = entry.data[CONF_DEVICE_NO]
    device = next(
        (
            candidate
            for candidate in devices
            if str(candidate.get("device_no")) == device_no
        ),
        None,
    )
    if device is None:
        _LOGGER.error(
            "Configured device_no=%s not found in account list for entry_id=%s",
            device_no,
            entry.entry_id,
        )
        create_device_mapping_unsupported_issue(hass, entry.entry_id)
        raise ConfigEntryNotReady("Configured Watchdog was not returned by the account")
    clear_issue(hass, entry.entry_id, ISSUE_DEVICE_MAPPING_UNSUPPORTED)
    clear_runtime_issues(hass, entry.entry_id)

    metadata = metadata_from_device_row(device_no, device)
    coordinator = WatchdogCoordinator(hass, client, device_no, metadata)
    coordinator.config_entry = entry
    coordinator.configure_connection(
        str(entry.options.get(CONF_CONNECTION_MODE, DEFAULT_CONNECTION_MODE)),
        int(entry.options.get(CONF_POLL_INTERVAL_MINUTES, DEFAULT_POLL_INTERVAL_MINUTES)),
    )
    entry.runtime_data = WatchdogRuntimeData(client, coordinator)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Keep stored config-entry metadata aligned with current cloud metadata so
    # device registry fields stay accurate across reloads/restarts.
    updated_data = {
        **entry.data,
        CONF_DEVICE_ID: metadata.device_id or entry.data.get(CONF_DEVICE_ID),
        CONF_DEVICE_NAME: metadata.name or entry.data.get(CONF_DEVICE_NAME),
        CONF_FIRMWARE: metadata.firmware or entry.data.get(CONF_FIRMWARE),
        CONF_MCU_FIRMWARE: metadata.mcu_firmware or entry.data.get(CONF_MCU_FIRMWARE),
        CONF_CONNECT_TYPE: metadata.connect_type or entry.data.get(CONF_CONNECT_TYPE),
        CONF_SOCKET_STATE: metadata.socket_state or entry.data.get(CONF_SOCKET_STATE),
        CONF_START_FROM: metadata.start_from or entry.data.get(CONF_START_FROM),
    }
    if updated_data != entry.data:
        hass.config_entries.async_update_entry(entry, data=updated_data)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_start()
    _LOGGER.info("Setup complete for entry_id=%s", entry.entry_id)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: WatchdogConfigEntry,
) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading entry_id=%s", entry.entry_id)
    await entry.runtime_data.coordinator.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: WatchdogConfigEntry) -> None:
    """Reload config entry when options change."""
    _LOGGER.info("Options updated; reloading entry_id=%s", entry.entry_id)
    apply_package_log_level(str(entry.options.get(CONF_LOG_LEVEL, DEFAULT_LOG_LEVEL)))
    await hass.config_entries.async_reload(entry.entry_id)
