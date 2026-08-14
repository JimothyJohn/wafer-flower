# H2S print settings — per component

One profile does 90 % of this system: **0.20mm Standard @BBL H2S · Generic
PLA · 10 % infill · 6 top shells · Textured PEI · no supports anywhere**
(that's `scripts/slice.py` with no flags — it flattens the Bambu profiles
itself, never hand Orca an unflattened JSON). Every part is designed
support-free: grooves and bays carry 45° roofs, the widest bridge is the
Ø10 pattern capsule. Infill barely matters here — sliced mass is
skin-dominated (measured: 10 % vs 45 % moves a segment ~15 g, walls and
top shells do the rest) — so resist the urge to crank it.

The **pinion is the only precision part**. Everything else is
fit-by-design with clearances already tuned via coupons.

| Component | STL | Qty | Profile | Infill | Orientation | Sliced | Notes |
|---|---|---|---|---|---|---|---|
| Segment | `stl/segment.stl` | 9 | 0.20mm Standard | 10 % | flat bottom down | 72.8 g · 2h30 | 6 top shells (slice.py default). Print ONE, pass T1/T4 (land flat ≤0.15), then commit to ×9 |
| Pinion | `stl/pinion.stl` | 1 | **0.08mm High Quality** | 100 % | bore vertical | ~1 h alone | The fussy one — see below |
| Jig fence, outboard | `stl/cure_jig_outboard.stl` | 1 | 0.20mm Standard | 10 % | as exported | 115.3 g · 3h25 | |
| Jig fence, inboard | `stl/cure_jig_inboard.stl` | 1 | 0.20mm Standard | 10 % | as exported | 47.8 g · 1h35 | |
| Jig pin | `stl/cure_jig_pin.stl` | 1 | 0.20mm Standard | 10 % | lying on its D-flat | 7.4 g · 20 m | 327 mm long — brim only if it curls |
| Top idler unit | `stl/bracket_top.stl` | 1 | 0.20mm Standard | 15 % | as exported | 48.4 g · 1h16 | Idlers are bought F625ZZ — nothing printed |
| Motor shell | `stl/bracket_shell.stl` | — | — | — | — | — | **DO NOT PRINT** — still 22PG-shaped, orphaned by the N20. Needs the rework first |
| Static saddle | `stl/bracket_bottom_static.stl` | 1 | 0.20mm Standard | 15 % | as exported | 79.0 g · 2h09 | |
| Printed M5/M6 screws + nuts | `stl/m5_*.stl`, `stl/m6_*.stl` | as needed | 0.20mm Standard | 100 % | threads vertical | ~2 g ea | M5 is the FDM floor — chase the first fit; M6 threads by hand |
| Coupon batch | `stl/coupons/*.stl` | 1 set | 0.20mm Standard | 10 % | as exported | ~43 g · 2h48 | Print BEFORE the ×9. Socket notches = clearance index, 1 = tightest |

`fitcheck_*.stl` files are view-only assemblies — never print them.

## The pinion (the one part worth fussing over)

Measured reality from the first batch: the Ø3.2 bore printed at **2.25 mm**
— FDM shrinks small holes badly at 0.20 mm layers. To nail it instead of
drilling:

- Print it **alone**, `0.08mm High Quality @BBL H2S`, 100 % infill,
  bore axis vertical (as exported).
- Set **X-Y hole compensation ≈ +0.2 mm** (Orca: Quality → Precision).
  This inflates holes only — outer tooth surfaces untouched.
- Verify on the coupon (`stl/coupons/pinion.stl`) before printing the
  final: shaft should slip in snug with the D-flat engaging.
- If the flat still prints mushy, drilling 1/8" + adhesive stays the
  fallback — but then the flat is gone and the glue carries all torque.

```
python scripts/slice.py stl/pinion.stl --process "0.08mm High Quality @BBL H2S" --infill 100
```

## Knobs that matter (and the ones that don't)

- **X-Y hole compensation**: only for the pinion bore. Leave it 0 for
  everything else — the keyhole (Ø6.5 vs Ø6.2 pin) and dovetails
  (0.25/side) already carry their clearance in the CAD.
- **Elephant-foot compensation**: keep the profile default (~0.15). The
  dovetails and grooves slide on first-layer geometry; if a dovetail
  coupon binds at the bottom only, raise this before touching the CAD.
- **Seam**: "Aligned", parked on the back/inner side for segments. Cosmetic
  only.
- **Material**: PLA for everything — indoor wall art, finger-force loads.
  PETG buys nothing here (the @45 % PETG segments were the old baseline).
- **Don't**: supports (nothing needs them), rafts, glue stick on textured
  PEI, flow/pressure-advance tuning sessions. If a fit fails, the fix is a
  coupon and one setting, not a calibration spiral.

## slice.py quick reference

```
python scripts/slice.py                          # segment + pinion, project defaults
python scripts/slice.py stl/segment.stl          # one part
python scripts/slice.py stl/coupons/*.stl        # the test batch
python scripts/slice.py <stl> --infill 15        # bracket parts
python scripts/slice.py <stl> --process "0.08mm High Quality @BBL H2S"
```

Output lands in `gcode/` (`.gcode.3mf` is what the printer's SD/Handy
wants). The printed mass in the log line is the authority — book values
in CLAUDE.md came from exactly this.
