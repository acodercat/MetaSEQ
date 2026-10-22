"""Nature-styled data-layer maps for the Figure 1a layer-stack concept.

Draws one map per grounded data stream (planning, population, road traffic,
meteorology, air quality), all sharing the same extent, projection-corrected
aspect, and a flat land silhouette — no raster basemap tiles, no place labels.
Each layer is saved as a transparent PNG plus a combined isometric stack
preview, as DESIGN DRAFTS for the user (nothing here touches the manuscript).

Style notes (vs the migrated map scripts):
- no CartoDB tiles: flat vector silhouette avoids tile branding/label noise
  and tile-attribution requirements. The silhouette is derived from the
  deployment DB's EIA-habitat + land-use-zoning polygons (government data);
  only the gallery's osm_* layers are OSM-derived and, if used in the paper,
  need an "(c) OpenStreetMap contributors" credit in the caption;
- manuscript palette family (Fig. 4/6): blues carry information, red reserved;
- thin marks, frameless legends, no boxed chrome, 300 dpi, RGB.

DB pulls are cached under phase2_benchmark/gis_cache/ so iteration is fast.

Run (network needed on first run only):
    cd scripts/gis
    uv run --with geopandas --with contextily --with osmnx \
           --with "psycopg[binary]" --with sqlalchemy --with pydantic-settings \
           python layer_maps.py
"""

from __future__ import annotations

import pickle

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import PowerNorm
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path as MPath
from PIL import Image

from db import FRAMEWORK, HERE, engine

CACHE = FRAMEWORK / "gis_cache"
OUT = HERE / "layers_out"
OUT.mkdir(exist_ok=True)

# shared canvas: territory extent, aspect corrected at the centre latitude
LON0, LON1, LAT0, LAT1 = 113.815, 114.45, 22.145, 22.585
ASPECT = 1 / np.cos(np.radians((LAT0 + LAT1) / 2))
MM = 1 / 25.4                       # mm -> inch
STACK_W_MM = 183                    # Nature double column
LAYER_W_IN = 160 * MM
FIGSIZE = (LAYER_W_IN, LAYER_W_IN * (LAT1 - LAT0) * ASPECT / (LON1 - LON0))

# manuscript palette family (Figure 4/6)
C_LIGHT = "#5cb3e0"
C_DARK = "#1e4e9e"
C_RED = "#e73618"
C_LAND = "#ececec"
C_COAST = "#c9c9c9"
INK = "#333333"

