"""Push coordinator for Power Watchdog WiFi."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api import ReadOnlyWatchdogClient, WatchdogAuthError, WatchdogConnectionError
from .const import (
    DOMAIN,
    TELEMETRY_AVAILABILITY_TIMEOUT_SECONDS,
    WS_RECONNECT_MAX_SECONDS,
    WS_RECONNECT_MIN_SECONDS,
)
from .models import WatchdogSnapshot

_LOGGER = logging.getLogger(__name__)


class WatchdogCoordinator(DataUpdateCoordinator[WatchdogSnapshot]):
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
        self._availability_task: asyncio.Task[None] | None = None
        self._availability_timeout = timedelta(
            seconds=TELEMETRY_AVAILABILITY_TIMEOUT_SECONDS
        )
        self._timed_out = False
        self.data = WatchdogSnapshot()

    async def async_start(self) -> None:
        """Start the push listener."""
        if self._task is None:
            self._task = self.config_entry.async_create_background_task(
                self.hass,
                self._async_listen(),
                f"{DOMAIN}_{self.device_no}",
            )
        if self._availability_task is None:
            self._availability_task = self.config_entry.async_create_background_task(
                self.hass,
                self._async_track_availability_timeout(),
                f"{DOMAIN}_{self.device_no}_availability",
            )

    async def async_stop(self) -> None:
        """Stop the push listener."""
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._availability_task is not None:
            self._availability_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._availability_task
            self._availability_task = None

    @property
    def available(self) -> bool:
        """Return coordinator availability based on telemetry timeout."""
        if self.data.latest_telemetry is None:
            return False
        return not self._timed_out

    async def _async_listen(self) -> None:
        delay = WS_RECONNECT_MIN_SECONDS
        while True:
            try:
                first_valid_packet = True
                async for event in self.client.async_telemetry(self.device_no):
                    snapshot = self.data
                    packet_count = snapshot.packet_count + 1
                    decode_error_count = snapshot.decode_error_count + int(
                        event.decode_error
                    )
                    reconnect_count = snapshot.reconnect_count
                    last_successful_connect_timestamp = (
                        snapshot.last_successful_connect_timestamp
                    )

                    if event.telemetry is not None and first_valid_packet:
                        if last_successful_connect_timestamp is not None:
                            reconnect_count += 1
                        last_successful_connect_timestamp = dt_util.utcnow()
                        first_valid_packet = False

                    if event.telemetry is not None:
                        self._timed_out = False
                        self.async_set_updated_data(
                            WatchdogSnapshot(
                                latest_telemetry=event.telemetry,
                                last_telemetry_timestamp=dt_util.utcnow(),
                                reconnect_count=reconnect_count,
                                decode_error_count=decode_error_count,
                                packet_count=packet_count,
                                last_connection_error=None,
                                last_successful_connect_timestamp=(
                                    last_successful_connect_timestamp
                                ),
                            )
                        )
                        delay = WS_RECONNECT_MIN_SECONDS
                    else:
                        self.async_set_updated_data(
                            WatchdogSnapshot(
                                latest_telemetry=snapshot.latest_telemetry,
                                last_telemetry_timestamp=snapshot.last_telemetry_timestamp,
                                reconnect_count=reconnect_count,
                                decode_error_count=decode_error_count,
                                packet_count=packet_count,
                                last_connection_error=snapshot.last_connection_error,
                                last_successful_connect_timestamp=(
                                    last_successful_connect_timestamp
                                ),
                            )
                        )

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
                snapshot = self.data
                self.async_set_updated_data(
                    WatchdogSnapshot(
                        latest_telemetry=snapshot.latest_telemetry,
                        last_telemetry_timestamp=snapshot.last_telemetry_timestamp,
                        reconnect_count=snapshot.reconnect_count,
                        decode_error_count=snapshot.decode_error_count,
                        packet_count=snapshot.packet_count,
                        last_connection_error=str(err),
                        last_successful_connect_timestamp=(
                            snapshot.last_successful_connect_timestamp
                        ),
                    )
                )
            await asyncio.sleep(delay)
            delay = min(delay * 2, WS_RECONNECT_MAX_SECONDS)

    async def _async_track_availability_timeout(self) -> None:
        """Track timeout-based availability for telemetry."""
        while True:
            await asyncio.sleep(1)
            snapshot = self.data
            last_telemetry_timestamp = snapshot.last_telemetry_timestamp
            timed_out = (
                last_telemetry_timestamp is not None
                and dt_util.utcnow() - last_telemetry_timestamp > self._availability_timeout
            )
            if timed_out != self._timed_out:
                self._timed_out = timed_out
                self.async_update_listeners()
