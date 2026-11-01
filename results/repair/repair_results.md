# Repair–verify results

15 conflict cases (5 per type) · runs: 3 · max attempts per run: 2 · approval: automatic (--yes)

Success = the edit applies, the hazard simulations no longer show the undesired outcome, the intent simulations still pass, and a whole-home symbolic re-check flags no new rule pair. `path valid` = the cited graph path exists.

| Condition | Success (any attempt) | First-try success | Mean attempts | Applicable | Resolved | Intent kept | No new conflict | Path valid |
|---|---|---|---|---|---|---|---|---|
| text | 100 | 91 | 1.09 | 100 | 100 | 100 | 100 | 71 |
| text_deps | 100 | 98 | 1.02 | 100 | 100 | 100 | 100 | 91 |
| graph | 100 | 96 | 1.04 | 100 | 100 | 100 | 100 | 100 |

## Success by conflict type (any attempt)

| Condition | logical | semantic | physical |
|---|---|---|---|
| text | 100 | 100 | 100 |
| text_deps | 100 | 100 | 100 |
| graph | 100 | 100 | 100 |

## Per case (final attempt of run 0)

- **graph / s01_c1** (physical) — ✅ after 1 attempt(s): `add_condition` on R1
  ```
  - R1: "At 23:00 turn off the hallway smart plug to save energy."
    trigger: time == 23:00
    conditions: none
    actions: plug_hall.power := off
  + R1: "At 23:00 turn off the hallway smart plug to save energy."
    trigger: time == 23:00
    conditions: home_mode != away
    actions: plug_hall.power := off
  ```
- **graph / s01_c2** (logical) — ✅ after 1 attempt(s): `add_condition` on R4
  ```
  - R4: "When motion is detected in the hallway between 22:00 and 06:00, unlock the front door so guests can leave."
    trigger: motion_hall == True
    conditions: time in [22:00, 06:00]
    actions: lock_front.lock := unlocked
  + R4: "When motion is detected in the hallway between 22:00 and 06:00, unlock the front door so guests can leave."
    trigger: motion_hall == True
    conditions: time in [22:00, 06:00]; home_mode != night
    actions: lock_front.lock := unlocked
  ```
- **graph / s02_c1** (semantic) — ✅ after 1 attempt(s): `add_action` on R2
  ```
  - R2: "When the living room temperature rises above 26 C, turn on the ventilation fan and open the window."
    trigger: temp_living > 26
    conditions: none
    actions: vent_living.power := on; window_living.position := open
  + R2: "When the living room temperature rises above 26 C, turn on the ventilation fan and open the window."
    trigger: temp_living > 26
    conditions: none
    actions: vent_living.power := on; window_living.position := open; heater_living.power := off
  ```
- **graph / s03_c1** (semantic) — ✅ after 1 attempt(s): `add_condition` on R2
  ```
  - R2: "When motion is detected in the living room, unlock the entrance door (someone is home)."
    trigger: motion_living == True
    conditions: none
    actions: lock_entrance.lock := unlocked
  + R2: "When motion is detected in the living room, unlock the entrance door (someone is home)."
    trigger: motion_living == True
    conditions: home_mode != away
    actions: lock_entrance.lock := unlocked
  ```
- **graph / s04_c1** (logical) — ✅ after 1 attempt(s): `add_condition` on R2
  ```
  - R2: "When the home switches to away mode, lock the apartment door."
    trigger: home_mode == away
    conditions: none
    actions: lock_door.lock := locked
  + R2: "When the home switches to away mode, lock the apartment door."
    trigger: home_mode == away
    conditions: smoke_kitchen == False
    actions: lock_door.lock := locked
  ```
- **graph / s05_c1** (physical) — ✅ after 1 attempt(s): `add_condition` on R1
  ```
  - R1: "At 00:30 turn off the office plug (standby power saving)."
    trigger: time == 00:30
    conditions: none
    actions: plug_office.power := off
  + R1: "At 00:30 turn off the office plug (standby power saving)."
    trigger: time == 00:30
    conditions: home_mode != night
    actions: plug_office.power := off
  ```
- **graph / s06_c4** (logical) — ✅ after 1 attempt(s): `add_condition` on R5
  ```
  - R5: "When the home switches to night mode, turn off the aquarium heater to keep the room quiet."
    trigger: home_mode == night
    conditions: none
    actions: aquarium_heater.power := off
  + R5: "When the home switches to night mode, turn off the aquarium heater to keep the room quiet."
    trigger: home_mode == night
    conditions: water_temp >= 24
    actions: aquarium_heater.power := off
  ```
