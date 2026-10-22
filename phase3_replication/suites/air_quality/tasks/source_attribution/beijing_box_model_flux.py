"""Beijing's haze buildup as a box, and the slope that is not a flux
(source_attribution).

TRAP, restored 2026-10-07. The naive path is a dimensional slip: the buildup
rate is 1.64 ug/m3 per hour and the variable asks for ug/m2 per hour, so an
agent that stores the bare slope has skipped the step the mass balance exists
to force — multiplying by the depth of the box. The scored answer is 261.

**The 2026-10-06 difficulty upgrade dissolved that trap and was reverted.** It
added a second flux, the column-storage tendency under the recorded hourly
depth, and asked the agent to "compare the fixed-depth buildup flux with the
column-storage tendency when the well-mixed layer follows the recorded hourly
depth". Asking for a second quantity that is explicitly about the depth makes
the depth impossible to miss, which is exactly the Round-9 dissolution rule: a
surface that names the thing the trap tests. The case was reclassified baseline
in the same pass, which was the honest consequence rather than the defect.

What the upgrade got right is kept: `moving_boundary_not_emission`, which asks
the response to say that a growing layer can add column mass while the
concentration falls, so neither tendency bounds an emission. That belongs in the
claims, and it costs the trap nothing.

"""

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_START, _END = "2021-02-09 00:00", "2021-02-13 23:00"


def _flux() -> dict:
    bj = DATA_DIR
    df = pd.read_csv(bj / "air_quality.csv")
    met = pd.read_csv(bj / "met_era5.csv")
    for d in (df, met):
        d["dt"] = pd.to_datetime(d[["year", "month", "day", "hour"]])

    pm = (
        df[(df["dt"] >= _START) & (df["dt"] <= _END)]
        .groupby("dt")["PM2.5"].mean()
    )
    hours = (pm.index - pm.index[0]).total_seconds() / 3600.0
    slope = float(np.polyfit(hours, pm.values, 1)[0])

    blh = float(
        met[(met["dt"] >= _START) & (met["dt"] <= _END)]["blh_m"].mean()
    )
    return {"slope": slope, "blh": blh, "flux": slope * blh}


def validate_accumulation_flux(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("accumulation_flux")
    if val is None:
        return ValidatorResult(
            False, "accumulation_flux not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"accumulation_flux={val!r} is not a number"
        )

    gt = _flux()
    if reports_as(val, gt["flux"], decimals=1):
        return ValidatorResult(
            True,
            f"correct: {val} ~ {gt['flux']:.0f} ug/m2/h "
            f"({gt['slope']:.2f} ug/m3/h over a {gt['blh']:.0f} m layer)",
        )
    return ValidatorResult(
        False, f"accumulation_flux={val}, expected ~{gt['flux']:.0f} ug/m2/h"
    )


tools = []
variables = [
    Variable(
        "accumulation_flux",
        None,
        "Store the surface-equivalent PM2.5 source flux implied by the "
        "buildup as a float in micrograms per square metre per hour, 1 "
        "decimal place. Derive the buildup rate as the ordinary least-squares "
        "slope of the hourly network-mean PM2.5 against time over the window, "
        "and use the window-mean boundary-layer height.",
    ),
]







validators = {
    "validate_accumulation_flux": validate_accumulation_flux,
}
