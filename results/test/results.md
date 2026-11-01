# SHGRAG experiment results

Model: `claude-opus-5-5` · effort: `medium` · runs: 3 · cases: 40

Values are mean ± std across runs (percent). `API/format errors` counts calls that returned no valid structured answer (API failure, refusal, schema violation); misclassifications are the FP/FN columns.

## Overall conflict-vs-clean detection

| Condition | Precision | Recall | F1 | Accuracy | FP | FN | API/format errors | Run agreement |
|---|---|---|---|---|---|---|---|---|
| graph | 84.1 ± 2.4 | 100.0 ± 0.0 | 91.3 ± 1.4 | 93.3 ± 1.2 | 2.7 ± 0.5 | 0.0 ± 0.0 | 0.0 ± 0.0 | 97.5 |
| graph_noaffects | 82.4 ± 0.0 | 100.0 ± 0.0 | 90.3 ± 0.0 | 92.5 ± 0.0 | 3.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 100.0 |
| symbolic | 85.7 ± 0.0 | 85.7 ± 0.0 | 85.7 ± 0.0 | 90.0 ± 0.0 | 2.0 ± 0.0 | 2.0 ± 0.0 | 0.0 ± 0.0 | 100.0 |
| text | 79.9 ± 1.1 | 85.7 ± 5.8 | 82.7 ± 3.3 | 87.5 ± 2.0 | 3.0 ± 0.0 | 2.0 ± 0.8 | 0.0 ± 0.0 | 95.0 |
| text_deps | 84.1 ± 2.4 | 100.0 ± 0.0 | 91.3 ± 1.4 | 93.3 ± 1.2 | 2.7 ± 0.5 | 0.0 ± 0.0 | 0.0 ± 0.0 | 97.5 |

## Per-type detection recall (flagged as any conflict)

| Condition | logical | semantic | physical |
|---|---|---|---|
| graph | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 |
| graph_noaffects | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 |
| symbolic | 100.0 ± 0.0 | 75.0 ± 0.0 | 80.0 ± 0.0 |
| text | 100.0 ± 0.0 | 50.0 ± 20.4 | 100.0 ± 0.0 |
| text_deps | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 |

## Per-type F1 (detection; FP = clean cases labelled with that type)

| Condition | logical | semantic | physical |
|---|---|---|---|
| graph | 90.9 ± 0.0 | 92.6 ± 5.2 | 90.9 ± 0.0 |
| graph_noaffects | 90.9 ± 0.0 | 88.9 ± 0.0 | 90.9 ± 0.0 |
| symbolic | 90.9 ± 0.0 | 75.0 ± 0.0 | 88.9 ± 0.0 |
| text | 90.9 ± 0.0 | 55.2 ± 17.1 | 90.9 ± 0.0 |
| text_deps | 90.9 ± 0.0 | 92.6 ± 5.2 | 90.9 ± 0.0 |

## Per-type F1 (type label must also be correct)

| Condition | logical | semantic | physical |
|---|---|---|---|
| graph | 90.9 ± 0.0 | 92.6 ± 5.2 | 90.9 ± 0.0 |
| graph_noaffects | 83.3 ± 0.0 | 80.0 ± 0.0 | 66.7 ± 0.0 |
| symbolic | 76.9 ± 0.0 | 57.1 ± 0.0 | 75.0 ± 0.0 |
| text | 83.3 ± 0.0 | 35.7 ± 10.1 | 62.2 ± 3.1 |
| text_deps | 90.9 ± 0.0 | 92.6 ± 5.2 | 90.9 ± 0.0 |

## Ablation: full graph vs. graph without AFFECTS edges

| Metric | Full graph | No AFFECTS | Δ (pp) |
|---|---|---|---|
| Overall F1 | 91.3 ± 1.4 | 90.3 ± 0.0 | +1.0 |
| Overall recall | 100.0 ± 0.0 | 100.0 ± 0.0 | +0.0 |
| logical recall | 100.0 ± 0.0 | 100.0 ± 0.0 | +0.0 |
| semantic recall | 100.0 ± 0.0 | 100.0 ± 0.0 | +0.0 |
| physical recall | 100.0 ± 0.0 | 100.0 ± 0.0 | +0.0 |

## Explanation grounding (automatic proxy)

Share of correctly flagged conflicts whose explanation/evidence mentions all ground-truth key nodes. This proxy only checks that key nodes are named; it does not show that direction, steps or timing are right. The expert rubric is built with `python -m shgrag rubric-sheet` (docs/annotation_guidelines.md).