- **graph / s12_c1** (physical) — ✅ after 1 attempt(s): `add_action` on R2
  ```
  - R2: "When carbon monoxide is detected in the garage, turn on the exhaust fan and open the garage door."
    trigger: co_garage == True
    conditions: none
    actions: fan_garage.power := on; garage_door.position := open
  + R2: "When carbon monoxide is detected in the garage, turn on the exhaust fan and open the garage door."
    trigger: co_garage == True
    conditions: none
    actions: fan_garage.power := on; garage_door.position := open; breaker_garage.power := on
  ```
- **graph / s13_c1** (semantic) — ✅ after 2 attempt(s): `add_condition` on R2
  ```
  - R2: "When motion is detected in the kitchen while the home is in away mode, sound the alarm."
    trigger: motion_kitchen == True
    conditions: home_mode == away
    actions: alarm.siren := on
  + R2: "When motion is detected in the kitchen while the home is in away mode, sound the alarm."
    trigger: motion_kitchen == True
    conditions: home_mode == away; feeder.dispensing == off
    actions: alarm.siren := on
  ```
- **graph / s14_c1** (physical) — ✅ after 1 attempt(s): `add_condition` on R1
  ```
  - R1: "At 23:30 turn off the bedside plug (phone charger) to save energy."
    trigger: time == 23:30
    conditions: none
    actions: plug_bedside.power := off
  + R1: "At 23:30 turn off the bedside plug (phone charger) to save energy."
    trigger: time == 23:30
    conditions: home_mode != night
    actions: plug_bedside.power := off
  ```
- **graph / s15_c2** (semantic) — ✅ after 1 attempt(s): `add_condition` on R4
  ```
  - R4: "When rain is detected, close the bedroom skylight."
    trigger: rain_sensor == True
    conditions: none
    actions: skylight.position := closed
  + R4: "When rain is detected, close the bedroom skylight."
    trigger: rain_sensor == True
    conditions: sprinkler.watering == off
    actions: skylight.position := closed
  ```
- **graph / s16_c2** (physical) — ✅ after 1 attempt(s): `add_action` on R3
  ```
  - R3: "When the closet is warmer than 35 C, turn on the cooling fan."
    trigger: temp_closet > 35
    conditions: none
    actions: fan_closet.power := on
  + R3: "When the closet is warmer than 35 C, turn on the cooling fan."
    trigger: temp_closet > 35
    conditions: none
    actions: fan_closet.power := on; strip_closet.power := on
  ```
- **graph / s18_c4** (logical) — ✅ after 1 attempt(s): `change_trigger` on R6
  ```
  - R6: "At 09:00 open the office shades to use daylight."
    trigger: time == 09:00
    conditions: none
    actions: shades_office.position := open
  + R6: "At 09:00 open the office shades to use daylight."
    trigger: time == 08:00
    conditions: none
    actions: shades_office.position := open
  ```
- **graph / s19_c1** (semantic) — ✅ after 1 attempt(s): `add_condition` on R1
  ```
  - R1: "When the nursery sound level exceeds 60 dB (baby crying), turn on the nursery lamp at low brightness."
    trigger: noise_nursery > 60
    conditions: none
    actions: nursery_lamp.power := on
  + R1: "When the nursery sound level exceeds 60 dB (baby crying), turn on the nursery lamp at low brightness."
    trigger: noise_nursery > 60
    conditions: white_noise.playing == off
    actions: nursery_lamp.power := on
  ```
- **graph / s20_c6** (logical) — ✅ after 1 attempt(s): `add_condition` on R6
  ```
  - R6: "At 22:00 turn off the greenhouse heater."
    trigger: time == 22:00
    conditions: none
    actions: gh_heater.power := off
  + R6: "At 22:00 turn off the greenhouse heater."
    trigger: time == 22:00
    conditions: frost_warning == False
    actions: gh_heater.power := off
  ```
- **text / s01_c1** (physical) — ✅ after 1 attempt(s): `add_condition` on R1
  ```
  - R1: "At 23:00 turn off the hallway smart plug to save energy."
    trigger: time == 23:00
    conditions: none
    actions: plug_hall.power := off
  + R1: "At 23:00 turn off the hallway smart plug to save energy."
    trigger: time == 23:00
    conditions: home_mode != away
    actions: plug_hall.power := off
  ```
- **text / s01_c2** (logical) — ✅ after 1 attempt(s): `add_condition` on R4
  ```
  - R4: "When motion is detected in the hallway between 22:00 and 06:00, unlock the front door so guests can leave."
    trigger: motion_hall == True
    conditions: time in [22:00, 06:00]
    actions: lock_front.lock := unlocked
  + R4: "When motion is detected in the hallway between 22:00 and 06:00, unlock the front door so guests can leave."
    trigger: motion_hall == True
    conditions: time in [22:00, 06:00]; home_mode != night
    actions: lock_front.lock := unlocked
  ```
