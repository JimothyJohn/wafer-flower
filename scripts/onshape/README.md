# OnShape FeatureScript port — Halo beveloid drive

`wafer_halo_beveloid.fs` gives OnShape native, procedural generation of the
gear at the segment edge (straight or spiral), in the style of Anthony Lu's
**Gear Lab** FeatureScript. Paste it into a Feature Studio (New tab →
Feature Studio), commit, and the features appear in the Part Studio
toolbar under the custom-features flyout.

`gearlab.fs` (if present, untracked) is a checkout of Gear Lab's public
top-level wrapper for reference: its `export import` line pulls the whole
implementation from a private versioned Onshape module, which is why arc
support lives in our FeatureScript instead of a Gear Lab patch.

## The three features

| Feature | What it builds | How to use it |
|---|---|---|
| **Halo Beveloid Band** | One segment's 40° external tooth band: 45° cone big-at-wall, flush root at the band OD, joints mid-space. (The GENERATED crossed-beveloid tooth form — mates the Halo Crossed Pinion, NOT a Gear Lab bevel.) | Build at origin (wall face on XY, sector centred on +X), then boolean-union onto the segment body. `Full ring` gives all N sectors for assembly checks. |
| **Halo Crossed Pinion** | The Rev B.5 drive pinion: 20T 45° cone (Ø9.9→Ø25.3 tips), apex toward the halo centre, hub + D-bore on the big end. | Mate its axis **radial** — vertical at 12 o'clock, motor above, shaft down — small end at the reported ring radius, axis ~13.6 mm in front of the ring's wall plane. Ratio 5.4:1 → ~2 rpm, PWM-dialed. |
| **Halo Straight Bevel Arc** | A CLASSICAL spherical-involute straight bevel gear (intersecting shafts — the tooth system Gear Lab makes) cut to any arc: 40° default = 12 of 108 teeth, ends mid-space; 360° = full gear. Flanks are exact cones through the apex; end faces are true spheres about it. | Defaults are the halo pair (108/20, module 5.384, Σ 90°, α 20°, face 30). Optionally pick a plane/vertex as **Placement** (apex at its origin, axis along its normal, flip available); else it builds apex at the world origin, axis +Z. Make the pinion in Gear Lab with the settings the info banner prints (teeth, same module/PA, Bevel Angle = Σ − δ, tooth width in modules), mate the two apexes coincident at the shaft angle, and use **Adjust angle** to clock the teeth into mesh. Root fillet (× module) and involute steps are in the dialog; backlash stays on the pinion by repo convention. |

## Installing the custom feature in any project

1. Open (or create) an Onshape document to hold your FeatureScripts — a
   dedicated "My FeatureScripts" document is best, so every project can
   link to one place.
2. New tab → **Feature Studio**, paste ALL of `wafer_halo_beveloid.fs`,
   and let it save (fix-ups: the file targets FS/std 1803; accept
   Onshape's "update to latest version" offer if it nags).
3. Same document: the features appear immediately in that Part Studio's
   custom-feature flyout (the rightmost toolbar icon).
   Other documents: create a **Version** of the FeatureScript document
   first (Versions and history → Create version) — then in any Part
   Studio: custom-feature flyout → **Other documents** → search your
   FeatureScript document → pick the feature. Onshape pins the version;
   bump it from the same menu after edits.

Both features default to the shipped Rev B.3 numbers (N=9, Ri=255, bw=30,
module 5.6 nominal → 5.384 flush, face 9.5, PA 20°, straight teeth). Spiral
is one slider — the sections get the same twist the Python twist-extrude
applies.

## Why not Gear Lab directly?

Gear Lab is excellent for its domain, but its bevel gears are **spherical
involutes for intersecting shafts sized for true rolling** — and a
true-rolling 45°/45° pair only exists at 1:1. The halo pair runs 90° shafts
at 5.4:1 with both members on 45° cones, which no rolling-cone construction
allows; the flanks are conjugate because the Python model **generates**
them under the imposed motion, and the FS features rebuild those envelopes
analytically. The pinion can also be far smaller than the rolling size
(rho is free — that's what keeps the sculpture low-profile). Gear Lab also
has no ring-sector output, no flush-root module retune, and no joint-phase
convention.

Gear Lab is still the right tool if you just want to eyeball a 45° bevel
pair on intersecting axes, or generate a plain spur.

## Fidelity vs the Python model

`scripts/segment_stl.py` **generates** the ring as the swept envelope of
its cutter (conjugate by construction, mesh sweep gated at ≤0.05 mm³). The
FS features build **analytic involute sections and loft** — identical at
the mid-face, a few hundredths off toward the faces. At this drive's
~mN·m loads that is cosmetic; keep backlash ≥ 0.3 mm on printed parts (the
repo ships 0.3 — at the pinion's 0.8 mm section module, 0.6 would halve
the tooth). The Python gates remain the authority for anything that
prints — in particular the **gear_F ceiling** (face height must clear the
neighbour wafer's clearance plane; the gate computes 9.83 mm at the deep-bevel base (tmin=15)).

## Crib sheet at Rev B.5 (low-profile)

- 108T ring (12/segment), flush module **5.384** (5.6 nominal)
- Front radii: root 284.0, pitch 290.7, tip 296.1; wall = front × 1.0327
- Face 9.5 mm, cone 45°, straight (spiral 0°)
- 20T crossed pinion: pitch rho 8 (FREE — not the rolling value; conjugacy
  is by generation; 8 at 20T = the 0.8 mm section-module print floor),
  face 7, tips Ø9.9→Ø25.3, axis 13.6 mm off the wall plane
- Ratio 108/20 = **5.4:1** — ~2 rpm at the ring from an ~11 rpm shaft
  (22PG-2430BL 720:1, integrated driver, PWM-dialed; catalog-typical
  ~16 rpm no-load → ~3 rpm ceiling)
- Hub Ø16 × 6 mm on the big (motor) end, bore Ø4.2 with 0.5 D-flat
  (22PG 4 mm D-shaft — catalog-typical, measure the purchased unit)

`docs/onshape-variables.html` still carries the 46 copy-paste variable
expressions for the rest of the segment; these features replace only the
gear, which was the one part DXF import couldn't make parametric.