| Condition | Grounded |
|---|---|
| graph | 100.0 ± 0.0 |
| graph_noaffects | 97.6 ± 3.4 |
| symbolic | 66.7 ± 0.0 |
| text | 91.6 ± 0.6 |
| text_deps | 100.0 ± 0.0 |

## Home-level 95% confidence intervals (cluster bootstrap over 8 homes, 5000 resamples)

Whole homes are resampled with all their cases and runs, so cases of one home and repeated runs are not treated as independent samples. Values pool all runs.

| Condition | Precision | Recall | F1 | Accuracy |
|---|---|---|---|---|
| graph | 84.0 [72.4, 95.7] | 100.0 [100.0, 100.0] | 91.3 [84.0, 97.8] | 93.3 [86.8, 98.5] |
| graph_noaffects | 82.4 [70.0, 94.1] | 100.0 [100.0, 100.0] | 90.3 [82.4, 97.0] | 92.5 [85.0, 97.8] |
| symbolic | 85.7 [71.4, 100.0] | 85.7 [68.8, 100.0] | 85.7 [75.0, 96.3] | 90.0 [81.1, 97.6] |
| text | 80.0 [64.0, 93.8] | 85.7 [71.8, 97.9] | 82.8 [69.0, 96.3] | 87.5 [75.4, 97.5] |
| text_deps | 84.0 [72.4, 95.7] | 100.0 [100.0, 100.0] | 91.3 [84.0, 97.8] | 93.3 [86.8, 98.5] |

### Paired differences (B − A, same cases, home-level CI)

| A | B | ΔF1 [95% CI] | ΔAccuracy [95% CI] | P(Δ≤0) F1 | both correct | only A | only B | both wrong |
|---|---|---|---|---|---|---|---|---|
| text | graph | +8.5 [+2.2, +16.1] | +5.8 [+1.5, +11.4] | 0.004 | 35 | 0 | 2 | 3 |
| text | text_deps | +8.5 [+2.2, +16.1] | +5.8 [+1.5, +11.4] | 0.004 | 35 | 0 | 2 | 3 |
| text_deps | graph | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | 1.000 | 37 | 0 | 0 | 3 |
| graph_noaffects | graph | +1.0 [+0.0, +3.2] | +0.8 [+0.0, +2.6] | 0.336 | 37 | 0 | 0 | 3 |
| text | symbolic | +3.0 [-9.8, +12.5] | +2.5 [-5.7, +10.3] | 0.313 | 34 | 1 | 2 | 3 |

### Per-home accuracy (mean over cases and runs)

| Home | Cases | text | graph | text_deps | graph_noaffects |
|---|---|---|---|---|---|
| t01_basement_sump | 5 | 0.93 | 1.00 | 1.00 | 1.00 |
| t02_media_room | 5 | 0.67 | 0.80 | 0.80 | 0.80 |
| t03_steam_shower | 5 | 0.80 | 0.87 | 0.87 | 0.80 |
| t04_pool | 6 | 1.00 | 1.00 | 1.00 | 1.00 |
| t05_mode_chain | 5 | 1.00 | 1.00 | 1.00 | 1.00 |
| t06_bedroom_ventilation | 4 | 1.00 | 1.00 | 1.00 | 1.00 |
| t07_driveway | 4 | 0.50 | 0.75 | 0.75 | 0.75 |
| t08_awning | 6 | 1.00 | 1.00 | 1.00 | 1.00 |

## Significance (exact McNemar, majority vote over runs)

| A | B | only A correct | only B correct | p-value |
|---|---|---|---|---|
| text | graph | 0 | 2 | 0.5000 |
| text | text_deps | 0 | 2 | 0.5000 |
| text_deps | graph | 0 | 0 | 1.0000 |
| graph_noaffects | graph | 0 | 0 | 1.0000 |
| text | symbolic | 1 | 2 | 1.0000 |

McNemar uses one majority vote per case (cases treated as independent); the home-level bootstrap above is the more conservative estimate when cases of a home are correlated.

## Error cases (majority vote)

- **graph** — FP: t02_c3, t03_c2, t07_c4; FN: –
  - unstable across runs: t03_c2
- **graph_noaffects** — FP: t02_c3, t03_c2, t07_c4; FN: –
- **symbolic** — FP: t02_c3, t03_c2; FN: t06_c1, t07_c1
- **text** — FP: t02_c3, t03_c2, t07_c4; FN: t02_c2, t07_c1
  - unstable across runs: t01_c2, t02_c2
- **text_deps** — FP: t02_c3, t03_c2, t07_c4; FN: –
  - unstable across runs: t03_c2
