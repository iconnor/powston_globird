# GloBird ZEROHERO Controller

A simple fixed-tariff battery control rule for GloBird ZEROHERO VPP plans.

This rule is designed for sites where Powston controls the battery and the tariff value comes from fixed daily windows, not wholesale price arbitrage.

## Purpose

The controller has four operating goals:

1. Charge the battery during the free import window.
2. Export during the daily Super Export Credit window when battery SOC is above reserve.
3. Avoid grid imports during the ZEROHERO credit window.
4. Use the battery normally for household load outside the special tariff windows.

It deliberately avoids complex wholesale-market logic, forecast price logic, price rails, feed-in caps, and solar curtailment.

## Tariff behaviour modelled

The uploaded GloBird ZEROHERO plans use the following common windows:

| Window              |              Time | Controller behaviour                                 |
| ------------------- | ----------------: | ---------------------------------------------------- |
| Free import         | 11:00am to 2:00pm | Import to charge battery to target SOC               |
| ZEROHERO credit     |  6:00pm to 9:00pm | Avoid imports where possible                         |
| Super Export Credit |  6:00pm to 9:00pm | Export when battery is above reserve                 |
| Other times         |   All other times | Auto, unless battery is at night reserve after solar |

The controller treats the tariff as a timetable rather than as a live price signal.

## Supported network keys

The rules engine provides a `network` variable. The controller normalises this value to lower case and uses it to select time windows.

Currently confirmed GloBird ZEROHERO network keys:

```python
energex
ausgrid
endeavour
essential
sapn
ausnet
citipower
jemena
powercor
united
```

Other possible `network` values may exist in Powston, but should not be assumed to be on GloBird ZEROHERO unless the plan has been verified.

Known possible values include:

```python
sapn
None
energex
westernpower
jemena
Citipower
ausnet
united
ergon
endeavour
ausgrid
tasnetworks
powercor
essential
other
evoenergy
```

## Inputs expected from Powston

The rule expects the following variables to already exist in the Powston rules engine context.

| Variable             | Meaning                                                           |
| -------------------- | ----------------------------------------------------------------- |
| `interval_time`      | Current billable interval time                                    |
| `battery_soc`        | Battery state of charge as a percentage                           |
| `night_reserve`      | SOC needed from now until sunrise or the next cheap-energy window |
| `is_daytime`         | Whether there is meaningful solar production                      |
| `network`            | DNSP/network identifier                                           |
| `buy_price`          | Logged for diagnostics only                                       |
| `sell_price`         | Logged for diagnostics only                                       |
| `decisions.reason()` | Powston decision wrapper for action traceability                  |

`night_reserve` is assumed to be derived elsewhere from values such as `BATTERY_SOC_NEEDED` and `BATTERY_SOC_AC`. This controller does not calculate it.

## Outputs set by this rule

| Output                     | Values used                           |
| -------------------------- | ------------------------------------- |
| `action`                   | `auto`, `import`, `export`, `stopped` |
| `feed_in_power_limitation` | `None`                                |

The controller intentionally does not set `solar`.

## Feed-in power limitation policy

`feed_in_power_limitation` is left as `None` by default.

This is intentional. On some inverter mappings, setting a feed-in limit while in `auto` can turn down solar production. That may increase imports when PV output drops suddenly, such as when cloud passes over the site.

The rule therefore avoids feed-in limits unless a later version explicitly needs an export cap for a specific inverter or network requirement.

## Control logic

### 11am to 2pm: free import window

If the battery is below `TARGET_SOC`, the rule sets:

```python
action = "import"
```

This charges the battery during the free-energy window.

If the battery is already full, the rule uses:

```python
action = "auto"
```

This lets the site operate normally and keeps solar running normally.

### 6pm to 9pm: ZEROHERO and Super Export window

If battery SOC is above `night_reserve + EXPORT_BUFFER_SOC`, the rule sets:

```python
action = "export"
```

If the battery is at or near reserve, the rule uses:

```python
action = "auto"
```

This avoids deliberately draining below the calculated reserve.

### Other times

If the site is not in daytime and the battery is at or below `night_reserve`, the rule sets:

```python
action = "stopped"
```

This preserves battery energy for later.

Otherwise, the rule sets:

```python
action = "auto"
```

This lets the battery cover household load normally.

## Reference implementation

