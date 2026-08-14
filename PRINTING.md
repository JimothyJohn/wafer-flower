# H2S print settings — per component

Canonical parts are **Nick's OnShape exports in `stl/mine/`** (the
parametric RE lives in `scripts/mine_stl.py`; legacy parts are archived
under `scripts/legacy/` and their settings dropped from this file).

One profile does 90 % of this system: **0.20mm Standard @BBL H2S · Generic
PLA · 10 % infill · 6 top shells · Textured PEI · no supports** — that's
`scripts/slice.py` with no flags. The **pinion is the only precision
part**; everything else is fit-by-design.

Heads-up: the `stl/mine/` exports sit in **assembly pose** (the segment
slices fine; the small parts sit off-bed / on edge). Re-orient in the
slicer: pinion bore-vertical, motor-mount plate flat, band flat side down.

| Component | STL | Qty | Profile | Infill | Sliced (PLA @10 %) | Notes |
|---|---|---|---|---|---|---|
| Segment | `stl/mine/Segment - segment.stl` | 9 | 0.20mm Standard | 10 % | **51.6 g · 1h38** | flat bottom down, prints as exported. Tab/pocket joint — print ONE, check the lap fit before ×9 |
| Pinion | `stl/mine/Segment - pinion.stl` | 1 | **0.08mm High Quality** | 100 % | **0.68 g · 19 m** | re-pose bore-vertical; print alone; see below |
| Motor mount plate | `stl/mine/MotorDoc - motorMount.stl` | 1 | 0.20mm Standard | 15 % | ~8 g (10.7 cm³, not sliced) | lay the 6 mm plate flat. M5 on the 25 mm grid |
| Motor band | `stl/mine/MotorDoc - mountingBand.stl` | 1 | 0.20mm Standard | 15 % | ~5 g (6.1 cm³, not sliced) | the N20 clamp strap |
| Static saddle | `stl/mine/BottomStaticBracket - staticBracket.stl` | 1 | 0.20mm Standard | 15 % | ~14 g (18.6 cm³, not sliced) | M5 on the 25 mm grid |

Full frame: 9 × 51.6 g ≈ 465 g of PLA, ~15 h of printing. Assembly with
wafers ≈ 1.62 kg on the wall.

## The pinion (the one part worth fussing over)

Measured reality from the first batch: small bores print badly undersize
at 0.20 mm layers (a Ø3.2 came out 2.25). Nick's part is a **plain Ø3.0
through bore, no D-flat — retention is glue** (gel CA is enough; see
DESIGN_LOG). To make the bore land snug instead of drilling:

- Print it **alone**, `0.08mm High Quality @BBL H2S`, 100 % infill,
  bore axis vertical.
- Set **X-Y hole compensation ≈ +0.2 mm** (Orca: Quality → Precision) —
  inflates holes only, teeth untouched.
- Dry-fit on the shaft before gluing; the 60:1 ratio means the joint
  sees the N20's full stall torque at takeoff, so full cure before power.

```
python scripts/slice.py <re-posed pinion>.stl --process "0.08mm High Quality @BBL H2S" --infill 100
```

## Knobs that matter (and the ones that don't)

- **X-Y hole compensation**: pinion bore only. Everything else carries
  its clearance in the CAD (0.2 mm mating relief, Nick's OnShape values).
- **Elephant-foot compensation**: keep the profile default (~0.15). The
  lap tabs mate on first-layer geometry — if a tab binds at the bottom
  only, raise this before touching the CAD.
- **Material**: PLA throughout — indoor wall art, finger-force loads.
- **Don't**: supports, rafts, glue stick, flow-tuning spirals. If a fit
  fails, it's one setting or one CAD value, not a calibration session.

## slice.py quick reference

```
python scripts/slice.py "stl/mine/Segment - segment.stl"        # one segment
python scripts/slice.py <stl> --infill 15                       # mounts
python scripts/slice.py <stl> --process "0.08mm High Quality @BBL H2S" --infill 100
```

Output lands in `gcode/` (`.gcode.3mf` is what the printer wants). The
printed-mass line in the log is the authority.
