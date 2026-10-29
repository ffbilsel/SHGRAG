# SHGRAG experiment results

Model: `claude-opus-5-5` · effort: `medium` · runs: 3 · cases: 75

Values are mean ± std across runs (percent).

## Overall conflict-vs-clean detection

| Condition | Precision | Recall | F1 | Accuracy | FP | FN | Errors | Run agreement |
|---|---|---|---|---|---|---|---|---|
| graph | 96.2 ± 1.0 | 100.0 ± 0.0 | 98.1 ± 0.5 | 97.8 ± 0.6 | 1.7 ± 0.5 | 0.0 ± 0.0 | 0.0 ± 0.0 | 98.7 |
| graph_noaffects | 96.9 ± 0.0 | 75.4 ± 1.1 | 84.8 ± 0.7 | 84.9 ± 0.6 | 1.0 ± 0.0 | 10.3 ± 0.5 | 0.0 ± 0.0 | 98.7 |
| symbolic | 91.3 ± 0.0 | 100.0 ± 0.0 | 95.5 ± 0.0 | 94.7 ± 0.0 | 4.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 100.0 |
| text | 89.7 ± 1.7 | 96.0 ± 2.2 | 92.7 ± 1.1 | 91.6 ± 1.3 | 4.7 ± 0.9 | 1.7 ± 0.9 | 0.0 ± 0.0 | 93.3 |

## Per-type detection recall (flagged as any conflict)

| Condition | logical | semantic | physical |
|---|---|---|---|
| graph | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 |
| graph_noaffects | 100.0 ± 0.0 | 76.2 ± 3.4 | 46.2 ± 0.0 |
| symbolic | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 |
| text | 100.0 ± 0.0 | 95.2 ± 6.7 | 92.3 ± 0.0 |

## Per-type F1 (detection; FP = clean cases labelled with that type)

| Condition | logical | semantic | physical |
|---|---|---|---|
| graph | 100.0 ± 0.0 | 94.4 ± 1.5 | 100.0 ± 0.0 |
| graph_noaffects | 96.8 ± 0.0 | 86.4 ± 2.2 | 63.2 ± 0.0 |
| symbolic | 93.8 ± 0.0 | 93.3 ± 0.0 | 100.0 ± 0.0 |
| text | 96.8 ± 0.0 | 88.8 ± 3.3 | 92.3 ± 0.0 |

## Per-type F1 (type label must also be correct)

| Condition | logical | semantic | physical |
|---|---|---|---|
| graph | 100.0 ± 0.0 | 94.4 ± 1.5 | 100.0 ± 0.0 |
| graph_noaffects | 96.8 ± 0.0 | 83.1 ± 2.2 | 55.6 ± 0.0 |
| symbolic | 93.8 ± 0.0 | 93.3 ± 0.0 | 100.0 ± 0.0 |
| text | 95.6 ± 1.6 | 85.1 ± 4.2 | 88.0 ± 0.0 |

## Ablation: full graph vs. graph without AFFECTS edges

| Metric | Full graph | No AFFECTS | Δ (pp) |
|---|---|---|---|
| Overall F1 | 98.1 ± 0.5 | 84.8 ± 0.7 | +13.2 |
| Overall recall | 100.0 ± 0.0 | 75.4 ± 1.1 | +24.6 |
| logical recall | 100.0 ± 0.0 | 100.0 ± 0.0 | +0.0 |
| semantic recall | 100.0 ± 0.0 | 76.2 ± 3.4 | +23.8 |
| physical recall | 100.0 ± 0.0 | 46.2 ± 0.0 | +53.8 |

## Explanation grounding (automatic proxy)

Share of correctly flagged conflicts whose explanation/evidence mentions all ground-truth key nodes. The required 0/1 expert check uses `annotations.csv`.

| Condition | Grounded |
|---|---|
| graph | 100.0 ± 0.0 |
| graph_noaffects | 100.0 ± 0.0 |
| symbolic | 69.0 ± 0.0 |
| text | 99.2 ± 1.1 |

## Significance (exact McNemar, majority vote over runs)

| A | B | only A correct | only B correct | p-value |
|---|---|---|---|---|
| text | graph | 0 | 4 | 0.1250 |
| graph_noaffects | graph | 1 | 10 | 0.0117 |
| text | symbolic | 2 | 4 | 0.6875 |

## Error cases (majority vote)

- **graph** — FP: s07_c2, s13_c2; FN: –
  - unstable across runs: s07_c2
- **graph_noaffects** — FP: s07_c2; FN: s01_c1, s02_c3, s05_c1, s05_c2, s06_c1, s11_c2, s14_c1, s16_c2, s19_c2, s20_c2
  - unstable across runs: s15_c1
- **symbolic** — FP: s07_c2, s10_c2, s13_c2, s16_c3; FN: –
- **text** — FP: s03_c3, s07_c2, s07_c3, s13_c2, s13_c3; FN: s14_c1
  - unstable across runs: s02_c3, s13_c2, s13_c3, s15_c2, s15_c3
