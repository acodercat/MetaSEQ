"""Daily maximum 8-hour ozone (MDA8), shared by several Beijing tasks.

Copied from AirBench `evals/_shared/mda8.py`; the only change is that the
station metadata is read from this domain's data directory. Task modules
import it as `domains.beijing.mda8`.
"""


import pandas as pd

MIN_HOURS_PER_WINDOW = 6
_WINDOW = 8


def hourly_to_mda8(hourly: pd.Series) -> pd.Series:
    """Daily maximum 8-hour ozone from an hourly series, per HJ 663-2013.

    `hourly` must be indexed by timestamp (local time) and may have gaps; it is
    reindexed to a continuous hourly grid so a missing hour is a missing value
    rather than a silently skipped row. Returns a Series indexed by date.
    """
    s = hourly.sort_index()
    s = s.asfreq("h") if s.index.freq is None else s
    rolling = s.rolling(_WINDOW, min_periods=MIN_HOURS_PER_WINDOW).mean()

    # Label each window by the day that owns it. Windows ending at 00:00 are
    # that day's 24:00 endpoint, so they belong to the PREVIOUS date.
    owner = pd.Series(rolling.index.normalize(), index=rolling.index)
    midnight = rolling.index.hour == 0
    owner[midnight] = rolling.index[midnight].normalize() - pd.Timedelta(days=1)

    candidate = (rolling.index.hour >= 8) | midnight
    return rolling[candidate].groupby(owner[candidate]).max()


def _city_points() -> set:
    """The 城市点 A.2 admits: everything but the background site."""
    from domains.beijing.data import DATA_DIR

    meta = pd.read_csv(DATA_DIR / "station_metadata.csv")
    return set(meta.loc[meta["included_in_city_aggregate"], "station"])


def frame_to_mda8(
    df: pd.DataFrame,
    value_col: str = "O3",
    station: str | None = None,
) -> pd.Series:
    """MDA8 per date from a wide benchmark frame with year/month/day/hour columns."""
    sel = df if station is None else df[df["station"] == station]

    def one(frame: pd.DataFrame) -> pd.Series:
        stamps = pd.to_datetime(
            dict(year=frame["year"], month=frame["month"],
                 day=frame["day"], hour=frame["hour"])
        )
        hourly = pd.Series(frame[value_col].to_numpy(), index=stamps).sort_index()
        return hourly_to_mda8(hourly.groupby(level=0).mean())

    # HJ 663-2013 A.2: the CITY daily maximum 8-hour ozone is the arithmetic
    # mean of the stations' own daily maxima — "城市O3的日最大8小时平均：各点位
    # 臭氧日最大8小时平均浓度值的算术平均值" — not the daily maximum of a
    # network-mean hourly series. The two differ: on 2023 they give 96.859 and
    # 96.202, and 99 of 365 days differ by more than 1 ug/m3. An earlier comment
    # here asserted the opposite and every city-level ozone case inherited it.
    #
    # And "各点位" is footnoted in A.2: "点位指城市点，不包括区域点、背景点、
    # 污染监控点和路边交通点". Dingling is the network's background site and is
    # excluded from Beijing's city aggregate — `station_metadata.csv` has carried
    # the flag all along in `included_in_city_aggregate`, and only
    # `beijing_product_provenance` was reading it.
    if station is None and "station" in sel and sel["station"].nunique() > 1:
        points = _city_points()
        city = sel[sel["station"].isin(points)]
        per_station = [
            one(g) for _, g in city.dropna(subset=[value_col]).groupby("station")
        ]
        return pd.concat(per_station, axis=1).mean(axis=1)
    return one(sel)
