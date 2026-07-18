# Example Power Watchdog dashboard

This directory contains an optional dashboard demonstrating the entities
provided by the Power Watchdog WiFi integration.

The dashboard is not installed automatically and is not required for the
integration to operate.

## Required HACS frontend cards

Install these frontend cards through HACS before importing the dashboard:

- [Config Template Card](https://github.com/iantrich/config-template-card)
- [ApexCharts Card](https://github.com/RomRider/apexcharts-card)
- [card-mod](https://github.com/thomasloven/lovelace-card-mod)

The shared example uses a built-in Home Assistant Entities card for the time
range selector, so Mushroom is not required.

## 1. Create the graph-time helper

Either create an **Input select** helper in the Home Assistant UI with entity ID
`input_select.graph_time_range`, or merge the contents of `helpers.yaml` into
`configuration.yaml`.

The helper must contain these options exactly:

- `1 Hour`
- `3 Hours`
- `6 Hours`
- `12 Hours`
- `24 Hours`
- `3 Days`
- `7 Days`

Restart Home Assistant if you add the helper through YAML.

## 2. Find your device entity prefix

Open:

**Settings → Devices & services → Devices → your Power Watchdog**

Look at an entity such as the L1 voltage sensor. For example:

```text
sensor.my_power_watchdog_l1_voltage
```

In this example, the entity prefix is `my_power_watchdog`.

## 3. Customize the example

Open `power_watchdog_dashboard.yaml` and replace every occurrence of the generic
prefix `watchdog` with your actual entity prefix.

For example:

```text
sensor.watchdog_l1_voltage
```

becomes:

```text
sensor.my_power_watchdog_l1_voltage
```

This single replacement updates all Power Watchdog sensor and binary-sensor
references in the dashboard.

## 4. Import through the dashboard editor

1. Go to **Settings → Dashboards**.
2. Create a new dashboard.
3. Open it and select **Edit dashboard**.
4. Open the three-dot menu and choose **Raw configuration editor**.
5. Paste the contents of `power_watchdog_dashboard.yaml`.
6. Save.

## Alternative: YAML dashboard

Copy the example to:

```text
/config/dashboards/power_watchdog.yaml
```

Then add this to `configuration.yaml`:

```yaml
lovelace:
  dashboards:
    power-watchdog:
      mode: yaml
      filename: dashboards/power_watchdog.yaml
      title: Power Watchdog
      icon: mdi:lightning-bolt-outline
      show_in_sidebar: true
```

Restart Home Assistant after changing `configuration.yaml`.

## Scope of the shared example

The shared dashboard includes only entities created by this integration:
frequency, energy, voltage, current, power, and error state. Installation-specific
environmental sensors and private device names have intentionally been removed.
