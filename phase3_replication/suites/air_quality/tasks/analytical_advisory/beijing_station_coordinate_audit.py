"""Station-coordinate consistency before automatic district assignment.

Execution baseline: compute the largest coordinate discrepancy and the count
of conflicting district labels, then advise on assigning station readings.
These facts do not estimate resident exposure or establish which source is
correct. Resolving authoritative records, relocation history or surveying may
be appropriate; a resurvey is not the only permissible remedy.
Independent raw-data check: 3.496075 km at Gucheng; two district mismatches,
Dongsi and Wanshouxigong. The two defects occur at different stations.
PV checks the measured discrepancies; CC evaluates the bounded recommendation.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_R_EARTH_KM = 6371.0


def _haversine_km(lat1, lon1, lat2, lon2):
    p = np.pi / 180.0
    a = (
        np.sin((lat2 - lat1) * p / 2) ** 2
        + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2
    )
    return 2 * _R_EARTH_KM * np.arcsin(np.sqrt(a))


def _audit() -> dict:
    st = pd.read_csv(
        DATA_DIR / "station_metadata.csv",
        dtype={"station_code": "string"},
    )
    gap = _haversine_km(
        st["latitude"].values, st["longitude"].values,
        st["registry_latitude"].values, st["registry_longitude"].values,
    )
    return {
        "max_gap_km": float(np.max(gap)),
        "mismatches": int((st["district_consistency"] == "mismatch").sum()),
    }


def validate_coordinate_audit(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {}
    for name in ("max_coordinate_separation_km", "district_mismatch_stations"):
        v = runtime.retrieve(name)
        if v is None:
            return ValidatorResult(False, f"{name} not set", variables_not_set=True)
        if not is_finite_number(v):
            return ValidatorResult(False, f"{name}={v!r} is not a number")
        got[name] = v
    gt = _audit()
    errors = []
    if not reports_as(got["max_coordinate_separation_km"], gt["max_gap_km"], decimals=1):
        errors.append(f"max_coordinate_separation_km={got['max_coordinate_separation_km']}, "
                      f"expected ~{gt['max_gap_km']:.1f} km")
    if not compare_numeric(got["district_mismatch_stations"], gt["mismatches"], tolerance=0):
        errors.append(f"district_mismatch_stations={got['district_mismatch_stations']}, expected {gt['mismatches']}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: {gt['max_gap_km']:.1f} km maximum separation, "
                                 f"{gt['mismatches']} district mismatches")


tools = []
variables = [
    Variable("max_coordinate_separation_km", None,
             "Store the largest great-circle separation between a station's two "
             "recorded coordinate sets, as a float in kilometres to 1 decimal place."),
    Variable("district_mismatch_stations", None,
             "Store how many stations have a site-identity district that "
             "disagrees with the district their coordinates fall in, as an integer."),

]
validators = {"validate_coordinate_audit": validate_coordinate_audit}
