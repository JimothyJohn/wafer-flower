# Design log

Bench notes tracking the wafer-halo design over time — print results,
measurements, decisions, and assumptions clocked for later verification.
Newest entry first. (Started 2026-08-12 at Nick's request; CLAUDE.md stays
the machine-facing spec, this file is the human trail.)

## 2026-08-14 — One pipeline (Nick: "archive and grow mine_stl.py")

The legacy generator suite — segment_stl's three drive modes, the tape
jig, the idler bracket, coupons, viewer export, STEP, manual, printed
hardware — moved to `scripts/legacy/` (README there; segment_stl stays
imported as a library for the gear machinery). `mine_stl.py` grew the
rest of the pipeline: wafers on the tower land, the 9-ring and full
assembly, and gates for every clearance (wafer vs own/neighbour
segments, wafer vs wafer, pinion static pose — all 0.00000; shingle air
gap > 6 mm at θ 3°). CI now runs syntax + mine_stl only.

Sliced truth for the new architecture (PLA @10 %): **segment 51.6 g /
1h38** (vs 72.8 legacy — the thin-wall tower earns its keep), frame
~465 g, assembly on the wall ~1.62 kg. **Pinion 0.68 g / 19 min** at
0.08 mm / 100 % as its own job. Small `stl/mine/` parts export in
assembly pose — re-orient in the slicer (PRINTING.md).

Also Nick's process call, recorded in CLAUDE.md: **straight-to-master
is the blessed flow for this repo** — art project, always iterating,
no PR ceremony.

## 2026-08-13 — Nick's architecture lands: stl/mine/ is canonical

Nick dropped his own OnShape builds into `stl/mine/` — segment, pinion,
motor dock (plate + strap band), static saddle — and retired the
repo-generated parts. Reverse-engineered (`scripts/mine_stl.py`):

- **Band Ri 320 → Ro 350** (was 255–285), inner slab 9 tall, **face
  teeth** on the outer annulus: 80/segment → **720-tooth ring,
  m 0.95833** — his OnShape build follows the FeatureScript Arc-Segment
  math to the digit (module from the annulus middle, joints mid-slot,
  pinion axis z = tip − m + rp = 10.79).
- **12T pinion, 60:1** → 0.25 rpm at the 15 rpm N20 (one rev / 4 min).
  Plain Ø3.0 through bore, **no D-flat** — glued retention is the design.
- **Tilt θ = 3°** (was 5), and it lives in the tower top: land plane
  z = 38.8 + y·tan 3°. The standoff is a **±7.5° twin-wall X-braced
  tower** with an arch — sculptural, hand-designed.
- **Lap-tab joints** (1.06° past the joint face) — no dovetails, no
  keyhole, no retention grooves. The whole legacy jig/bracket/coupon
  pipeline belongs to the previous architecture.
- Parametric RE: drive geometry exact (pinion IoU 0.956 vs his mesh,
  mesh sweep 0.00000), tower coarse (IoU 0.80, volume +4.9%). Gates in
  `mine_stl.py`; his meshes stay canonical (viewer overlay).
- Clocked assumptions: PA 25°, backlash 0.15 (FS defaults — consistent
  with the flanks, not directly measured).

