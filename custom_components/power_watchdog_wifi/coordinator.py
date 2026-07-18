"""Push coordinator for Power Watchdog WiFi.

This coordinator is the central runtime state machine for the integration.
It combines multiple concerns in one place so entities can stay thin:
- telemetry subscription lifecycle and reconnect/backoff behavior
- timeout-based availability transitions
- runtime counters for diagnostics
- periodic metadata refresh
- derived metric calculation + persistence
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from contextlib import suppress
from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api import ReadOnlyWatchdogClient, WatchdogAuthError, WatchdogConnectionError
from .const import (
    DERIVED_ENERGY_STATE_PERSIST_INTERVAL_SECONDS,
    DERIVED_ENERGY_STORAGE_KEY,
    DERIVED_ENERGY_STORAGE_VERSION,
    DERIVED_ROLLING_POWER_WINDOW_SECONDS,
    DEVICE_METADATA_REFRESH_INTERVAL_SECONDS,
    DOMAIN,
    TELEMETRY_AVAILABILITY_TIMEOUT_SECONDS,
    WS_RECONNECT_MAX_SECONDS,
    WS_RECONNECT_MIN_SECONDS,
)
from .models import (
    WatchdogDerivedEnergyState,
    WatchdogDeviceMetadata,
    WatchdogSnapshot,
    WatchdogTelemetry,
    metadata_from_device_row,
)
from .repairs import (
    clear_runtime_issues,
    create_auth_failed_issue,
    create_cannot_connect_issue,
)

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
        self._derived_rolling_power_window = timedelta(
            seconds=DERIVED_ROLLING_POWER_WINDOW_SECONDS
        )
        self._derived_state_persist_interval = timedelta(
            seconds=DERIVED_ENERGY_STATE_PERSIST_INTERVAL_SECONDS
        )
        self._derived_energy_store: Store[dict[str, Any]] = Store(
            hass,
            DERIVED_ENERGY_STORAGE_VERSION,
            f"{DERIVED_ENERGY_STORAGE_KEY}_{device_no}",
        )
        self._derived_energy_state: WatchdogDerivedEnergyState | None = None
        self._last_derived_state_persist_timestamp: datetime | None = None
        self._rolling_power_values: deque[tuple[datetime, float]] = deque()
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
        await self._async_load_derived_energy_state()
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
        await self._async_maybe_persist_derived_energy_state(force=True)

    @property
    def available(self) -> bool:
        """Return coordinator availability based on telemetry timeout."""
        if self.data.latest_telemetry is None:
            return False
        return not self._timed_out

    async def _async_listen(self) -> None:
        # Reconnect with exponential backoff; delay resets whenever a valid
        # packet is processed.
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
                        # Reconnect is the best moment to refresh metadata;
                        # cloud-side firmware/connectivity fields can change.
                        await self._async_refresh_device_metadata(force=True)

                    if event.telemetry is not None:
                        clear_runtime_issues(self.hass, self.config_entry.entry_id)
                        now = dt_util.utcnow()
                        (
                            derived_today_energy_kwh,
                            derived_yesterday_energy_kwh,
                            derived_rolling_average_power_w,
                        ) = self._update_derived_metrics(event.telemetry, now)
                        await self._async_maybe_persist_derived_energy_state(
                            force=False
                        )
                        self._timed_out = False
                        self.async_set_updated_data(
                            replace(
                                self.data,
                                latest_telemetry=event.telemetry,
                                last_telemetry_timestamp=now,
                                reconnect_count=reconnect_count,
                                decode_error_count=decode_error_count,
                                packet_count=packet_count,
                                last_connection_error=None,
                                last_successful_connect_timestamp=(
                                    last_successful_connect_timestamp
                                ),
                                derived_today_energy_kwh=derived_today_energy_kwh,
                                derived_yesterday_energy_kwh=(
                                    derived_yesterday_energy_kwh
                                ),
                                derived_rolling_average_power_w=(
                                    derived_rolling_average_power_w
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
                create_auth_failed_issue(self.hass, self.config_entry.entry_id)
                self.async_set_update_error(
                    WatchdogAuthError("Authentication failed")
                )
                return
            except WatchdogConnectionError as err:
                create_cannot_connect_issue(self.hass, self.config_entry.entry_id)
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
                and dt_util.utcnow() - last_telemetry_timestamp
                > self._availability_timeout
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

        # Metadata refreshes should not discard runtime counters/telemetry, so
        # we replace only metadata-related fields on the current snapshot.
        metadata = metadata_from_device_row(self.device_no, device)
        self.async_set_updated_data(
            replace(
                self.data,
                device_metadata=metadata,
                last_device_refresh_timestamp=dt_util.utcnow(),
            )
        )

    async def _async_load_derived_energy_state(self) -> None:
        """Load persisted derived daily energy state."""
        stored = await self._derived_energy_store.async_load()
        if not isinstance(stored, dict):
            return
        try:
            day_iso = str(stored["day_iso"])
            day_start_total_energy_kwh = float(stored["day_start_total_energy_kwh"])
            today_energy_kwh = float(stored["today_energy_kwh"])
            yesterday_energy_kwh = float(stored["yesterday_energy_kwh"])
            date.fromisoformat(day_iso)
        except (KeyError, TypeError, ValueError):
            _LOGGER.warning("Invalid persisted derived energy state; ignoring")
            return

        self._derived_energy_state = WatchdogDerivedEnergyState(
            day_iso=day_iso,
            day_start_total_energy_kwh=day_start_total_energy_kwh,
            today_energy_kwh=max(0.0, today_energy_kwh),
            yesterday_energy_kwh=max(0.0, yesterday_energy_kwh),
        )
        self.data = replace(
            self.data,
            derived_today_energy_kwh=self._derived_energy_state.today_energy_kwh,
            derived_yesterday_energy_kwh=self._derived_energy_state.yesterday_energy_kwh,
        )

    async def _async_maybe_persist_derived_energy_state(self, force: bool) -> None:
        """Persist derived energy state on interval or forced shutdown."""
        if self._derived_energy_state is None:
            return

        now = dt_util.utcnow()
        if not force and self._last_derived_state_persist_timestamp is not None:
            if (
                now - self._last_derived_state_persist_timestamp
                < self._derived_state_persist_interval
            ):
                return

        await self._derived_energy_store.async_save(
            {
                "day_iso": self._derived_energy_state.day_iso,
                "day_start_total_energy_kwh": (
                    self._derived_energy_state.day_start_total_energy_kwh
                ),
                "today_energy_kwh": self._derived_energy_state.today_energy_kwh,
                "yesterday_energy_kwh": self._derived_energy_state.yesterday_energy_kwh,
            }
        )
        self._last_derived_state_persist_timestamp = now

    def _update_derived_metrics(
        self,
        telemetry: WatchdogTelemetry,
        now_utc: datetime,
    ) -> tuple[float, float, float]:
        """Update derived rolling power and day-bucket energy metrics."""
        total_energy_kwh = telemetry.total_energy_kwh
        total_power_w = telemetry.total_power_w
        now_day_iso = dt_util.as_local(now_utc).date().isoformat()

        state = self._derived_energy_state
        if state is None:
            state = WatchdogDerivedEnergyState(
                day_iso=now_day_iso,
                day_start_total_energy_kwh=total_energy_kwh,
                today_energy_kwh=0.0,
                yesterday_energy_kwh=0.0,
            )
        elif now_day_iso != state.day_iso:
            previous_day = date.fromisoformat(state.day_iso)
            current_day = date.fromisoformat(now_day_iso)
            day_gap = (current_day - previous_day).days
            # If we miss more than one local day, yesterday is reset because
            # we cannot reliably reconstruct skipped-day buckets.
            state = WatchdogDerivedEnergyState(
                day_iso=now_day_iso,
                day_start_total_energy_kwh=total_energy_kwh,
                today_energy_kwh=0.0,
                yesterday_energy_kwh=state.today_energy_kwh if day_gap == 1 else 0.0,
            )
        elif total_energy_kwh < state.day_start_total_energy_kwh:
            # Device/cloud counters can reset; re-anchor the daily baseline to
            # avoid negative derived daily energy.
            state = replace(
                state,
                day_start_total_energy_kwh=total_energy_kwh,
                today_energy_kwh=0.0,
            )
        else:
            state = replace(
                state,
                today_energy_kwh=max(
                    0.0, total_energy_kwh - state.day_start_total_energy_kwh
                ),
            )
        self._derived_energy_state = state

        self._rolling_power_values.append((now_utc, total_power_w))
        cutoff = now_utc - self._derived_rolling_power_window
        while self._rolling_power_values and self._rolling_power_values[0][0] < cutoff:
            self._rolling_power_values.popleft()
        rolling_average_power_w = sum(
            value for _, value in self._rolling_power_values
        ) / len(self._rolling_power_values)

        return (
            state.today_energy_kwh,
            state.yesterday_energy_kwh,
            rolling_average_power_w,
        )
