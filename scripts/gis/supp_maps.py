"""Supplementary data-layer atlas: six georeferenced maps in the ORIGINAL
HK_maps style (CartoDB Voyager basemap, lat/lon degree axes), one panel per
data stream. Draft for the SI — nothing here touches the manuscript.

Panels (a-f): monitoring network / road-traffic congestion snapshot /
1-km population grid / OSM building footprints / EIA habitat / OSM road
network. All data from the deployment DB caches under phase2_benchmark/gis_cache/.

Caption must credit the basemap: (c) OpenStreetMap contributors (c) CARTO
(the original scripts drew tiles with attribution=False).

Run:
    cd scripts/gis
    uv run --with geopandas --with contextily --with osmnx \
           --with "psycopg[binary]" --with sqlalchemy --with pydantic-settings \
           python supp_maps.py
"""

from __future__ import annotations

import pickle
from pathlib import Path

import contextily as ctx
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import PowerNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MultipleLocator

from db import BENCHMARK, HERE
from layer_maps import (land_clip, load_boundary, load_habitat, load_osm,
                        load_stations, population_grid)

OUT = HERE.parent.parent / "manuscript" / "figures" / "supp_atlas.pdf"

# reuse the old project's 305-MB tile cache; new tiles land there too
ctx.set_cache_dir("/home/codercat/Desktop/Workplace/AI-gen-report-HKGAI/cache")

# original HK_maps extent and axis style
LON0, LON1 = 113.8403, 114.4075
LAT0, LAT1 = 22.2052, 22.5633
ASPECT = 1 / np.cos(np.radians((LAT0 + LAT1) / 2))

MM = 1 / 25.4  # Nature double column = 183 mm; fonts below are true print pt
plt.rcParams.update({
    "font.family": ["Liberation Sans", "Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 6,
    "pdf.fonttype": 42,
    "axes.linewidth": 0.5,
})

CONGESTION = {0: ("#B9C2C9", "Free flow"), 1: ("#A7CCDF", "Light"),
              2: ("#367DA8", "Moderate"), 3: ("#15486D", "Heavy")}


def new_panel(ax):
    ax.axis([LON0, LON1, LAT0, LAT1])
    ax.set_aspect(ASPECT)
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Voyager,
                    crs="EPSG:4326", attribution=False)
    for spine in ax.spines.values():
        spine.set_color("#666666")
        spine.set_alpha(0.8)
    # 0.1-degree ticks: finer auto-ticks collide after 1-d.p. formatting
    ax.xaxis.set_major_locator(MultipleLocator(0.1))
    ax.yaxis.set_major_locator(MultipleLocator(0.1))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.1f}°E"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, p: f"{y:.1f}°N"))
    ax.tick_params(labelsize=5, width=0.4, length=2, color="#666666",
                   labelcolor="#333333", pad=1.5)


def legend(ax, handles):
    leg = ax.legend(handles=handles, loc="upper right", frameon=True,
                    facecolor="white", framealpha=0.8, fontsize=5.5,
                    labelcolor="#333333", handlelength=1.3,
                    handletextpad=0.4, borderpad=0.4, edgecolor="none")
    leg.get_frame().set_linewidth(0)


def panel_stations(ax):
    met = load_stations("weather_station")
    aq = load_stations("air_quality_station")
    met.plot(ax=ax, marker="^", markersize=34, color="#0072B2",
             edgecolor="#00517F", linewidth=0.7, alpha=0.9, zorder=3)
    aq.plot(ax=ax, marker="s", markersize=34, color="#D55E00",
            edgecolor="#963F00", linewidth=0.7, alpha=0.9, zorder=4)
    legend(ax, [
        Line2D([0], [0], marker="^", color="none", markerfacecolor="#0072B2",
               markersize=6, label="Weather station (52)"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor="#D55E00",
               markersize=6, label="Air-quality station (18)"),
    ])


def panel_traffic(ax):
    snap = pickle.load(open(BENCHMARK / "gis_cache" / "traffic_cache" /
                            "2025-09-01_08-00-00.pkl", "rb"))
    handles = []
    for status, (color, label) in CONGESTION.items():
        seg = snap[snap["congestion_status"] == status]
        if len(seg):
            seg.plot(ax=ax, color=color, linewidth=1.0 if status else 0.7,
                     zorder=3 + status)
        handles.append(Line2D([0], [0], color=color, lw=2, label=label))
    legend(ax, handles)


def panel_population(ax, boundary):
    arr, extent = population_grid()
    im = ax.imshow(arr, extent=extent, origin="lower", cmap="Blues",
                   norm=PowerNorm(2.0, vmin=0, vmax=4.9), alpha=0.82,
                   interpolation="nearest", zorder=2)
    im.set_clip_path(land_clip(ax, boundary))


def panel_buildings(ax):
    bld = load_osm("BUILDING")
    polys = bld[bld.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    polys.plot(ax=ax, facecolor="#0072B2", edgecolor="none", alpha=0.85, zorder=3)


def panel_habitat(ax):
    hab = load_habitat()
    dev = hab["habitat_type"].isin(["DEVELOPED_AREA", "VILLAGE_AREA"])
    hab[~dev].plot(ax=ax, facecolor="#6f9e55", edgecolor="none",
                   alpha=0.7, zorder=2)
    hab[dev].plot(ax=ax, facecolor="#8d8d8d", edgecolor="none",
                  alpha=0.7, zorder=2)
    legend(ax, [Patch(facecolor="#6f9e55", alpha=0.7, label="Natural habitat"),
                Patch(facecolor="#8d8d8d", alpha=0.7, label="Developed / village")])


def panel_roads(ax):
    osm = load_osm("ROAD")
    lines = osm[osm.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    lines.plot(ax=ax, color="#41556b", linewidth=0.3, alpha=0.8, zorder=3)


TITLES = [
    "Monitoring network",
    "Road traffic (2025-09-01 08:00 snapshot)",
    "Population (1-km grid, WorldPop 2020)",
    "Building footprints (OSM)",
    "EIA habitat coverage",
    "Road network (OSM)",
]


def main() -> None:
    boundary = load_boundary()
    fig, axes = plt.subplots(3, 2, figsize=(183 * MM, 208 * MM))
    panels = [panel_stations, panel_traffic,
              lambda ax: panel_population(ax, boundary), panel_buildings,
              panel_habitat, panel_roads]
    for i, (ax, draw, title) in enumerate(zip(axes.flat, panels, TITLES)):
        new_panel(ax)
        draw(ax)
        ax.annotate(chr(97 + i), xy=(0, 1.03), xycoords="axes fraction",
                    fontsize=8, fontweight="bold", va="bottom")
        ax.annotate(title, xy=(0.06, 1.03), xycoords="axes fraction",
                    fontsize=8, va="bottom")
    fig.subplots_adjust(left=0.055, right=0.985, top=0.965, bottom=0.028,
                        wspace=0.16, hspace=0.22)
    fig.savefig(OUT, facecolor="white", dpi=300)
    plt.close(fig)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
