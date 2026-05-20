# GloBird ZEROHERO simple fixed-tariff controller
# Network-aware version.
#
# Current uploaded ZEROHERO plans use the same control windows:
# - Free energy: 11am-2pm
# - ZEROHERO / Super Export: 6pm-9pm
# - Peak feed-in period: 4pm-11pm, but this controller does not need it directly
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
    "energex": {
        "free_start": 11 * 60,
        "free_end": 14 * 60,
        "bonus_start": 18 * 60,
        "bonus_end": 21 * 60,
    },
    "ausgrid": {
        "free_start": 11 * 60,
        "free_end": 14 * 60,
        "bonus_start": 18 * 60,
        "bonus_end": 21 * 60,
    },
    "endeavour": {
        "free_start": 11 * 60,
        "free_end": 14 * 60,
        "bonus_start": 18 * 60,
        "bonus_end": 21 * 60,
    },
    "essential": {
        "free_start": 11 * 60,
        "free_end": 14 * 60,
        "bonus_start": 18 * 60,
        "bonus_end": 21 * 60,
    },
    "sapn": {
        "free_start": 11 * 60,
        "free_end": 14 * 60,
        "bonus_start": 18 * 60,
        "bonus_end": 21 * 60,
    },
    "ausnet": {
        "free_start": 11 * 60,
        "free_end": 14 * 60,
        "bonus_start": 18 * 60,
        "bonus_end": 21 * 60,
    },
    "citipower": {
        "free_start": 11 * 60,
        "free_end": 14 * 60,
        "bonus_start": 18 * 60,
        "bonus_end": 21 * 60,
    },
    "jemena": {
        "free_start": 11 * 60,
        "free_end": 14 * 60,
        "bonus_start": 18 * 60,
        "bonus_end": 21 * 60,
    },
    "powercor": {
        "free_start": 11 * 60,
        "free_end": 14 * 60,
        "bonus_start": 18 * 60,
        "bonus_end": 21 * 60,
    },
    "united": {
        "free_start": 11 * 60,
        "free_end": 14 * 60,
        "bonus_start": 18 * 60,
        "bonus_end": 21 * 60,
    },
}

# Use default ZEROHERO windows unless the network needs custom windows later.
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

# Safe default: normal Powston behaviour
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