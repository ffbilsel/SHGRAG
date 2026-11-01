# SHGRAG experiment results

Model: `claude-opus-5-5` · effort: `medium` · runs: 3 · cases: 75

Values are mean ± std across runs (percent). `API/format errors` counts calls that returned no valid structured answer (API failure, refusal, schema violation); misclassifications are the FP/FN columns.

## Overall conflict-vs-clean detection

| Condition | Precision | Recall | F1 | Accuracy | FP | FN | API/format errors | Run agreement |
|---|---|---|---|---|---|---|---|---|
| graph | 96.2 ± 1.0 | 100.0 ± 0.0 | 98.1 ± 0.5 | 97.8 ± 0.6 | 1.7 ± 0.5 | 0.0 ± 0.0 | 0.0 ± 0.0 | 97.3 |
| graph_noaffects | 96.9 ± 0.0 | 74.6 ± 1.1 | 84.3 ± 0.7 | 84.4 ± 0.6 | 1.0 ± 0.0 | 10.7 ± 0.5 | 0.0 ± 0.0 | 98.7 |
| symbolic | 91.3 ± 0.0 | 100.0 ± 0.0 | 95.5 ± 0.0 | 94.7 ± 0.0 | 4.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 100.0 |
| text | 90.3 ± 1.4 | 81.7 ± 3.0 | 85.8 ± 2.3 | 84.9 ± 2.3 | 3.7 ± 0.5 | 7.7 ± 1.2 | 0.0 ± 0.0 | 90.7 |
| text_deps | 95.5 ± 0.0 | 100.0 ± 0.0 | 97.7 ± 0.0 | 97.3 ± 0.0 | 2.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 100.0 |

## Per-type detection recall (flagged as any conflict)

| Condition | logical | semantic | physical |
|---|---|---|---|
| graph | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 |
| graph_noaffects | 100.0 ± 0.0 | 73.8 ± 3.4 | 46.2 ± 0.0 |
| symbolic | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 |
| text | 100.0 ± 0.0 | 78.6 ± 0.0 | 64.1 ± 9.6 |
| text_deps | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 |

## Per-type F1 (detection; FP = clean cases labelled with that type)

| Condition | logical | semantic | physical |
|---|---|---|---|
| graph | 98.9 ± 1.5 | 95.5 ± 1.5 | 100.0 ± 0.0 |
| graph_noaffects | 96.8 ± 0.0 | 84.9 ± 2.2 | 63.2 ± 0.0 |
| symbolic | 93.8 ± 0.0 | 93.3 ± 0.0 | 100.0 ± 0.0 |
| text | 96.8 ± 0.0 | 82.5 ± 1.5 | 74.2 ± 6.9 |
| text_deps | 98.9 ± 1.5 | 94.4 ± 1.5 | 100.0 ± 0.0 |

## Per-type F1 (type label must also be correct)

| Condition | logical | semantic | physical |
|---|---|---|---|
| graph | 98.9 ± 1.5 | 95.5 ± 1.5 | 100.0 ± 0.0 |
| graph_noaffects | 96.8 ± 0.0 | 81.5 ± 2.2 | 55.6 ± 0.0 |
| symbolic | 93.8 ± 0.0 | 93.3 ± 0.0 | 100.0 ± 0.0 |
| text | 95.6 ± 1.6 | 78.6 ± 2.3 | 68.3 ± 7.5 |
| text_deps | 98.9 ± 1.5 | 94.4 ± 1.5 | 100.0 ± 0.0 |

## Ablation: full graph vs. graph without AFFECTS edges

| Metric | Full graph | No AFFECTS | Δ (pp) |
|---|---|---|---|
| Overall F1 | 98.1 ± 0.5 | 84.3 ± 0.7 | +13.8 |
| Overall recall | 100.0 ± 0.0 | 74.6 ± 1.1 | +25.4 |
| logical recall | 100.0 ± 0.0 | 100.0 ± 0.0 | +0.0 |
| semantic recall | 100.0 ± 0.0 | 73.8 ± 3.4 | +26.2 |
| physical recall | 100.0 ± 0.0 | 46.2 ± 0.0 | +53.8 |

## Explanation grounding (automatic proxy)

Share of correctly flagged conflicts whose explanation/evidence mentions all ground-truth key nodes. This proxy only checks that key nodes are named; it does not show that direction, steps or timing are right. The expert rubric is built with `python -m shgrag rubric-sheet` (docs/annotation_guidelines.md).

| Condition | Grounded |
|---|---|
| graph | 100.0 ± 0.0 |
| graph_noaffects | 100.0 ± 0.0 |
| symbolic | 69.0 ± 0.0 |
| text | 100.0 ± 0.0 |
| text_deps | 100.0 ± 0.0 |

## Home-level 95% confidence intervals (cluster bootstrap over 20 homes, 5000 resamples)

Whole homes are resampled with all their cases and runs, so cases of one home and repeated runs are not treated as independent samples. Values pool all runs.

