"""The suite prompt as the tool harness's agent reads it.

The suite's prompts (ported from AirBench) describe the code harness's protocol: one fenced
```python block per response. Under the tool harness exactly those paragraphs are swapped for
their tool-calling counterparts, and the domain's `<examples>` block, whose fenced code shows
what a step runs, is introduced as tool calls. Nothing else changes. A prompt that no longer
carries one of the protocol paragraphs verbatim is refused rather than half-translated.

The paragraphs and their counterparts are AirBench's (``core/system_instructions.py`` at
d5bcc29, ``_TOOL_PROTOCOL`` and ``_TOOL_EXAMPLES_NOTE``, public here), copied verbatim, so
the two projects' tool-harness agents read the same words.
"""

from __future__ import annotations

from errors import ConfigurationError

# The paragraphs of the suite prompt that describe the fence protocol, each with its
# tool-calling counterpart. Only these differ between the harnesses.
TOOL_PROTOCOL = (
    (
        """  - Each response contains exactly one ```python``` block with nothing after
    the closing fence. The environment runs it and returns the real output; if
    further analysis is needed, write the next block in your NEXT response.
  - Only a Markdown ```python fence is executed. Code delivered any other way
    is read as prose and never runs, so the turn ends having computed nothing.
    Do not wrap code in a provider-specific tag, a special token, or any markup
    native to your own model family, even if that is your usual habit.
""",
        """  - Each step is one call of the `python` tool with the code to run. The
    environment runs it and returns the real output; if further analysis is
    needed, call the tool again in your NEXT response.
  - Only code passed to the `python` tool is executed. Code written in the text
    of a response is read as prose and never runs, so the turn ends having
    computed nothing. The ```python blocks in these instructions and examples
    show code to pass to the tool.
""",
    ),
    (
        """  - The session is a persistent Jupyter-like environment: variables, functions
    and imports persist across cells and can be referenced directly, without
    locals(), globals() or any special access. Reuse earlier results instead of
    re-running identical queries.
""",
        """  - The runtime is persistent. Every `python` call runs in the same session,
    across all steps and all questions of this task: variables, functions,
    imports and earlier results persist and can be referenced directly, without
    locals(), globals() or any special access. Reuse earlier results instead of
    re-running identical queries.
""",
    ),
    (
        """  What a step looks like. A complete first response is only this — one fence,
  nothing before or after it (table_df stands for whichever registered table
  or query result the question needs):

```python
# Orient before filtering: the columns and periods in play
print(table_df.columns.tolist())
print(table_df.head())
```

  This is not a step. It runs nothing, and because it contains no code the
  turn ends here with every output variable still unassigned:
""",
        """  What a step looks like. A complete first response is only one `python` tool
  call, with code such as this (table_df stands for whichever registered table
  or query result the question needs):

    # Orient before filtering: the columns and periods in play
    print(table_df.columns.tolist())
    print(table_df.head())

  This is not a step. It runs nothing, and because it calls no tool the turn
  ends here with every output variable still unassigned:
""",
    ),
    ("Keep each block compact,", "Keep each call compact,"),
)

_EXAMPLES_TAG = "<examples>\n"
TOOL_EXAMPLES_NOTE = (
    "In these examples each ```python block stands for one call of the `python` tool:\n"
    "only code passed to the tool runs, never code written in the message itself.\n"
)


def for_tool_harness(prompt: str) -> str:
    """*prompt*, a suite system prompt in the fence protocol's words, in the tool harness's."""
    for code, tool in TOOL_PROTOCOL:
        if prompt.count(code) != 1:
            raise ConfigurationError(
                f"prompt does not carry the fence-protocol paragraph once: {code[:60]!r}")
        prompt = prompt.replace(code, tool)
    if prompt.count(_EXAMPLES_TAG) == 1:
        prompt = prompt.replace(_EXAMPLES_TAG, _EXAMPLES_TAG + TOOL_EXAMPLES_NOTE)
    return prompt
