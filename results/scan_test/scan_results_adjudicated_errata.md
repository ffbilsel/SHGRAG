# Whole-home scan results

Each reasoner sees all rules of a home and must list every conflicting rule set and its type. A prediction counts as correct when it names the same rule set as a ground-truth conflict (a pair inside a ground-truth triple also counts). Ground truth = conflict cases + `home_conflicts`. LLM runs are pooled; CIs resample homes.

Homes: 8 · ground-truth conflicts (minimal sets): 21 · rule pairs in these homes: 139

| Condition | Precision | Recall | F1 | Typed recall | Logical / semantic / physical recall | FP per home | FP on labelled clean pairs | API/format errors |
|---|---|---|---|---|---|---|---|---|
| text | 84.6 [66, 100] | 69.8 [48, 89] | 76.5 [59, 92] | 55.6 | 88 / 28 / 86 | 0.33 | 5 | 0 |
| text_deps | 95.0 [90, 100] | 90.5 [75, 100] | 92.7 [83, 99] | 88.9 | 88 / 83 / 100 | 0.12 | 0 | 0 |
| graph | 90.8 [82, 100] | 93.7 [83, 100] | 92.2 [84, 98] | 92.1 | 92 / 89 / 100 | 0.25 | 1 | 0 |
| graph_noaffects | 86.7 [76, 100] | 82.5 [69, 93] | 84.6 [74, 93] | 77.8 | 92 / 56 / 95 | 0.33 | 2 | 0 |
| symbolic | 85.7 [72, 100] | 85.7 [68, 100] | 85.7 [72, 97] | 71.4 | 100 / 83 / 71 | 0.38 | 1 | 0 |

## Misses and false positives per home (all runs)

### text
- t01_basement_sump: missed R3+R4; FP –
- t02_media_room: missed R3+R7, R6+R7; FP R3+R4, R4+R5, R5+R6
- t03_steam_shower: missed R1+R2, R1+R5; FP –
- t05_mode_chain: missed R1+R5; FP R3+R4, R6+R7
- t07_driveway: missed R1+R2, R4+R5; FP –

### text_deps
- t02_media_room: missed –; FP R1+R2
- t03_steam_shower: missed R1+R5; FP –
- t05_mode_chain: missed R1+R5; FP R1+R2+R7
- t07_driveway: missed –; FP R1+R3

### graph
- t02_media_room: missed –; FP R1+R2
- t03_steam_shower: missed R1+R5; FP –
- t05_mode_chain: missed R1+R5; FP R1+R2+R7, R6+R7
- t07_driveway: missed –; FP R1+R3

### graph_noaffects
- t01_basement_sump: missed R3+R4; FP –
- t02_media_room: missed –; FP R1+R2, R3+R4
- t03_steam_shower: missed R1+R5; FP –
- t05_mode_chain: missed R1+R5; FP R1+R2+R7, R6+R7
- t06_bedroom_ventilation: missed R2+R4; FP –
- t07_driveway: missed R1+R2; FP R3+R5

### symbolic
- t02_media_room: missed –; FP R3+R4, R3+R6
- t06_bedroom_ventilation: missed R1+R2; FP –
- t07_driveway: missed R1+R2, R4+R5; FP R1+R3

