"""'2+26' channel membership — the roster is the exam (comparative_assessment).

Diagnostic trap on policy knowledge. The regional file carries 31 cities: the 28
officially designated '2+26' air-pollution transmission-channel cities (Beijing,
Tianjin, 8 in Hebei, 4 in Shanxi, 7 in Shandong, 7 in Henan) plus three northern
Hebei cities — Zhangjiakou, Chengde, Qinhuangdao — that sit outside the channel.
The runtime schema says only "the official '2+26' cities plus northern Hebei",
so answering requires KNOWing the official roster, not reading it off the data.

Winter 2023 (Dec 2022 - Feb 2023), each city's own mean then the cross-city
average:

- correct path (28 channel cities): 68.69 ug/m3.
- wrong path: averaging all 31 -> 65.17, pulled down 3.5 by the three clean
  northern cities (Zhangjiakou's winter mean is just 24.6).
- wrong path: misreading '2+26' as the 26 without the two municipalities ->
  70.59.

Robustness: pooling all channel station-hours equals the per-city-then-average
value to two decimals; the separation is stable across all six winters in the
record (+2.3 to +3.5). The domain's default daily construction (an hourly
cross-city mean, averaged over each day's hours, then over the days) does NOT
agree: it reads 68.501, a thousandth above the rounding line, and read 68.49 on
the label-date day, so whether it reports 68 or 69 turns on where midnight
falls. The variable therefore names the construction — each city's own winter
mean, then the plain average across cities — which the default would otherwise
override. It is not a pin on the roster, so it costs the trap nothing.

Tolerance history: +/-0.005 against three decimals until 2026-09-02, when
dropping Zibo (68.7229 against 68.6940) was six bands out; at whole units
that omission passes, which is accepted — the roster errors the case
exists to catch do not. Earlier still: Pooling and per-city-then-average agree to two decimals
(above), so the band absorbs nothing methodological and only has to carry the
0.005 that 2-decimal reporting needs; it was +/-0.5. The all-31 roster (65.17)
is 70 bands out and the 26-city misreading (70.59) is 38.

Ground truths are recomputed here from the CSV; the roster constant below IS the
answer key for membership and must match the official designation.

**Rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The query no longer dictates the aggregation order, and the figure is
scored to the nearest whole ug/m3 — per-city means averaged and pooled
station-hours both read 69, while the roster errors the case exists to
catch read 65 (all 31 cities) and 71 (the 26 without the municipalities).
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number
from tasks import Turn

# Official '2+26' transmission-channel cities (2 municipalities + 26 prefecture
# cities across Hebei/Shanxi/Shandong/Henan), as designated in the national
# air-pollution action plan for the Beijing-Tianjin-Hebei air corridor.
_CHANNEL = {
    "北京", "天津",
    "石家庄", "唐山", "廊坊", "保定", "沧州", "衡水", "邢台", "邯郸",
    "太原", "阳泉", "长治", "晋城",
    "济南", "淄博", "济宁", "德州", "聊城", "滨州", "菏泽",
    "郑州", "开封", "安阳", "鹤壁", "新乡", "焦作", "濮阳",
}
_WINTER_YEAR = 2023


def _winter(df: pd.DataFrame) -> pd.DataFrame:
    # Hour h is the hour ending at h:00: the winter runs from the 01:00 label
    # of 1 December 2022 to the 00:00 label of 1 March 2023.
    ending = pd.to_datetime(df[["year", "month", "day", "hour"]]) - pd.Timedelta(hours=1)
    start = pd.Timestamp(_WINTER_YEAR - 1, 12, 1)
    return df[(ending >= start) & (ending < pd.Timestamp(_WINTER_YEAR, 3, 1))]


def _means() -> dict:
    cities = pd.read_csv(DATA_DIR / "region_cities.csv")
    per_city = _winter(cities).groupby("city")["PM2.5"].mean()
    return {
        "correct": float(per_city[per_city.index.isin(_CHANNEL)].mean()),
    }


def validate_channel_winter_pm25(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("channel_winter_pm25")
    if val is None:
        return ValidatorResult(
            False, "channel_winter_pm25 not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"channel_winter_pm25={val!r} is not a number"
        )

    gt = _means()
    # To the nearest whole ug/m3: 69 with the cities' own means averaged and
    # with their station-hours pooled; the all-31 roster reads 65 and the
    # 26-city misreading 71.
    if round(float(val)) == round(gt["correct"]):
        return ValidatorResult(True, f"correct: {val} ~ {gt['correct']:.0f} ug/m3 (28 cities)")
    return ValidatorResult(False, f"channel_winter_pm25={val}, expected ~{gt['correct']:.0f}")


tools = []
variables = [
    Variable(
        "channel_winter_pm25",
        None,
        "Store the winter-2023 mean PM2.5 across the '2+26' channel cities as "
        "a float in ug/m3 to the nearest whole unit, taking each city's own "
        "mean over the winter's hours and then the plain average of those "
        "city means.",
    ),
]
validators = {"validate_channel_winter_pm25": validate_channel_winter_pm25}
