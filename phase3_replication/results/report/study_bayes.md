# Primary model (pre-registration §5)

Bayesian logistic regressions on the four core arms' scored runs, bambi default priors, 4 chains × 2,000 draws (seed 20260929, target accept 0.99). Probability scale, averaged over the tasks (and backbones) the fit holds.

## pooled over backbones

`correct ~ decomposition * verification + (1|task) + (1|backbone) + (1|task:backbone)`; 10656 runs. Convergence: max r̂ 1.004, min bulk ESS 910, min tail ESS 1,375, divergent transitions 0.

| quantity | posterior mean (pp) | 95% interval (pp) | P(> 0) |
|---|---|---|---|
| verification (main effect) | +5.4 | [+4.3, +6.6] | 1.000 |
| decomposition (main effect) | +1.6 | [+0.5, +2.7] | 0.997 |
| interaction | -3.2 | [-5.5, -1.0] | 0.002 |
| H2: verification − decomposition (= B − C) | +3.9 | [+2.3, +5.4] | 1.000 |
| H1 D − A | +7.0 | [+5.4, +8.7] | 1.000 |
| H2a B − A | +7.1 | [+5.5, +8.7] | 1.000 |
| H2b C − A | +3.2 | [+1.6, +4.8] | 1.000 |
| H2c D − B | -0.0 | [-1.6, +1.5] | 0.484 |

## claude-sonnet-5-5

`correct ~ decomposition * verification + (1|task)`; 1332 runs. Convergence: max r̂ 1.002, min bulk ESS 2,762, min tail ESS 3,325, divergent transitions 0.

| quantity | posterior mean (pp) | 95% interval (pp) | P(> 0) |
|---|---|---|---|
| verification (main effect) | +3.9 | [+2.1, +5.7] | 1.000 |
| decomposition (main effect) | +3.3 | [+1.5, +5.1] | 1.000 |
| interaction | -8.1 | [-11.6, -4.8] | 0.000 |
| H2: verification − decomposition (= B − C) | +0.6 | [-1.2, +2.4] | 0.741 |
| H1 D − A | +7.2 | [+4.2, +10.4] | 1.000 |
| H2a B − A | +7.9 | [+5.0, +11.0] | 1.000 |
| H2b C − A | +7.3 | [+4.5, +10.4] | 1.000 |
| H2c D − B | -0.7 | [-2.6, +1.0] | 0.203 |

## deepseek-v4-flash

`correct ~ decomposition * verification + (1|task)`; 1332 runs. Convergence: max r̂ 1.003, min bulk ESS 1,665, min tail ESS 2,724, divergent transitions 0.

| quantity | posterior mean (pp) | 95% interval (pp) | P(> 0) |
|---|---|---|---|
| verification (main effect) | +4.7 | [+1.4, +8.1] | 0.999 |
| decomposition (main effect) | -0.0 | [-3.4, +3.3] | 0.497 |
| interaction | -2.3 | [-8.7, +4.1] | 0.247 |
| H2: verification − decomposition (= B − C) | +4.8 | [+0.2, +9.4] | 0.979 |
| H1 D − A | +4.7 | [-0.1, +9.5] | 0.972 |
| H2a B − A | +5.9 | [+1.2, +10.5] | 0.994 |
| H2b C − A | +1.1 | [-3.6, +5.9] | 0.678 |
| H2c D − B | -1.2 | [-5.7, +3.2] | 0.302 |

## deepseek-v4-flash-thinking

`correct ~ decomposition * verification + (1|task)`; 1332 runs. Convergence: max r̂ 1.001, min bulk ESS 2,154, min tail ESS 3,112, divergent transitions 0.

| quantity | posterior mean (pp) | 95% interval (pp) | P(> 0) |
|---|---|---|---|
| verification (main effect) | +6.7 | [+3.6, +9.8] | 1.000 |
| decomposition (main effect) | +0.1 | [-3.0, +3.3] | 0.530 |
| interaction | +3.9 | [-2.1, +10.0] | 0.895 |
| H2: verification − decomposition (= B − C) | +6.6 | [+2.1, +11.1] | 0.998 |
| H1 D − A | +6.8 | [+2.6, +11.1] | 0.999 |
| H2a B − A | +4.7 | [+0.5, +9.1] | 0.985 |
| H2b C − A | -1.9 | [-6.6, +2.9] | 0.216 |
| H2c D − B | +2.1 | [-1.8, +6.1] | 0.847 |

## deepseek-v4-pro-0813

`correct ~ decomposition * verification + (1|task)`; 1332 runs. Convergence: max r̂ 1.001, min bulk ESS 2,602, min tail ESS 3,603, divergent transitions 0.

