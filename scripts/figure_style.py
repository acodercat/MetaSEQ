"""Publication figure styling: one palette for every figure in the paper.

Semantic colours (shared with data_figure_style, which holds the definitions):
    SINGLE  slate      #506B91  single agent (arm A)
    MULTI   teal       #238779  MetaSEQ (arm D)
    VOTE    terracotta #BF7954  voted single-agent baseline (G); errors introduced
    INK / MUTED / GRID / PALE   text, secondary text, gridlines, panel fill
    BLUE_MAP            sequential teal ramp for heat maps
Fonts: Arial or Liberation Sans, 7 pt body, 6.5 pt ticks; 180 mm width; vector text.
Schematic scripts (fig_overview, style_archived_atlas) import from
here; data scripts import data_figure_style directly. Both resolve to the same values.
"""
from data_figure_style import (MM, WIDTH, INK, MUTED, GRID, SINGLE, SINGLE_LIGHT, MULTI,
                               MULTI_LIGHT, VOTE, PALE, BLUE_MAP, setup, clean_axis, panel, save)

__all__ = ["MM", "WIDTH", "INK", "MUTED", "GRID", "SINGLE", "SINGLE_LIGHT", "MULTI", "MULTI_LIGHT",
           "VOTE", "PALE", "BLUE_MAP", "setup", "clean_axis", "panel", "save"]
