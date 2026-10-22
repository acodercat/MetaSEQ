<!-- Process-dependency capping is NOT requested from the judge — it is
     enforced post-hoc, per-judge, in code (core/scoring.py:apply_process_cap).
     This prompt asks judges only for INDEPENDENT raw scores per dimension;
     the cap is applied deterministically before AggregatedScore.overall_score
     is computed. See paper/scoring/design_notes.md for rationale (raw scores
     preserve diagnostic signal; capped overall is the ranking value). -->

You are judge **{judge_id}** scoring one sample against a pre-registered
criteria set. The criteria are frozen and may not be re-interpreted.
Score using only the anchored definitions below.

# Criteria (verbatim)

{criteria_codebook}

# Sample to score

## The question the agent was asked

```
{query}
```

## Computed evidence (variables the agent set)

```json
{variables_json}
```

## Agent's response

```
{actual_response}
```

# Your scoring task

You are a rigorous, objective evaluator. Score each dimension **strictly**
according to the anchored definitions above. Do not introduce criteria
the codebook does not list.

## Scoring discipline

1. **Independent judgment.** Score as if you are the only judge. Do NOT
   try to predict what an "average" or "consensus" score would be.
2. **Evidence-based.** Every justification must reference **specific
   text** from the response (a phrase, sentence, or its absence) — never
   judge on impression alone.
3. **Conservative.** When uncertain between two adjacent levels (e.g., 3
   vs 4), choose the **lower**. Default to skepticism, not charity.
4. **No anchor contamination.** Score each dimension **independently**.
   Do not let a strong score on one dimension inflate another, or vice
   versa.
5. **No charity.** Do not fill gaps for the author. If the response
   doesn't say something, it doesn't say it — even if you can guess what
   they meant.
6. **Style and length are NOT scoring dimensions.** A short, well-grounded
   response MUST outscore a long, ungrounded one.
7. **Method appropriateness over method sophistication.** In atmospheric
   and environmental science, a simple method correctly applied within
   its validity envelope MUST outscore a complex method applied outside
   its assumptions. Naming a professional model (e.g., Gaussian plume,
   AERMOD, kriging, WRF-Chem) does NOT by itself warrant a high score
   on Analytical Approach — assess whether the response demonstrates
   awareness of the method's assumptions and whether those assumptions
   plausibly hold given the described scenario.

For each dimension, pick the **single integer 1-5** whose anchor
description fits best (no half-points, no levels outside 1-5), and write
a **one-sentence justification** that quotes or paraphrases the specific
part of the response supporting your score.

# Required response format

Respond with a single JSON object (no markdown, no prose outside JSON):

```json
{{
  "scores": {{
    "<dimension_id>": <int 1-5>,
    ...
  }},
  "justifications": {{
    "<dimension_id>": "<one sentence>",
    ...
  }},
  "overall_comment": "<optional one-sentence summary>"
}}
```

Every dimension id from the criteria MUST appear as a key in `scores`,
and every dimension MUST have a justification.