| quantity | posterior mean (pp) | 95% interval (pp) | P(> 0) |
|---|---|---|---|
| verification (main effect) | +0.7 | [-2.2, +3.8] | 0.685 |
| decomposition (main effect) | -0.2 | [-3.2, +2.9] | 0.460 |
| interaction | +3.2 | [-2.8, +9.1] | 0.850 |
| H2: verification − decomposition (= B − C) | +0.9 | [-3.3, +5.1] | 0.660 |
| H1 D − A | +0.6 | [-3.6, +4.8] | 0.608 |
| H2a B − A | -0.8 | [-5.0, +3.4] | 0.347 |
| H2b C − A | -1.7 | [-5.9, +2.5] | 0.212 |
| H2c D − B | +1.4 | [-2.8, +5.6] | 0.746 |

## gpt-6-luna

`correct ~ decomposition * verification + (1|task)`; 1332 runs. Convergence: max r̂ 1.004, min bulk ESS 1,819, min tail ESS 2,670, divergent transitions 0.

| quantity | posterior mean (pp) | 95% interval (pp) | P(> 0) |
|---|---|---|---|
| verification (main effect) | +9.5 | [+6.1, +13.0] | 1.000 |
| decomposition (main effect) | -0.0 | [-3.4, +3.4] | 0.497 |
| interaction | -1.0 | [-7.7, +5.6] | 0.383 |
| H2: verification − decomposition (= B − C) | +9.5 | [+4.6, +14.4] | 1.000 |
| H1 D − A | +9.5 | [+4.7, +14.4] | 1.000 |
| H2a B − A | +10.1 | [+5.4, +14.8] | 1.000 |
| H2b C − A | +0.5 | [-4.7, +5.6] | 0.581 |
| H2c D − B | -0.5 | [-5.0, +4.0] | 0.407 |

## qwen3.8-27b

`correct ~ decomposition * verification + (1|task)`; 1332 runs. Convergence: max r̂ 1.002, min bulk ESS 1,665, min tail ESS 2,615, divergent transitions 0.

| quantity | posterior mean (pp) | 95% interval (pp) | P(> 0) |
|---|---|---|---|
| verification (main effect) | +8.9 | [+5.3, +12.5] | 1.000 |
| decomposition (main effect) | +7.1 | [+3.5, +10.9] | 1.000 |
| interaction | -8.6 | [-15.9, -1.4] | 0.009 |
| H2: verification − decomposition (= B − C) | +1.8 | [-3.3, +6.8] | 0.751 |
| H1 D − A | +16.0 | [+10.8, +21.3] | 1.000 |
| H2a B − A | +13.2 | [+7.9, +18.4] | 1.000 |
| H2b C − A | +11.4 | [+6.1, +16.7] | 1.000 |
| H2c D − B | +2.9 | [-2.0, +7.8] | 0.871 |

## qwen3.8-27b-thinking

`correct ~ decomposition * verification + (1|task)`; 1332 runs. Convergence: max r̂ 1.001, min bulk ESS 1,901, min tail ESS 3,386, divergent transitions 0.

| quantity | posterior mean (pp) | 95% interval (pp) | P(> 0) |
|---|---|---|---|
| verification (main effect) | +5.9 | [+3.1, +8.8] | 1.000 |
| decomposition (main effect) | +2.1 | [-0.8, +5.0] | 0.922 |
| interaction | -4.5 | [-10.1, +1.2] | 0.059 |
| H2: verification − decomposition (= B − C) | +3.9 | [-0.1, +7.9] | 0.972 |
| H1 D − A | +8.0 | [+3.9, +12.1] | 1.000 |
| H2a B − A | +8.2 | [+4.1, +12.3] | 1.000 |
| H2b C − A | +4.3 | [-0.1, +8.6] | 0.973 |
| H2c D − B | -0.2 | [-4.0, +3.6] | 0.466 |

## qwen3.8-flash

`correct ~ decomposition * verification + (1|task)`; 1332 runs. Convergence: max r̂ 1.002, min bulk ESS 1,497, min tail ESS 2,443, divergent transitions 0.

| quantity | posterior mean (pp) | 95% interval (pp) | P(> 0) |
|---|---|---|---|
| verification (main effect) | +2.5 | [-1.1, +6.1] | 0.915 |
| decomposition (main effect) | -0.2 | [-3.8, +3.4] | 0.464 |
| interaction | -6.1 | [-13.2, +1.0] | 0.042 |
| H2: verification − decomposition (= B − C) | +2.7 | [-2.3, +7.7] | 0.853 |
| H1 D − A | +2.3 | [-2.8, +7.4] | 0.819 |
| H2a B − A | +5.6 | [+0.6, +10.6] | 0.986 |
| H2b C − A | +2.9 | [-2.1, +7.9] | 0.873 |
| H2c D − B | -3.2 | [-8.2, +1.8] | 0.100 |

Versions: bambi 0.21.0, PyMC 6.3.2, ArviZ 1.3.0, NumPy 2.5.3, pandas 3.0.6.

