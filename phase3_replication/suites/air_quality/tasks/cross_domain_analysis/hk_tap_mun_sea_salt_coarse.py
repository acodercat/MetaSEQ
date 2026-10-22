"""Difficulty upgrade — hk_tap_mun_sea_salt_coarse (2026-10-06).

Coastal fine/coarse wind response with a direction comparison that also changes fine PM.
Professional consequence: Assess whether the data warrant publishing a wind-clears-air or marine-source statement.
Plausible wrong reading: A broad speed band is not exact matching, and the reported direction contrast is not a coarse-only sea-salt control. No chemical tracer identifies the source.

Source concept: https://acp.copernicus.org/articles/24/1895/2024/
The paper supports the concept, not these dataset-specific answers. This case
uses its stated data, time conventions and statistical target; no causal or
surface-emission claim is inferred from a column or conditional association.

Independent raw-data results frozen before authoring the advanced helper:
{
  "wind_quartile_pm25_change_pct": -11.970078714158172,
  "wind_quartile_coarse_change_pct": 29.998145821898213,
  "strong_wind_hours": 2064,
  "light_wind_hours": 2120,
  "easterly_minus_westerly_coarse": 1.1262972793629746,
  "easterly_minus_westerly_pm25": 1.6940520979614533,
  "moderate_easterly_hours": 1370,
  "moderate_westerly_hours": 473
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

from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from domains.hk.db import read_frame

_STATION = "Tap Mun"


def _joined() -> pd.DataFrame:
    aq = read_frame(text("""
        select h.datetime, h.pm2_5, h.pm10
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        where s.name_en = :station and h.pm2_5 is not null and h.pm10 is not null
          and h.datetime > '2025-01-01' and h.datetime <= '2026-01-01'
    """), {"station": _STATION})
    wind = read_frame(text("""
        select h.datetime, h.wind_speed, h.wind_degree
        from hourly_station_weather h
        join weather_station s on s.id = h.station_id
        where s.name_en = :station and h.wind_speed > 0 and h.wind_degree is not null
          and h.datetime > '2025-01-01' and h.datetime <= '2026-01-01'
    """), {"station": _STATION})
    frame = aq.merge(wind, on="datetime")
    frame["coarse"] = frame["pm10"] - frame["pm2_5"]
    return frame


def _routes() -> List[Tuple[str, pd.DataFrame, pd.DataFrame]]:
    """(name, light-wind rows, strong-wind rows) under seven constructions."""
    f = _joined()
    routes = []
    for lo, hi in ((10, 45), (10, 30), (15, 40)):
        routes.append((f"below {lo} against {hi} and above",
                       f[f["wind_speed"] < lo], f[f["wind_speed"] >= hi]))
    for q in (3, 4, 5):
        tile = pd.qcut(f["wind_speed"], q, labels=False, duplicates="drop")
        routes.append((f"lowest against highest of {q} tiles",
                       f[tile == tile.min()], f[tile == tile.max()]))
    daily = f.assign(day=(f["datetime"] - pd.Timedelta(hours=1)).dt.date)
    daily = daily.groupby("day")[["pm2_5", "pm10", "coarse", "wind_speed"]].mean()
    tile = pd.qcut(daily["wind_speed"], 4, labels=False)
    routes.append(("daily means, lowest against highest quartile",
                   daily[tile == 0], daily[tile == 3]))
    return routes


def _conclusions(light: pd.DataFrame, strong: pd.DataFrame) -> Dict[str, object]:
    change = {c: (strong[c].mean() - light[c].mean()) / light[c].mean()
              for c in ("pm2_5", "coarse", "pm10")}
    pm25_falls = change["pm2_5"] < 0
    return {
        "pm25_with_stronger_wind": "falls" if pm25_falls else "rises",
        "coarse_with_stronger_wind": "rises" if change["coarse"] > 0 else "falls",
        "pm10_falls_as_much_as_pm25": bool(pm25_falls and change["pm10"] <= 0.5 * change["pm2_5"]),
        "line_holds_for": ("fine particulate only"
                           if pm25_falls and change["pm10"] > 0.5 * change["pm2_5"]
                           else "both fractions" if pm25_falls else "neither"),
    }


def _figures() -> Dict[str, object]:
    table = [(name, _conclusions(light, strong)) for name, light, strong in _routes()]
    out: Dict[str, object] = {}
    for key in table[0][1]:
        values = {row[key] for _, row in table}
        if len(values) != 1:
            raise RuntimeError(f"{key} is not invariant across constructions: "
                               + "; ".join(f"{n}={row[key]!r}" for n, row in table))
        out[key] = values.pop()
    return out


def _normalise(value) -> str:
    return str(value).strip().lower()


def _check(got: Dict[str, object]) -> ValidatorResult:
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _figures()
    errors = []
    for name, val in got.items():
        expected = gt[name]
        if isinstance(expected, bool):
            ok = (isinstance(val, bool) and val == expected) or (
                isinstance(val, str) and _normalise(val) in {str(expected).lower(),
                                                              "yes" if expected else "no"})
        else:
            ok = _normalise(val) == _normalise(expected)
        if not ok:
            errors.append(f"{name}={val!r}, expected {expected!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]!r}" for n in got))


def validate_wind_response(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "pm25_with_stronger_wind": runtime.retrieve("pm25_with_stronger_wind"),
        "coarse_with_stronger_wind": runtime.retrieve("coarse_with_stronger_wind"),
        "pm10_falls_as_much_as_pm25": runtime.retrieve("pm10_falls_as_much_as_pm25"),
    })


def validate_desk_line(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "line_holds_for": runtime.retrieve("line_holds_for"),
    })


tools = []
variables = [
    Variable("pm25_with_stronger_wind", None,
             "Store how Tap Mun's PM2.5 changes from its lightest winds to its "
             "strongest over 2025, as one of exactly these strings: 'falls', "
             "'rises'. Wind is the Tap Mun weather station's, paired to the "
             "air-quality row with the same timestamp; coarse particulate is "
             "PM10 minus PM2.5 on the same station-hour."),
    Variable("coarse_with_stronger_wind", None,
             "Store the same for Tap Mun's coarse particulate, as 'falls' or 'rises'."),
    Variable("pm10_falls_as_much_as_pm25", None,
             "Store True if PM10 falls from the lightest winds to the strongest "
             "by at least half as much, in proportion to its own level, as PM2.5 "
             "does; else False."),
    Variable("line_holds_for", None,
             "Store which fraction the desk's line 'strong winds clear the air' "
             "holds for at Tap Mun, as one of exactly these strings: 'fine "
             "particulate only', 'both fractions', 'neither'."),
    Variable('wind_quartile_pm25_change_pct', None, 'Store 100 times (strong-wind mean PM2.5 divided by light-wind mean PM2.5 minus one), as a percentage to 2 decimal places. Form linear-interpolated 25th/75th wind-speed percentiles on 2025 Tap Mun station-hours with positive wind speed, reported direction, PM2.5 and PM10. Light includes speeds at or below the 25th percentile; strong includes speeds at or above the 75th. Use unrounded inputs.'),
    Variable('wind_quartile_coarse_change_pct', None, 'Store the analogous strong-versus-light percentage change in coarse particulate, to 2 decimal places, under exactly that shared cohort. Coarse particulate is contemporaneous PM10 minus PM2.5.'),
    Variable('strong_wind_hours', None, 'Store the exact integer number of station-hours in that strong-wind group.'),
    Variable('light_wind_hours', None, 'Store the exact integer number in that light-wind group.'),
    Variable('easterly_minus_westerly_coarse', None, 'Store easterly-minus-westerly mean coarse particulate in µg/m³ to 2 decimal places, among the same complete station-hours with wind speed strictly between those 25th/75th percentiles. Easterly bearings are 45-135 degrees inclusive, westerly 225-315 inclusive.'),
    Variable('easterly_minus_westerly_pm25', None, 'Store the matching easterly-minus-westerly PM2.5 difference on exactly the same moderate-wind direction groups, in µg/m³ to 2 decimal places.'),
    Variable('moderate_easterly_hours', None, 'Store the exact integer number of complete moderate-wind easterly station-hours.'),
    Variable('moderate_westerly_hours', None, 'Store the exact integer number of complete moderate-wind westerly station-hours.'),
]


# Difficulty upgrade 2026-10-06: older docstring magnitudes describe the
# earlier scoring surface. Added metrics below are recomputed from source data.
# Their single declared decimal report is checked by reports_as; counts are
# exact. The independent raw-data maps were frozen before these helpers.

def _advanced_metrics():
    frame = _joined().dropna(subset=["pm2_5", "pm10", "wind_speed", "wind_degree"])
    lo, hi = frame["wind_speed"].quantile([.25, .75])
    light, strong = frame[frame["wind_speed"] <= lo], frame[frame["wind_speed"] >= hi]
    mid = frame[(frame["wind_speed"] > lo) & (frame["wind_speed"] < hi)]
    east = mid[mid["wind_degree"].between(45,135)]
    west = mid[mid["wind_degree"].between(225,315)]
    return {"wind_quartile_pm25_change_pct": float((strong["pm2_5"].mean()/light["pm2_5"].mean()-1)*100),
            "wind_quartile_coarse_change_pct": float((strong["coarse"].mean()/light["coarse"].mean()-1)*100),
            "strong_wind_hours": len(strong), "light_wind_hours": len(light),
            "easterly_minus_westerly_coarse": float(east["coarse"].mean()-west["coarse"].mean()),
            "easterly_minus_westerly_pm25": float(east["pm2_5"].mean()-west["pm2_5"].mean()),
            "moderate_easterly_hours": len(east), "moderate_westerly_hours": len(west)}










def validate_harder_turn_1(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "pm25_with_stronger_wind": runtime.retrieve("pm25_with_stronger_wind"),
        "coarse_with_stronger_wind": runtime.retrieve("coarse_with_stronger_wind"),
        "pm10_falls_as_much_as_pm25": runtime.retrieve("pm10_falls_as_much_as_pm25"),
        "wind_quartile_pm25_change_pct": runtime.retrieve("wind_quartile_pm25_change_pct"),
        "wind_quartile_coarse_change_pct": runtime.retrieve("wind_quartile_coarse_change_pct"),
        "strong_wind_hours": runtime.retrieve("strong_wind_hours"),
        "light_wind_hours": runtime.retrieve("light_wind_hours"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    original = validate_wind_response(response, runtime, turn)
    if not original.success:
        return original
    gt = _advanced_metrics()
    errors = []
    if not is_finite_number(got["wind_quartile_pm25_change_pct"]) or not reports_as(got["wind_quartile_pm25_change_pct"], gt["wind_quartile_pm25_change_pct"], decimals=2):
        errors.append(f"wind_quartile_pm25_change_pct={got["wind_quartile_pm25_change_pct"]!r}, expected {gt["wind_quartile_pm25_change_pct"]!r}")
    if not is_finite_number(got["wind_quartile_coarse_change_pct"]) or not reports_as(got["wind_quartile_coarse_change_pct"], gt["wind_quartile_coarse_change_pct"], decimals=2):
        errors.append(f"wind_quartile_coarse_change_pct={got["wind_quartile_coarse_change_pct"]!r}, expected {gt["wind_quartile_coarse_change_pct"]!r}")
    if not is_finite_number(got["strong_wind_hours"]) or not compare_numeric(got["strong_wind_hours"], gt["strong_wind_hours"], tolerance=0):
        errors.append(f"strong_wind_hours={got["strong_wind_hours"]!r}, expected {gt["strong_wind_hours"]!r}")
    if not is_finite_number(got["light_wind_hours"]) or not compare_numeric(got["light_wind_hours"], gt["light_wind_hours"], tolerance=0):
        errors.append(f"light_wind_hours={got["light_wind_hours"]!r}, expected {gt["light_wind_hours"]!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: numerical evidence and original conclusion")


def validate_harder_turn_2(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "line_holds_for": runtime.retrieve("line_holds_for"),
        "easterly_minus_westerly_coarse": runtime.retrieve("easterly_minus_westerly_coarse"),
        "easterly_minus_westerly_pm25": runtime.retrieve("easterly_minus_westerly_pm25"),
        "moderate_easterly_hours": runtime.retrieve("moderate_easterly_hours"),
        "moderate_westerly_hours": runtime.retrieve("moderate_westerly_hours"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    original = validate_desk_line(response, runtime, turn)
    if not original.success:
        return original
    gt = _advanced_metrics()
    errors = []
    if not is_finite_number(got["easterly_minus_westerly_coarse"]) or not reports_as(got["easterly_minus_westerly_coarse"], gt["easterly_minus_westerly_coarse"], decimals=2):
        errors.append(f"easterly_minus_westerly_coarse={got["easterly_minus_westerly_coarse"]!r}, expected {gt["easterly_minus_westerly_coarse"]!r}")
    if not is_finite_number(got["easterly_minus_westerly_pm25"]) or not reports_as(got["easterly_minus_westerly_pm25"], gt["easterly_minus_westerly_pm25"], decimals=2):
        errors.append(f"easterly_minus_westerly_pm25={got["easterly_minus_westerly_pm25"]!r}, expected {gt["easterly_minus_westerly_pm25"]!r}")
    if not is_finite_number(got["moderate_easterly_hours"]) or not compare_numeric(got["moderate_easterly_hours"], gt["moderate_easterly_hours"], tolerance=0):
        errors.append(f"moderate_easterly_hours={got["moderate_easterly_hours"]!r}, expected {gt["moderate_easterly_hours"]!r}")
    if not is_finite_number(got["moderate_westerly_hours"]) or not compare_numeric(got["moderate_westerly_hours"], gt["moderate_westerly_hours"], tolerance=0):
        errors.append(f"moderate_westerly_hours={got["moderate_westerly_hours"]!r}, expected {gt["moderate_westerly_hours"]!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: numerical evidence and original conclusion")


validators = {
    "validate_wind_response": validate_wind_response,
    "validate_desk_line": validate_desk_line,
    "validate_harder_turn_2": validate_harder_turn_2,
    "validate_harder_turn_1": validate_harder_turn_1,
}
