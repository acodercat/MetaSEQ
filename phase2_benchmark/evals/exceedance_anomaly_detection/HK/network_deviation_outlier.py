
import numpy as np
import pandas as pd
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, compare_numeric, is_finite_number
def validate_network_outlier(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    outlier_station = runtime.retrieve("outlier_station")
    outlier_hour = runtime.retrieve("outlier_hour")
    station_pm25 = runtime.retrieve("station_pm25")
    network_mean = runtime.retrieve("network_mean")
    zscore = runtime.retrieve("zscore")

    if outlier_station is None:
        return ValidatorResult(False, "outlier_station not set", variables_not_set=True)
    if outlier_hour is None:
        return ValidatorResult(False, "outlier_hour not set", variables_not_set=True)
    if station_pm25 is None:
        return ValidatorResult(False, "station_pm25 not set", variables_not_set=True)
    if network_mean is None:
        return ValidatorResult(False, "network_mean not set", variables_not_set=True)
    if zscore is None:
        return ValidatorResult(False, "zscore not set", variables_not_set=True)

    # Get hourly PM2.5 for all GENERAL stations on Oct 5
    data = pd.read_sql(
        text("""
            SELECT aqs.name_en,
                   EXTRACT(HOUR FROM hsaq.datetime)::int AS hour,
                   hsaq.pm2_5
            FROM hourly_station_air_quality hsaq
            JOIN air_quality_station aqs ON hsaq.station_id = aqs.id
            WHERE hsaq.datetime >= '2025-10-05' AND hsaq.datetime < '2025-10-06'
              AND hsaq.pm2_5 IS NOT NULL
              AND aqs.station_type = 'GENERAL'
        """),
        engine,
    )

    # Compute hourly network mean and std
    hourly_stats = data.groupby("hour")["pm2_5"].agg(["mean", "std"]).reset_index()
    hourly_stats.columns = ["hour", "net_mean", "net_std"]

    merged = data.merge(hourly_stats, on="hour")
    # Filter out hours with zero std (no variation)
    merged = merged[merged["net_std"] > 0].copy()
    merged["zscore"] = (merged["pm2_5"] - merged["net_mean"]) / merged["net_std"]
    merged["abs_zscore"] = merged["zscore"].abs()

    idx = merged["abs_zscore"].idxmax()
    row = merged.loc[idx]

    expected_station = row["name_en"]
    expected_hour = int(row["hour"])
    expected_pm25 = round(float(row["pm2_5"]), 1)
    expected_mean = round(float(row["net_mean"]), 1)
    expected_zscore = round(float(row["zscore"]), 2)

    errors = []

    if not isinstance(outlier_station, str):
        errors.append("outlier_station should be str")
    elif outlier_station.strip().lower() != expected_station.strip().lower():
        errors.append(f"outlier_station='{outlier_station}', expected '{expected_station}'")

    if not is_finite_number(outlier_hour):
        errors.append("outlier_hour should be numeric")
    elif int(outlier_hour) != expected_hour:
        errors.append(f"outlier_hour={int(outlier_hour)}, expected {expected_hour}")

    if not is_finite_number(station_pm25):
        errors.append("station_pm25 should be numeric")
    elif abs(station_pm25 - expected_pm25) > 1.0:
        errors.append(f"station_pm25={station_pm25}, expected ~{expected_pm25}")

    if not is_finite_number(network_mean):
        errors.append("network_mean should be numeric")
    elif abs(network_mean - expected_mean) > 1.0:
        errors.append(f"network_mean={network_mean}, expected ~{expected_mean}")

    if not is_finite_number(zscore):
        errors.append("zscore should be numeric")
    # Signed comparison: positive z = station above network mean, negative
    # = below. Erasing the sign would mask a directional misreading.
    elif not compare_numeric(zscore, expected_zscore, tolerance=0.3):
        errors.append(f"zscore={zscore}, expected ~{expected_zscore}")

    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True,
        f"Correct: {expected_station} at hour {expected_hour}, PM2.5={expected_pm25}, "
        f"network_mean={expected_mean}, z={expected_zscore}",
    )
tools = []
variables = [
    Variable("outlier_station", None, "Station with the largest absolute z-score on Oct 5 (str)."),
    Variable("outlier_hour", None, "Hour of day (0-23) of the outlier event (int)."),
    Variable("station_pm25", None, "Station PM2.5 at the outlier hour, 1dp (float)."),
    Variable("network_mean", None, "Network mean PM2.5 at the outlier hour, 1dp (float)."),
    Variable("zscore", None, "Z-score of the outlier, 2dp (float)."),
]
validators = {"validate_network_outlier": validate_network_outlier}
