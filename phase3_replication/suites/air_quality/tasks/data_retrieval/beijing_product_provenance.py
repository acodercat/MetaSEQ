"""Station network vs city product — data lineage (data_retrieval).

Provenance BASELINE, deliberately not a diagnostic trap. The runtime carries two
PM10 numbers for Beijing at the same hour, in the same unit: the mean over the
twelve monitoring stations and the value in the city-level regional record. At
the peak of the 15 March 2021 dust storm they differ by 1056.25 ug/m3 — 14 % of
the station mean, 16 % of the city value.

- station_network_pm10: 7506.25 (all twelve stations reporting, no nulls).
- the city record carries 6450.0 for that hour — not scored since 2026-09-02;
  the claims require noticing it.

What the discrepancy licenses, and what it does not. It establishes that the two
published series are not numerically interchangeable at this hour. It does NOT
establish that they rest on independent measurements: the city series could
equally be a differently quality-controlled, station-selected or otherwise
processed aggregate of the same monitoring data. Nothing in the corpus documents
the reconciliation, so the claims require only the supported conclusion — the
gap is real, its origin is undetermined here, and the two figures must not be
substituted for one another.

The station figure is pinned to all twelve stations because the subset matters:
restricting to the eleven flagged `included_in_city_aggregate` gives 7599.0,
which is FURTHER from the city product, not closer — so that flag does not
reconcile the products either.

Both retrievals are explicitly located by the query, which is why this case is
classified easy: putting one source in both variables would be disobeying the
instruction rather than falling for a domain error. The case earns its place
through the CC channel, where the response has to characterise the gap without
over-reading it.

Tolerances, until 2026-09-02: +/-1 ug/m3 on the station mean and +/-5 on the
city value; the station figure is now scored to the nearest hundred. The
station band was +/-30, justified against the 1056 gap the case turns on and the
93 that separates the twelve-station mean from the documented eleven-station
subset — but Gate B found the subsets that matter are nearer than that: dropping
Changping, Tiantan or Wanliu reads 7513.82, 7513.36 or 7504.55 against 7506.25,
the closest only 1.7 out. At +/-1 all three are excluded and the correct value
still clears 2-decimal reporting by two orders of magnitude.

Both ground truths are recomputed here from the CSVs.

**Rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier query told the agent that the runtime holds a second PM10 for
the same hour and asked for both; the rebuilt one asks what PM10 was and
asks the agent to account for what it finds. The station-network figure is
scored to the nearest hundred (7,500 with any one station dropped as well
as with all twelve; the eleven-station subset rounds to 7,600); the city
record's 6,450 is now the claims' to require — noticing it is the exam.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number
from tasks import Turn

_WHEN = dict(year=2021, month=3, day=15, hour=9)
_CITY = "北京"


def _values() -> dict:
    bj = DATA_DIR
    df = pd.read_csv(bj / "air_quality.csv")
    cities = pd.read_csv(bj / "region_cities.csv")

    hour = df[
        (df["year"] == _WHEN["year"]) & (df["month"] == _WHEN["month"])
        & (df["day"] == _WHEN["day"]) & (df["hour"] == _WHEN["hour"])
    ]
    city = cities[
        (cities["city"] == _CITY) & (cities["year"] == _WHEN["year"])
        & (cities["month"] == _WHEN["month"]) & (cities["day"] == _WHEN["day"])
        & (cities["hour"] == _WHEN["hour"])
    ]
    return {
        "station_network": float(hour["PM10"].mean()),
        "city_product": float(city["PM10"].iloc[0]),
    }


def validate_provenance_pair(response: str, runtime, turn: Turn) -> ValidatorResult:
    v = runtime.retrieve("station_network_pm10")
    if v is None:
        return ValidatorResult(False, "station_network_pm10 not set", variables_not_set=True)
    if not is_finite_number(v):
        return ValidatorResult(False, f"station_network_pm10={v!r} is not a number")
    gt = _values()
    # To the nearest hundred: 7,506 across the twelve stations; dropping any
    # one station reads 7,504 to 7,514; the city record's 6,450 and the
    # eleven-station subset's 7,599 both round elsewhere.
    if int(100 * round(float(v) / 100)) == int(100 * round(gt["station_network"] / 100)):
        return ValidatorResult(True, f"correct: about {gt['station_network']:.0f} ug/m3 across the "
                                     f"twelve stations (the city record carries {gt['city_product']:.0f})")
    if compare_numeric(v, gt["city_product"], tolerance=5):
        return ValidatorResult(False, f"station_network_pm10={v}: that is the city record's value; the "
                                      f"twelve stations average {gt['station_network']:.0f}")
    return ValidatorResult(False, f"station_network_pm10={v}, expected ~{gt['station_network']:.0f}")


tools = []
variables = [
    Variable("station_network_pm10", None,
             "Store Beijing's PM10 at that hour as the mean over the twelve "
             "monitoring stations, as a float in ug/m3 to the nearest hundred."),
]
validators = {"validate_provenance_pair": validate_provenance_pair}
