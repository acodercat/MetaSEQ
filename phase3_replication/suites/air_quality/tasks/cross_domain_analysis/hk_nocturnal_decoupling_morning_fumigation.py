"""Difficulty upgrade — hk_nocturnal_decoupling_morning_fumigation (2026-10-06).

Night cohorts, morning molar Ox addition and an independent sounding-frequency comparison.
Professional consequence: Assess whether a hill-valley night proxy can support a fumigation explanation.
Plausible wrong reading: A surface Ox change excludes titration alone but does not identify entrainment; the sounding cohort must be re-ranked on reported launch dates, not counted as absence when a launch is missing.

Source concept: https://www.londonair.org.uk/london/reports/clapp_and%20_jenkin_O3_NOX.pdf
The paper supports the concept, not these dataset-specific answers. This case
uses its stated data, time conventions and statistical target; no causal or
surface-emission claim is inferred from a column or conditional association.

The pre-dawn hour is one hour, starting 05:00 (stamp 06:00), for the pollutants
as for the temperature contrast; the first output's description says so. Multi-hour
pre-dawn windows, each hour required complete, shrink the joint cohort (stamps
02-05: 55/55 nights, NO2 excess 22.43; 03-06: 54/55, 21.70; 01-06: 44/45, 24.56).
Stated after the 2026-10-07 triage, where three runs read the window so.

Independent raw-data results frozen before authoring the advanced helper:
{
  "decoupled_predawn_no2_excess": 22.020560747663545,
  "decoupled_predawn_pm25_excess": -1.0691588785046715,
  "decoupled_nights": 107,
  "mixed_nights": 107,
  "decoupled_morning_ox_change": 37.43711059190031,
  "mixed_morning_ox_change": 8.710903426791276,
  "sounding_inversion_frequency_gap_pp": 30.508474576271187,
  "stable_sounding_days": 118,
  "mixed_sounding_days": 118
}

Numerical answers use the decimal places declared on their variables and
reports_as; counts use tolerance zero and finite-number guards. This excludes
adjacent reported answers, not just gross errors. All sample definitions and
units are visible. Author-selected analysis recipes are marked execution in
the scenario, and are not counted as autonomous method discovery.

The earlier module/validator remains for its original outputs; the current
scenario calls the extended validator requiring those and the added evidence.
The pre-upgrade content is archived in .codex-review/difficulty_20261006/before.
"""

from typing import Dict, List, Tuple

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from domains.hk.db import read_frame

_STATION = "Sha Tin"
_PRE_DAWN = 5          # the hour STARTING at 05:00, i.e. the row stamped 06:00
_MORNING_HOUR = 10     # the hour starting at 10:00
_HILLS = ("Tate's Cairn", "Tai Mo Shan", "Ngong Ping")
_VALLEYS = ("Sha Tin", "Tai Po")
# Turn 3's ranking: every weather station at 400 m or more, against Sha Tin
# (as the variable states) and Tai Po (the neighbouring valley), in each of
# the three hours before dawn.
_STABILITY_HILLS = _HILLS + ("The Peak",)
_STABILITY_HOURS = (4, 5, 6)

# Odd oxygen added between the pre-dawn hour and mid-morning, above which the
# rise cannot be titration reversal. Titration conserves Ox exactly, so the
# margin only has to clear measurement noise; the routes read 31.5 to 50.5 on
# the decoupled mornings against 6.3 to 11.3 on the well-mixed ones.
_OX_ADDED_MARGIN = 15.0
AGREE_NIGHTLY = "night by night"
AGREE_RANKING = "in ranking only"
AGREE_NONE = "not at all"


