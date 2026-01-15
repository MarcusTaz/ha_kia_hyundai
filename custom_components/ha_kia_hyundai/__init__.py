import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_SCAN_INTERVAL,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from hyundai_kia_connect_api import VehicleManager
from hyundai_kia_connect_api.exceptions import AuthenticationError, APIError

from .const import (
    DOMAIN,
    PLATFORMS,
    DEFAULT_SCAN_INTERVAL,
    CONFIG_FLOW_VERSION,
)
from .services import async_setup_services, async_unload_services
from .vehicle_coordinator import VehicleCoordinator

_LOGGER = logging.getLogger(__name__)

# Region and Brand constants
REGION_USA = 3
BRAND_KIA = 1


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating configuration from version %s.%s", config_entry.version, config_entry.minor_version)

    if config_entry.version > CONFIG_FLOW_VERSION:
        # This means the user has downgraded from a future version
        return False

    # Add migration logic here if needed for v2.0
    _LOGGER.debug("Migration to configuration version %s.%s successful", config_entry.version, config_entry.minor_version)
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up Kia USA from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    async_setup_services(hass)

    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]

    scan_interval = timedelta(
        minutes=config_entry.options.get(
            CONF_SCAN_INTERVAL,
            DEFAULT_SCAN_INTERVAL,
        )
    )

    # Create VehicleManager for USA Kia
    try:
        vehicle_manager = VehicleManager(
            region=REGION_USA,
            brand=BRAND_KIA,
            username=username,
            password=password,
            pin="",  # Not required for USA
        )
        
        # Login and get vehicles
        _LOGGER.debug("Logging in to Kia USA account")
        await hass.async_add_executor_job(vehicle_manager.check_and_refresh_token)
        
        # Update vehicle data
        _LOGGER.debug("Fetching vehicle data")
        await hass.async_add_executor_job(
            vehicle_manager.update_all_vehicles_with_cached_state
        )
        
    except AuthenticationError as err:
        _LOGGER.error("Authentication failed: %s", err)
        raise ConfigEntryAuthFailed(err) from err
    except APIError as err:
        _LOGGER.error("API error: %s", err)
        raise ConfigEntryError(f"API error: {err}") from err
    except Exception as err:
        _LOGGER.error("Unexpected error during setup: %s", err)
        raise ConfigEntryError(f"Unexpected error: {err}") from err

    if not vehicle_manager.vehicles:
        raise ConfigEntryError("No vehicles found in account")

    _LOGGER.debug("Found %d vehicle(s)", len(vehicle_manager.vehicles))

    # Create coordinators for each vehicle
    coordinators = {}
    for vehicle_id, vehicle in vehicle_manager.vehicles.items():
        _LOGGER.debug(
            "Setting up vehicle: %s (%s)",
            vehicle.name,
            vehicle.model,
        )
        
        coordinator = VehicleCoordinator(
            hass=hass,
            config_entry=config_entry,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle.name,
            vehicle_model=vehicle.model,
            vehicle_manager=vehicle_manager,
            scan_interval=scan_interval,
        )
        
        _LOGGER.debug("First update for vehicle %s", vehicle.name)
        await coordinator.async_config_entry_first_refresh()
        _LOGGER.debug("First update finished for vehicle %s", vehicle.name)
        
        coordinators[vehicle_id] = coordinator

    # Store all coordinators under this config entry
    hass.data[DOMAIN][config_entry.entry_id] = {
        "coordinators": coordinators,
        "vehicle_manager": vehicle_manager,
    }

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    if not config_entry.update_listeners:
        config_entry.add_update_listener(async_update_options)

    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):
        # Clean up stored data
        entry_data = hass.data[DOMAIN].pop(config_entry.entry_id, None)
        if entry_data and "vehicle_manager" in entry_data:
            # The multi-region API doesn't require explicit session cleanup
            _LOGGER.debug("Unloaded Kia USA integration")
            
    if not hass.data[DOMAIN]:
        async_unload_services(hass)
        
    return unload_ok
