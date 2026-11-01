"""One-off migration (2026-11): add `situation` / `undesired_outcome` to every
dev conflict case and mark hard (near-miss) clean cases. Kept for provenance."""

import json
import re
import sys
from pathlib import Path

OUT = {
 "s01_c1": ("Home is in away mode at or after 23:00, when R1 switches the hallway plug off.", "The hallway camera loses power and does not record the front door while nobody is home."),
 "s01_c2": ("Home is in night mode and the hallway motion sensor fires between 22:00 and 06:00.", "R4 unlocks the front door that R3 locked for the night; the door stays unlocked at night."),
 "s02_c1": ("R1 turns the living-room heater on at 18:00 and the room warms above 26 C.", "R2 opens the window and starts the fan while the heater is still heating: energy is wasted and the room is heated and vented at once."),
 "s02_c3": ("Living room above 26 C triggers R2; the open window then cools the room below 19 C.", "R4 switches the heater back on: a heat/vent loop that wastes energy."),
 "s02_c4": ("At 18:00 while the home is in away mode.", "R1 turns the living-room heater on and R5 turns it off at the same moment; the final state depends on execution order."),
 "s03_c1": ("The robot vacuum starts at 10:00 on a weekday while the occupants are out.", "The vacuum's movement triggers the living-room motion sensor and R2 unlocks the entrance door of an empty home."),
 "s03_c2": ("The vacuum runs at 10:00 while the home is in away mode.", "The vacuum triggers the living-room motion sensor and R3 sounds the alarm (false alarm)."),
 "s04_c1": ("Smoke is detected in the kitchen while (or just after) the home switches to away mode.", "R1 unlocks the door for evacuation and R2 locks it; the evacuation route may end up locked."),
 "s04_c2": ("A smoke event is in progress at 08:00.", "R4 turns the air handler back on after R1 shut it down, spreading smoke through the flat."),
 "s05_c1": ("Home is in night mode after 00:30, when R1 has turned the office plug off.", "The router loses power, so the garden camera cannot upload recordings to the cloud overnight."),
 "s05_c2": ("Home is in away mode after 00:30.", "The router is off, so doorbell notifications that R3 enabled are never delivered while nobody is home."),
 "s06_c1": ("Home switches to night mode while the aquarium water is (or becomes) colder than 24 C.", "The power strip cuts the aquarium heater (and pump), so R2 cannot keep the water warm; fish are exposed to cold water overnight."),
 "s06_c4": ("Home is in night mode and the water temperature falls below 24 C.", "R5 switches the aquarium heater off while R2 switches it on; the heater state flips and the water may stay cold."),
 "s07_c1": ("Home is in away mode (main valve closed) at 06:00.", "R2 starts watering but no water reaches the irrigation line; the garden is not watered during the holiday."),
 "s08_c1": ("Bright daylight above 800 lux in the living room.", "R1 closes the blinds, the room drops below 150 lux and R2 switches the ceiling lights on during the day; possible open/close oscillation."),
 "s08_c4": ("At 07:30 on a morning when the living room is already brighter than 800 lux.", "R3 opens the blinds and R1 closes them again; the blinds fight each other."),
 "s09_c1": ("From 20:00, once the humidifier has raised nursery humidity above 55 %.", "R2 starts the dehumidifier against the running humidifier; both run all night against each other."),
 "s09_c4": ("At 20:00 while nursery humidity is above 55 %.", "R2 turns the dehumidifier on and R5 turns it off at the same time."),
 "s10_c1": ("Night mode is active when the wake-up alarm rings.", "The bedroom bulb has no power (wall switch off), so R2's wake-up fade cannot run."),
 "s11_c1": ("Someone arrives home between 17:00 and 19:00, around 18:00.", "R1 sets 23 C and R2 sets 19 C on the same thermostat; the final setpoint depends on timing."),
 "s11_c2": ("The living room is warmer than 24 C so R3 starts cooling, and the AC drives it below 20 C.", "R4 switches the thermostat to heat while the AC is still cooling; heating and cooling fight each other."),
 "s12_c1": ("Home is in away mode (garage breaker off) and carbon monoxide is detected in the garage.", "R2 cannot start the exhaust fan because its circuit is off; the CO safety response is lost."),
 "s12_c2": ("CO is detected in the garage while the home switches to away mode.", "R2 opens the garage door to vent CO and R3 closes it."),
 "s12_c3": ("The car is parked in the garage and the home is then (or already) in away mode.", "The breaker cuts the charger circuit, so R4's charging stops and the car is not charged."),
 "s13_c1": ("At 12:00 while the home is in away mode.", "The feeder attracts the cat into the kitchen, its motion triggers R2 and the siren sounds (false alarm every noon)."),
 "s13_c4": ("Kitchen motion while the home is in home mode.", "R3 starts and R6 stops camera recording on the same motion event; the privacy intent of R6 is defeated or recording flickers."),
 "s14_c1": ("Night mode is active at 23:30.", "R1 turns off the bedside plug that actually powers the CPAP machine; a medical device stops during sleep."),
 "s14_c2": ("A fall is detected while the home is (or switches) into night mode.", "R3 unlocks the entrance for paramedics and R4 locks it; paramedics may be locked out."),
 "s15_c1": ("At 10:00 on a hot day: R2 opens the window and the living room rises above 27 C.", "R1 runs the AC while the window is open; energy is wasted cooling the outside."),
 "s15_c2": ("At 14:00 on a dry, sunny day.", "The sprinkler wets the rain sensor and R4 closes the skylight although it is not raining (false rain)."),
 "s15_c5": ("At 10:00 on a hot morning while the AC is cooling.", "R2 opens the window and R6 closes it again; the window state flips."),
 "s16_c1": ("Night mode is active at 01:00.", "The closet strip is off, so the NAS has no power and the nightly backup does not run."),
 "s16_c2": ("Night mode is active and the closet becomes warmer than 35 C (e.g. during a backup).", "The cooling fan is on the strip that R2 switched off, so R3 cannot cool the closet; equipment may overheat."),
 "s17_c1": ("The teenager's phone arrives home between 23:00 and 06:00.", "R1 unlocks the door and R2 immediately relocks it; the teenager is locked out or the lock oscillates."),
 "s18_c1": ("A cool day: R1 closes the shades at 09:00 and solar gain is lost.", "The office cools below 20 C and R2 starts the radiator; heating replaces free solar gain (energy waste)."),
 "s18_c4": ("At 09:00 every day.", "R1 closes and R6 opens the same shades at the same time; the final position depends on execution order."),
 "s19_c1": ("From 19:30, when the white-noise speaker plays in the nursery.", "The noise pushes the sound level above 60 dB; R1 treats it as crying and turns on the lamp, which may wake the baby."),
 "s19_c2": ("The TV is turned on after 20:00 and the soundbar plays.", "Soundbar noise carries into the nursery, exceeds 60 dB and R1 switches the nursery lamp on (false crying detection)."),
 "s20_c1": ("A frost warning: R1 heats the greenhouse above 18 C.", "R2 opens the roof vent during frost and releases the heat; heater and vent fight each other."),
 "s20_c2": ("A frost warning is active at or after 22:00.", "R3 cuts the outdoor plug that feeds the greenhouse heater; frost protection is lost overnight."),
 "s20_c5": ("Frost night: R1 heats, R2 vents above 18 C and R3 cuts the heater's plug at 22:00.", "Frost protection is lost (plug off) and heat is vented while it runs; plants are exposed to frost."),
 "s20_c6": ("A frost warning is active at 22:00.", "R1 keeps the greenhouse heater on while R6 switches it off; frost protection depends on execution order."),
}

