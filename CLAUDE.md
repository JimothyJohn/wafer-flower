# Wafer Halo

Wall art: 9× Ø300 mm silicon wafers arranged in an overlapping swirl ("iris")
ring, each adhesively bonded to an identical 3D-printed frame segment. Zero
hardware on the frame; all fixturing lives in a reusable bench jig. This repo
iterates the FRAME METHOD; mounting/hanging is deferred.

## Frozen physics (do not re-derive; correct as of Rev B)
- Wafer: Ø300 × 0.775 mm, 128 g, silicon 2.33 g/cm³. N=9 segments × 40°.
- Tilt θ is about each wafer's RADIAL axis (leading edge up). Tilt about the
  tangent axis is WRONG — it gives a cone with no neighbor clearance.
- θ RESOLVED: aesthetic choice, not structural. Even θ=5 gives a 14.3 mm
  neighbor z-gap vs the 3 mm requirement, and droop is ~0.01 mm either way.
  θ only buys standoff depth (26.9 mm @ 5° → 52.9 @ 10° → 78.4 @ 15°) at
  ~6.5% assembly mass and ~8% dovetail margin per degree. Pick on looks.
- CURRENT PARAMS (Rev B.2, user-set 30 mm caps): θ=5°, R_pitch=350,
  band Ri=255 w=30, t_min=10, bondline 1.1. Part is 25.0 mm tall, 30 mm wide.
- θ=5 IS FORCED by the 30 mm thickness cap at N=9 (θ=7.5 → 32.1, θ=10 → 39.6).
  N=12 would allow θ=10 at 27.9 mm if the deeper look is wanted back.
- The 30 mm cap + t_min 10 FIXED the worst margin: dovetail 2.1× → 4.8×
  (S_joint 256 → 427 mm³, assembly 2.29 → 1.64 kg).
- Wafer footprint projects as ellipse: semi-axes 150 (radial) ×
  150·cosθ (tangential).
- Hide window (frame invisible from front) at joint meridian (20°):
  solve ((ρcos20−R)/150)² + (ρsin20/(150cosθ))² = 1. ≈ [240, 416] mm @ θ=10.
- Protrusion envelope = 2·150·sinθ + wafer t. Edge swing = ±150·sinθ.
- KNOWN BUG FIXED IN REV B: segment land near its leading joint rises above
  the NEIGHBOR wafer's plane (collision ~34 mm @ θ=10). Every segment needs
  a second cut: neighbor's wafer plane − 3 mm clearance. Costs ~6° of land;
  ~34° of 40° remains bondable. Never remove this cut.

## Frame design (v3 / Rev B)
- Segment = 40° ring sector, flat bottom, top = min(own wafer plane − bond,
  neighbor plane − 3). Tapered thickness: t_min at trailing edge to
  t_min + 2·Ro·sin20°·tanθ at leading. Dovetail joints 12/16 × 8 mm,
  female +0.25 clearance (tune via coupon), slide in Z, no tools.
- Land plane construction: plane through radial line at (R,0), angle θ from
  Top, offset −(t_wafer/2 + bondline).
- Ø5 JIG KEYHOLE is RADIAL and BLIND: in from the OUTER arc face at a=0,
  15 mm deep, axis at z_bot+t_min/2 (centred in the slab, always solid).
  Deliberately not through the land — the land face stays unbroken.
- ADHESIVE POCKET, 1 mm deep, inset into the land. It meters glue and gives a
  positive bondline stop. It CANNOT self-centre the wafer: the whole band lies
  under the wafer's interior (rim is 55 mm inboard, 215 mm outboard, closest
  approach 9.1 mm), so no pocket edge here can ever touch the rim. Centring
  stays the jig's job. Pocket must clear the dovetail zones or it punches into
  the socket and turns the part into a tunnel.
- NUT LIVES IN THE JIG (single-peg side), not the segment. Segment has no
  nut trap.
- INTERNAL RING GEAR on a planar flange (6 mm) sitting on the flat bottom,
  extending inward from Ri to the root circle. WHY THERE: neither the inner
  nor outer edge of the segment is planar — both follow the tilted land and
  swing ±15 mm out of the ring plane per sector (30 mm p-p), so a fixed
  pinion cannot mesh with them. The flat bottom is the segment's ONLY planar
  face. Do not try to put teeth on a rim.