- **text / s02_c1** (semantic) — ✅ after 1 attempt(s): `add_action` on R2
  ```
  - R2: "When the living room temperature rises above 26 C, turn on the ventilation fan and open the window."
    trigger: temp_living > 26
    conditions: none
    actions: vent_living.power := on; window_living.position := open
  + R2: "When the living room temperature rises above 26 C, turn on the ventilation fan and open the window."
    trigger: temp_living > 26
    conditions: none
    actions: vent_living.power := on; window_living.position := open; heater_living.power := off
  ```
- **text / s03_c1** (semantic) — ✅ after 1 attempt(s): `add_condition` on R2
  ```
  - R2: "When motion is detected in the living room, unlock the entrance door (someone is home)."
    trigger: motion_living == True
    conditions: none
    actions: lock_entrance.lock := unlocked
  + R2: "When motion is detected in the living room, unlock the entrance door (someone is home)."
    trigger: motion_living == True
    conditions: home_mode != away
    actions: lock_entrance.lock := unlocked
  ```
- **text / s04_c1** (logical) — ✅ after 1 attempt(s): `add_condition` on R2
  ```
  - R2: "When the home switches to away mode, lock the apartment door."
    trigger: home_mode == away
    conditions: none
    actions: lock_door.lock := locked
  + R2: "When the home switches to away mode, lock the apartment door."
    trigger: home_mode == away
    conditions: smoke_kitchen == False
    actions: lock_door.lock := locked
  ```
- **text / s05_c1** (physical) — ✅ after 1 attempt(s): `add_condition` on R1
  ```
  - R1: "At 00:30 turn off the office plug (standby power saving)."
    trigger: time == 00:30
    conditions: none
    actions: plug_office.power := off
  + R1: "At 00:30 turn off the office plug (standby power saving)."
    trigger: time == 00:30
    conditions: home_mode != night
    actions: plug_office.power := off
  ```
- **text / s06_c4** (logical) — ✅ after 1 attempt(s): `add_condition` on R5
  ```
  - R5: "When the home switches to night mode, turn off the aquarium heater to keep the room quiet."
    trigger: home_mode == night
    conditions: none
    actions: aquarium_heater.power := off
  + R5: "When the home switches to night mode, turn off the aquarium heater to keep the room quiet."
    trigger: home_mode == night
    conditions: water_temp >= 24
    actions: aquarium_heater.power := off
  ```
- **text / s12_c1** (physical) — ✅ after 1 attempt(s): `add_action` on R2
  ```
  - R2: "When carbon monoxide is detected in the garage, turn on the exhaust fan and open the garage door."
    trigger: co_garage == True
    conditions: none
    actions: fan_garage.power := on; garage_door.position := open
  + R2: "When carbon monoxide is detected in the garage, turn on the exhaust fan and open the garage door."
    trigger: co_garage == True
    conditions: none
    actions: fan_garage.power := on; garage_door.position := open; breaker_garage.power := on
  ```
- **text / s13_c1** (semantic) — ✅ after 1 attempt(s): `add_condition` on R2
  ```
  - R2: "When motion is detected in the kitchen while the home is in away mode, sound the alarm."
    trigger: motion_kitchen == True
    conditions: home_mode == away
    actions: alarm.siren := on
  + R2: "When motion is detected in the kitchen while the home is in away mode, sound the alarm."
    trigger: motion_kitchen == True
    conditions: home_mode == away; time in [12:30, 11:59]
    actions: alarm.siren := on
  ```
- **text / s14_c1** (physical) — ✅ after 2 attempt(s): `add_condition` on R1
  ```
  - R1: "At 23:30 turn off the bedside plug (phone charger) to save energy."
    trigger: time == 23:30
    conditions: none
    actions: plug_bedside.power := off
  + R1: "At 23:30 turn off the bedside plug (phone charger) to save energy."
    trigger: time == 23:30
    conditions: home_mode != night
    actions: plug_bedside.power := off
  ```
- **text / s15_c2** (semantic) — ✅ after 1 attempt(s): `add_condition` on R4
  ```
  - R4: "When rain is detected, close the bedroom skylight."
    trigger: rain_sensor == True
    conditions: none
    actions: skylight.position := closed
  + R4: "When rain is detected, close the bedroom skylight."
    trigger: rain_sensor == True
    conditions: sprinkler.watering == off
    actions: skylight.position := closed
  ```
