import json
import logging
from pathlib import Path
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)
ENERGY_FILE = ".storage/energy"
STORE_VERSION = 1

async def _async_load_energy_config(hass):
    path = Path(hass.config.path(ENERGY_FILE))
    if not path.exists():
        _LOGGER.warning("Energy configuration file not found at %s", path)
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        _LOGGER.error("Error loading energy config: %s", e)
        return None

async def setup_device_energy_cost_sensors(hass, async_add_entities):
    data = await _async_load_energy_config(hass)
    if not data:
        return

    # Find grid price entity
    price_entity = None
    for source in data.get("energy_sources", []):
        if source.get("type") == "grid" and source.get("price_entity"):
            price_entity = source["price_entity"]
            break
    if not price_entity:
        _LOGGER.warning("No price entity found in energy configuration")
        return

    devices = [d["entity_id"] for d in data.get("device_consumption", []) if "entity_id" in d]
    if not devices:
        _LOGGER.info("No device consumption entities found in energy configuration")
        return

    sensors = []
    for device_entity in devices:
        name = device_entity.split(".")[1].replace("_energy", "").replace("_", " ").title()
        sensors.append(DeviceEnergyCostSensor(hass, device_entity, price_entity, name))
    async_add_entities(sensors, True)


class DeviceEnergyCostSensor(SensorEntity):
    _attr_device_class = "monetary"
    _attr_native_unit_of_measurement = "€"
    _attr_state_class = "total_increasing"
    _attr_icon = "mdi:currency-eur"

    def __init__(self, hass, energy_entity_id, price_entity_id, friendly_name):
        self.hass = hass
        self._energy_entity_id = energy_entity_id
        self._price_entity_id = price_entity_id
        self._attr_name = f"{friendly_name} Energy Cost"
        self._attr_unique_id = f"{energy_entity_id}_cost"
        self._attr_state = 0.0
        self._unsub = None
        self._store = Store(hass, STORE_VERSION, f"{self._attr_unique_id}.json")
        self._last_energy = None

    async def async_added_to_hass(self):
        if stored := await self._store.async_load():
            self._attr_state = stored.get("total_cost", 0.0)
            self._last_energy = stored.get("last_energy")

        @callback
        def state_listener(event):
            self.async_schedule_update_ha_state(True)

        self._unsub = async_track_state_change_event(
            self.hass, [self._energy_entity_id, self._price_entity_id], state_listener
        )

    async def async_will_remove_from_hass(self):
        if self._unsub:
            self._unsub()

    async def async_update(self):
        energy_state = self.hass.states.get(self._energy_entity_id)
        price_state = self.hass.states.get(self._price_entity_id)

        if not energy_state or not price_state:
            return

        try:
            energy_kwh = float(energy_state.state)
            price_per_kwh = float(price_state.state)
        except (ValueError, TypeError):
            return

        if self._last_energy is None:
            self._last_energy = energy_kwh
            return

        delta_energy = energy_kwh - self._last_energy
        if delta_energy > 0:
            delta_cost = delta_energy * price_per_kwh
            self._attr_state = round(self._attr_state + delta_cost, 6)
            self._last_energy = energy_kwh
            await self._store.async_save({
                "total_cost": self._attr_state,
                "last_energy": self._last_energy,
            })

        # Update currency from HA configuration
        self._attr_native_unit_of_measurement = getattr(self.hass.config.units, "currency", "€")
