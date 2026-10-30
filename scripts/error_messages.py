"""Descriptive extraction from validator messages, not a causal failure taxonomy."""
import re

NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
NUMERIC_MISMATCH = re.compile(
    r"(\w+)=(" + NUMBER + r"),?\s+expected\s+~?(" + NUMBER + r")(?![\d.eE+\-])")
ORDER = ["unset", "gross >=50%", "mid 2-50%", "near miss <2%", "other/unparsed"]


def error_class(message):
    """Use the largest relative discrepancy explicitly reported at the first failed turn.

    Missing outputs take precedence. Zero references, quoted numeric strings,
    nonfinite values and messages with no parsed numeric pair are not assigned
    a relative-error bin. Unreported variables are never assumed to be correct.
    """
    if "not set" in message:
        return "unset"
    pairs = NUMERIC_MISMATCH.findall(message)
    if not pairs or any(float(expected) == 0 for _, _, expected in pairs):
        return "other/unparsed"
    maximum = max(abs(float(got) - float(expected)) / abs(float(expected))
                  for _, got, expected in pairs)
    return ("gross >=50%" if maximum >= .5 else
            "mid 2-50%" if maximum >= .02 else "near miss <2%")


MISMATCH = re.compile(r"(\w+)=(.+?), expected ~?\+?(.+?)(?:;|$)")
NOT_SET = re.compile(r"^\s*(\[.*?\]|[\w, ]+?)\s+not set")
STORED_TYPE = re.compile(r"stored \[(.*?)\] as a type JSON cannot hold")
NOT_NUMBER = re.compile(r"(\w+)=(\S+) is not a number")


def _names(text):
    return [v.strip(" '\"") for v in text.strip("[] ").split(",") if v.strip(" '\"")]


def parse_variables(message):
    """Every required output a validator message names, with how it failed: a dict from the
    variable name to (kind, got, expected). kind is "unset" (a "not set" list, written either
    as `a, b not set` or `['a', 'b'] not set`), "type" (`stored ['a'] as a type JSON cannot
    hold`), or "mismatch" (`var=got, expected ref`, or `var=nan is not a number`); got and
    expected are the strings as written, with any unit after the reference dropped. A message
    that names no output (for instance `incorrect channel peak(s)`) gives an empty dict, and
    the caller treats the turn's outputs as undetermined. Descriptive only."""
    out = {}
    message = message or ""
    m = NOT_SET.search(message)
    if m:
        for v in _names(m.group(1)):
            out[v] = ("unset", None, None)
    for m in STORED_TYPE.finditer(message):
        for v in _names(m.group(1)):
            out[v] = ("type", None, None)
    for var, got in NOT_NUMBER.findall(message):
        out[var] = ("mismatch", got, None)
    for var, got, expected in MISMATCH.findall(message):
        out[var] = ("mismatch", got.strip(), expected.strip().split(" ")[0])
    return out
