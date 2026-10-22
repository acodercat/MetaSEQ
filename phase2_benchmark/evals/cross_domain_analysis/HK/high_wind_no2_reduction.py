
import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def validate_high_wind_no2_reduction(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    """Check the agent computes the percentage reduction in NO2 at the windiest station's nearest AQ station."""
    pct_reduction = runtime.retrieve("no2_pct_reduction")

    ground_truth = pd.read_sql(
        text(
            "WITH max_wind AS ( "
            "    SELECT sw.station_id AS weather_station_id, "
            "           date_trunc('hour', sw.datetime) AS peak_hour, "
            "           sw.wind_speed "
            "    FROM hourly_station_weather sw "
            "    WHERE sw.datetime::date = '2025-10-05' "
            "    ORDER BY sw.wind_speed DESC NULLS LAST LIMIT 1 "
            "), "
            "nearest_aq AS ( "
            "    SELECT aqs.id AS station_id "
            "    FROM air_quality_station aqs "
            "    JOIN weather_station ws ON ws.id = (SELECT weather_station_id FROM max_wind) "
            "    ORDER BY ST_Distance(aqs.coordinate, ws.coordinate) ASC LIMIT 1 "
            "), "
            "no2_peak AS ( "
            "    SELECT hsaq.no2 AS peak_no2 "
            "    FROM hourly_station_air_quality hsaq "
            "    JOIN nearest_aq na ON hsaq.station_id = na.station_id "
            "    WHERE hsaq.datetime = (SELECT peak_hour FROM max_wind) "
            "), "
            "no2_day_avg AS ( "
            "    SELECT ROUND(AVG(hsaq.no2)::numeric, 2) AS avg_no2 "
            "    FROM hourly_station_air_quality hsaq "
            "    JOIN nearest_aq na ON hsaq.station_id = na.station_id "
            "    WHERE hsaq.datetime::date = '2025-10-05' "
            ") "
            "SELECT "
            "    ROUND(((nda.avg_no2 - np.peak_no2) / NULLIF(nda.avg_no2, 0) * 100)::numeric, 1) AS pct_reduction "
            "FROM no2_peak np, no2_day_avg nda"
        ),
        engine,
    )
    if ground_truth.empty or pd.isna(ground_truth["pct_reduction"].iloc[0]):
        return ValidatorResult(False, "No ground-truth data for NO2 wind reduction")

    expected = float(ground_truth["pct_reduction"].iloc[0])

    if pct_reduction is None:
        return ValidatorResult(False, "no2_pct_reduction not set")
    if not is_finite_number(pct_reduction):
        # isinstance(x, float) alone lets NaN through — nan > 0.5 is False,
        # so a NaN value would silently validate as correct.
        return ValidatorResult(False, f"no2_pct_reduction should be a finite number, got {pct_reduction!r}")
    if abs(pct_reduction - expected) > 0.5:
        return ValidatorResult(False, f"no2_pct_reduction: {pct_reduction}, expected ≈ {expected}")

    return ValidatorResult(True, f"Correct NO2 reduction: {pct_reduction}%")

tools = []
variables = [
    Variable("no2_pct_reduction", None,
        "Store the percentage reduction in NO2 at the windiest hour vs. day average on 2025-10-05 (float)."),
]
validators = {
    "validate_high_wind_no2_reduction": validate_high_wind_no2_reduction,
}
