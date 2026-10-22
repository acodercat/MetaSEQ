# study

The single agent and the MetaSEQ topology, without analysis rules, on DeepSeek-V4 Flash,
qwen3.8-flash, GPT-6 Luna, Qwen3.8-27B (thinking off and on), DeepSeek-V4 Flash with thinking,
deepseek-v4-pro-0813 and claude-sonnet-5-5 under the tool harness: the suite's tasks x 3
repeats each.

Suite `air_quality` · 2 arms × 8 models (deepseek-v4-flash, qwen3.8-flash, gpt-6-luna, qwen3.8-27b, qwen3.8-27b-thinking, deepseek-v4-flash-thinking, deepseek-v4-pro-0813, claude-sonnet-5-5) · repeats 3

Run status counts: scored 5328

## Accuracy by arm (task-level: every turn must pass)

| arm | model | passed / scored | accuracy | missing | median steps | tokens/task | tokens/correct | turns at step cap |
|---|---|---|---|---|---|---|---|---|
| single_agent_bare | deepseek-v4-flash | 263/333 | 79.0% | 0 | 10 | 115,525 | 146,273 | 0 |
| single_agent_bare | qwen3.8-flash | 231/333 | 69.4% | 0 | 16 | 318,926 | 459,751 | 2 |
| single_agent_bare | gpt-6-luna | 242/333 | 72.7% | 0 | 5 | 44,650 | 61,440 | 0 |
| single_agent_bare | qwen3.8-27b | 202/333 | 60.7% | 0 | 10 | 173,485 | 285,993 | 14 |
| single_agent_bare | qwen3.8-27b-thinking | 263/333 | 79.0% | 0 | 8 | 149,245 | 188,968 | 0 |
| single_agent_bare | deepseek-v4-flash-thinking | 272/333 | 81.7% | 0 | 8 | 80,169 | 98,148 | 0 |
| single_agent_bare | deepseek-v4-pro-0813 | 280/333 | 84.1% | 0 | 9 | 109,427 | 130,140 | 0 |
| single_agent_bare | claude-sonnet-5-5 | 301/333 | 90.4% | 0 | 5 | 66,996 | 74,119 | 0 |
| multi_agent_fixed_roles_verified | deepseek-v4-flash | 279/333 | 83.8% | 0 | 37 | 403,566 | 481,676 | 36 |
| multi_agent_fixed_roles_verified | qwen3.8-flash | 239/333 | 71.8% | 0 | 50 | 762,335 | 1,062,165 | 233 |
| multi_agent_fixed_roles_verified | gpt-6-luna | 274/333 | 82.3% | 0 | 18 | 165,614 | 201,275 | 1 |
| multi_agent_fixed_roles_verified | qwen3.8-27b | 256/333 | 76.9% | 0 | 42 | 510,611 | 664,193 | 85 |
| multi_agent_fixed_roles_verified | qwen3.8-27b-thinking | 290/333 | 87.1% | 0 | 33 | 557,014 | 639,606 | 9 |
| multi_agent_fixed_roles_verified | deepseek-v4-flash-thinking | 295/333 | 88.6% | 0 | 34 | 381,169 | 430,269 | 19 |
| multi_agent_fixed_roles_verified | deepseek-v4-pro-0813 | 282/333 | 84.7% | 0 | 31 | 344,115 | 406,348 | 11 |
| multi_agent_fixed_roles_verified | claude-sonnet-5-5 | 326/333 | 97.9% | 0 | 19 | 304,202 | 310,734 | 0 |

## Paired contrast

| contrast | scope | control → treatment | Δ pp [95% interval] | p | recovered / regressed | McNemar p |
|---|---|---|---|---|---|---|
| H1 orchestration vs single | deepseek-v4-flash | 79.0% → 83.8% | +4.8 [-0.6, +10.5] | 0.075 | 41/25 | 0.064 |
| H1 orchestration vs single | qwen3.8-flash | 69.4% → 71.8% | +2.4 [-3.9, +8.7] | 0.469 | 49/41 | 0.461 |
| H1 orchestration vs single | gpt-6-luna | 72.7% → 82.3% | +9.6 [+4.2, +15.3] | 0.0006 | 51/19 | 0.000166 |
| H1 orchestration vs single | qwen3.8-27b | 60.7% → 76.9% | +16.2 [+9.9, +22.8] | 0 | 77/23 | 5.51e-08 |
| H1 orchestration vs single | qwen3.8-27b-thinking | 79.0% → 87.1% | +8.1 [+3.6, +12.9] | 0 | 41/14 | 0.000355 |
| H1 orchestration vs single | deepseek-v4-flash-thinking | 81.7% → 88.6% | +6.9 [+2.1, +12.0] | 0.004 | 41/18 | 0.00379 |
| H1 orchestration vs single | deepseek-v4-pro-0813 | 84.1% → 84.7% | +0.6 [-4.8, +6.6] | 0.814 | 30/28 | 0.896 |
| H1 orchestration vs single | claude-sonnet-5-5 | 90.4% → 97.9% | +7.5 [+3.0, +12.3] | 0.0018 | 32/7 | 7.03e-05 |
| H1 orchestration vs single | pooled | 77.1% → 84.1% | +7.0 [+4.7, +9.6] | 0 | 362/175 | 5.1e-16 |

Protocol fingerprints per arm (code, prompts and environment the runs were made under): multi_agent_fixed_roles_verified: 8720db542895b835, 4c487ada6a6a4fcc, e4d34b3e173db994, f706e8d480f8b5b2, d43d47732e6c8ac2, 57629fa71391d453; single_agent_bare: 8720db542895b835, 4c487ada6a6a4fcc, e4d34b3e173db994, f706e8d480f8b5b2, d43d47732e6c8ac2, 57629fa71391d453

## Failed turns by cause

| arm | outputs not set | wrong type | model failure | out of steps | wrong value |
|---|---|---|---|---|---|
| multi_agent_fixed_roles_verified | 50 | 15 | 4 | 79 | 302 |
| single_agent_bare | 181 | 4 | 0 | 1 | 502 |