| Condition | Precision | Recall | F1 | Accuracy |
|---|---|---|---|---|
| graph | 96.2 [91.0, 100.0] | 100.0 [100.0, 100.0] | 98.1 [95.3, 100.0] | 97.8 [94.7, 100.0] |
| graph_noaffects | 96.9 [89.8, 100.0] | 74.6 [62.2, 86.2] | 84.3 [75.2, 91.4] | 84.4 [77.5, 91.1] |
| symbolic | 91.3 [83.3, 97.9] | 100.0 [100.0, 100.0] | 95.5 [90.9, 98.9] | 94.7 [89.5, 98.7] |
| text | 90.4 [78.5, 100.0] | 81.7 [70.1, 92.1] | 85.8 [77.1, 92.4] | 84.9 [76.7, 91.7] |
| text_deps | 95.5 [88.4, 100.0] | 100.0 [100.0, 100.0] | 97.7 [93.8, 100.0] | 97.3 [93.1, 100.0] |

### Paired differences (B − A, same cases, home-level CI)

| A | B | ΔF1 [95% CI] | ΔAccuracy [95% CI] | P(Δ≤0) F1 | both correct | only A | only B | both wrong |
|---|---|---|---|---|---|---|---|---|
| text | graph | +12.2 [+5.6, +20.8] | +12.9 [+6.0, +21.0] | 0.000 | 63 | 1 | 11 | 0 |
| text | text_deps | +11.8 [+5.5, +19.6] | +12.4 [+6.0, +19.6] | 0.000 | 63 | 1 | 10 | 1 |
| text_deps | graph | +0.4 [-1.0, +2.5] | +0.4 [-1.2, +2.8] | 0.452 | 73 | 0 | 1 | 1 |
| graph_noaffects | graph | +13.7 [+5.7, +23.4] | +13.3 [+5.6, +21.2] | 0.000 | 62 | 1 | 12 | 0 |
| text | symbolic | +9.6 [+2.8, +17.8] | +9.8 [+2.3, +17.9] | 0.004 | 61 | 3 | 10 | 1 |

### Per-home accuracy (mean over cases and runs)

| Home | Cases | text | graph | text_deps | graph_noaffects |
|---|---|---|---|---|---|
| s01_hallway_security | 4 | 1.00 | 1.00 | 1.00 | 0.75 |
| s02_bedroom_climate | 4 | 1.00 | 1.00 | 1.00 | 0.83 |
| s03_robot_vacuum | 3 | 0.67 | 1.00 | 1.00 | 1.00 |
| s04_kitchen_safety | 3 | 1.00 | 1.00 | 1.00 | 1.00 |
| s05_router_dependency | 4 | 0.50 | 1.00 | 1.00 | 0.50 |
| s06_aquarium | 4 | 0.92 | 1.00 | 1.00 | 0.75 |
| s07_irrigation_water | 3 | 0.33 | 0.89 | 0.67 | 0.67 |
| s08_lighting_blinds | 4 | 1.00 | 1.00 | 1.00 | 1.00 |
| s09_humidity_bathroom | 4 | 1.00 | 1.00 | 1.00 | 1.00 |
| s10_wall_switch_bulbs | 3 | 1.00 | 1.00 | 1.00 | 1.00 |
| s11_thermostat_schedule | 3 | 0.78 | 1.00 | 1.00 | 0.67 |
| s12_garage_ev | 4 | 1.00 | 1.00 | 1.00 | 1.00 |
| s13_pet_feeder | 4 | 0.83 | 0.75 | 0.75 | 1.00 |
| s14_elderly_care | 3 | 0.67 | 1.00 | 1.00 | 0.67 |
| s15_window_ac | 5 | 0.93 | 1.00 | 1.00 | 1.00 |
| s16_server_closet | 4 | 0.83 | 1.00 | 1.00 | 0.75 |
| s17_multi_user_locks | 3 | 1.00 | 1.00 | 1.00 | 1.00 |
| s18_shades_solar | 4 | 0.75 | 1.00 | 1.00 | 0.75 |
| s19_tv_baby_monitor | 3 | 0.67 | 1.00 | 1.00 | 0.67 |
| s20_greenhouse | 6 | 0.89 | 0.94 | 1.00 | 0.83 |

## Significance (exact McNemar, majority vote over runs)

| A | B | only A correct | only B correct | p-value |
|---|---|---|---|---|
| text | graph | 1 | 11 | 0.0063 |
| text | text_deps | 1 | 10 | 0.0117 |
| text_deps | graph | 0 | 1 | 1.0000 |
| graph_noaffects | graph | 1 | 12 | 0.0034 |
| text | symbolic | 3 | 10 | 0.0923 |

McNemar uses one majority vote per case (cases treated as independent); the home-level bootstrap above is the more conservative estimate when cases of a home are correlated.

## Error cases (majority vote)

- **graph** — FP: s13_c2; FN: –
  - unstable across runs: s07_c2, s20_c4
- **graph_noaffects** — FP: s07_c2; FN: s01_c1, s02_c3, s05_c1, s05_c2, s06_c1, s11_c2, s14_c1, s16_c2, s18_c1, s19_c2, s20_c2
  - unstable across runs: s02_c3
- **symbolic** — FP: s07_c2, s10_c2, s13_c2, s16_c3; FN: –
- **text** — FP: s03_c3, s07_c2, s07_c3, s13_c3; FN: s05_c1, s05_c2, s11_c2, s14_c1, s18_c1, s19_c2, s20_c2
  - unstable across runs: s06_c1, s11_c2, s13_c3, s15_c2, s16_c1, s16_c2, s20_c2
- **text_deps** — FP: s07_c2, s13_c2; FN: –
