"""Push coordinator for Power Watchdog WiFi."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from contextlib import suppress
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api import ReadOnlyWatchdogClient, WatchdogAuthError, WatchdogConnectionError
from .const import (
    DEVICE_METADATA_REFRESH_INTERVAL_SECONDS,
    DOMAIN,
    TELEMETRY_AVAILABILITY_TIMEOUT_SECONDS,
    WS_RECONNECT_MAX_SECONDS,
    WS_RECONNECT_MIN_SECONDS,
)
from .models import WatchdogDeviceMetadata, WatchdogSnapshot, metadata_from_device_row

_LOGGER = logging.getLogger(__name__)


class WatchdogCoordinator(DataUpdateCoordinator[WatchdogSnapshot]):
    """Maintain a read-only WebSocket subscription."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: ReadOnlyWatchdogClient,
        device_no: str,
        initial_device_metadata: WatchdogDeviceMetadata | None = None,
    ) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.client = client
        self.device_no = device_no
        self._task: asyncio.Task[None] | None = None
        self._availability_task: asyncio.Task[None] | None = None
        self._metadata_task: asyncio.Task[None] | None = None
        self._availability_timeout = timedelta(
            seconds=TELEMETRY_AVAILABILITY_TIMEOUT_SECONDS
        )
        self._device_refresh_interval = timedelta(
            seconds=DEVICE_METADATA_REFRESH_INTERVAL_SECONDS
        )
        self._timed_out = False
        now = dt_util.utcnow()
        self.data = WatchdogSnapshot(
            device_metadata=initial_device_metadata,
            last_device_refresh_timestamp=(
                now if initial_device_metadata is not None else None
            ),
        )

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
        if self._metadata_task is None:
            self._metadata_task = self.config_entry.async_create_background_task(
                self.hass,
                self._async_refresh_metadata_periodic(),
                f"{DOMAIN}_{self.device_no}_metadata",
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
        if self._metadata_task is not None:
            self._metadata_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._metadata_task
            self._metadata_task = None

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
                        await self._async_refresh_device_metadata(force=True)

                    if event.telemetry is not None:
                        self._timed_out = False
                        self.async_set_updated_data(
                            replace(
                                self.data,
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
                            replace(
                                self.data,
                                reconnect_count=reconnect_count,
                                decode_error_count=decode_error_count,
                                packet_count=packet_count,
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
                    replace(
                        snapshot,
                        last_connection_error=str(err),
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

    async def _async_refresh_metadata_periodic(self) -> None:
        """Refresh metadata on a bounded interval."""
        while True:
            await asyncio.sleep(DEVICE_METADATA_REFRESH_INTERVAL_SECONDS)
            await self._async_refresh_device_metadata(force=False)

    async def _async_refresh_device_metadata(self, force: bool) -> None:
        """Refresh normalized metadata from the device list."""
        snapshot = self.data
        last_refresh = snapshot.last_device_refresh_timestamp
        if (
            not force
            and last_refresh is not None
            and dt_util.utcnow() - last_refresh < self._device_refresh_interval
        ):
            return

        try:
            devices = await self.client.async_list_devices()
        except WatchdogConnectionError as err:
            _LOGGER.warning("Power Watchdog metadata refresh failed: %s", err)
            return

        device = next(
            (
                candidate
                for candidate in devices
                if str(candidate.get("device_no")) == self.device_no
            ),
            None,
        )
        if device is None:
            return

        metadata = metadata_from_device_row(self.device_no, device)
        self.async_set_updated_data(
            replace(
                self.data,
                device_metadata=metadata,
                last_device_refresh_timestamp=dt_util.utcnow(),
            )
        )
