# Device Energy Cost Integration

This custom Home Assistant integration adds **per-device energy cost calculation** to the Energy Dashboard.

## Installation

1. Copy `custom_components/device_energy_cost/` into your HA `config/` directory.
2. Restart Home Assistant.
3. You should see sensors appear for each device in your Energy Dashboard.

## Usage

Backfill one device to test:
```yaml
service: device_energy_cost.backfill
data:
  entity_id: sensor.dishwasher_energy_cost
  days: 7
```

Backfill all devices (default 30 days if `days` is omitted):
```yaml
service: device_energy_cost.backfill
```

The costs are stored in HA's **long-term statistics**, just like the native total cost.

Currency is automatically pulled from Home Assistant configuration.
