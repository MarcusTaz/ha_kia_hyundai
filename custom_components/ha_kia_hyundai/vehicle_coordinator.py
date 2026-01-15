from asyncio import sleep
from datetime import timedelta, datetime
from logging import getLogger

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util
from homeassistant.core import HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, REQUEST_REFRESH_DEFAULT_COOLDOWN

from hyundai_kia_connect_api import VehicleManager

from custom_components.ha_kia_hyundai import DOMAIN
from custom_components.ha_kia_hyundai.const import (
    DELAY_BETWEEN_ACTION_IN_PROGRESS_CHECKING,
    TEMPERATURE_MAX,
    TEMPERATURE_MIN,
    SeatSettings,
)

_LOGGER = getLogger(__name__)


class VehicleCoordinator(DataUpdateCoordinator):
    """Kia US vehicle coordinator."""

    climate_desired_defrost: bool = False
    climate_desired_heating_acc: bool = False
    desired_driver_seat_comfort: SeatSettings | None = None
    desired_passenger_seat_comfort: SeatSettings | None = None
    desired_left_rear_seat_comfort: SeatSettings | None = None
    desired_right_rear_seat_comfort: SeatSettings | None = None

    def __init__(
            self,
            hass: HomeAssistant,
            config_entry: ConfigEntry,
            vehicle_id: str,
            vehicle_name: str,
            vehicle_model: str,
            vehicle_manager: VehicleManager,
            scan_interval: timedelta,
    ) -> None:
        """Initialize the vehicle coordinator."""
        self.vehicle_id: str = vehicle_id
        self.vehicle_name: str = vehicle_name
        self.vehicle_model: str = vehicle_model
        self.vehicle_manager: VehicleManager = vehicle_manager
        
        request_refresh_debouncer = Debouncer(
            hass,
            _LOGGER,
            cooldown=REQUEST_REFRESH_DEFAULT_COOLDOWN,
            immediate=False,
        )

        async def refresh() -> dict:
            """Refresh vehicle data."""
            try:
                # Update vehicle with cached state
                await hass.async_add_executor_job(
                    vehicle_manager.update_vehicle_with_cached_state,
                    vehicle_id
                )
                
                # Get the vehicle object
                vehicle = vehicle_manager.vehicles.get(vehicle_id)
                if vehicle is None:
                    _LOGGER.error(f"Vehicle {vehicle_id} not found in manager")
                    return {}
                
                # Return the vehicle object itself as data
                # The properties will access it directly
                return {"vehicle": vehicle}
                
            except Exception as err:
                _LOGGER.error(f"Error refreshing vehicle data: {err}")
                raise

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}-{self.vehicle_name}",
            update_interval=scan_interval,
            update_method=refresh,
            request_refresh_debouncer=request_refresh_debouncer,
            always_update=False
        )

    @property
    def vehicle(self):
        """Get the vehicle object from data."""
        if self.data and "vehicle" in self.data:
            return self.data["vehicle"]
        return None

    @property
    def id(self) -> str:
        """Return kia vehicle id."""
        return self.vehicle_id

    @property
    def can_remote_lock(self) -> bool:
        return True  # Assume all USA Kia vehicles support remote lock

    @property
    def doors_locked(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'door_lock'):
            return self.vehicle.door_lock
        return None

    @property
    def last_action_name(self) -> str:
        # The new library doesn't expose action tracking the same way
        return None

    @property
    def latitude(self) -> float:
        if self.vehicle and hasattr(self.vehicle, 'location_latitude'):
            return self.vehicle.location_latitude
        return None

    @property
    def longitude(self) -> float:
        if self.vehicle and hasattr(self.vehicle, 'location_longitude'):
            return self.vehicle.location_longitude
        return None

    @property
    def ev_battery_level(self) -> float:
        if self.vehicle and hasattr(self.vehicle, 'ev_battery_percentage'):
            return self.vehicle.ev_battery_percentage
        return None

    @property
    def odometer_value(self) -> float:
        if self.vehicle and hasattr(self.vehicle, 'odometer'):
            return self.vehicle.odometer
        return None

    @property
    def car_battery_level(self) -> int:
        if self.vehicle and hasattr(self.vehicle, 'car_battery_percentage'):
            return self.vehicle.car_battery_percentage
        return None

    @property
    def last_synced_to_cloud(self) -> datetime:
        if self.vehicle and hasattr(self.vehicle, 'last_updated_at'):
            return self.vehicle.last_updated_at
        return None

    @property
    def last_synced_from_cloud(self) -> datetime:
        if self.vehicle and hasattr(self.vehicle, 'last_updated_at'):
            return self.vehicle.last_updated_at
        return None

    @property
    def next_service_mile_value(self) -> float:
        if self.vehicle and hasattr(self.vehicle, 'next_service_mile'):
            return self.vehicle.next_service_mile
        return None

    @property
    def can_remote_climate(self) -> bool:
        return True  # Assume all USA Kia EVs support remote climate

    @property
    def climate_hvac_on(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'air_control_is_on'):
            return self.vehicle.air_control_is_on
        return None

    @property
    def climate_temperature_value(self) -> int:
        if self.vehicle and hasattr(self.vehicle, 'air_temperature'):
            temp = self.vehicle.air_temperature
            if temp:
                try:
                    return int(temp)
                except:
                    pass
        return None

    @property
    def climate_defrost_on(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'defrost_is_on'):
            return self.vehicle.defrost_is_on
        return None

    @property
    def climate_heated_rear_window_on(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'back_window_heater_is_on'):
            return self.vehicle.back_window_heater_is_on
        return None

    @property
    def climate_heated_side_mirror_on(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'side_mirror_heater_is_on'):
            return self.vehicle.side_mirror_heater_is_on
        return None

    @property
    def climate_heated_steering_wheel_on(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'steering_wheel_heater_is_on'):
            return self.vehicle.steering_wheel_heater_is_on
        return None

    @property
    def door_hood_open(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'hood_is_open'):
            return self.vehicle.hood_is_open
        return None

    @property
    def door_trunk_open(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'trunk_is_open'):
            return self.vehicle.trunk_is_open
        return None

    @property
    def door_front_left_open(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'front_left_door_is_open'):
            return self.vehicle.front_left_door_is_open
        return None

    @property
    def door_front_right_open(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'front_right_door_is_open'):
            return self.vehicle.front_right_door_is_open
        return None

    @property
    def door_back_left_open(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'back_left_door_is_open'):
            return self.vehicle.back_left_door_is_open
        return None

    @property
    def door_back_right_open(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'back_right_door_is_open'):
            return self.vehicle.back_right_door_is_open
        return None

    @property
    def engine_on(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'engine_is_running'):
            return self.vehicle.engine_is_running
        return None

    @property
    def tire_all_on(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'tire_pressure_all_warning_is_on'):
            return self.vehicle.tire_pressure_all_warning_is_on
        return None

    @property
    def low_fuel_light_on(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'low_fuel_light_is_on'):
            return self.vehicle.low_fuel_light_is_on
        return None

    @property
    def fuel_level(self) -> float:
        if self.vehicle and hasattr(self.vehicle, 'fuel_level'):
            return self.vehicle.fuel_level
        return None

    @property
    def ev_battery_charging(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'ev_battery_is_charging'):
            return self.vehicle.ev_battery_is_charging
        return None

    @property
    def ev_plugged_in(self) -> bool:
        if self.vehicle and hasattr(self.vehicle, 'ev_battery_is_plugged_in'):
            return self.vehicle.ev_battery_is_plugged_in
        return None

    @property
    def ev_charge_limits_ac(self) -> int:
        if self.vehicle and hasattr(self.vehicle, 'ev_charge_limits_ac'):
            return self.vehicle.ev_charge_limits_ac
        return None

    @property
    def ev_charge_limits_dc(self) -> int:
        if self.vehicle and hasattr(self.vehicle, 'ev_charge_limits_dc'):
            return self.vehicle.ev_charge_limits_dc
        return None

    @property
    def ev_charge_current_remaining_duration(self) -> int:
        if self.vehicle and hasattr(self.vehicle, 'ev_estimated_current_charge_duration'):
            return self.vehicle.ev_estimated_current_charge_duration
        return None

    @property
    def ev_remaining_range_value(self) -> int:
        if self.vehicle and hasattr(self.vehicle, 'ev_driving_range'):
            return self.vehicle.ev_driving_range
        return None

    @property
    def fuel_remaining_range_value(self) -> int:
        if self.vehicle and hasattr(self.vehicle, 'fuel_driving_range'):
            return self.vehicle.fuel_driving_range
        return None

    @property
    def total_remaining_range_value(self) -> int:
        if self.vehicle and hasattr(self.vehicle, 'total_driving_range'):
            return self.vehicle.total_driving_range
        return None

    @property
    def has_climate_seats(self) -> bool:
        """Return true if heated or cooled seats installed."""
        # Assume modern Kia EVs have this feature
        return True

    @property
    def front_seat_options(self) -> dict:
        """Return front seat options."""
        return {"heat": True, "vent": True}  # Default for modern vehicles

    @property
    def rear_seat_options(self) -> dict:
        """Return rear seat options."""
        return {"heat": True}  # Default for modern vehicles

    @property
    def climate_driver_seat(self) -> tuple:
        """Get the status of the left front seat."""
        # The new API doesn't expose seat comfort status the same way
        # Return a default "off" status
        return (0, 1)

    @property
    def climate_passenger_seat(self) -> tuple:
        """Get the status of the right front seat."""
        return (0, 1)

    @property
    def climate_left_rear_seat(self) -> tuple:
        """Get the status of the left rear seat."""
        return (0, 1)

    @property
    def climate_right_rear_seat(self) -> tuple:
        """Get the status of the right rear seat."""
        return (0, 1)