def _weather() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Hour-start-indexed temperature and wind at the candidate stations."""
    frame = read_frame(text("""
        select h.datetime, s.name_en as station, h.temperature, h.wind_speed
        from hourly_station_weather h
        join weather_station s on s.id = h.station_id
        where s.name_en = any(:stations)
          and h.datetime > '2025-01-01' and h.datetime <= '2026-01-01'
    """), {"stations": list(_STABILITY_HILLS + _VALLEYS)})
    start = frame["datetime"] - pd.Timedelta(hours=1)
    keys = [start.dt.normalize().rename("day"), start.dt.hour.rename("hour")]
    temps = frame.pivot_table(index=keys, columns="station", values="temperature")
    winds = frame.pivot_table(index=keys, columns="station", values="wind_speed")
    return temps, winds


def _air() -> pd.DataFrame:
    """Sha Tin's pre-dawn and mid-morning values, one row per 2025 night."""
    frame = read_frame(text("""
        select h.datetime, h.no2, h.o3, h.pm2_5
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        where s.name_en = :station
          and h.datetime > '2025-01-01' and h.datetime <= '2026-01-01'
    """), {"station": _STATION})
    start = frame["datetime"] - pd.Timedelta(hours=1)
    frame["ox"] = (frame["o3"] / 48.0 + frame["no2"] / 46.0) * 46.0   # molar, as NO2
    hours = frame.pivot_table(index=start.dt.normalize(), columns=start.dt.hour,
                              values=["o3", "no2", "pm2_5", "ox"])
    early, late = _PRE_DAWN, _MORNING_HOUR
    return pd.DataFrame({
        "no2_predawn": hours[("no2", early)], "pm25_predawn": hours[("pm2_5", early)],
        "o3_predawn": hours[("o3", early)], "ox_predawn": hours[("ox", early)],
        "no2_ten": hours[("no2", late)], "o3_ten": hours[("o3", late)],
        "ox_ten": hours[("ox", late)],
    }).dropna()


def _sounding() -> pd.Series:
    frame = pd.read_csv(DATA_DIR / "sounding_indices.csv",
                        parse_dates=["datetime"])
    frame = frame[frame["hour"] == 8]
    return frame.set_index(frame["datetime"].dt.normalize())["inversion_temp_diff_k"]


def _routes() -> List[Tuple[str, pd.Series, pd.Series]]:
    """Six defensible ways to call a night decoupled or well mixed.

    Each entry is (name, decoupled mask, well-mixed mask) over the nights
    `_air()` holds. They deliberately span the choices an analyst could make:
    which hill, which valley, fixed bands or terciles, and wind alone.
    """
    temps, winds = _weather()
    air = _air()
    pre_t = temps.xs(_PRE_DAWN, level="hour")
    pre_w = winds.xs(_PRE_DAWN, level="hour")
    routes = []

    def add(name, series, decoupled, mixed):
        frame = air.join(series.rename("v"), how="inner").dropna(subset=["v"])
        routes.append((name, decoupled(frame["v"]), mixed(frame["v"]), frame))

    for hill, valley in (("Tate's Cairn", "Sha Tin"), ("Tai Mo Shan", "Sha Tin"),
                         ("Tate's Cairn", "Tai Po"), ("Ngong Ping", "Sha Tin")):
        diff = pre_t[hill] - pre_t[valley]
        if (hill, valley) == ("Tate's Cairn", "Sha Tin"):
            add("bands", diff, lambda v: v > -2.0, lambda v: v <= -5.0)
        lo, hi = diff.quantile(1 / 3), diff.quantile(2 / 3)
        add(f"terciles {hill} - {valley}", diff,
            lambda v, hi=hi: v > hi, lambda v, lo=lo: v <= lo)
    add("wind only", pre_w["Sha Tin"], lambda v: v <= 3.0, lambda v: v >= 8.0)
    return routes


