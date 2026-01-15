import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry, OptionsFlow
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant import config_entries
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback

from hyundai_kia_connect_api import VehicleManager
from hyundai_kia_connect_api.exceptions import AuthenticationError, APIError

from .const import (
    DOMAIN,
    CONFIG_FLOW_VERSION,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# Region and Brand constants
REGION_USA = 3
BRAND_KIA = 1


class KiaUvoOptionFlowHandler(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self.schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=999)),
            }
        )

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            _LOGGER.debug("user input in option flow : %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=self.schema)


@config_entries.HANDLERS.register(DOMAIN)
class KiaUvoConfigFlowHandler(config_entries.ConfigFlow):

    VERSION = CONFIG_FLOW_VERSION
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    data: dict[str, Any] = {}
    vehicle_manager: VehicleManager | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return KiaUvoOptionFlowHandler(config_entry)

    async def async_step_reauth(self, user_input: dict[str, Any] | None = None):
        """Handle reauth."""
        _LOGGER.debug(f"Reauth with input: {user_input}")
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step - get username and password."""
        _LOGGER.debug(f"User step with input: {user_input}")
        
        data_schema = {
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        }
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            
            try:
                # Create VehicleManager for USA Kia
                _LOGGER.info("Creating VehicleManager for USA Kia...")
                self.vehicle_manager = VehicleManager(
                    region=REGION_USA,
                    brand=BRAND_KIA,
                    username=username,
                    password=password,
                    pin="",  # Not required for USA
                )
                
                # Attempt login (this handles OTP automatically via the library)
                _LOGGER.info("Attempting login...")
                await self.hass.async_add_executor_job(
                    self.vehicle_manager.check_and_refresh_token
                )
                
                # Get vehicles
                _LOGGER.info("Fetching vehicles...")
                await self.hass.async_add_executor_job(
                    self.vehicle_manager.update_all_vehicles_with_cached_state
                )
                
                if not self.vehicle_manager.vehicles:
                    errors["base"] = "no_vehicles"
                else:
                    # Store credentials for later
                    self.data = user_input
                    _LOGGER.info(f"Found {len(self.vehicle_manager.vehicles)} vehicle(s)")
                    return await self.async_step_create_entries()
                    
            except AuthenticationError as e:
                _LOGGER.error(f"Authentication failed: {e}")
                errors["base"] = "invalid_auth"
            except APIError as e:
                _LOGGER.error(f"API error: {e}")
                errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.exception(f"Unexpected error during login: {e}")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", 
            data_schema=vol.Schema(data_schema), 
            errors=errors
        )

    async def async_step_create_entries(self):
        """Create config entries for all vehicles found."""
        if self.vehicle_manager is None:
            return self.async_abort(reason="unknown")
        
        # Handle reauth - update existing entry
        if self.source == SOURCE_REAUTH:
            reauth_entry = self._get_reauth_entry()
            return self.async_update_reload_and_abort(
                reauth_entry,
                data_updates=self.data,
            )
        
        # For new setup: create ONE entry for the account (all vehicles)
        # Use the first vehicle's ID as the unique_id for the account
        first_vehicle_id = next(iter(self.vehicle_manager.vehicles.keys()))
        account_name = f"Kia USA Account ({self.data[CONF_USERNAME]})"
        
        await self.async_set_unique_id(f"kia_usa_{self.data[CONF_USERNAME]}")
        self._abort_if_unique_id_configured()
        
        _LOGGER.info(f"Creating account entry with {len(self.vehicle_manager.vehicles)} vehicles")
        return self.async_create_entry(
            title=account_name,
            data=self.data,
        )
