import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.util import dt as dt_util
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    statistics_during_period,
)
from homeassistant.const import UnitOfEnergy

_LOGGER = logging.getLogger(__name__)
DOMAIN = "device_energy_cost"


async def async_register_services(hass: HomeAssistant):
    async def handle_backfill(call: ServiceCall):
        entity_id = call.data.get("entity_id")
        days = int(call.data.get("days", 30))

        data = await _async_load_energy_config(hass)
        if not data:
            _LOGGER.warning("Energy configuration not found; cannot backfill.")
            return

        price_entity = None
        for source in data.get("energy_sources", []):
            if source.get("type") == "grid" and source.get("price_entity"):
                price_entity = source["price_entity"]
                break
        if not price_entity:
            _LOGGER.warning("No price entity found in energy configuration.")
            return

        devices = [d["entity_id"] for d in data.get("device_consumption", []) if "entity_id" in d]
        if entity_id:
            devices = [d for d in devices if entity_id.endswith(f"{d}_cost") or entity_id == f"{d}_cost"]
            if not devices:
                _LOGGER.error("Entity %s is not a recognized cost sensor.", entity_id)
                return

        now = dt_util.utcnow()
        start = now - timedelta(days=days)

        for dev_entity in devices:
            cost_entity_id = f"{dev_entity}_cost"
            await _async_backfill_single(
                hass, dev_entity, price_entity, cost_entity_id, start, now
            )

        _LOGGER.info("Device Energy Cost backfill completed.")

    async def _async_load_energy_config(hass):
        import json
        import os
        storage_path = hass.config.path(".storage/energy")
        if not os.path.exists(storage_path):
            return None
        try:
            with open(storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            _LOGGER.error("Error reading energy config: %s", e)
            return None

    async def _async_backfill_single(hass, energy_entity, price_entity, cost_entity, start, end):
        energy_stats = await statistics_during_period(hass, start, end, [energy_entity], period="hour")
        price_stats = await statistics_during_period(hass, start, end, [price_entity], period="hour")

        if not energy_stats or not price_stats:
            _LOGGER.warning("Missing stats for %s or %s", energy_entity, price_entity)
            return

        energy_stat = list(energy_stats.values())[0]
        price_stat = list(price_stats.values())[0]

        cost_series = []
        last_sum = None
        total_cost = 0.0
        currency = getattr(hass.config.units, "currency", "EUR")

        for point in energy_stat:
            t = point["start"]
            energy_sum = point.get("sum")
            if last_sum is not None and energy_sum is not None:
                delta = energy_sum - last_sum
                price = next((p["mean"] for p in price_stat if abs((p["start"] - t).total_seconds()) < 1800), None)
                if price is None:
                    continue
                total_cost += delta * price
            last_sum = energy_sum
            cost_series.append({"start": t, "sum": total_cost, "state": total_cost})

        if not cost_series:
            _LOGGER.warning("No cost data computed for %s", energy_entity)
            return

        metadata = {
            "has_mean": False,
            "has_sum": True,
            "name": f"{energy_entity.split('.')[1].replace('_', ' ').title()} Energy Cost",
            "source": DOMAIN,
            "statistic_id": cost_entity,
            "unit_of_measurement": currency,
        }

        await async_add_external_statistics(hass, metadata, cost_series)
        _LOGGER.info("Backfill for %s inserted %d points", energy_entity, len(cost_series))

    hass.services.async_register(DOMAIN, "backfill", handle_backfill)