HARD = {
 "s01_c4": "R1 cuts a plug at night, but that plug does not power the lock.",
 "s03_c3": "The vacuum does create motion, but in a different room than R4's sensor.",
 "s05_c3": "R4 also cuts a plug at 00:30, but it only powers the desk lamp.",
 "s05_c4": "R4 also cuts a plug at 00:30, but it is not on the doorbell's network path.",
 "s06_c2": "Another plug goes off at night mode, but it powers only the TV.",
 "s06_c3": "Opposite actions on the heater, but under non-overlapping thresholds (hysteresis).",
 "s07_c2": "Watering raises soil moisture and triggers R4, which is the intended feedback loop.",
 "s07_c3": "A valve closes when away, but it is a separate line from the irrigation supply.",
 "s08_c2": "Opposite actions on the blinds, but at non-overlapping times.",
 "s09_c2": "Opposite fan actions under non-overlapping humidity thresholds.",
 "s10_c2": "The corridor bulb is turned off and on, but by soft commands at different times.",
 "s11_c3": "Different setpoints on the same thermostat, but at different times of day.",
 "s14_c3": "A plug goes off at 23:30, but it powers the reading lamp, not the CPAP.",
 "s16_c3": "The backup heats the closet and triggers the fan; a designed feedback loop.",
 "s16_c4": "A plug goes off at night mode, but it powers the printer, not the NAS.",
 "s18_c2": "Opposite radiator actions under non-overlapping thresholds.",
 "s18_c3": "Two away-mode rules act on the desk heater, but both turn it off.",
 "s20_c3": "Grow lights switch on, but they are not modelled as heating the greenhouse.",
 "s20_c4": "Opposite vent actions under non-overlapping thresholds.",
 "s15_c3": "A window opens, but it does not affect the rain sensor.",
 "s13_c3": "The litter box cycles at noon, but it is not near a motion sensor used by R5.",
}


def q(s: str) -> str:
    return json.dumps(s)  # JSON string is valid YAML


def main(data_dir: str) -> None:
    for p in sorted(Path(data_dir).glob("*.yaml")):
        lines = p.read_text().splitlines(keepends=True)
        out, cur = [], None
        for ln in lines:
            m = re.match(r"\s*- id: (s\d+_c\d+)\s*$", ln)
            if m:
                cur = m.group(1)
            out.append(ln)
            if cur and re.match(r"\s+justification:", ln):
                ind = re.match(r"(\s+)", ln).group(1)
                if cur in OUT and "situation:" not in "".join(lines):
                    sit, outc = OUT[cur]
                    out.append(f"{ind}situation: {q(sit)}\n{ind}undesired_outcome: {q(outc)}\n")
                if cur in HARD and "hard:" not in "".join(lines):
                    out.append(f"{ind}situation: {q('Near miss: ' + HARD[cur])}\n{ind}hard: true\n")
                cur = None
        p.write_text("".join(out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/scenarios")