- GEAR TOOTH COUNT MUST DIVIDE BY N or the pitch breaks at every joint.
  Module 2, N=9: 28T/segment = 252T (pitch Ø504, tips r=250) needs Ri≈255 —
  10 mm clear of the hide window. At Ri=248 only 243T fits and tips clear by
  1 mm, inside print tolerance. Calculator flags this live (r_gearok).
  28T pinion → exactly 9:1; axis at r=224, inside the Ø500 central hole, so
  motor + rollers + wall anchor all mount on one hidden hub plate.
- DESIGN FORK RESOLVED (user's call): keep the one-piece wedge and add the
  gear flange. Rejected: two-piece planar-ring + bolted-saddle split (would
  have cut 124→67 g and raised joint margin to 2.7×, but adds a screw per
  station, breaking zero-hardware).
- Bond: compliant adhesive ONLY (acrylic foam tape or SMP/MS-polymer).
  Gravity shear 0.13 kPa vs ~500 kPa capability (~4000×); governing load is
  thermal: ΔT=20 K × Δα≈57 ppm/K × L_max=96 mm ≈ 110 µm slip → 10 % shear
  strain on a 1.1 mm bondline ≈ 6.0 kPa, ~47× gravity. Rigid epoxy is banned
  — it puts that slip into the Si. Full-surface adhesive adds nothing:
  τ_th scales with distance from the land centroid, NOT with area, so a
  bigger patch is a worse patch.
- Jig (bench, reusable): registers on the segment's own dovetail socket +
  edge rails; downhill R150.3 arc fence + push pad self-center the wafer;
  press over the LAND CENTROID, never the unsupported wafer center.
- Bond sequence: one segment at a time flat on bench, then assemble ring.

## Statics (OP 015 in docs/index.html; solver validated against an
## independent Python model, all 20 readouts matching)
- Ø300 station: wafer 1.25 N over 96 cm² land. Gravity shear 0.13 kPa,
  peel 0.27 kPa. Both noise. Thermal (above) governs the bond.
- Land centroid sits at ρ=271 vs wafer CG at R=350 → 79 mm peel arm and
  197 mm of unsupported outboard wafer. Mounted droop 0.11 mm (fine vs the
  3 mm gap); flat-on-bench droop 0.61 mm.
- Silicon self-weight bending 0.60 MPa mounted / 3.4 MPa flat vs a ~30 MPa
  edge-flaw allowable. But a 2–3 N point load at the free edge hits that
  allowable — press over the LAND CENTROID only.
- ASSEMBLY: 2.29 kg / 22.5 N (9× 128 g Si + 9× 127 g PETG at 45% density,
  gear flange included). Ri=255 variant: 2.31 kg / 22.6 N.
- TIGHTEST MARGIN IN THE BUILD: single centred dovetail on a one-point
  hang. M ≈ W·R/π = 2.5 N·m, S_joint = 6×16²/6 = 256 mm³ → 9.7 MPa vs
  ~20 MPa printed-PETG allowable = 2.0×. Everything else is 47–4000×.
  Fix via two dovetails per face, two hang points (±50°), or a ledge.
- Centring the band under the wafer CG is NOT free: +23% mass, +30%
  thermal shear, and it drags the dovetail margin 2.0× → 1.7×.

## Verified from the solid model (scripts/segment_stl.py), not just formulas
- Segment 217.0 cm³ → 124 g at 45% infill. Frame 1.12 kg + 1.15 kg Si = 2.27 kg.
- PART IS 37.2 mm TALL, not the 44.5 mm the taper formula gives. That formula
  (tmin + 2·rise + bond) is the UN-CUT wedge; the clearance cut removes the top
  corner. Use the solid, not the formula, for print-height and bed checks.
- CLEARANCE DISC MUST BE OVERSIZED (clr_edge=2 mm). Cut at exactly the wafer
  radius and the cut wall lands tangent to the neighbour's rim → zero lateral
  clearance vs T6's ±0.5 mm centring + the wafer's ±0.2 mm diameter tol.
- The clearance cut is a DISC, never a half-space: a half-space removes
  material 300 mm outside the neighbour wafer's footprint (caught by a guard).
- Measured: T1 clearance exactly 3.000 mm, dovetail/socket interference 0 mm³.
- Dovetail is a prism only over the bottom `tmin`, open at the flat bottom so
  segments slide together in Z. It cannot be full-height: each segment's top
  follows ITS OWN wafer, so tail and socket tops would never match.

## Bugs the solid model caught (do not reintroduce)
- z_bot MUST be −(rise + landOff + t_min), NOT −(rise + bond + t_min). Using
  bond alone leaves the base slab poking wafer_T/2 = 0.39 mm ABOVE the land at
  the trailing outer corner, pressing into the bondline. The traveler's OP 010
  step 4 had this too; both fixed.
- Clearance cut is a DISC of radius r + clr_edge (2 mm), positioned at
  −clrOff (below the neighbour's mid-plane), extending +n. Sign and finiteness
  both matter: +clrOff let the segment rise through the neighbour's wafer.
- INTERNAL GEAR PAIRS CO-ROTATE. Ring and pinion turn the SAME direction.
  Using the external counter-rotating convention reads as 245 mm³ of
  interference from a profile that is actually conjugate.
- Multi-body STLs: weld per body. Welding across touching bodies makes
  non-manifold edges where 4 triangles meet.

## Glue area (measured, θ=5, one Ø300 station)
- Load: 1.247 N shear, 0.109 N peel, peel arm 80 mm → 8.73 N·mm.
- Governing area at 4× design factor: ~350 mm² = TWO 13×13 mm pads separated
  ~20 mm RADIALLY (radial separation is what resists the peel moment).
- That is ~3% of the available land. SHRINKING THE BOND IMPROVES IT: thermal
  stress scales with distance from the bond centroid, not area —
  full land 6.02 kPa → two 25×25 pads 2.04 → two 10×10 pads 0.70 kPa.
- So the land is free for interlocking/design features. Do not full-coverage.

## Test gates before printing ×9 (docs/index.html)
T1 neighbor clearance (2-segment print + disks, ≥3 mm), T2 dovetail coupons,
T3 adhesive shear + 10–30 °C thermal cycling (THE gate), T4 land flatness
≤0.15 mm, T5 taper min thickness, T6 centering repeatability ≤0.5 mm,
T7 dovetail hang (≥2× the 2.5 N·m joint moment, 24 h).

## Repo contents
- docs/index.html — current traveler (Rev B): three.js parametric
  calculator with a live statics solver (OP 015) and a 3-way view switcher
  (full halo / one station / frame only, with the land colour-coded against
  the clearance cut), CAD steps, test points, motion/pinion concept, and a
  full 33-line BOM. Needs CDN for three.js r128.
- docs/spec-sheet.html — customer-facing capability & care spec.
- docs/onshape-variables.html — 46 copy-paste OnShape variable expressions,
  live recompute. Includes the CLOSED-FORM hide window (quadratic in rho after
  normalising by r) — the traveler solves it by bisection, OnShape need not.
- scripts/segment_stl.py — THE CAD. Parametric CSG -> watertight STLs
  (segment / pair / frame / assembly / pinion) + DXF sketch profiles in
  stl/dxf/ for OnShape. Needs `pip install manifold3d`. Every PARAMS entry is
  also a CLI flag. Run it before trusting any dimension.
- STEP export was built and then dropped at the user's call: it lands in
  OnShape as one dumb non-parametric solid, so DXF + the #variables is the
  route that stays editable. Do not rebuild it without being asked.
- scripts/*.py — halo_gen.py, v3_dxf_gen.py (parametric; edit constants).
- NOTE: cad/ and tools/ do not exist in this repo. Only README.md and
  docs/ are tracked by git; CLAUDE.md, V3_NOTES.md, ONSHAPE_RECIPE.md and
  scripts/ are untracked.

## Conventions & preferences
- User (Nick) is technical; be direct, lead with problems, no praise
  padding. Structurally-sound-over-minimal on the frame. Quantify claims.
- Wafer handling: edges only, never flex, never acetone on the PRINT
  (crazes PETG/softens PLA; acetone on silicon is fine). Denatured alcohol
  or 91% IPA for prep.
- Adhesives on the shelf at Home Depot: Scotch-Mount Extreme (acrylic foam,
  ~1.1 mm), Loctite PL Premium Max 9 oz (SMP = MS-polymer), mineral
  spirits for SMP cleanup.

## Likely next tasks
1. FIX THE DOVETAIL (2.0× margin) — two per face is the cheapest path.
   Everything else in the design has ≥47× margin.
2. Regenerate DXFs with Rev B params (scripts/v3_dxf_gen.py constants).
3. Port the calculator's segment surface function to a mesh/STEP generator
   (build123d or CadQuery) so parts export directly without OnShape.
4. Lock a Rev C traveler once θ is picked and the joint is fixed.
5. Motion: INTERNAL 252-tooth module-2 ring gear on the flat-bottom flange
   (see Frame design), 28 T pinion = exactly 9:1, ~3.3 mN·m at the pinion.
   Pinion supplies torque ONLY; 3 V-groove rollers on the outer rim carry
   the 22.5 N. Rotation fully reverses the peel term every rev → T3 becomes
   a cyclic test, but it also retires the single-point-hang joint case.
