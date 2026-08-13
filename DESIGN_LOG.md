# Design log

Bench notes tracking the wafer-halo design over time — print results,
measurements, decisions, and assumptions clocked for later verification.
Newest entry first. (Started 2026-08-12 at Nick's request; CLAUDE.md stays
the machine-facing spec, this file is the human trail.)

## 2026-08-12 — First coupon batch on the H2S

### What worked

- **Saddle-slide static-friction bearing: it's going to work.** Slides
  easily, and because the groove prints along the same grain as the ring
  arc, the surface feel is excellent. The wheel-less bottom rest is
  validated in principle.
- **Motor mounting looks great** — no problems expected. Still need to
  make sure the design includes drywall-anchor-friendly holes and/or
  through-bolting for a stud (stud preferred when available).
- **Dovetails not yet tested**, but the 0.2 mm relief being used on mating
  features is looking good so far.
- **Mounts feel really small** — hoping they hold. Watch this at assembly.

### Pinion: measured vs printed

- Motor shaft (actual): **3.0 mm max diameter, 0.5 mm recessed flat**.
- Printed pinion bore measured **2.25 mm max, 0.25 mm flat** — well under
  the 3.2 / 0.5 nominal; FDM small-bore undersize at these settings.
- Drilled the bore out to 1/8" (3.175 mm); the flat is gone and the shaft
  **barely grips → epoxy retention is the plan**. The flat as printed was
  too imprecise to trust anyway.
- Takeaway: **print the pinion as its own job at super-fine settings**
  (~1 h standalone) instead of dragging every other part's print time up.
  Candidate tooling change: a fine-profile option in `scripts/slice.py`
  for small precision parts.

### Motor locked in

- **6 VDC N20, 15 rpm, USB-powered.** Expect it to be torquey as hell at
  this ratio — takeoff behavior will be interesting to watch.
- Through the face drive (288/13 ≈ 22.2:1) that's ~0.68 rpm at the ring,
  one rev in ~90 s.
- This answers the open TODO question on the N20 spec. The bracket motor
  shell is still 22PG-shaped (24 V unit, retired) — needs an N20 rework
  before printing a shell.

### Change shipped today: capped tip-side hub on the pinion

`scripts/onshape/face_gear.fs` — the pinion now grows a **second hub at
the end opposite the motor**, same length and radius as the motor-side hub
(one parameter drives both). The bore stops **1 mm short inside the cap**,
so the far end is sealed:

- spaces the gear off the rail behind it, protecting the back;
- gives shaft epoxy a pocket to pool in against a closed end instead of
  squeezing out the front onto the mechanics.

> **CLOCKED ASSUMPTION (verify at assembly):** the capped hub actually
> helps the epoxy pool, seal, and bond better. Check squeeze-out, fill,
> and grip on the first epoxied pinion before trusting it.

### Epoxy application plan (keep it off the mechanics)

- Dry-fit first and check clocking/mesh; only then glue.
- Degrease the shaft with IPA, scuff it lightly; a drilled 1/8" bore
  needs no prep beyond dust-out.
- Thin coat on the **shaft only**, middle of the engagement — nothing at
  the bore mouth, nothing on the 1–2 mm of shaft nearest the gearbox face
  (protects the motor bearing; the motor-side hub is the shield).
- Insert with a slow twist to spread, wipe squeeze-out immediately with an
  IPA swab.
- Cure **motor-up, cap-down** so gravity pulls excess into the sealed cap
  pocket, away from the bearing and teeth.
- **Set time is not cure time** (2026-08-12, caught Nick off guard): the
  "5-minute" / "30-minute" on the label is working/fixture time — the
  joint is tack-hard but at ~20-30% strength. Full chemical cure is
  ~24 h for most epoxies, longer in a cold room. This joint takes the
  N20's stall torque at takeoff (~0.2-0.3 N·m through a Ø3.2 bond), so
  run it only after full cure: glue in the evening, spin in the morning.
- 5-minute epoxy is fine here; a retaining compound (Loctite 603-class)
  is the metal-shaft alternative but epoxy is right on printed plastic.

### FeatureScript scope locked: pinion + rack only

No motor in the FeatureScript — it generates exactly two bodies, the
rack-toothed arc and the pinion. The Motor Envelope second feature stays
dead (added `b4a21e2`, reverted `0bfc53d`); if it lingers in the OnShape
doc it's a stale paste, delete it there. Motor housing design happens
outside the FS.

### Keyhole / standoff idea (not yet implemented)

Move the keyhole **down so the bottom of the hole sits just above the gear
teeth**. That frees the wafer standoff above it to be **hollowed out in an
abstract pattern along the extrusion** — cosmetic mass removal. Needs the
`keyhole_z()` derivation in `segment_stl.py` revisited (it currently
derives the axis from the bore radius above the slab top).

### Fasteners and cabling (open)

- Bought **M5 flatheads**; assuming M5 **square nuts** are at the office.
  Probably need relief added for both — **unverified**. Note: current
  printed parts carry captive **hex** pockets (8 AF) and no countersinks,
  so flathead + square nut means a pocket/countersink change in
  `bracket_stl.py`, not just a value tweak.
- Cable routing needs an unobtrusive answer — likely **flat USB-C
  cables** run along/behind the mounts.