def _sounding_agreement() -> List[Dict[str, object]]:
    """Turn 3's verdict under the comparison its variable states.

    2025's nights are ranked by the pre-dawn temperature at a hill station
    minus the valley's, and the most stable third is compared with the least
    stable third by the share of each whose 08:00 launch that morning reports
    an inversion. Nights without a launch are left out rather than counted as
    launches without an inversion. One row per hill, valley and hour.
    """
    temps, _ = _weather()
    launches = _sounding()
    launches = launches[(launches.index >= "2025-01-01") & (launches.index < "2026-01-01")]
    reported = launches.notna()
    rows = []
    for hour in _STABILITY_HOURS:
        pre = temps.xs(hour, level="hour")
        for hill in _STABILITY_HILLS:
            for valley in _VALLEYS:
                diff = (pre[hill] - pre[valley]).dropna()
                diff = diff[diff.index.isin(reported.index)]
                flag = reported.reindex(diff.index)
                lo, hi = diff.quantile(1 / 3), diff.quantile(2 / 3)
                stable, mixed = flag[diff > hi].mean(), flag[diff <= lo].mean()
                if stable > 0.95 and mixed < 0.05:
                    agreement = AGREE_NIGHTLY
                elif stable >= 2.0 * mixed:
                    agreement = AGREE_RANKING
                else:
                    agreement = AGREE_NONE
                rows.append({"route": f"{hill} - {valley} {hour:02d}:00",
                             "sounding_agreement": agreement,
                             "stable": stable, "mixed": mixed})
    return rows


def _conclusions(name: str, decoupled: pd.Series, mixed: pd.Series,
                 frame: pd.DataFrame) -> Dict[str, object]:
    inv, mix = frame[decoupled], frame[mixed]
    no2_ratio = inv["no2_predawn"].mean() / mix["no2_predawn"].mean()
    pm_ratio = inv["pm25_predawn"].mean() / mix["pm25_predawn"].mean()
    d_o3 = inv["o3_ten"].mean() - inv["o3_predawn"].mean()
    d_no2 = inv["no2_ten"].mean() - inv["no2_predawn"].mean()
    d_ox = inv["ox_ten"].mean() - inv["ox_predawn"].mean()
    # Odd oxygen is what titration conserves, so a rise in it is oxidant the
    # surface layer did not have before. WHERE it came from is not settled by
    # this record — see the docstring — so the scored verdict stops here.
    return {
        "route": name,
        "pollutant_that_responds_more": "NO2" if no2_ratio > pm_ratio else "PM2.5",
        "no2_higher_on_decoupled_nights": bool(no2_ratio > 1.0),
        "oxidant_was_added": bool(d_ox > _OX_ADDED_MARGIN),
        "ozone_rise_exceeds_no2_fall": bool(d_o3 > abs(d_no2)),
    }


def _figures() -> Dict[str, object]:
    """The scored conclusions, and a refusal if any route disagrees on one.

    A conclusion is scorable here only because every defensible route reaches
    it; that is checked on every call rather than asserted in prose.
    """
    table = [_conclusions(name, dec, mix, frame)
             for name, dec, mix, frame in _routes()]
    table += _sounding_agreement()
    out: Dict[str, object] = {}
    for key in ("pollutant_that_responds_more", "no2_higher_on_decoupled_nights",
                "oxidant_was_added", "ozone_rise_exceeds_no2_fall",
                "sounding_agreement"):
        table_key = [row for row in table if key in row]
        values = {row[key] for row in table_key}
        if len(values) != 1:
            raise RuntimeError(
                f"{key} is not invariant across routes: "
                + "; ".join(f"{row['route']}={row[key]}" for row in table_key))
        out[key] = values.pop()
    return out


def _normalise(value) -> str:
    text_value = str(value).strip().lower().replace("₂", "2").replace("_", " ")
    aliases = {
        "nitrogen dioxide": "no2", "fine particulate": "pm2.5", "pm25": "pm2.5",
        "true": "true", "false": "false", "yes": "true", "no": "false",
    }
    return aliases.get(text_value, text_value)


def _check(got: Dict[str, object]) -> ValidatorResult:
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _figures()
    errors = []
    for name, val in got.items():
        expected = gt[name]
        if isinstance(expected, bool):
            ok = isinstance(val, bool) and val == expected
            if not ok and isinstance(val, str):
                ok = _normalise(val) == str(expected).lower()
        else:
            ok = _normalise(val) == _normalise(expected)
        if not ok:
            errors.append(f"{name}={val!r}, expected {expected!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]!r}" for n in got))


