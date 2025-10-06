import logging
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

async def setup_device_energy_cost_sensors(hass, async_add_entities):
    # Placeholder: In future could dynamically register sensors for each device in Energy Dashboard
    _LOGGER.debug("Setting up device energy cost sensors (placeholder)")
