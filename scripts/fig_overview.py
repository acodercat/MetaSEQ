"""Fig. 1, the overview of MetaSEQ: (a) the observation layers over Hong Kong, (b) the four
specialist roles, (c) the workflow from query to answer, including the synthesis stage and the
verifier used in both controlled experiments. Everything is vector except the basemap tile of
panel a, which is taken from the archived data-layer atlas (supp_atlas.pdf, panel a).

    uv run --project phase3_replication --with matplotlib --with pymupdf python scripts/fig_overview.py

Writes manuscript/figures/overall.pdf (and .png). The author-supplied original is kept in
figures/archive_sources/overall_original.pdf.
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, FancyBboxPatch, Circle, Arc
import pymupdf

from figure_style import setup, WIDTH, MM, INK, MUTED, GRID, MULTI, PALE

setup()
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript/figures"
H = 152   # figure height, mm; coordinates below are in mm from the bottom-left corner
UP = 16   # panels a and b sit this much higher than in the 136-mm layout

LAYERS = [("Air quality", "18 monitoring stations"), ("Meteorology", "52 weather stations"),
          ("Road traffic", "4,300 monitored segments"), ("Population", "1-km residential grid"),
          ("Planning", "EIA habitat coverage"), ("Urban context", "OSM buildings and roads")]
ROLES = [("Knowledge Retriever", "Retrieves from an authoritative corpus\nLinks every fact to its source"),
         ("Statistical Analysis Agent", "Writes the database queries\nComputes summary statistics"),
         ("Environmental Expert Agent", "Multivariate and geospatial analysis\nRuns its analysis as code"),
         ("Health Insight Advisor", "Exposure and risk analysis\nPlain-language health guidance")]


def card(ax, x, y, w, h, title, body, rule=MULTI):
    ax.add_patch(Rectangle((x, y), w, h, fc="white", ec="#C9CBCE", lw=.5))
    ax.text(x + 2.5, y + h - 2.8, title, fontsize=7, weight="bold", va="top")
    ax.text(x + 2.5, y + h - 8.0, body, fontsize=6.0, va="top", linespacing=1.5, color=INK)


# ---- line icons, all in INK at one stroke width, drawn in mm around a centre --------------
LW = .7


def _seg(ax, pts, **kw):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=kw.pop("color", INK), lw=kw.pop("lw", LW), solid_capstyle="round",
            solid_joinstyle="round", **kw)


def icon_person(ax, cx, cy, r=2.2):
    ax.add_patch(Circle((cx, cy + r * .55), r * .42, fc="white", ec=INK, lw=LW))
    ax.add_patch(Arc((cx, cy - r * .55), r * 1.7, r * 1.6, theta1=0, theta2=180, ec=INK, lw=LW))
    _seg(ax, [(cx - r * .85, cy - r * .55), (cx + r * .85, cy - r * .55)])


def icon_clipboard(ax, cx, cy, r=2.2):
    ax.add_patch(FancyBboxPatch((cx - r * .7, cy - r), r * 1.4, r * 1.9, boxstyle="round,pad=0,rounding_size=.3",
                                fc="white", ec=INK, lw=LW))
    ax.add_patch(Rectangle((cx - r * .3, cy + r * .7), r * .6, r * .35, fc="white", ec=INK, lw=LW))
    for k in range(3):
        y = cy + r * .35 - k * r * .5
        ax.plot(cx - r * .4, y, "o", ms=1.3, color=INK)
        _seg(ax, [(cx - r * .15, y), (cx + r * .45, y)])


def icon_page_lens(ax, cx, cy, r=2.2):
    ax.add_patch(Rectangle((cx - r * .8, cy - r * .9), r * 1.3, r * 1.8, fc="white", ec=INK, lw=LW))
    for k in range(3):
        _seg(ax, [(cx - r * .55, cy + r * .5 - k * r * .4), (cx + r * .2, cy + r * .5 - k * r * .4)])
    ax.add_patch(Circle((cx + r * .45, cy - r * .35), r * .4, fc="white", ec=INK, lw=LW))
    _seg(ax, [(cx + r * .73, cy - r * .63), (cx + r * 1.0, cy - r * .9)])


def icon_bars(ax, cx, cy, r=2.2):
    for k, h in enumerate((.6, 1.3, .9, 1.7)):
        ax.add_patch(Rectangle((cx - r * .95 + k * r * .5, cy - r * .9), r * .32, r * h, fc="white", ec=INK, lw=LW))
    _seg(ax, [(cx - r * 1.05, cy - r * .9), (cx + r * 1.05, cy - r * .9)])


def icon_wind(ax, cx, cy, r=2.2):
    ax.add_patch(Arc((cx - r * .2, cy + r * .1), r * 1.1, r * .9, theta1=0, theta2=200, ec=INK, lw=LW))
    ax.add_patch(Arc((cx + r * .35, cy + r * .25), r * 1.0, r * .9, theta1=300, theta2=180, ec=INK, lw=LW))
    _seg(ax, [(cx - r * .75, cy - r * .2), (cx + r * .85, cy - r * .2)])
    _seg(ax, [(cx - r * .9, cy - r * .6), (cx + r * .3, cy - r * .6)])
    _seg(ax, [(cx - r * .5, cy - r * 1.0), (cx + r * .6, cy - r * 1.0)])


def icon_pulse(ax, cx, cy, r=2.2):
    _seg(ax, [(cx - r, cy), (cx - r * .5, cy), (cx - r * .3, cy + r * .7), (cx, cy - r * .7),
              (cx + r * .25, cy + r * .4), (cx + r * .45, cy), (cx + r, cy)])


def icon_merge(ax, cx, cy, r=2.2):
    for dy in (r * .6, -r * .6):
        _seg(ax, [(cx - r, cy + dy), (cx - r * .3, cy + dy), (cx + r * .15, cy)])
    ax.add_patch(FancyArrowPatch((cx + r * .1, cy), (cx + r * 1.05, cy), arrowstyle="-|>", mutation_scale=5,
                                 color=INK, lw=LW, shrinkA=0, shrinkB=0))


def icon_check_lens(ax, cx, cy, r=2.2):
    ax.add_patch(Circle((cx - r * .15, cy + r * .15), r * .75, fc="white", ec=INK, lw=LW))
    _seg(ax, [(cx + r * .38, cy - r * .38), (cx + r * .95, cy - r * .95)], lw=LW * 1.3)
    _seg(ax, [(cx - r * .5, cy + r * .15), (cx - r * .25, cy - r * .15), (cx + r * .25, cy + r * .5)])


def icon_report(ax, cx, cy, r=2.2):
    ax.add_patch(Rectangle((cx - r * .8, cy - r * .95), r * 1.6, r * 1.9, fc="white", ec=INK, lw=LW))
    _seg(ax, [(cx - r * .5, cy + r * .55), (cx + r * .5, cy + r * .55)])
    _seg(ax, [(cx - r * .5, cy + r * .2), (cx + r * .2, cy + r * .2)])
    for k, h in enumerate((.35, .7, .5)):
        ax.add_patch(Rectangle((cx - r * .5 + k * r * .35, cy - r * .75), r * .22, r * h, fc=INK, ec=INK, lw=0))


def icon_doc(ax, cx, cy, r=2.2):
    ax.add_patch(Rectangle((cx - r * .8, cy - r * .95), r * 1.6, r * 1.9, fc="white", ec=INK, lw=LW))
    _seg(ax, [(cx - r * .5, cy + r * .55), (cx + r * .5, cy + r * .55)], lw=LW * 1.4)
    for k in range(3):
        _seg(ax, [(cx - r * .5, cy + r * .1 - k * r * .35), (cx + r * (.5 if k < 2 else .1), cy + r * .1 - k * r * .35)])


def stage(ax, x, y, w, h, label, icon, blue=True, lw=.7, label_dy=None, icon_dy=None,
          fill="white", fontsize=6.3):
    """A workflow stage: outlined box, icon in the upper half, label in the lower half."""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.0", fc=fill,
                                ec=MULTI if blue else "#C9CBCE", lw=lw))
    icon(ax, x + w / 2, y + (icon_dy if icon_dy is not None else h * .62))
    ax.text(x + w / 2, y + (label_dy if label_dy is not None else h * .22), label, ha="center", va="center",
            fontsize=fontsize, linespacing=1.15)


def arrow(ax, x0, x1, y, label=None, dy=1.3, color=MUTED):
    ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>", mutation_scale=6, color=color, lw=.7,
                                 shrinkA=0, shrinkB=0))
    if label:
        ax.text((x0 + x1) / 2, y + dy, label, ha="center", va="bottom", fontsize=5.6, color=MUTED)


def order_badge(ax, x, y, n):
    """The position of a worker in the Coordinator's plan."""
    ax.add_patch(Circle((x, y), 1.7, fc=MULTI, ec="none"))
    ax.text(x, y - .05, str(n), ha="center", va="center", fontsize=5.2, color="white", weight="bold")


