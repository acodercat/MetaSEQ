"""Beijing ozone exceedances — the MDA8 window convention
(exceedance_anomaly_detection).

China's Grade II ozone limit (160 ug/m3) is judged on the maximum daily 8-hour
average, and HJ 663-2013 Annex A defines that precisely: the largest trailing
8-hour running mean whose window ENDS between 08:00 and 24:00, each window
needing at least 6 valid hours. Getting the metric "roughly right" is not
enough. At Dongsi over June-August 2023 the standard gives 42 exceedance days, and
admitting windows that end 01:00-07:00 gives 49. Restarting the rolling window
at each calendar day gives 42 as well, which is a remeasurement recorded in
`evals/_shared/mda8.py`: it reads 41 only without the hourly reindexing that
module performs, where a gap silently shortens a window. This paragraph said 41
until a Gate A review on 2026-09-06; the live discriminator is the endpoint set,
not the daily restart.

Tolerance 0. The count is exact once the standard is named, so a neighbouring
value is a different method rather than rounding, and no band could separate 42
from 49 without also admitting readings in between. The ground truth is recomputed here from the CSV through the
shared HJ 663 implementation in `evals/_shared/mda8.py`.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number
from tasks import Turn
from domains.beijing.mda8 import frame_to_mda8

_STATION, _YEAR, _MONTHS = "Dongsi", 2023, (6, 7, 8)
_LIMIT = 160.0


def _counts() -> dict:
    df = pd.read_csv(DATA_DIR / "air_quality.csv")
    # Hour h ends at h:00, so 2023 is 1 January 01:00 to 1 January 2024 00:00.
    stamp = pd.to_datetime(df[["year", "month", "day", "hour"]])
    in_year = (stamp - pd.Timedelta(hours=1)).dt.year == _YEAR
    year = df[(df["station"] == _STATION) & in_year]

    # HJ 663: the whole year feeds the rolling window, then restrict to summer,
    # so the 1 June windows keep their 31 May history.
    mda8 = frame_to_mda8(year)
    summer_mda8 = mda8[mda8.index.month.isin(_MONTHS)]

    return {
        "correct": int((summer_mda8 > _LIMIT).sum()),
    }


def validate_exceedance_days(
    response: str, runtime, turn: Turn
) -> ValidatorResult:
    val = runtime.retrieve("exceedance_days")
    if val is None:
        return ValidatorResult(
            False, "exceedance_days not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(False, f"exceedance_days={val!r} is not a number")

    gt = _counts()
    if compare_numeric(val, gt["correct"], tolerance=0):
        return ValidatorResult(
            True, f"correct: {val} MDA8 exceedance days"
        )
    return ValidatorResult(
        False, f"exceedance_days={val}, expected {gt['correct']}"
    )


tools = []
variables = [
    Variable(
        "exceedance_days",
        None,
        "Store the number of days in June-August 2023 at Dongsi whose ozone "
        "exceeded the Grade II 8-hour limit, as an integer.",
    ),
]
validators = {"validate_exceedance_days": validate_exceedance_days}
