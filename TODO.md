# TODO

## Open questions for Nick

(my_frame_segment.stl orientation answered 2026-07-21: same frame as
segment.stl; the viewer overlay expects that and warns until the re-export
lands)

(2026-07-22 items closed 2026-08-12 as OBE: the gearmotor N20-worm
envelope and #10-24 plate contract died with the parked spur drive and
the bracket rewrite; the viewer drive-module preset died with the drive
module. 2026-07-26 drive-axis fork answered same day: crossed radial
shaft shipped as Rev B.5. 2026-07-27 22PG envelope OBE: the motor is
now a 6 V 15 rpm N20 on USB — the 22PG-shaped shell in bracket_stl.py
is orphaned, superseded by the repo-vs-bench sync item below.)

- 2026-08-09 N20 direct-slide drive: which N20 exactly (gear ratio +
  voltage, e.g. "6V 298:1 100rpm")? The no-bearing feasibility math
  assumed a 6V 298:1-class unit (stall 3–4 kg·cm, ≤2 kg·cm gearbox
  limit); the answer flips from "comfortable" to "marginal" if it's a
  low-ratio (fast) wind. Also: OK to put UHMW/PTFE tape on the slide
  pads, or must it be bare printed plastic?
  (2026-08-12 partially answered: 6 VDC, 15 rpm, USB power — a high-ratio
  wind, torque-comfortable. Still open: the slide-pad tape question, and
  the N20 body/shaft envelope measurements for the motor shell.)

- 2026-08-12 repo-vs-bench sync: Nick's OnShape design already carries
  0.2 mm mating relief, an N20-shaped motor mount, M5 square-nut pockets
  (flathead screws), and his own pinion bore — all printed. The repo
  scripts (bracket_stl.py hex pockets + 22PG shell, coupon relief set,
  segment_stl bore) trail it. To sync, need Nick's values: square-nut
  pocket dims + relief (he hasn't verified relief yet), N20 body/shaft
  envelope, mount geometry. Until then repo bracket/coupon outputs are
  stale for printing.

(2026-08-12 keyhole relocation DONE same day: bore bottom now gear_F +
0.3 above the flat bottom, riser hollow pattern shipped as pat_* params
in segment_stl.py, all gates green — see DESIGN_LOG.md. Open follow-up:
retune docs/assets/calc.js's mass model, which over-reads ~7 % because
it doesn't know the pattern; and the pattern LOOK is a default awaiting
Nick's taste pass — knobs are pat_n/w/d/tilt/wall/end/gap.)