def main():
    fig = plt.figure(figsize=(WIDTH, H * MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, 180), ylim=(0, H))
    ax.axis("off")

    # ---- a: observation layers --------------------------------------------------------------
    ax.text(3, H - 2, "a", fontsize=9, weight="bold", va="top")
    ax.text(8, H - 2.4, "Environmental observations over Hong Kong", fontsize=7, weight="bold", va="top")
    map_box = (3, 70 + UP, 84, 56)     # x, y, w, h in mm; the atlas panel is inserted here
    ax.add_patch(Rectangle(map_box[:2], map_box[2], map_box[3], fc="white", ec=GRID, lw=.6))
    for i, (title, desc) in enumerate(LAYERS):
        x = 4 + (i % 3) * 28.5
        y = 63 + UP - (i // 3) * 9.5
        ax.text(x + 2, y, title, fontsize=6.5, weight="bold", va="top")
        ax.text(x + 2, y - 3.4, desc, fontsize=5.9, va="top", color=MUTED)

    # ---- b: specialist roles ----------------------------------------------------------------
    ax.text(93, H - 2, "b", fontsize=9, weight="bold", va="top")
    ax.text(98, H - 2.4, "Specialist roles", fontsize=7, weight="bold", va="top")
    for i, (title, body) in enumerate(ROLES):
        x = 94 + (i % 2) * 43.5
        y = 103 + UP - (i // 2) * 21
        card(ax, x, y, 41, 17, title, body)
    ax.text(94, 77 + UP, "All roles work in one shared workspace; every result is computed by code.",
            fontsize=6, color=MUTED, va="top")

    # ---- c: workflow -------------------------------------------------------------------------
    # One left-to-right spine: question -> plan -> workers in plan order -> synthesis -> verifier
    # -> answer. The workspace box holds the workers and the two closing stages. Two markers show
    # the answer snapshots the experiments score: (1) as the synthesis worker left it, (2) after
    # the verifier recomputed every value from the data. Wording is for a general reader; the
    # caption maps it to the paper's terms (required outputs, staged variables, shared runtime).
    ax.text(3, 59, "c", fontsize=9, weight="bold", va="top")
    ax.text(8, 58.6, "Analysis workflow", fontsize=7, weight="bold", va="top")
    # horizontal layout, in mm: every gap holds the label written on its arrow
    rx, ry, rh = 44, 10, 40                   # the shared runtime box (its width follows the stages)
    gw, gh, gap = 18.5, 13, 1.5               # worker grid: 2 x 2
    gx, gy = rx + 3, ry + 6.5                 # grid origin (bottom-left)
    grid_right = gx + 2 * gw + gap
    sw, vw = 15, 17                           # synthesis, verifier
    sx = grid_right + 13
    vx = sx + sw + 10
    rw = vx + vw + 1.5 - rx
    fx = rx + rw + 8                          # Result Formatter
    fw, aw = 15, 10.5
    yc = gy + gh + gap / 2                    # the spine: the row every stage is centred on
    hb = 20                                   # height of the stages on the spine
    yb = yc - hb / 2

    stage(ax, 2, yb, 11, hb, "User", icon_person, blue=False, lw=.5)
    arrow(ax, 13, 22, yc, "question")
    stage(ax, 22, yb, 15, hb, "Coordinator", icon_clipboard, fontsize=6.0)
    arrow(ax, 37, gx, yc)
    ax.text((37 + rx) / 2, yc + 1.3, "plan", ha="center", va="bottom", fontsize=5.6, color=MUTED)

    ax.add_patch(FancyBboxPatch((rx, ry), rw, rh, boxstyle="round,pad=0,rounding_size=1.2", fc="white", ec=INK, lw=.6))
    ax.text(rx + 3, ry + rh - 2.0, "One shared workspace", fontsize=6.3, weight="bold", va="top")
    ax.text(rx + 3 + 29, ry + rh - 2.0, "every result is computed by code", fontsize=5.6, color=MUTED, va="top")

    workers = [("Knowledge\nRetriever", icon_page_lens), ("Statistical\nAnalysis Agent", icon_bars),
               ("Environmental\nExpert Agent", icon_wind), ("Health Insight\nAdvisor", icon_pulse)]
    for k, (label, ic) in enumerate(workers):
        wx = gx + (k % 2) * (gw + gap)
        wy = gy + (1 - k // 2) * (gh + gap)
        stage(ax, wx, wy, gw, gh, label, ic, label_dy=gh * .24, icon_dy=gh * .68, fontsize=6.0)
        order_badge(ax, wx + 2.3, wy + gh - 2.3, k + 1)

    stage(ax, sx, yb, sw, hb, "Synthesis", icon_merge, label_dy=hb * .2)
    stage(ax, vx, yb, vw, hb, "Verifier", icon_check_lens, lw=1.1, fill=PALE, label_dy=hb * .2)
    arrow(ax, grid_right, sx, yc)
    ax.text((grid_right + sx) / 2, yc + 1.1, "intermediate\nresults", ha="center", va="bottom", fontsize=5.4, color=MUTED, linespacing=1.1)
    arrow(ax, sx + sw, vx, yc)
    arrow(ax, vx + vw, fx, yc)
    stage(ax, fx, yb, fw, hb, "Result\nFormatter", icon_doc, label_dy=hb * .2)
    arrow(ax, fx + fw, fx + fw + 4, yc)
    stage(ax, fx + fw + 4, yb, aw, hb, "Answer", icon_report, blue=False, lw=.5, fontsize=6.0)

    # output snapshots: (1) as synthesis left them, (2) after the verifier
    def snapshot(x, n, text):
        ax.add_patch(Circle((x, yc + 2.6), 1.7, fc="white", ec=INK, lw=.6))
        ax.text(x, yc + 2.55, str(n), ha="center", va="center", fontsize=5.2, color=INK, weight="bold")
        ax.text(x, yc + 4.9, text, ha="center", va="bottom", fontsize=5.4, color=MUTED, linespacing=1.1)
    snapshot((sx + sw + vx) / 2, 1, "answer\ndrafted")
    snapshot((rx + rw + fx) / 2 + .3, 2, "answer\nchecked")

    # what each stage does, under its box
    def note(x, text):
        ax.text(x, yb - 1.4, text, fontsize=5.4, color=MUTED, ha="center", va="top", linespacing=1.1)
    note(22 + 7.5, "splits the question\ninto steps")
    note(sx + sw / 2, "assembles\nthe answer")
    note(vx + vw / 2, "recalculates every\nvalue from the data")
    note(fx + fw / 2, "writes the report\nand charts")

    ax.text(3, 2.0, "Basemap © OpenStreetMap contributors © CARTO; monitoring locations from the data-layer atlas (Supplementary Fig. 9).",
            fontsize=5.4, color=MUTED, va="bottom")

    base = OUT / "overview_layout.pdf"
    fig.savefig(base)
    plt.close(fig)

    # insert the atlas map (panel a of supp_atlas.pdf) into the reserved box, vector symbols kept
    doc = pymupdf.open(base)
    atlas = pymupdf.open(OUT / "supp_atlas.pdf")
    # Remove, not merely hide, everything outside the map panel: a viewport clip leaves the
    # atlas's axis ticks ("22.4°N" ...) in the text layer, where extractors still find them.
    clip = pymupdf.Rect(36, 25, 258, 168)
    page = atlas[0]
    for r in (pymupdf.Rect(0, 0, page.rect.width, clip.y0), pymupdf.Rect(0, clip.y1, page.rect.width, page.rect.height),
              pymupdf.Rect(0, 0, clip.x0, page.rect.height), pymupdf.Rect(clip.x1, 0, page.rect.width, page.rect.height)):
        page.add_redact_annot(r)
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
    k = 72 / 25.4
    x, y, w, h = map_box
    dest = pymupdf.Rect((x + .4) * k, (H - y - h + .4) * k, (x + w - .4) * k, (H - y - .4) * k)
    doc[0].show_pdf_page(dest, atlas, 0, clip=clip, keep_proportion=True)
    doc.save(OUT / "overall.pdf", garbage=4, deflate=True)
    doc[0].get_pixmap(dpi=220).save(OUT / "overall.png")
    base.unlink()
    print("written", OUT / "overall.pdf")


if __name__ == "__main__":
    main()