plt.rcParams.update({
    "font.family": ["Liberation Sans", "Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 6,
    "figure.dpi": 450,
})


def cached(name: str, loader):
    # GeoDataFrame pickles are geopandas-version-coupled: if a future upgrade
    # fails to load them, just delete phase2_benchmark/gis_cache/*.pkl and re-run.
    path = CACHE / f"{name}.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    data = loader()
    path.write_bytes(pickle.dumps(data))
    return data


def load_boundary() -> gpd.GeoDataFrame:
    """Land silhouette derived from the EIA habitat coverage (no external
    geocoder: nominatim is unreachable from this network). Buffer out/in to
    close slivers between adjacent habitat polygons, then simplify."""
    def build():
        from shapely.ops import unary_union
        hab = load_habitat()
        zones = load_zones()  # covers the urban areas habitat data misses
        from shapely.geometry import MultiPolygon, Polygon
        geoms = list(hab.geometry.make_valid().values) + \
                list(zones.geometry.make_valid().values)
        land = unary_union(geoms).buffer(0.004).buffer(-0.004)
        # drop interior rings: gaps in zoning coverage, not real water
        parts = land.geoms if isinstance(land, MultiPolygon) else [land]
        land = MultiPolygon([Polygon(g.exterior) for g in parts if g.area > 1e-5])
        land = land.simplify(0.0003)
        return gpd.GeoDataFrame(geometry=[land], crs=hab.crs)
    return cached("hk_land_silhouette_v3", build)


def load_zones() -> gpd.GeoDataFrame:
    def fetch():
        q = """SELECT ST_SimplifyPreserveTopology(geometry::geometry, 0.0004) AS geometry
               FROM land_use_zone WHERE geometry IS NOT NULL"""
        return gpd.read_postgis(q, engine, geom_col="geometry")
    return cached("hk_land_use_zones", fetch)


def load_habitat() -> gpd.GeoDataFrame:
    def fetch():
        q = """SELECT habitat_type,
                      ST_SimplifyPreserveTopology(geometry::geometry, 0.0004) AS geometry
               FROM eia_habitat WHERE geometry IS NOT NULL"""
        return gpd.read_postgis(q, engine, geom_col="geometry")
    return cached("hk_habitat_simplified", fetch)


def load_roads() -> gpd.GeoDataFrame:
    def fetch():
        q = """SELECT free_flow_speed, geometry::geometry AS geometry
               FROM road_segment WHERE geometry IS NOT NULL"""
        return gpd.read_postgis(q, engine, geom_col="geometry")
    return cached("hk_road_segments", fetch)


def load_stations(table: str) -> gpd.GeoDataFrame:
    def fetch():
        cols = "station_type," if table == "air_quality_station" else ""
        q = f"""SELECT {cols} coordinate::geometry AS geometry
                FROM {table} WHERE coordinate IS NOT NULL"""
        return gpd.read_postgis(q, engine, geom_col="geometry")
    return cached(f"hk_{table}", fetch)


def load_osm(main_type: str) -> gpd.GeoDataFrame:
    def fetch():
        q = f"""SELECT geometry_type,
                       ST_SimplifyPreserveTopology(geometry::geometry, 0.0002) AS geometry
                FROM osm_feature
                WHERE main_type = '{main_type}' AND geometry IS NOT NULL"""
        return gpd.read_postgis(q, engine, geom_col="geometry")
    return cached(f"hk_osm_{main_type.lower()}", fetch)


def load_population() -> pd.DataFrame:
    return pd.read_csv(FRAMEWORK / "datasets" / "HK_population_1km.csv")


def population_grid():
    """Rasterise the 1-km point grid onto its native lattice so cells tile
    seamlessly (scatter markers leave gaps between cells)."""
    pop = load_population()
    step = 1 / 120  # the CSV lattice spacing (~1 km)
    # anchor the lattice on the data's own origin: the CSV grid is offset from
    # the canvas corner, and rounding against LON0/LAT0 would shift every cell
    # by a uniform ~0.3 cell (~300 m)
    lon_org = pop["longitude"].min()
    lat_org = pop["latitude"].min()
    ci = np.round((pop["longitude"] - lon_org) / step).astype(int)
    ri = np.round((pop["latitude"] - lat_org) / step).astype(int)
    arr = np.full((ri.max() + 1, ci.max() + 1), np.nan)
    arr[ri, ci] = np.log10(pop["population"] + 1)
    extent = (lon_org - step / 2, lon_org + (ci.max() + 0.5) * step,
              lat_org - step / 2, lat_org + (ri.max() + 0.5) * step)
    return arr, extent


def land_clip(ax, boundary):
    """PathPatch of the land silhouette, for clipping rasters to the coast."""
    verts, codes = [], []
    geom = boundary.geometry.iloc[0]
    for poly in getattr(geom, "geoms", [geom]):
        pts = list(poly.exterior.coords)
        verts.extend(pts)
        codes.extend([MPath.MOVETO] + [MPath.LINETO] * (len(pts) - 2)
                     + [MPath.CLOSEPOLY])
    patch = PathPatch(MPath(verts, codes), transform=ax.transData,
                      facecolor="none", edgecolor="none")
    ax.add_patch(patch)
    return patch


def new_ax():
    fig = plt.figure(figsize=FIGSIZE)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(LON0, LON1)
    ax.set_ylim(LAT0, LAT1)
    ax.set_aspect(ASPECT, adjustable="datalim")
    ax.axis("off")
    # the layer plate: gives each stratum a visible, identical footprint
    ax.add_patch(Rectangle((LON0, LAT0), LON1 - LON0, LAT1 - LAT0,
                           facecolor="white", edgecolor="#d4d4d4",
                           linewidth=0.5, zorder=0))
    return fig, ax


def draw_land(ax, boundary):
    boundary.plot(ax=ax, facecolor=C_LAND, edgecolor=C_COAST, linewidth=0.5, zorder=1)


def finish(fig, name: str):
    path = OUT / f"{name}.png"
    fig.savefig(path, dpi=450, transparent=True)
    plt.close(fig)
    print("wrote", path.name)


def layer_planning(boundary):
    fig, ax = new_ax()
    draw_land(ax, boundary)
    hab = load_habitat()
    dev = hab["habitat_type"].isin(["DEVELOPED_AREA", "VILLAGE_AREA"])
    developed, natural = hab[dev], hab[~dev]
    # validated green for natural cover; developed areas as neutral grey
    # (grey/green pair beats green/tan: tan failed CVD ΔE 2.0, normal 5.7)
    natural.plot(ax=ax, facecolor="#6f9e55", edgecolor="none", alpha=0.75, zorder=2)
    developed.plot(ax=ax, facecolor="#b9b9b9", edgecolor="none", alpha=0.75, zorder=2)
    finish(fig, "layer1_planning")


def layer_population(boundary):
    fig, ax = new_ax()
    draw_land(ax, boundary)
    arr, extent = population_grid()
    im = ax.imshow(arr, extent=extent, origin="lower", cmap="Blues",
                   norm=PowerNorm(2.0, vmin=0, vmax=4.9),
                   interpolation="nearest", zorder=2)
    im.set_clip_path(land_clip(ax, boundary))
    finish(fig, "layer2_population")


def layer_traffic(boundary):
    fig, ax = new_ax()
    draw_land(ax, boundary)
    roads = load_roads()
    minor = roads[roads["free_flow_speed"] < 60]
    major = roads[roads["free_flow_speed"] >= 60]
    minor.plot(ax=ax, color=C_LIGHT, linewidth=0.55, zorder=2)
    major.plot(ax=ax, color=C_DARK, linewidth=0.95, zorder=3)
    finish(fig, "layer3_traffic")


def layer_meteorology(boundary):
    fig, ax = new_ax()
    draw_land(ax, boundary)
    met = load_stations("weather_station")
    met.plot(ax=ax, marker="^", markersize=34, color=C_LIGHT,
             edgecolor="white", linewidth=0.6, zorder=3)
    finish(fig, "layer4_meteorology")


def layer_air_quality(boundary):
    fig, ax = new_ax()
    draw_land(ax, boundary)
    aq = load_stations("air_quality_station")
    gen = aq[aq["station_type"] == "GENERAL"]
    road = aq[aq["station_type"] == "ROADSIDE"]
    gen.plot(ax=ax, marker="o", markersize=46, color=C_DARK,
             edgecolor="white", linewidth=0.7, zorder=3)
    road.plot(ax=ax, marker="^", markersize=52, color=C_RED,
              edgecolor="white", linewidth=0.7, zorder=4)
    finish(fig, "layer5_air_quality")


def layer_building(boundary):
    fig, ax = new_ax()
    draw_land(ax, boundary)
    bld = load_osm("BUILDING")
    polys = bld[bld.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    # validated purple: keeps the urban footprint distinct from the blue
    # population fill and the blue traffic lines
    polys.plot(ax=ax, facecolor="#7a5fb5", edgecolor="none", alpha=0.85, zorder=2)
    finish(fig, "layer_building")


def layer_road(boundary):
    fig, ax = new_ax()
    draw_land(ax, boundary)
    osm = load_osm("ROAD")
    lines = osm[osm.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    lines.plot(ax=ax, color="#5b6b7a", linewidth=0.28, alpha=0.85, zorder=2)
    finish(fig, "layer_road")


LAYERS = [  # bottom -> top; population at the base keeps the two blue
    # layers (population fill, traffic lines) non-adjacent
    ("layer2_population", "Population", "1-km residential grid"),
    ("layer1_planning", "Planning layers", "EIA habitat: natural (green) / developed (grey)"),
    ("layer3_traffic", "Road traffic", "4,300 monitored segments"),
    ("layer4_meteorology", "Meteorology", "52 weather stations"),
    ("layer5_air_quality", "Air quality", "18 stations: general / roadside"),
]

# real extra layers shown as tightly-stacked fading plates under the base:
# the stack reads as "... and more", without labelling all of them
GHOSTS = [("layer_building", 0.45), ("layer_road", 0.30)]

# isometric shear: x' = x + K*(H - y), y' squashed by S
K, S, GAP_FRAC = 0.30, 0.44, 0.62


def iso(img: Image.Image) -> Image.Image:
    w, h = img.size
    out_w, out_h = int(w + K * h), int(h * S)
    # PIL AFFINE takes the inverse map: input = (a x' + b y' + c, d x' + e y' + f)
    return img.transform((out_w, out_h), Image.AFFINE,
                         (1, -K / S, 0, 0, 1 / S, 0), Image.BICUBIC)


def faded(img: Image.Image, alpha: float) -> Image.Image:
    img = img.copy()
    img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
    return img


def ghost_plate(img_sheared: Image.Image, alpha: float) -> Image.Image:
    """A visible 'sheet' for the more-layers effect: the layer's own plate is
    white and vanishes on the white canvas, so draw a light-grey parallelogram
    plate (same shear geometry) and lay the faded content over it."""
    from PIL import ImageDraw
    w, h = img_sheared.size
    h0 = h / S
    kx = K * h0  # horizontal offset of the sheared bottom edge
    base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base)
    draw.polygon([(0, 0), (w - kx, 0), (w - 1, h - 1), (kx, h - 1)],
                 fill=(240, 240, 240, 255), outline=(210, 210, 210, 255))
    base.alpha_composite(faded(img_sheared, alpha))
    return base


def stack_preview():
    imgs = [iso(Image.open(OUT / f"{name}.png").convert("RGBA")) for name, _, _ in LAYERS]
    ghosts = [ghost_plate(iso(Image.open(OUT / f"{name}.png").convert("RGBA")), a)
              for name, a in GHOSTS]
    w, h = imgs[0].size
    gap = int(h * GAP_FRAC)
    ghost_gap = int(gap * 0.48)  # tighter than the labelled gap: a pile
    total_h = h + gap * (len(imgs) - 1)
    pad_top = int(h * 0.16)
    pad_bot = ghost_gap * len(ghosts)
    margin = int(w * 0.02)  # breathing room so plate corners aren't edge-cut
    canvas = Image.new("RGBA", (int(w * 1.42) + margin, total_h + pad_top + pad_bot),
                       (255, 255, 255, 255))
    y_base = pad_top + total_h - h
    for j, g in enumerate(reversed(ghosts)):  # deepest (faintest) first
        canvas.alpha_composite(g, (margin, y_base + (len(ghosts) - j) * ghost_gap))
    for i, img in enumerate(imgs):  # bottom layer pasted first, lowest position
        canvas.alpha_composite(img, (margin, y_base - i * gap))

    dpi = 450
    fig_w_in = STACK_W_MM * MM
    fig = plt.figure(figsize=(fig_w_in, fig_w_in * canvas.height / canvas.width),
                     dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(canvas)
    ax.axis("off")
    ax.annotate("a", xy=(w * 0.012, pad_top * 0.45), fontsize=8,
                fontweight="bold", color=INK, va="center")
    for i, (_, title, sub) in enumerate(LAYERS):
        y = pad_top + total_h - h - i * gap + h * 0.42
        x = margin + w * 1.05  # clear of the sheared plates' top-right corners
        ax.annotate(title, xy=(x, y), fontsize=7, fontweight="bold",
                    color=INK, va="center")
        ax.annotate(sub, xy=(x, y + h * 0.14), fontsize=5.5,
                    color="#666666", va="center")
    x_lab = margin + w * 1.05
    y_ghost = pad_top + total_h - h * 0.12 + ghost_gap * len(ghosts)
    ax.annotate("\u22ef", xy=(x_lab, y_ghost), fontsize=9, color="#999999",
                va="center")
    ax.annotate("+ further layers: buildings, road network, \u2026",
                xy=(x_lab + w * 0.035, y_ghost), fontsize=5.5,
                color="#999999", va="center")
    # 10-km scale bar on the composite (not sheared with the layers)
    w0 = w - K * h / S  # pre-shear plate width in px: horizontal scale source
    km10 = 10 / (111.32 * np.cos(np.radians((LAT0 + LAT1) / 2)))
    bar = w0 * km10 / (LON1 - LON0)
    x1 = margin + w0 * 0.99
    y_bar = pad_top + total_h - h * 0.055
    ax.plot([x1 - bar, x1], [y_bar, y_bar], color=C_COAST, linewidth=1.0,
            solid_capstyle="butt")
    ax.annotate("10 km", xy=(x1 - bar / 2, y_bar - h * 0.035), ha="center",
                va="bottom", fontsize=5, color="#666666")
    fig.savefig(OUT / "stack_preview.png", dpi=dpi, facecolor="white")
    plt.close(fig)
    print("wrote stack_preview.png  (%.0f mm wide)" % STACK_W_MM)


def main():
    boundary = load_boundary()
    layer_planning(boundary)
    layer_population(boundary)
    layer_building(boundary)
    layer_road(boundary)
    layer_traffic(boundary)
    layer_meteorology(boundary)
    layer_air_quality(boundary)
    stack_preview()


if __name__ == "__main__":
    main()