def validate_night_layer(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "pollutant_that_responds_more": runtime.retrieve("pollutant_that_responds_more"),
        "no2_higher_on_decoupled_nights": runtime.retrieve("no2_higher_on_decoupled_nights"),
    })


def validate_morning_ozone(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "oxidant_was_added": runtime.retrieve("oxidant_was_added"),
        "ozone_rise_exceeds_no2_fall": runtime.retrieve("ozone_rise_exceeds_no2_fall"),
    })


def validate_corroboration(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "sounding_agreement": runtime.retrieve("sounding_agreement"),
    })


tools = []
variables = [
    Variable("pollutant_that_responds_more", None,
             "Store which of the two pollutants, NO2 or PM2.5, is affected more "
             "by a decoupled night at the Sha Tin air-quality station, as the "
             "string 'NO2' or 'PM2.5'."),
    Variable("no2_higher_on_decoupled_nights", None,
             "Store True if Sha Tin's pre-dawn NO2 is higher on the nights you "
             "classify as decoupled than on the nights you classify as well "
             "mixed, else False."),
    Variable("oxidant_was_added", None,
             "Store True if the ozone that appears at Sha Tin between the "
             "pre-dawn hour and mid-morning on the decoupled nights is oxidant "
             "added to the surface layer, rather than ozone released from the "
             "NO2 already in it, else False."),
    Variable("ozone_rise_exceeds_no2_fall", None,
             "Store True if, on the decoupled nights, the mean ozone rise from the "
             "pre-dawn hour to mid-morning is larger than the mean NO2 fall over "
             "the same hours, else False."),
    Variable("sounding_agreement", None,
             "Store how far the King's Park 08:00 radiosonde agrees with the "
             "surface stations about which 2025 nights were stable. Rank the "
             "nights by the pre-dawn temperature at a hill station of 400 m or "
             "more minus Sha Tin's (the less negative, the more stable), take "
             "the most stable third and the least stable third, and find in "
             "each the share of mornings whose 08:00 launch reports an "
             "inversion, leaving out mornings with no launch. Store 'night by "
             "night' if that share is above 95 % in the most stable third and "
             "below 5 % in the least stable; otherwise 'in ranking only' if the "
             "most stable third's share is at least twice the least stable "
             "third's; otherwise 'not at all'."),
    Variable('decoupled_predawn_no2_excess', None, "Store upper-third-minus-lower-third Sha Tin NO2 in the pre-dawn hour, in µg/m³ to 2 decimal places. The pre-dawn hour is the single hour starting 05:00 (stamp 06:00), one hour and not a multi-hour mean, for the pollutants as for the temperature contrast. Rank the Tate's Cairn minus Sha Tin temperature contrast in that hour, on 2025 nights with NO2, PM2.5 and O3 all reported in that hour and NO2 and O3 reported in the hour starting 10:00. Upper is strictly above the linear 2/3 quantile, lower at or below the 1/3 quantile, from this joint cohort."),
    Variable('decoupled_predawn_pm25_excess', None, 'Store the corresponding upper-third-minus-lower-third pre-dawn PM2.5 contrast on exactly that joint cohort, in µg/m³ to 2 decimal places.'),
    Variable('decoupled_nights', None, 'Store the exact integer number of complete nights in that upper-third air/temperature cohort.'),
    Variable('mixed_nights', None, 'Store the exact integer number in that lower-third cohort.'),
    Variable('decoupled_morning_ox_change', None, 'Store mean morning-minus-pre-dawn molar odd oxygen for the earlier upper-third night group, as NO2-equivalent µg/m³ to 2 decimal places. Use O3 and NO2 molar masses 48 and 46 g/mol, the same complete nights and unrounded hourly inputs.'),
    Variable('mixed_morning_ox_change', None, 'Store the corresponding morning-minus-pre-dawn odd-oxygen change for the earlier lower-third group, in the same units to 2 decimal places.'),
    Variable('sounding_inversion_frequency_gap_pp', None, "Store upper-third-minus-lower-third 08:00 sounding inversion frequency, in percentage points to 2 decimal places. Re-rank the same 05:00 Tate's Cairn-Sha Tin temperature contrast within dates with a reported King's Park 08:00 launch in 2025; upper is above the 2/3 quantile and lower at or below the 1/3 quantile. A reported inversion temperature difference denotes an inversion; a launch without one does not. Missing launches are excluded."),
    Variable('stable_sounding_days', None, "Store the exact integer number of reported launch dates in that sounding comparison's upper-third group."),
    Variable('mixed_sounding_days', None, 'Store the exact integer number in its lower-third group.'),
]

