# TODO

## Open questions for Nick

(2026-08-13 legacy-vs-mine answered 2026-08-14: "Archive and grow
mine_stl.py into the one pipeline" — done: scripts/legacy/ holds the old
generators, CI runs mine_stl only, PRINTING.md re-pointed, sliced
numbers in. Same day: straight-to-master is the blessed flow here.)

- 2026-08-13 assumed gear numbers in mine_stl.py: PA 25° / backlash
  0.15 (FS defaults). If your OnShape feature used different values,
  say so and I'll re-pin.
(2026-08-14 viewer rebuild DONE 2026-08-15: mine_stl --viewer exports
the canonical scene, viewer.html/js rebuilt, hero.js showreel ported to
the architecture — Playwright-verified, zero console errors.)

(2026-08-15 calc legacy-preview item DONE 2026-08-16: calc.js rebuilt
around the canonical architecture — slider storm verified, canonical
reset lands on the sliced 51.6 g, cadCmd emits mine_stl.py flags.)

- 2026-08-16 motor dock + saddle still aren't in the viewer scene —
  need your assembly poses (or re-export them positioned relative to
  the ring) to place them.
- 2026-08-14 bonding workflow for the new architecture: the tower-top
  pad is small and the legacy tape jig doesn't fit this design — is
  hand placement on the pad accurate enough, or does the one pipeline
  grow a new drop-jig for the tower land?

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

(2026-08-20 §2 RPM target ANSWERED same day: "1 RPM like a clock". The
24T-pinion route collides with the wafer field — 158.5 mm³, ceiling 17T
— so the calibration is 12T + a 30 rpm 6 V N20 replacement motor →
exactly 1.000 rpm. Still open below: confirming that motor.)

- 2026-08-20 replacement motor: exact 1 rpm wants a **30 rpm 6 V N20**
  (standard wind) with the 12T pinion. Confirm that's the purchase (and
  its body/shaft envelope for the dock) — any other speed shifts the
  ring by mot_rpm/30 rpm.
- 2026-08-20 (08-19 review §3) rail: I read "outboard" as AXIAL (away
  from the wall — the tilt-drift/CG rationale only works axially) and
  shipped a clocked-guess rib inward of the bore, running face r 316,
  z 4..9, top flush with the band front face, 45° chamfer under. Confirm
  against your OnShape part (or send dims) — the static bracket contact
  and §7's 30° angle depend on it.
- 2026-08-20 (08-19 review §4) "end features" kept while hollowing:
  transcription ambiguous — I kept the joint tab/pocket zones (3° each
  end) plus the tower arc solid. Right features? Should the bays also
  run under the tower?
- 2026-08-20 (08-19 review §5) rail/joint misalignment: current revision
  or only the old one? Cut a test piece before changing anything.
- 2026-08-20 (08-19 review §7) bracket angle "call it thirty degrees" —
  working number, confirm against the rail geometry.
- 2026-08-20 canonical re-export: stl/mine/ segment + pinion predate the
  revision (compare IoU 0.63 / 0.20 by design) — re-export from OnShape
  once the full-section/half-count pass lands there.

(2026-08-12 keyhole relocation DONE same day: bore bottom now gear_F +
0.3 above the flat bottom, riser hollow pattern shipped as pat_* params
in segment_stl.py, all gates green — see DESIGN_LOG.md. calc.js retuned
same evening with the pattern mirrored + sliced truth: bays ADD 3.6 g
at 10% infill (skin beats infill), docs carry 72.8 g / 1.81 kg. Still
open: the pattern LOOK is a default awaiting Nick's taste pass — knobs
are pat_n/w/d/tilt/wall/end/gap.)
