# Device Energy Cost Integration

This custom Home Assistant integration extends the Energy Dashboard with per-device **energy cost calculations**,
using the same energy sources and price entities you already configured.

## ⚙️ Installation

1. Copy the `device_energy_cost` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Check **Developer Tools → Services** for `device_energy_cost.backfill`.

## 🧠 Usage

You can backfill cost data for a single device to test:

```yaml
service: device_energy_cost.backfill
data:
  entity_id: sensor.dishwasher_energy_cost
  days: 60
```

Or run it without specifying an entity to backfill all devices configured in your Energy Dashboard.

The cost is stored in Home Assistant’s native long-term statistics, just like total cost,
and appears in the **Energy Dashboard** after refreshing.

## ⚠️ Notes

- Currency automatically matches your Home Assistant configuration.
- Default backfill period is 30 days.
- Results are written directly to the statistics database.