# Difficulty upgrade 2026-10-06: older docstring magnitudes describe the
# earlier scoring surface. Added metrics below are recomputed from source data.
# Their single declared decimal report is checked by reports_as; counts are
# exact. The independent raw-data maps were frozen before these helpers.

def _advanced_metrics():
    temperature, _ = _weather()
    early = temperature.xs(5, level="hour")
    contrast = (early["Tate's Cairn"]-early["Sha Tin"]).dropna()
    air = _air().join(contrast.rename("contrast"), how="inner").dropna()
    lo, hi = air["contrast"].quantile([1/3, 2/3])
    stable, mixed = air[air["contrast"] > hi], air[air["contrast"] <= lo]
    launches = _sounding()
    launches = launches[(launches.index >= "2025-01-01") & (launches.index < "2026-01-01")]
    weather = contrast[contrast.index.isin(launches.index)]
    slo, shi = weather.quantile([1/3, 2/3])
    stable_launch = launches.reindex(weather[weather > shi].index)
    mixed_launch = launches.reindex(weather[weather <= slo].index)
    return {"decoupled_predawn_no2_excess": float(stable["no2_predawn"].mean()-mixed["no2_predawn"].mean()),
            "decoupled_predawn_pm25_excess": float(stable["pm25_predawn"].mean()-mixed["pm25_predawn"].mean()),
            "decoupled_nights": len(stable), "mixed_nights": len(mixed),
            "decoupled_morning_ox_change": float((stable["ox_ten"]-stable["ox_predawn"]).mean()),
            "mixed_morning_ox_change": float((mixed["ox_ten"]-mixed["ox_predawn"]).mean()),
            "sounding_inversion_frequency_gap_pp": float((stable_launch.notna().mean()-mixed_launch.notna().mean())*100),
            "stable_sounding_days": len(stable_launch), "mixed_sounding_days": len(mixed_launch)}











