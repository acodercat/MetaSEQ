
import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def validate_ozone_diurnal_peak(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    """Check the agent finds the peak O3 hour at Tap Mun on 2025-07-05.

    Domain context: Tap Mun is a rural background station in Hong Kong.
    Ozone is produced photochemically during daytime and typically peaks
    in the early-to-mid afternoon (12:00–16:00) at background sites
    where NO titration is minimal.
    """
    peak_o3 = runtime.retrieve("tap_mun_peak_o3")
    peak_hour = runtime.retrieve("tap_mun_peak_o3_hour")

    ground_truth = pd.read_sql(
        text(
            "SELECT EXTRACT(HOUR FROM hsaq.datetime)::int AS peak_hour, "
            "       hsaq.o3 AS peak_o3 "
            "FROM hourly_station_air_quality hsaq "
            "JOIN air_quality_station aqs ON hsaq.station_id = aqs.id "
            "WHERE aqs.name_en = 'Tap Mun' "
            "  AND hsaq.datetime::date = '2025-07-05' "
            "  AND hsaq.o3 IS NOT NULL "
            "ORDER BY hsaq.o3 DESC "
            "LIMIT 1"
        ),
        engine,
    )
    if ground_truth.empty:
        return ValidatorResult(False, "No ground-truth data for Tap Mun O3 on 2025-07-05")

    expected_o3 = float(ground_truth["peak_o3"].iloc[0])
    expected_hour = int(ground_truth["peak_hour"].iloc[0])

    errors = []

    if peak_o3 is None:
        errors.append("tap_mun_peak_o3 not set")
    elif not is_finite_number(peak_o3):
        errors.append(f"tap_mun_peak_o3 should be numeric, got {type(peak_o3).__name__}")
    elif abs(peak_o3 - expected_o3) > 0.5:
        errors.append(f"tap_mun_peak_o3: {peak_o3}, expected ≈ {expected_o3}")

    if peak_hour is None:
        errors.append("tap_mun_peak_o3_hour not set")
    else:
        # Accept int, float, or string representations of the hour
        try:
            actual_hour = int(float(str(peak_hour).replace(":00", "")))
        except (ValueError, TypeError):
            errors.append(f"tap_mun_peak_o3_hour: cannot parse '{peak_hour}' as hour")
            actual_hour = None

        if actual_hour is not None and actual_hour != expected_hour:
            errors.append(f"tap_mun_peak_o3_hour: {peak_hour} (parsed {actual_hour}), expected {expected_hour}")

    if errors:
        return ValidatorResult(False, "; ".join(errors))

    return ValidatorResult(
        True,
        f"Correct: peak O3={peak_o3} at hour {peak_hour} (expected hour {expected_hour})",
    )

tools = []
variables = [
    Variable("tap_mun_peak_o3", None,
        "Store the peak hourly O3 concentration (float, µg/m³)."),
    Variable("tap_mun_peak_o3_hour", None,
        "Store the hour of day (0-23) when the peak O3 occurred (int)."),
]
validators = {
    "validate_ozone_diurnal_peak": validate_ozone_diurnal_peak,
}
