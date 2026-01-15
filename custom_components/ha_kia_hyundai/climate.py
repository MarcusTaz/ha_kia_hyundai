"""Create climate platform."""
from logging import getLogger
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
    PRECISION_WHOLE,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VehicleCoordinator
from .vehicle_coordinator_base_entity import VehicleCoordinatorBaseEntity
from .const import (
    DOMAIN,
    TEMPERATURE_MIN,
    TEMPERATURE_MAX,
)

_LOGGER = getLogger(__name__)

SUPPORT_FLAGS = (
    ClimateEntityFeature.TURN_ON
    | ClimateEntityFeature.TURN_OFF
    | ClimateEntityFeature.TARGET_TEMPERATURE
)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up climate entities."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators = entry_data["coordinators"]
    
    entities = []
    for coordinator in coordinators.values():
        if coordinator.can_remote_climate:
            _LOGGER.debug(f"Adding climate entity for {coordinator.vehicle_name}")
            entities.append(Thermostat(coordinator))
        else:
            _LOGGER.debug(f"Skipping climate entity for {coordinator.vehicle_name}, cannot remote start")
    
    if entities:
        async_add_entities(entities)


class Thermostat(VehicleCoordinatorBaseEntity, ClimateEntity):
    """Create thermostat."""
    _attr_supported_features = SUPPORT_FLAGS
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, coordinator: VehicleCoordinator):
        """Create thermostat."""
        super().__init__(coordinator, ClimateEntityDescription(
            name="Climate",
            key="climate",
        ))
        self._attr_target_temperature = int(self.coordinator.climate_temperature_value or 72)
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.HEAT_COOL,
        ]
        self._attr_target_temperature_step = PRECISION_WHOLE
        self._attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
        self._attr_max_temp = TEMPERATURE_MAX
        self._attr_min_temp = TEMPERATURE_MIN

    @property
    def hvac_mode(self) -> HVACMode | str | None:
        """Return hvac mode."""
        if self.coordinator.climate_hvac_on:
            return HVACMode.HEAT_COOL
        else:
            return HVACMode.OFF

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Update hvac mode."""
        _LOGGER.debug(f"set_hvac_mode; hvac_mode:{hvac_mode}")
        
        match hvac_mode.strip().lower():
            case HVACMode.OFF:
                await self.hass.async_add_executor_job(
                    self.coordinator.vehicle_manager.stop_climate,
                    self.coordinator.vehicle_id
                )
            case HVACMode.HEAT_COOL | HVACMode.AUTO:
                await self.hass.async_add_executor_job(
                    self.coordinator.vehicle_manager.start_climate,
                    self.coordinator.vehicle_id,
                    int(self.target_temperature),
                    self.coordinator.climate_desired_defrost,
                    True,  # climate on
                    self.coordinator.climate_desired_heating_acc,
                )
        
        self.coordinator.async_update_listeners()
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        _LOGGER.debug(f"set_temperature; kwargs:{kwargs}")
        self._attr_target_temperature = kwargs.get(ATTR_TEMPERATURE)
        self.coordinator.async_update_listeners()