def validate_harder_turn_1(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "pollutant_that_responds_more": runtime.retrieve("pollutant_that_responds_more"),
        "no2_higher_on_decoupled_nights": runtime.retrieve("no2_higher_on_decoupled_nights"),
        "decoupled_predawn_no2_excess": runtime.retrieve("decoupled_predawn_no2_excess"),
        "decoupled_predawn_pm25_excess": runtime.retrieve("decoupled_predawn_pm25_excess"),
        "decoupled_nights": runtime.retrieve("decoupled_nights"),
        "mixed_nights": runtime.retrieve("mixed_nights"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    original = validate_night_layer(response, runtime, turn)
    if not original.success:
        return original
    gt = _advanced_metrics()
    errors = []
    if not is_finite_number(got["decoupled_predawn_no2_excess"]) or not reports_as(got["decoupled_predawn_no2_excess"], gt["decoupled_predawn_no2_excess"], decimals=2):
        errors.append(f"decoupled_predawn_no2_excess={got["decoupled_predawn_no2_excess"]!r}, expected {gt["decoupled_predawn_no2_excess"]!r}")
    if not is_finite_number(got["decoupled_predawn_pm25_excess"]) or not reports_as(got["decoupled_predawn_pm25_excess"], gt["decoupled_predawn_pm25_excess"], decimals=2):
        errors.append(f"decoupled_predawn_pm25_excess={got["decoupled_predawn_pm25_excess"]!r}, expected {gt["decoupled_predawn_pm25_excess"]!r}")
    if not is_finite_number(got["decoupled_nights"]) or not compare_numeric(got["decoupled_nights"], gt["decoupled_nights"], tolerance=0):
        errors.append(f"decoupled_nights={got["decoupled_nights"]!r}, expected {gt["decoupled_nights"]!r}")
    if not is_finite_number(got["mixed_nights"]) or not compare_numeric(got["mixed_nights"], gt["mixed_nights"], tolerance=0):
        errors.append(f"mixed_nights={got["mixed_nights"]!r}, expected {gt["mixed_nights"]!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: numerical evidence and original conclusion")


def validate_harder_turn_2(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "oxidant_was_added": runtime.retrieve("oxidant_was_added"),
        "ozone_rise_exceeds_no2_fall": runtime.retrieve("ozone_rise_exceeds_no2_fall"),
        "decoupled_morning_ox_change": runtime.retrieve("decoupled_morning_ox_change"),
        "mixed_morning_ox_change": runtime.retrieve("mixed_morning_ox_change"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    original = validate_morning_ozone(response, runtime, turn)
    if not original.success:
        return original
    gt = _advanced_metrics()
    errors = []
    if not is_finite_number(got["decoupled_morning_ox_change"]) or not reports_as(got["decoupled_morning_ox_change"], gt["decoupled_morning_ox_change"], decimals=2):
        errors.append(f"decoupled_morning_ox_change={got["decoupled_morning_ox_change"]!r}, expected {gt["decoupled_morning_ox_change"]!r}")
    if not is_finite_number(got["mixed_morning_ox_change"]) or not reports_as(got["mixed_morning_ox_change"], gt["mixed_morning_ox_change"], decimals=2):
        errors.append(f"mixed_morning_ox_change={got["mixed_morning_ox_change"]!r}, expected {gt["mixed_morning_ox_change"]!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: numerical evidence and original conclusion")


def validate_harder_turn_3(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "sounding_agreement": runtime.retrieve("sounding_agreement"),
        "sounding_inversion_frequency_gap_pp": runtime.retrieve("sounding_inversion_frequency_gap_pp"),
        "stable_sounding_days": runtime.retrieve("stable_sounding_days"),
        "mixed_sounding_days": runtime.retrieve("mixed_sounding_days"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    original = validate_corroboration(response, runtime, turn)
    if not original.success:
        return original
    gt = _advanced_metrics()
    errors = []
    if not is_finite_number(got["sounding_inversion_frequency_gap_pp"]) or not reports_as(got["sounding_inversion_frequency_gap_pp"], gt["sounding_inversion_frequency_gap_pp"], decimals=2):
        errors.append(f"sounding_inversion_frequency_gap_pp={got["sounding_inversion_frequency_gap_pp"]!r}, expected {gt["sounding_inversion_frequency_gap_pp"]!r}")
    if not is_finite_number(got["stable_sounding_days"]) or not compare_numeric(got["stable_sounding_days"], gt["stable_sounding_days"], tolerance=0):
        errors.append(f"stable_sounding_days={got["stable_sounding_days"]!r}, expected {gt["stable_sounding_days"]!r}")
    if not is_finite_number(got["mixed_sounding_days"]) or not compare_numeric(got["mixed_sounding_days"], gt["mixed_sounding_days"], tolerance=0):
        errors.append(f"mixed_sounding_days={got["mixed_sounding_days"]!r}, expected {gt["mixed_sounding_days"]!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: numerical evidence and original conclusion")


validators = {
    "validate_night_layer": validate_night_layer,
    "validate_morning_ozone": validate_morning_ozone,
    "validate_corroboration": validate_corroboration,
    "validate_harder_turn_3": validate_harder_turn_3,
    "validate_harder_turn_1": validate_harder_turn_1,
    "validate_harder_turn_2": validate_harder_turn_2,
}
