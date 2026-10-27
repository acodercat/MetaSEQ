"""Write manuscript/tex/table_arms.tex: Table 2, experiment 2 by backbone and arm. The accuracy of
the four core arms and the voted baseline G, and the verification and decomposition main effects
with their intervals, per backbone and pooled, from the six-arm study tables through
replication_tables.

    uv run --project phase3_replication python scripts/table_arms.py
"""

from __future__ import annotations

from pathlib import Path

import replication_tables as rt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript" / "tex" / "table_arms.tex"


def rows() -> list[list[str]]:
    acc = rt.arm_accuracy(); pm = rt.per_model_effects(); fx = rt.factorial()
    out = []
    for m in rt.models() + ["pooled"]:
        a = acc.loc[m]
        if m == "pooled":
            ver = fx.loc["verification"]; dec = fx.loc["decomposition"]
            ver = (ver.estimate_pp, ver.lo_pp, ver.hi_pp); dec = (dec.estimate_pp, dec.lo_pp, dec.hi_pp)
        else:
            r = pm.loc[m]
            ver = (r.verification_pp, r.verification_lo, r.verification_hi)
            dec = (r.decomposition_pp, r.decomposition_lo, r.decomposition_hi)
        ver, dec = ((0.0 if abs(v[0]) < .05 else v[0], v[1], v[2]) for v in (ver, dec))   # no "-0.0"
        out.append([r"\textbf{Pooled}" if m == "pooled" else rt.LABELS[m],
                    *(f"{a[arm]:.1f}" for arm in (rt.A, rt.B, rt.C, rt.D, rt.G)),
                    f"{ver[0]:+.1f} [{ver[1]:+.1f}, {ver[2]:+.1f}]", f"{dec[0]:+.1f} [{dec[1]:+.1f}, {dec[2]:+.1f}]"])
    return out


def main() -> None:
    body = "\n".join(" & ".join(r) + r" \\" for r in rows())
    cc = rt.core_contrasts(); fx = rt.factorial()
    tex = r"""\begin{table}[!ht]
\centering
\fontsize{8.5}{11}\selectfont
\caption{\textbf{Experiment 2: the registered $2\times2$ of decomposition and verification, by backbone.} Validated accuracy, per cent, of the single agent (A), the single agent with the verifier (B), the fixed roles without the verifier (C), MetaSEQ (D, fixed roles with the verifier) and the three-run voting baseline G. Main effects in percentage points on per-task means: verification is the mean of B $-$ A and D $-$ C, decomposition the mean of C $-$ A and D $-$ B; 95\% intervals from 10,000 task resamples. The pooled interaction is """ + f"{fx.loc['interaction', 'estimate_pp']:+.1f} [{fx.loc['interaction', 'lo_pp']:+.1f}, {fx.loc['interaction', 'hi_pp']:+.1f}]" + r""" and D $-$ B is """ + f"{cc.loc['H2c', 'delta_pp']:+.1f} [{cc.loc['H2c', 'lo_pp']:+.1f}, {cc.loc['H2c', 'hi_pp']:+.1f}]" + r""". Per-backbone contrasts and the delegation arms are in Supplementary Tables~12 and~24.}
\label{tab:arms}
\setlength{\tabcolsep}{3.5pt}\renewcommand{\arraystretch}{1.12}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrrrrll@{}}
\toprule
Backbone & A & B & C & D & G & \shortstack[l]{Verification\\(pp) [95\% interval]} & \shortstack[l]{Decomposition\\(pp) [95\% interval]} \\
\midrule
""" + body + r"""
\bottomrule
\end{tabular*}
\end{table}
"""
    OUT.write_text(tex)
    print("written", OUT)


if __name__ == "__main__":
    main()
