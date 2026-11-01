# Whole-home scan results

Each reasoner sees all rules of a home and must list every conflicting rule set and its type. A prediction counts as correct when it names the same rule set as a ground-truth conflict (a pair inside a ground-truth triple also counts). Ground truth = conflict cases + `home_conflicts`. LLM runs are pooled; CIs resample homes.

Homes: 8 · ground-truth conflicts (minimal sets): 17 · rule pairs in these homes: 139

| Condition | Precision | Recall | F1 | Typed recall | Logical / semantic / physical recall | FP per home | FP on labelled clean pairs | API/format errors |
|---|---|---|---|---|---|---|---|---|
| text | 75.0 [59, 93] | 76.5 [55, 94] | 75.7 [58, 89] | 58.8 | 100 / 20 / 100 | 0.54 | 7 | 0 |
| text_deps | 85.0 [75, 96] | 100.0 [100, 100] | 91.9 [86, 98] | 98.0 | 100 / 100 / 100 | 0.38 | 3 | 0 |
| graph | 78.5 [65, 92] | 100.0 [100, 100] | 87.9 [79, 96] | 98.0 | 100 / 100 / 100 | 0.58 | 5 | 0 |
| graph_noaffects | 75.0 [59, 92] | 88.2 [74, 98] | 81.1 [67, 93] | 82.4 | 100 / 67 / 94 | 0.62 | 5 | 0 |
| symbolic | 71.4 [59, 88] | 88.2 [75, 100] | 78.9 [69, 90] | 70.6 | 100 / 80 / 83 | 0.75 | 2 | 0 |

## Misses and false positives per home (all runs)

### text
- t01_basement_sump: missed R3+R4; FP –
- t02_media_room: missed R3+R7, R6+R7; FP R3+R4, R4+R5, R5+R6
- t03_steam_shower: missed R1+R2; FP R1+R5
- t05_mode_chain: missed –; FP R3+R4, R6+R7
- t06_bedroom_ventilation: missed –; FP R3+R4
- t07_driveway: missed R1+R2; FP –

### text_deps
- t02_media_room: missed –; FP R1+R2
- t05_mode_chain: missed –; FP R1+R2+R7
- t06_bedroom_ventilation: missed –; FP R3+R4
- t07_driveway: missed –; FP R1+R3, R4+R5

### graph
- t02_media_room: missed –; FP R1+R2
- t03_steam_shower: missed –; FP R1+R5
- t05_mode_chain: missed –; FP R1+R2+R7, R1+R5, R6+R7
- t06_bedroom_ventilation: missed –; FP R3+R4
- t07_driveway: missed –; FP R1+R3, R4+R5

### graph_noaffects
- t01_basement_sump: missed R3+R4; FP –
- t02_media_room: missed –; FP R1+R2, R3+R4
- t05_mode_chain: missed –; FP R1+R2+R7, R1+R5, R6+R7
- t06_bedroom_ventilation: missed R2+R4; FP R3+R4
- t07_driveway: missed R1+R2; FP R3+R5, R4+R5

### symbolic
- t02_media_room: missed –; FP R3+R4, R3+R6
- t03_steam_shower: missed –; FP R1+R5
- t05_mode_chain: missed –; FP R1+R5
- t06_bedroom_ventilation: missed R1+R2; FP R3+R4
- t07_driveway: missed R1+R2; FP R1+R3