```python
# GloBird ZEROHERO simple fixed-tariff controller
# Network-aware version.
#
# Strategy:
# 1. Charge battery during free 11am-2pm energy window.
# 2. Export during 6pm-9pm Super Export Credit window.
# 3. Avoid importing during 6pm-9pm ZEROHERO credit window.
# 4. Use battery for house load outside of that.
# 5. Let solar run at full output. Do not cap feed-in in auto.

current_hour = interval_time.hour
current_minute = interval_time.minute
current_minutes = current_hour * 60 + current_minute

TARGET_SOC = 100
EXPORT_BUFFER_SOC = 2

# Powston rules engine provides:
# night_reserve = SOC needed from now until sunrise / next cheap energy window
# is_daytime = whether there is meaningful solar production
# network = DNSP/network identifier

# None means do not override export limit or turn down solar.
feed_in_power_limitation = None

# Normalise network value
try:
    network_key = str(network).strip().lower()
except Exception:
    network_key = "none"

# Known GloBird ZEROHERO networks from uploaded plans.
# These currently share the same time windows.
ZEROHERO_WINDOWS_BY_NETWORK = {
    "energex": {"free_start": 11 * 60, "free_end": 14 * 60, "bonus_start": 18 * 60, "bonus_end": 21 * 60},
    "ausgrid": {"free_start": 11 * 60, "free_end": 14 * 60, "bonus_start": 18 * 60, "bonus_end": 21 * 60},
    "endeavour": {"free_start": 11 * 60, "free_end": 14 * 60, "bonus_start": 18 * 60, "bonus_end": 21 * 60},
    "essential": {"free_start": 11 * 60, "free_end": 14 * 60, "bonus_start": 18 * 60, "bonus_end": 21 * 60},
    "sapn": {"free_start": 11 * 60, "free_end": 14 * 60, "bonus_start": 18 * 60, "bonus_end": 21 * 60},
    "ausnet": {"free_start": 11 * 60, "free_end": 14 * 60, "bonus_start": 18 * 60, "bonus_end": 21 * 60},
    "citipower": {"free_start": 11 * 60, "free_end": 14 * 60, "bonus_start": 18 * 60, "bonus_end": 21 * 60},
    "jemena": {"free_start": 11 * 60, "free_end": 14 * 60, "bonus_start": 18 * 60, "bonus_end": 21 * 60},
    "powercor": {"free_start": 11 * 60, "free_end": 14 * 60, "bonus_start": 18 * 60, "bonus_end": 21 * 60},
    "united": {"free_start": 11 * 60, "free_end": 14 * 60, "bonus_start": 18 * 60, "bonus_end": 21 * 60},
}

# Default to standard ZEROHERO windows.
# For stricter production behaviour, replace this fallback with normal Powston auto.
windows = ZEROHERO_WINDOWS_BY_NETWORK.get(network_key, {
    "free_start": 11 * 60,
    "free_end": 14 * 60,
    "bonus_start": 18 * 60,
    "bonus_end": 21 * 60,
})

FREE_START = windows["free_start"]
FREE_END = windows["free_end"]
BONUS_START = windows["bonus_start"]
BONUS_END = windows["bonus_end"]

action = decisions.reason(
    "auto",
    "Starting in auto mode - default",
    buy_price=buy_price,
    sell_price=sell_price,
    battery_soc=battery_soc,
    night_reserve=night_reserve,
    network=network_key,
    free_start=FREE_START,
    free_end=FREE_END,
    bonus_start=BONUS_START,
    bonus_end=BONUS_END,
    feed_in_power_limitation=feed_in_power_limitation,
)

# 11am-2pm: free grid energy, charge battery to full.
# Do not limit feed-in because feed-in caps can curtail solar.
if FREE_START <= current_minutes < FREE_END:
    if battery_soc < TARGET_SOC:
        action = decisions.reason(
            "import",
            "free energy window, charge battery to 100%",
            battery_soc=battery_soc,
            night_reserve=night_reserve,
            network=network_key,
            feed_in_power_limitation=feed_in_power_limitation,
        )
    else:
        action = decisions.reason(
            "auto",
            "battery full during free energy window, let solar run normally",
            battery_soc=battery_soc,
            night_reserve=night_reserve,
            network=network_key,
            feed_in_power_limitation=feed_in_power_limitation,
        )

# 6pm-9pm: ZEROHERO import-credit window and Super Export Credit window.
elif BONUS_START <= current_minutes < BONUS_END:
    if battery_soc > night_reserve + EXPORT_BUFFER_SOC:
        action = decisions.reason(
            "export",
            "bonus export window and battery is above reserve",
            battery_soc=battery_soc,
            night_reserve=night_reserve,
            export_buffer_soc=EXPORT_BUFFER_SOC,
            network=network_key,
            feed_in_power_limitation=feed_in_power_limitation,
        )
    else:
        action = decisions.reason(
            "auto",
            "bonus window but battery is at reserve",
            battery_soc=battery_soc,
            night_reserve=night_reserve,
            export_buffer_soc=EXPORT_BUFFER_SOC,
            network=network_key,
            feed_in_power_limitation=feed_in_power_limitation,
        )

# Other times: use battery normally, but preserve reserve at night.
else:
    if battery_soc <= night_reserve and not is_daytime:
        action = decisions.reason(
            "stopped",
            "battery at or below night reserve, preserve energy until solar or cheap power",
            battery_soc=battery_soc,
            night_reserve=night_reserve,
            network=network_key,
            feed_in_power_limitation=feed_in_power_limitation,
        )
    else:
        action = decisions.reason(
            "auto",
            "use battery normally for house load",
            battery_soc=battery_soc,
            night_reserve=night_reserve,
            network=network_key,
            feed_in_power_limitation=feed_in_power_limitation,
        )
```