Website repointed the same evening (Nick: "no one gives a shit about
the parameters on the first page… focus on the viewer and the artist"):
index is pure showreel + replicate/iterate cards, viewer leads, the
customize page is framed as "the sculpture as a program".

## 2026-08-13 — Pinion retention: epoxy is optional

Nick: "seems unnecessary… can't I just glue it?" Correct — at this
joint's loads (mN·m running, ~0.2–0.3 N·m worst-case stall), **thick/gel
CA (super glue) is plenty**: it bonds PLA about as well as anything
bonds PLA, and the ~100 mm² bore gives several × margin even at
derated CA strength. Best option is still mechanical: **reprint the
pinion with a true D-bore** (fine profile + hole compensation,
PRINTING.md) so the flat carries torque and glue only stops axial
walk-off — then a single drop of CA is genuinely all it needs.
**Do not** use anaerobic retaining compound / threadlocker (Loctite
603/242-class): anaerobics need metal on both sides and stay liquid
against plastic. Hot glue and foaming PU are also out (creep, mess).

## 2026-08-13 — Epoxy failure on the pinion/shaft joint

First epoxy attempt on the motor shaft + PLA pinion **never cured — just
gummy**. Gummy-forever is a chemistry failure, not adhesion: prime
suspects are off-ratio dispense (dual-plunger syringes short one side on
tiny dabs — purge a bead first) and under-mixing (a small dab needs a
real 45–60 s of folding). Also check hardener age and bench temperature.

**Diagnostic for the redo: keep the leftover mixed puddle on the card as
a control.** Puddle gummy too → ratio/mix/age. Puddle rock-hard, joint
gummy → contamination — on an N20 that means gearbox oil creeping down
the shaft; IPA-degrease immediately before gluing. Cleanup of the gum:
scrape while soft, IPA wipe — **no acetone near the PLA pinion**.

## 2026-08-12 — First coupon batch on the H2S

> **CORRECTION (same day, Nick):** the bench design was AHEAD of the repo
> when this printed. The 0.2 mm mating relief, the N20-shaped motor
> mount, the M5 square-nut pockets (+ flathead screws), and the pinion
> bore were **already incorporated in the design before the print** — in
> Nick's OnShape build, not the repo scripts. The "clash" flags further
> down compare against repo values (`bracket_stl.py` hex pockets, 22PG
> shell, coupon relief set) that simply trail the bench. Sync the repo
> scripts only from Nick's actual values; never treat the printed parts
> as wrong against repo defaults.

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

### Keyhole drop + riser hollow pattern — SHIPPED (same day)

`keyhole_z()` now puts the **bore bottom 0.3 above the gear teeth**
(bevel45: 9.80 vs 9.5 gear top; face: 6.80 vs 6.5; spur keeps legacy),
and the vacated inner face gets the **hollow pattern**: capsule pockets
20 mm deep into the inner face, Ø10, leaning 20° with the swirl, sized
per-window to the real ceilings (own land plane, neighbour clearance —
the leading-corner windows drop out on their own, 4 of 6 survive at
defaults). Blind bays, so genus stays 1; a solid pier stays at a=0 for
the jig prong and the keyhole. Segment 231 → 214 cm³ of solid volume.

> **Sliced truth (same day):** hollowing does NOT save mass at 10 %
> infill — the bays trade 16.9 cm³ of sparse infill for ~46 cm² of
> solid skin wall, and skins dominate: sliced mass **rises 69.2 →
> 72.8 g** (+10 min → 2h30). It's an aesthetic feature; keep it or
> kill it (`--pat_n 0`) on looks, not weight. Docs and calculator now
> carry the honest 72.8 g / 1.81 kg / 17.7 N numbers.

All knobs are `pat_*` CLI flags on `segment_stl.py` — count, width,
depth, lean, wall, joint margin, pier — so the "cool, abstract" part is
one command away from taste-tuning. Every downstream gate re-ran green:
segment (both drive modes), 14 jig checks (fences follow `keyhole_z()`
automatically), 12 coupon, 12 bracket, viewer `--verify`, STEP
round-trip. Known drift: the docs calculator's mass model doesn't know
the pattern yet (~7 % over-read).

### Fasteners and cabling (open)

- Bought **M5 flatheads**; assuming M5 **square nuts** are at the office.
  Probably need relief added for both — **unverified**. Note: current
  printed parts carry captive **hex** pockets (8 AF) and no countersinks,
  so flathead + square nut means a pocket/countersink change in
  `bracket_stl.py`, not just a value tweak.
- Cable routing needs an unobtrusive answer — likely **flat USB-C
  cables** run along/behind the mounts.
