# TODO

## Open questions for Nick

(my_frame_segment.stl orientation answered 2026-07-21: same frame as
segment.stl; the viewer overlay expects that and warns until the re-export
lands)

- 2026-07-22 gearmotor: the drive plate's N20-worm envelope (46×12.6×10.2,
  Ø3 D-shaft, shaft 9 mm from the nose end) is catalog-typical, not measured.
  Which unit are you buying? Re-run scripts/gearmotor_stl.py with measured
  dims before printing drive_plate.stl.
- 2026-07-22 bracket interface: the plate hangs on TWO #10-24 pan heads,
  56 mm apart (y=±28), heads ~4 mm proud, in the plane 16.5 mm behind the
  frame's flat bottom (z=−36.5 scene). OK to freeze this as the bracket
  contract, or do you want a different fastener/spacing?
- 2026-07-22 viewer: add the drive module (plate/clamp/motor/pinion) to
  viewer_export.py + docs/viewer.html as a preset? Left out to keep the PR
  additive; the fitcheck STL covers it meanwhile.
(2026-07-26 drive-axis fork answered same day: crossed radial shaft
shipped as Rev B.5 — generation owns conjugacy, the small pinion clears
the wafer field from the front.)

- 2026-07-27 22PG-2430BL 720:1 envelope: bracket_stl.py carries
  CATALOG-TYPICAL dims (body Ø24, nose Ø22×20, length 65, Ø4 D-shaft —
  the RobotShop datasheet PDF is CDN-blocked from here; speed ~16 rpm
  no-load is interpolated from the 19:1/630 rpm and 1370:1/8 rpm
  siblings). Measure the purchased unit (body Ø + length, nose Ø +
  length, shaft Ø + flat, mount holes) and re-run bracket_stl.py before
  printing the shell. Also: it's a 24 V-class motor with an integrated
  driver — what's the supply plan (24 V brick + PWM pot, or a
  microcontroller)? USB 5 V won't run it.
  (2026-08-09: likely OBE — Nick is now planning an N20; pinion bore is
  N20 3 mm D-flat in every mode as of this date.)

- 2026-08-09 N20 direct-slide drive: which N20 exactly (gear ratio +
  voltage, e.g. "6V 298:1 100rpm")? The no-bearing feasibility math
  assumed a 6V 298:1-class unit (stall 3–4 kg·cm, ≤2 kg·cm gearbox
  limit); the answer flips from "comfortable" to "marginal" if it's a
  low-ratio (fast) wind. Also: OK to put UHMW/PTFE tape on the slide
  pads, or must it be bare printed plastic?
  (2026-08-12 partially answered: 6 VDC, 15 rpm, USB power — a high-ratio
  wind, torque-comfortable. Still open: the slide-pad tape question, and
  the N20 body/shaft envelope measurements for the motor shell.)

- 2026-08-12 fasteners: M5 flatheads bought + M5 square nuts assumed on
  hand, but every printed part carries captive HEX pockets (8 AF) and no
  countersinks. Redesign bracket pockets for square nuts + countersunk
  heads, or stick with hex nuts and button/pan heads? Relief values for
  square nuts are unverified either way.

- 2026-08-12 keyhole relocation: move the keyhole down so the hole bottom
  sits just above the gear teeth, then hollow the freed standoff in an
  abstract pattern along the extrusion (DESIGN_LOG.md). Implement in
  segment_stl.py keyhole_z() when ready — say go.
