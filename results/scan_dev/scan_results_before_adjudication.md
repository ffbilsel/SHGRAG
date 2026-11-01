# Whole-home scan results

Each reasoner sees all rules of a home and must list every conflicting rule set and its type. A prediction counts as correct when it names the same rule set as a ground-truth conflict (a pair inside a ground-truth triple also counts). Ground truth = conflict cases + `home_conflicts`. LLM runs are pooled; CIs resample homes.

Homes: 20 · ground-truth conflicts (minimal sets): 44 · rule pairs in these homes: 196

| Condition | Precision | Recall | F1 | Typed recall | Logical / semantic / physical recall | FP per home | FP on labelled clean pairs | API/format errors |
|---|---|---|---|---|---|---|---|---|
| text | 91.5 [82, 99] | 73.5 [61, 85] | 81.5 [73, 89] | 72.7 | 94 / 60 / 58 | 0.15 | 5 | 0 |
| text_deps | 96.2 [90, 100] | 95.5 [89, 100] | 95.8 [92, 99] | 95.5 | 89 / 100 / 100 | 0.08 | 0 | 0 |
| graph | 95.5 [89, 100] | 95.5 [88, 100] | 95.5 [91, 99] | 94.7 | 93 / 95 / 100 | 0.10 | 0 | 0 |
| graph_noaffects | 93.2 [84, 100] | 72.7 [62, 83] | 81.7 [74, 88] | 68.9 | 96 / 62 / 50 | 0.12 | 0 | 0 |
| symbolic | 81.5 [67, 94] | 100.0 [100, 100] | 89.8 [80, 97] | 100.0 | 100 / 100 / 100 | 0.50 | 4 | 0 |

## Misses and false positives per home (all runs)

### text
- s02_bedroom_climate: missed R4+R5; FP –
- s03_robot_vacuum: missed –; FP R1+R4
- s05_router_dependency: missed R1+R2, R1+R3; FP –
- s06_aquarium: missed R1+R2; FP –
- s07_irrigation_water: missed –; FP R2+R3, R2+R5
- s11_thermostat_schedule: missed R3+R4; FP R1+R3
- s12_garage_ev: missed –; FP R1+R3
- s13_pet_feeder: missed R1+R2; FP –
- s14_elderly_care: missed R1+R2; FP –
- s15_window_ac: missed R1+R2, R3+R4; FP –
- s18_shades_solar: missed R1+R2; FP –
- s19_tv_baby_monitor: missed R1+R3; FP –
- s20_greenhouse: missed R1+R2, R1+R3; FP –

### text_deps
- s02_bedroom_climate: missed R4+R5; FP –
- s04_kitchen_safety: missed –; FP R1+R3
- s07_irrigation_water: missed –; FP R2+R3
- s08_lighting_blinds: missed R1+R3; FP –

### graph
- s02_bedroom_climate: missed R1+R2, R4+R5; FP –
- s04_kitchen_safety: missed –; FP R1+R3
- s07_irrigation_water: missed –; FP R2+R3
- s08_lighting_blinds: missed R1+R3; FP –

### graph_noaffects
- s01_hallway_security: missed R1+R2; FP –
- s02_bedroom_climate: missed R2+R4, R4+R5; FP –
- s05_router_dependency: missed R1+R2, R1+R3; FP –
- s06_aquarium: missed R1+R2; FP –
- s07_irrigation_water: missed –; FP R2+R3
- s11_thermostat_schedule: missed R3+R4; FP –
- s12_garage_ev: missed –; FP R1+R3, R1+R5
- s13_pet_feeder: missed R1+R2; FP –
- s14_elderly_care: missed R1+R2; FP –
- s15_window_ac: missed R1+R2; FP –
- s18_shades_solar: missed R1+R2; FP –
- s19_tv_baby_monitor: missed R1+R3; FP –
- s20_greenhouse: missed R1+R3; FP –

### symbolic
- s07_irrigation_water: missed –; FP R1+R4, R2+R3, R2+R4, R3+R4
- s08_lighting_blinds: missed –; FP R2+R4
- s10_wall_switch_bulbs: missed –; FP R3+R4
- s11_thermostat_schedule: missed –; FP R1+R3
- s13_pet_feeder: missed –; FP R1+R3, R1+R6
- s16_server_closet: missed –; FP R1+R3

