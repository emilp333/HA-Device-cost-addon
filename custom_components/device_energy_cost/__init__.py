import logging
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
from .const import DOMAIN, UPDATE_INTERVAL
from .sensor import setup_device_energy_cost_sensors
from .services import async_register_services

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    await async_register_services(hass)
    return True

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    await setup_device_energy_cost_sensors(hass, async_add_entities)

    async def _reload(now):
        _LOGGER.debug("Reloading device energy cost sensors")
        await setup_device_energy_cost_sensors(hass, async_add_entities)

    async_track_time_interval(hass, _reload, timedelta(seconds=UPDATE_INTERVAL))
