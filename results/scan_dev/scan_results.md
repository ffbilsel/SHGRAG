# Whole-home scan results

Each reasoner sees all rules of a home and must list every conflicting rule set and its type. A prediction counts as correct when it names the same rule set as a ground-truth conflict (a pair inside a ground-truth triple also counts). Ground truth = conflict cases + `home_conflicts`. LLM runs are pooled; CIs resample homes.

Homes: 20 · ground-truth conflicts (minimal sets): 46 · rule pairs in these homes: 196

| Condition | Precision | Recall | F1 | Typed recall | Logical / semantic / physical recall | FP per home | FP on labelled clean pairs | API/format errors |
|---|---|---|---|---|---|---|---|---|
| text | 93.4 [87, 99] | 71.7 [60, 83] | 81.1 [73, 88] | 71.0 | 94 / 56 / 59 | 0.12 | 5 | 0 |
| text_deps | 100.0 [100, 100] | 94.9 [89, 100] | 97.4 [94, 100] | 94.9 | 89 / 100 / 97 | 0.00 | 0 | 0 |
| graph | 100.0 [100, 100] | 95.7 [88, 100] | 97.8 [94, 100] | 94.9 | 93 / 96 / 100 | 0.00 | 0 | 0 |
| graph_noaffects | 96.1 [89, 100] | 71.7 [61, 82] | 82.2 [75, 88] | 68.1 | 96 / 58 / 54 | 0.07 | 0 | 0 |
| symbolic | 83.3 [72, 94] | 97.8 [93, 100] | 90.0 [83, 96] | 97.8 | 100 / 93 / 100 | 0.45 | 4 | 0 |

## Misses and false positives per home (all runs)

### text
- s02_bedroom_climate: missed R4+R5; FP –
- s03_robot_vacuum: missed –; FP R1+R4
- s04_kitchen_safety: missed R1+R3; FP –
- s05_router_dependency: missed R1+R2, R1+R3; FP –
- s06_aquarium: missed R1+R2; FP –
- s07_irrigation_water: missed R2+R3; FP R2+R5
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
- s07_irrigation_water: missed R2+R3; FP –
- s08_lighting_blinds: missed R1+R3; FP –

### graph
- s02_bedroom_climate: missed R1+R2, R4+R5; FP –
- s08_lighting_blinds: missed R1+R3; FP –

### graph_noaffects
- s01_hallway_security: missed R1+R2; FP –
- s02_bedroom_climate: missed R2+R4, R4+R5; FP –
- s04_kitchen_safety: missed R1+R3; FP –
- s05_router_dependency: missed R1+R2, R1+R3; FP –
- s06_aquarium: missed R1+R2; FP –
- s11_thermostat_schedule: missed R3+R4; FP –
- s12_garage_ev: missed –; FP R1+R3, R1+R5
- s13_pet_feeder: missed R1+R2; FP –
- s14_elderly_care: missed R1+R2; FP –
- s15_window_ac: missed R1+R2; FP –
- s18_shades_solar: missed R1+R2; FP –
- s19_tv_baby_monitor: missed R1+R3; FP –
- s20_greenhouse: missed R1+R3; FP –

### symbolic
- s04_kitchen_safety: missed R1+R3; FP –
- s07_irrigation_water: missed –; FP R1+R4, R2+R4, R3+R4
- s08_lighting_blinds: missed –; FP R2+R4
- s10_wall_switch_bulbs: missed –; FP R3+R4
- s11_thermostat_schedule: missed –; FP R1+R3
- s13_pet_feeder: missed –; FP R1+R3, R1+R6
- s16_server_closet: missed –; FP R1+R3

