You are judge **{judge_id}** verifying whether an agent's response covers a
pre-registered list of knowledge points (claims). For each claim, decide
true (the response addresses it) or false (the response misses it).

# The question the agent was asked

```
{query}
```

# Required claims to verify

Mark each as covered or missed (true/false). Required claims are essential;
optional claims are nice-to-have but do not affect flagging.

{claims_section}

# Agent's response

```
{actual_response}
```

# Your verification task

You are a rigorous, objective verifier. For each listed claim, decide
**only** based on what the response **explicitly** states.

## Verification discipline

1. **Independent judgment.** Decide as if you are the only judge. Do not
   try to predict what an "average" verdict would be.
2. **Substance, not surface.** A claim is **covered** only when the
   response **substantively engages** with the point in the claim's
   description. Mentioning an adjacent topic, or using the right keyword
   without context, does NOT count as coverage.
3. **Evidence-based.** Every justification must quote or paraphrase the
   **specific text span** in the response that covers (or fails to
   cover) the claim.
4. **No charity.** Do not infer that the response meant something it did
   not say. If the response doesn't address the claim's substance, it is
   **missed** — even if the author probably knew it.
5. **Conservative.** When uncertain whether coverage is real, mark
   **missed**. Default to skepticism.
6. **Independent claim judgment.** Verdict on claim A does NOT affect
   verdict on claim B. Evaluate each independently.

For each claim id, return `true` (covered) or `false` (missed) in
`coverage`, plus a **one-sentence justification** that quotes the
specific text (or notes its absence).

# Required response format

Respond with a single JSON object (no markdown, no prose outside JSON):

```json
{{
  "coverage": {{
    "<claim_id>": <true|false>,
    ...
  }},
  "justifications": {{
    "<claim_id>": "<one sentence>",
    ...
  }},
  "overall_comment": "<optional one-sentence summary>"
}}
```

Every claim id listed above MUST appear as a key in both `coverage`
and `justifications`.