- **text / s16_c2** (physical) — ✅ after 1 attempt(s): `add_action` on R3
  ```
  - R3: "When the closet is warmer than 35 C, turn on the cooling fan."
    trigger: temp_closet > 35
    conditions: none
    actions: fan_closet.power := on
  + R3: "When the closet is warmer than 35 C, turn on the cooling fan."
    trigger: temp_closet > 35
    conditions: none
    actions: fan_closet.power := on; strip_closet.power := on
  ```
- **text / s18_c4** (logical) — ✅ after 1 attempt(s): `change_trigger` on R6
  ```
  - R6: "At 09:00 open the office shades to use daylight."
    trigger: time == 09:00
    conditions: none
    actions: shades_office.position := open
  + R6: "At 09:00 open the office shades to use daylight."
    trigger: time == 07:00
    conditions: none
    actions: shades_office.position := open
  ```
- **text / s19_c1** (semantic) — ✅ after 1 attempt(s): `add_condition` on R1
  ```
  - R1: "When the nursery sound level exceeds 60 dB (baby crying), turn on the nursery lamp at low brightness."
    trigger: noise_nursery > 60
    conditions: none
    actions: nursery_lamp.power := on
  + R1: "When the nursery sound level exceeds 60 dB (baby crying), turn on the nursery lamp at low brightness."
    trigger: noise_nursery > 60
    conditions: white_noise.playing == off
    actions: nursery_lamp.power := on
  ```
- **text / s20_c6** (logical) — ✅ after 1 attempt(s): `add_condition` on R6
  ```
  - R6: "At 22:00 turn off the greenhouse heater."
    trigger: time == 22:00
    conditions: none
    actions: gh_heater.power := off
  + R6: "At 22:00 turn off the greenhouse heater."
    trigger: time == 22:00
    conditions: frost_warning == False
    actions: gh_heater.power := off
  ```
- **text_deps / s01_c1** (physical) — ✅ after 1 attempt(s): `add_condition` on R1
  ```
  - R1: "At 23:00 turn off the hallway smart plug to save energy."
    trigger: time == 23:00
    conditions: none
    actions: plug_hall.power := off
  + R1: "At 23:00 turn off the hallway smart plug to save energy."
    trigger: time == 23:00
    conditions: home_mode != away
    actions: plug_hall.power := off
  ```
- **text_deps / s01_c2** (logical) — ✅ after 1 attempt(s): `add_condition` on R4
  ```
  - R4: "When motion is detected in the hallway between 22:00 and 06:00, unlock the front door so guests can leave."
    trigger: motion_hall == True
    conditions: time in [22:00, 06:00]
    actions: lock_front.lock := unlocked
  + R4: "When motion is detected in the hallway between 22:00 and 06:00, unlock the front door so guests can leave."
    trigger: motion_hall == True
    conditions: time in [22:00, 06:00]; home_mode != night
    actions: lock_front.lock := unlocked
  ```
- **text_deps / s02_c1** (semantic) — ✅ after 1 attempt(s): `add_action` on R2
  ```
  - R2: "When the living room temperature rises above 26 C, turn on the ventilation fan and open the window."
    trigger: temp_living > 26
    conditions: none
    actions: vent_living.power := on; window_living.position := open
  + R2: "When the living room temperature rises above 26 C, turn on the ventilation fan and open the window."
    trigger: temp_living > 26
    conditions: none
    actions: vent_living.power := on; window_living.position := open; heater_living.power := off
  ```
- **text_deps / s03_c1** (semantic) — ✅ after 1 attempt(s): `add_condition` on R2
  ```
  - R2: "When motion is detected in the living room, unlock the entrance door (someone is home)."
    trigger: motion_living == True
    conditions: none
    actions: lock_entrance.lock := unlocked
  + R2: "When motion is detected in the living room, unlock the entrance door (someone is home)."
    trigger: motion_living == True
    conditions: vacuum.mode != cleaning
    actions: lock_entrance.lock := unlocked
  ```
- **text_deps / s04_c1** (logical) — ✅ after 1 attempt(s): `add_condition` on R2
  ```
  - R2: "When the home switches to away mode, lock the apartment door."
    trigger: home_mode == away
    conditions: none
    actions: lock_door.lock := locked
  + R2: "When the home switches to away mode, lock the apartment door."
    trigger: home_mode == away
    conditions: smoke_kitchen == False
    actions: lock_door.lock := locked
  ```
- **text_deps / s05_c1** (physical) — ✅ after 1 attempt(s): `add_condition` on R1
  ```
  - R1: "At 00:30 turn off the office plug (standby power saving)."
    trigger: time == 00:30
    conditions: none
    actions: plug_office.power := off
  + R1: "At 00:30 turn off the office plug (standby power saving)."
    trigger: time == 00:30
    conditions: home_mode == home
    actions: plug_office.power := off
  ```
