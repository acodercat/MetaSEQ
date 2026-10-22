# metaseq aggregation summary (auto-generated)

Coverage: 7 backbones x 2 topologies x 50 tasks = 700 runs; task sets identical across cells.

## Pooled (all-turns rule, primary)
- single 261/350 = 74.6% (Wilson 69.8-78.8)
- multi  298/350 = 85.1% (Wilson 81.0-88.5)
- discordant b/c = 55/18  (OR 3.06), exact McNemar p = 1.69e-05
- all-positive deltas across 7 backbones: exact sign test p = 0.016
## Pooled (final-turn rule, sensitivity)
- single 262/350 = 74.9%, multi 303/350 = 86.6%, b/c = 56/15, p = 1.04e-06
## Per-backbone (all-turns; % of 50)
-              GPT-5.5: 96% -> 98% (delta +2pp, b/c 2/1, McNemar p 1, recovery rate 100%; steps 2.5->10.8, tokens 16.3k->90.7k, tok/correct 17k->93k)
-      DeepSeek-V4-Pro: 88% -> 94% (delta +6pp, b/c 4/1, McNemar p 0.375, recovery rate 67%; steps 3.8->14.9, tokens 28.0k->138.6k, tok/correct 32k->147k)
-    Qwen3.5-397B-A17B: 80% -> 92% (delta +12pp, b/c 7/1, McNemar p 0.0703, recovery rate 70%; steps 4.6->18.0, tokens 33.1k->143.4k, tok/correct 41k->156k)
-      Qwen3.6-35B-A3B: 80% -> 84% (delta +4pp, b/c 8/6, McNemar p 0.791, recovery rate 80%; steps 4.6->17.6, tokens 40.5k->161.4k, tok/correct 51k->192k)
-    DeepSeek-V4-Flash: 74% -> 90% (delta +16pp, b/c 8/0, McNemar p 0.00781, recovery rate 62%; steps 4.3->16.8, tokens 34.3k->154.4k, tok/correct 46k->172k)
-          Qwen3.6-27B: 70% -> 82% (delta +12pp, b/c 10/4, McNemar p 0.18, recovery rate 67%; steps 4.4->18.0, tokens 35.7k->159.5k, tok/correct 51k->195k)
- Qwen2.5-72B-Instruct: 34% -> 56% (delta +22pp, b/c 16/5, McNemar p 0.0266, recovery rate 48%; steps 4.8->18.0, tokens 37.3k->147.4k, tok/correct 110k->263k)
## Capability spread (pp of 100): single 62 (SD 18.4) -> multi 42 (SD 13.0)
## Transitions (350 paired cells, all-turns)
- both pass 243, recovery (S✗→M✓) 55, regression (S✓→M✗) 18, both fail 34
## Recurring recoveries (task: #backbones with S✗→M✓, top 8)
- no2_pm25_traffic_dominance: 5
- visibility_pm25_temporal_correlation: 4
- hk_x_traffic_no2_condition: 3
- humidity_secondary_aerosol: 3
- ozone_diurnal_peak: 3
- hk_vor_central_schools: 3
- global_morans_i: 2
- hk_hard_same_hour_area_correlations: 2
## Recurring regressions (task: #backbones with S✓→M✗)
- o3_no2_photochemical_balance: 3
- global_morans_i: 2
- regulatory_compliance_investigation: 2
- thiessen_polygon_area: 1
- area_type_population_exposure_disparity: 1
- hk_deep_pm_ratio_max: 1
- hk_mt_worst_no2_context: 1
- hk_vor_smallest: 1
- aqhi_high_risk_episode: 1
- station_isolation_ranking: 1
- consecutive_exceedance: 1
- hk_cov_pop_newtown2km: 1
- hk_cov_schools_roadside5km: 1
- voronoi_population_aqhi_burden: 1
## Hard residue (multi fails in >=3 of 7 backbones)
- o3_no2_photochemical_balance: 5/7 (source_attribution)
- global_morans_i: 4/7 (spatial_analysis)
- station_isolation_ranking: 4/7 (spatial_analysis)
- thiessen_polygon_area: 4/7 (spatial_analysis)
- regulatory_compliance_investigation: 4/7 (exposure_assessment)
- hk_deep_pm_ratio_max: 4/7 (source_attribution)
- area_type_population_exposure_disparity: 3/7 (exposure_assessment)
## Category gains (all-turns; final-turn in parentheses)
- cross_domain_analysis: 68.3% -> 88.9% (+20.6pp; final-turn +20.6pp)
- data_retrieval: 81.0% -> 100.0% (+19.0pp; final-turn +19.0pp)
- source_attribution: 51.4% -> 68.6% (+17.1pp; final-turn +25.7pp)
- statistical_characterization: 78.6% -> 92.9% (+14.3pp; final-turn +14.3pp)
- spatial_analysis: 73.3% -> 81.9% (+8.6pp; final-turn +8.6pp)
- exposure_assessment: 73.5% -> 77.6% (+4.1pp; final-turn +6.1pp)
- comparative_assessment: 97.1% -> 100.0% (+2.9pp; final-turn +2.9pp)
- exceedance_anomaly_detection: 89.3% -> 89.3% (+0.0pp; final-turn +0.0pp)
## Mixed-logistic sensitivity
- BinomialBayesMixedGLM on the primary rule (correct ~ topology + task & backbone random intercepts): beta_multi = 1.011 (posterior sd 0.180), OR = 2.75, 95% interval 1.93-3.91
