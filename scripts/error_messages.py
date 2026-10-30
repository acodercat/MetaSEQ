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


def parse_variables(message):
    """Every required output a validator message names, with how it failed: a dict from the
    variable name to (kind, got, expected), where kind is "unset" (named in a "not set" list,
    got and expected None) or "mismatch" (a `var=got, expected ref` pair; got and expected are
    the strings as written, numeric or not, with any unit after the reference dropped).
    Variables the message does not name are not in the dict. Descriptive only."""
    out = {}
    m = re.search(r"^(.*?) not set", message or "")
    if m:
        for v in re.split(r",\s*", m.group(1)):
            if v.strip():
                out[v.strip()] = ("unset", None, None)
    for var, got, expected in MISMATCH.findall(message or ""):
        out[var] = ("mismatch", got.strip(), expected.strip().split(" ")[0])
    return out