## Strict network mode option

`network` only identifies the DNSP. It does not prove the customer is on GloBird ZEROHERO.

For production use, a stricter implementation can restrict this rule to confirmed ZEROHERO networks only:

```python
if network_key not in ZEROHERO_WINDOWS_BY_NETWORK:
    action = decisions.reason(
        "auto",
        "network is not in confirmed GloBird ZEROHERO list, using normal Powston behaviour",
        network=network_key,
    )
else:
    # run ZEROHERO logic
```

Use strict mode where applying this tariff rule to the wrong retail plan would create commercial risk.

## Configuration

| Constant            |   Default | Meaning                                           |
| ------------------- | --------: | ------------------------------------------------- |
| `TARGET_SOC`        |     `100` | SOC target during the free import window          |
| `EXPORT_BUFFER_SOC` |       `2` | SOC buffer above `night_reserve` before exporting |
| `FREE_START`        | `11 * 60` | Free import start in minutes after midnight       |
| `FREE_END`          | `14 * 60` | Free import end in minutes after midnight         |
| `BONUS_START`       | `18 * 60` | ZEROHERO and Super Export start                   |
| `BONUS_END`         | `21 * 60` | ZEROHERO and Super Export end                     |

## Design decisions

### Why no wholesale logic?

This controller is for a fixed retail tariff. The value is created by hitting known daily windows, not by chasing forecast wholesale prices.

### Why no solar curtailment?

Solar should run at full available output unless there is a specific reason to curtail. Using feed-in limits as a control mechanism can reduce solar output and may cause grid imports when PV changes quickly.

### Why use `auto` outside special windows?

`auto` lets the battery serve household load without forcing grid export. This is suitable for self-consumption outside the bonus export window.

### Why preserve `night_reserve`?

The rule assumes `night_reserve` represents the SOC needed to reach sunrise or the next cheap-energy window. Exporting below this level may create later imports.

## Testing checklist

Before deploying to a site, verify:

1. The customer is actually on a GloBird ZEROHERO plan.
2. The `network` value matches one of the expected keys.
3. `night_reserve` is populated and sensible.
4. `is_daytime` is populated.
5. `feed_in_power_limitation = None` is supported by the device mapping.
6. Import during 11am to 2pm charges the battery as expected.
7. Export during 6pm to 9pm starts only when SOC is above reserve.
8. Battery stops or returns to auto when SOC reaches reserve at night.
9. The site does not import materially during 6pm to 9pm under normal conditions.
10. Solar output is not being curtailed unintentionally.

## Operational cautions

This rule does not handle Critical Peak events. GloBird may provide Critical Peak import or export events separately. Those events require event-aware logic or a separate override signal.

This rule also does not cap exports to the first 15 kWh of Super Export Credit. It exports during the whole bonus window when SOC is above reserve. This is intentional for simplicity, but may be refined later if tracking daily exported kWh becomes available.

## Version notes

Initial scope:

* Fixed-tariff controller only
* Network-aware time window map
* No solar variable
* No feed-in cap in normal operation
* Uses `night_reserve` from the Powston rules e
