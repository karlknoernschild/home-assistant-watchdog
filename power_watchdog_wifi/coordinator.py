"""Push coordinator for Power Watchdog WiFi."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import ReadOnlyWatchdogClient, WatchdogAuthError, WatchdogConnectionError
from .const import (
    DOMAIN,
    WS_RECONNECT_MAX_SECONDS,
    WS_RECONNECT_MIN_SECONDS,
)
from .models import WatchdogTelemetry

_LOGGER = logging.getLogger(__name__)


class WatchdogCoordinator(DataUpdateCoordinator[WatchdogTelemetry]):
    """Maintain a read-only WebSocket subscription."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: ReadOnlyWatchdogClient,
        device_no: str,
    ) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.client = client
        self.device_no = device_no
        self._task: asyncio.Task[None] | None = None

    async def async_start(self) -> None:
        """Start the push listener."""
        if self._task is None:
            self._task = self.config_entry.async_create_background_task(
                self.hass,
                self._async_listen(),
                f"{DOMAIN}_{self.device_no}",
            )

    async def async_stop(self) -> None:
        """Stop the push listener."""
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _async_listen(self) -> None:
        delay = WS_RECONNECT_MIN_SECONDS
        while True:
            try:
                async for telemetry in self.client.async_telemetry(self.device_no):
                    self.async_set_updated_data(telemetry)
                    delay = WS_RECONNECT_MIN_SECONDS
            except asyncio.CancelledError:
                raise
            except WatchdogAuthError:
                _LOGGER.error("Power Watchdog authentication failed")
                self.async_set_update_error(
                    WatchdogAuthError("Authentication failed")
                )
                return
            except WatchdogConnectionError as err:
                _LOGGER.warning(
                    "Power Watchdog telemetry disconnected; retrying in %s seconds: %s",
                    delay,
                    err,
                )
                self.async_set_update_error(err)
            await asyncio.sleep(delay)
            delay = min(delay * 2, WS_RECONNECT_MAX_SECONDS)