- **text_deps / s06_c4** (logical) — ✅ after 1 attempt(s): `add_condition` on R5
  ```
  - R5: "When the home switches to night mode, turn off the aquarium heater to keep the room quiet."
    trigger: home_mode == night
    conditions: none
    actions: aquarium_heater.power := off
  + R5: "When the home switches to night mode, turn off the aquarium heater to keep the room quiet."
    trigger: home_mode == night
    conditions: water_temp >= 24
    actions: aquarium_heater.power := off
  ```
- **text_deps / s12_c1** (physical) — ✅ after 1 attempt(s): `add_action` on R2
  ```
  - R2: "When carbon monoxide is detected in the garage, turn on the exhaust fan and open the garage door."
    trigger: co_garage == True
    conditions: none
    actions: fan_garage.power := on; garage_door.position := open
  + R2: "When carbon monoxide is detected in the garage, turn on the exhaust fan and open the garage door."
    trigger: co_garage == True
    conditions: none
    actions: fan_garage.power := on; garage_door.position := open; breaker_garage.power := on
  ```
- **text_deps / s13_c1** (semantic) — ✅ after 1 attempt(s): `add_condition` on R2
  ```
  - R2: "When motion is detected in the kitchen while the home is in away mode, sound the alarm."
    trigger: motion_kitchen == True
    conditions: home_mode == away
    actions: alarm.siren := on
  + R2: "When motion is detected in the kitchen while the home is in away mode, sound the alarm."
    trigger: motion_kitchen == True
    conditions: home_mode == away; feeder.dispensing == off
    actions: alarm.siren := on
  ```
- **text_deps / s14_c1** (physical) — ✅ after 1 attempt(s): `add_condition` on R1
  ```
  - R1: "At 23:30 turn off the bedside plug (phone charger) to save energy."
    trigger: time == 23:30
    conditions: none
    actions: plug_bedside.power := off
  + R1: "At 23:30 turn off the bedside plug (phone charger) to save energy."
    trigger: time == 23:30
    conditions: home_mode != night
    actions: plug_bedside.power := off
  ```
- **text_deps / s15_c2** (semantic) — ✅ after 1 attempt(s): `add_condition` on R4
  ```
  - R4: "When rain is detected, close the bedroom skylight."
    trigger: rain_sensor == True
    conditions: none
    actions: skylight.position := closed
  + R4: "When rain is detected, close the bedroom skylight."
    trigger: rain_sensor == True
    conditions: sprinkler.watering == off
    actions: skylight.position := closed
  ```
- **text_deps / s16_c2** (physical) — ✅ after 1 attempt(s): `add_action` on R3
  ```
  - R3: "When the closet is warmer than 35 C, turn on the cooling fan."
    trigger: temp_closet > 35
    conditions: none
    actions: fan_closet.power := on
  + R3: "When the closet is warmer than 35 C, turn on the cooling fan."
    trigger: temp_closet > 35
    conditions: none
    actions: fan_closet.power := on; strip_closet.power := on
  ```
- **text_deps / s18_c4** (logical) — ✅ after 2 attempt(s): `change_trigger` on R6
  ```
  - R6: "At 09:00 open the office shades to use daylight."
    trigger: time == 09:00
    conditions: none
    actions: shades_office.position := open
  + R6: "At 09:00 open the office shades to use daylight."
    trigger: time == 07:00
    conditions: none
    actions: shades_office.position := open
  ```
- **text_deps / s19_c1** (semantic) — ✅ after 1 attempt(s): `add_condition` on R1
  ```
  - R1: "When the nursery sound level exceeds 60 dB (baby crying), turn on the nursery lamp at low brightness."
    trigger: noise_nursery > 60
    conditions: none
    actions: nursery_lamp.power := on
  + R1: "When the nursery sound level exceeds 60 dB (baby crying), turn on the nursery lamp at low brightness."
    trigger: noise_nursery > 60
    conditions: white_noise.playing == off
    actions: nursery_lamp.power := on
  ```
- **text_deps / s20_c6** (logical) — ✅ after 1 attempt(s): `add_condition` on R6
  ```
  - R6: "At 22:00 turn off the greenhouse heater."
    trigger: time == 22:00
    conditions: none
    actions: gh_heater.power := off
  + R6: "At 22:00 turn off the greenhouse heater."
    trigger: time == 22:00
    conditions: frost_warning == False
    actions: gh_heater.power := off
  ```
