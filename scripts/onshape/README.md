# OnShape FeatureScript port — Halo beveloid drive

`wafer_halo_beveloid.fs` gives OnShape native, procedural generation of the
gear at the segment edge (straight or spiral), in the style of Anthony Lu's
**Gear Lab** FeatureScript. Paste it into a Feature Studio (New tab →
Feature Studio), commit, and the two features appear in the Part Studio
toolbar under the custom-features flyout.

## The two features

| Feature | What it builds | How to use it |
|---|---|---|
| **Halo Beveloid Band** | One segment's 40° external tooth band: 45° cone big-at-wall, flush root at the band OD, joints mid-space. | Build at origin (wall face on XY, sector centred on +X), then boolean-union onto the segment body. `Full ring` gives all N sectors for assembly checks. |
| **Halo Crossed Pinion** | The Rev B.5 drive pinion: 10T 45° cone (Ø17→Ø41 tips), apex toward the halo centre, hub + Pololu D-bore on the big end. | Mate its axis **radial** — vertical at 12 o'clock, motor above, shaft down — small end at the reported ring radius, axis ~19 mm in front of the ring's wall plane. Ratio 10.8:1 → 1.00 rpm at 5 V. |

Both features default to the shipped Rev B.3 numbers (N=9, Ri=255, bw=30,
module 5.6 nominal → 5.384 flush, face 9.5, PA 20°, straight teeth). Spiral
is one slider — the sections get the same twist the Python twist-extrude
applies.

## Why not Gear Lab directly?

Gear Lab is excellent for its domain, but its bevel gears are **spherical
involutes for intersecting shafts**. The halo drive deliberately uses a
**parallel-axis beveloid pair** (conical involute): the ring's slice radius
falls 1 mm per mm of z while the pinion's rises, so the centre-radius sum is
constant across the face and the motor points straight out of the wall. A
radial-axis bevel pinion physically cannot fit this build — its swept disc
spans its full Ø along the wall normal, through the drywall behind or the
wafer field in front. Gear Lab also has no ring-sector output, no
flush-root module retune, and no joint-phase convention.

Gear Lab is still the right tool if you just want to eyeball a 45° bevel
pair on intersecting axes, or generate a plain spur.

## Fidelity vs the Python model

`scripts/segment_stl.py` **generates** the ring as the swept envelope of
its cutter (conjugate by construction, mesh sweep gated at ≤0.05 mm³). The
FS features build **analytic involute sections and loft** — identical at
the mid-face, a few hundredths off toward the faces. At this drive's
~mN·m loads that is cosmetic; keep backlash ≥ 0.4 mm on printed parts (the
repo ships 0.6). The Python gates remain the authority for anything that
prints — in particular the **gear_F ceiling** (face height must clear the
neighbour wafer's clearance plane; the gate computes 9.83 mm at the deep-bevel base (tmin=15)).

## Crib sheet at Rev B.3

- 108T ring (12/segment), flush module **5.384** (5.6 nominal)
- Front radii: root 284.0, pitch 290.7, tip 296.1; wall = front × 1.0327
- Face 9.5 mm, cone 45°, straight (spiral 0°)
- 10T crossed pinion: pitch rho 12 (FREE — not the rolling value; conjugacy
  is by generation), face 10, tips Ø17→Ø41, axis 19.1 mm off the wall plane
- Ratio 108/10 = **10.8:1** — 13 rpm × 5/6 V ÷ 10.8 = **1.00 rpm** at the ring
- Hub Ø16 × 6 mm on the big (motor) end, bore Ø3.2 with 0.4 D-flat
  (Pololu #1596 3 mm D-shaft)

`docs/onshape-variables.html` still carries the 46 copy-paste variable
expressions for the rest of the segment; these features replace only the
gear, which was the one part DXF import couldn't make parametric.
