# SHGRAG experiment results

Model: `claude-opus-5-5` · effort: `medium` · runs: 1 · cases: 75

Values are mean ± std across runs (percent).

## Overall conflict-vs-clean detection

| Condition | Precision | Recall | F1 | Accuracy | FP | FN | Errors | Run agreement |
|---|---|---|---|---|---|---|---|---|
| symbolic | 91.3 ± 0.0 | 100.0 ± 0.0 | 95.5 ± 0.0 | 94.7 ± 0.0 | 4.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 100.0 |
| symbolic_noaffects | 88.2 ± 0.0 | 35.7 ± 0.0 | 50.8 ± 0.0 | 61.3 ± 0.0 | 2.0 ± 0.0 | 27.0 ± 0.0 | 0.0 ± 0.0 | 100.0 |

## Per-type detection recall (flagged as any conflict)

| Condition | logical | semantic | physical |
|---|---|---|---|
| symbolic | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 |
| symbolic_noaffects | 100.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |

## Per-type F1 (detection; FP = clean cases labelled with that type)

| Condition | logical | semantic | physical |
|---|---|---|---|
| symbolic | 93.8 ± 0.0 | 93.3 ± 0.0 | 100.0 ± 0.0 |
| symbolic_noaffects | 93.8 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |

## Per-type F1 (type label must also be correct)

| Condition | logical | semantic | physical |
|---|---|---|---|
| symbolic | 93.8 ± 0.0 | 93.3 ± 0.0 | 100.0 ± 0.0 |
| symbolic_noaffects | 93.8 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |

## Explanation grounding (automatic proxy)

Share of correctly flagged conflicts whose explanation/evidence mentions all ground-truth key nodes. The required 0/1 expert check uses `annotations.csv`.

| Condition | Grounded |
|---|---|
| symbolic | 69.0 ± 0.0 |
| symbolic_noaffects | 100.0 ± 0.0 |

## Error cases (majority vote)

- **symbolic** — FP: s07_c2, s10_c2, s13_c2, s16_c3; FN: –
- **symbolic_noaffects** — FP: s07_c2, s10_c2; FN: s01_c1, s02_c1, s02_c3, s03_c1, s03_c2, s05_c1, s05_c2, s06_c1, s07_c1, s08_c1, s09_c1, s10_c1, s11_c2, s12_c1, s12_c3, s13_c1, s14_c1, s15_c1, s15_c2, s16_c1, s16_c2, s18_c1, s19_c1, s19_c2, s20_c1, s20_c2, s20_c5
