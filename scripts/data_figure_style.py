"""The paper's figure palette and rcParams; figure_style re-exports it for the schematics.

Categorical triple checked in OKLab (Machado 2009 CVD matrices): adjacent-pair ΔE ≥ 16.2 for
normal vision and ≥ 13.3 under protan, deutan and tritan simulation (targets 15 and 8)."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

MM = 1 / 25.4
WIDTH = 180 * MM

INK = "#253746"
MUTED = "#586974"
GRID = "#E8EDEE"
SINGLE = "#8E9196"        # single agent (A): neutral grey, the baseline
SINGLE_LIGHT = "#C9CBCE"
MULTI = "#1F5FA8"         # MetaSEQ (D): blue, the only saturated hue
MULTI_LIGHT = "#9DB9DD"
VOTE = "#E0812B"          # voted baseline (G); errors introduced: orange
PALE = "#F5F6F7"
BLUE_MAP = LinearSegmentedColormap.from_list(
    "score_blue", ["#F3F6FA", "#C6D6EC", "#7FA3D1", "#3F75B5", "#1F5FA8"])


def setup():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
        "legend.frameon": False, "legend.fontsize": 7,
        "xtick.major.width": .5, "ytick.major.width": .5,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "savefig.facecolor": "white", "axes.unicode_minus": True,
    })
    plt.rcParams.update({
        "font.size": 7.5, "axes.labelsize": 7.5, "axes.titlesize": 8,
        "xtick.labelsize": 7, "ytick.labelsize": 7,
        "legend.fontsize": 7, "axes.linewidth": .55,
        "axes.edgecolor": "#AAB5BA", "xtick.color": MUTED,
        "ytick.color": INK, "text.color": INK, "axes.labelcolor": INK,
        "xtick.major.size": 2.2, "ytick.major.size": 2.2,
    })


def clean_axis(ax, grid="x", left=False):
    for side in ("top", "right") + (() if left else ("left",)):
        ax.spines[side].set_visible(False)
    if not left:
        ax.tick_params(axis="y", length=0)
    if grid:
        ax.grid(axis=grid, color=GRID, linewidth=.5)
    ax.set_axisbelow(True)


def panel(fig, letter, x, y, title=None):
    """Bold lower-case letter; an optional plain title beside it, as Nature styles them."""
    fig.text(x, y, letter, fontsize=9, weight="bold", va="top", color="black")
    if title:
        fig.text(x + .022, y - .002, title, fontsize=7, va="top", color=INK)


def save(fig, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    for suffix in (".pdf", ".svg", ".png"):
        fig.savefig(path.with_suffix(suffix), dpi=220)
    plt.close(fig)
    print("written", path.with_suffix(".pdf"))
