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
  ~4% assembly mass and ~5% dovetail margin per degree (slicer-measured
  masses). Pick on looks.
- CURRENT PARAMS (Rev B.6 low-profile, 2026-07-27): θ=5°, R_pitch=350,
  band Ri=255 w=30, t_min=15, gear_F=9.5, bondline 1.1, pin_T=20,
  pin_rho=8 pin_face=7 gear_bl=0.3, stand=DERIVED 17.6 (the crossed
  pinion bulges 26.2 in front of the wall face; the wafers move forward
  to clear it). Part is 47.7 mm tall, total wall depth ~54. Nick
  2026-07-27: "minimalist" beats exact-1-rpm — 20T gives 5.4:1 (~2 rpm).
  The FIRST crossed rev used the textbook rolling pitch (rho 26.9 ->
  pinion Ø100, part 108) and Nick called it "way out of scale" —
  conjugacy is by GENERATION, so only the tooth count is forced and rho
  is a free packaging knob DOWN TO the 0.8 mm section-module print floor
  (2·pin_rho/pin_T ≥ ~0.8 — rho 8 at 20T sits exactly on it; gear_bl
  must drop 0.6 → 0.3 there or backlash halves the tooth). Finer RACK
  teeth RAISE the profile: more pinion teeth per ratio → bigger pinion
  floor. History: rho 12/10T was 61.0 tall, wall ~67.
- θ=5 IS FORCED by the 30 mm thickness cap at N=9 (θ=7.5 → 32.1, θ=10 → 39.6).
  N=12 would allow θ=10 at 27.9 mm if the deeper look is wanted back.
- The 30 mm cap + t_min 10 FIXED the worst margin: dovetail 2.0× → 4.5×
  at measured masses (S_joint 256 → 427 mm³, assembly 2.35 → 1.75 kg;
  2026-07-25 dt_h=5 later halves S_joint to 213 — see the statics bullet).
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
  dt_h = 5 TALL (2026-07-25, Nick, two rounds: the tmin-tall male read
  too thick, and the tmin-tall SOCKET left its roof <0.5 mm at the
  trailing edge — unprintable; socket cut is dt_h+0.5 so the roof is
  ~5.4 mm), female +0.25 clearance (tune via coupon), slide in Z, no
  tools. S_joint 213 mm³ — fine on the two-point idler hang (>3×), but
  revisit dt_h before ever returning to a single-point hang (2.2×).
- Land plane construction: plane through radial line at (R,0), angle θ from
  Top, offset −(t_wafer/2 + bondline).
- Ø6.5 (M6) JIG KEYHOLE is RADIAL and THROUGH (2026-07-24; was Ø5/#10-24):
  in from the OUTER arc face at a=0, hole_dep = bw+0.5 so it exits the
  inner face, axis at z1 + hole_r + 0.1 = z1+3.35 (13.35 mm above the flat
  bottom) — keyhole_z() now DERIVES from the bore radius so the bore bottom
  stays exactly 0.1 mm above the SLAB TOP z1 at any hole_D (reproduces the
  old z1+2.6 at Ø5; the gear band top is lower still at z_bot+gear_F, so
  the rod clears the teeth by ~5.6). The raised axis exists so the jig pin
  can pass through to an inboard fence (the second historical reason —
  swing room for rotating closures — died with the clamp drivetrain,
  2026-07-27 tape rework; nothing rotates on the pin any more). The
  printed Ø6.2 pin (or an M6 rod, Ø6.0) slides through the printed Ø6.5
  hole with NO reaming. Bore exits 0.1 mm
  ABOVE the gear flange (teeth untouched, mesh check still 0.000); the web
  under the pocket floor is now ~0.9 mm (was 2.4 at Ø5) — thin but
  unloaded; genus 1 proves it unbroken. The axis CANNOT go higher (web →
  breakout). Needs rise > zoff+hole_r+1.5 → θ ≥ ~4°; keyhole_z() in
  segment_stl.py is the single source of truth. A through hole makes the
  segment genus 1 — expected, not the pocket-tunnel bug. Segments printed
  with the old Ø5 (or old blind) hole: drill through from the outer face at
  6.5 mm (a mis-height hole just needs the jig bores redrilled to match,
  the fences don't care structurally).
- ADHESIVE POCKET, 1 mm deep, inset into the land. It meters glue and gives a
  positive bondline stop. It CANNOT self-centre the wafer: the whole band lies
  under the wafer's interior (rim is 55 mm inboard, 215 mm outboard, closest
  approach 9.1 mm), so no pocket edge here can ever touch the rim. Centring
  stays the jig's job. Pocket must clear the dovetail zones or it punches into
  the socket and turns the part into a tunnel.
- NUT LIVES IN THE JIG (single-peg side), not the segment. Segment has no
  nut trap.
- IDLER RETENTION GROOVE (2026-07-25, moved from the outer face):
  circumferential, in the INNER face at Ri — 2 deep, 1.5 straight ledge +
  45° chamfer roof, 2.5 mm up from the flat bottom. The bracket idlers'
  FLANGES ride in it (2026-07-27: bought F625ZZ flanged bearings, flange
  Ø18×1.0 — replaced the printed Ø48 wheels' 1.2×1.6 ribs): the ring
  hangs on the bearing bodies (rolling on the bore at Ri, 0.05 datum
  standoff — exact tangency reads as µm facet-chord overlap in the
  booleans) and the groove ledge walls are its axial restraint (±0.25
  float, hard jam at +0.5 out; -z the 1.0-tall flange only meets the 45°
  chamfer roof after ~1.35, so each tower carries a STOP PAD 0.5 behind
  the ring's back face). grv_d=0 deletes it.
- EXTERNAL BEVELOID GEAR (2026-07-25, third and final geometry — Nick:
  "the teeth are upside down, the pinion will engage from the top"; also
  straight teeth by joint call, gear_sp=0, 35 restores the spiral look):
  108 teeth (12/segment) on a 45° cone, BIG END AT THE WALL (r300.6 at
  the wall face → r296.1 at the front), working face toward the viewer —
  the mixer look. FLUSH MODULE: count is quantised in steps of N, so the
  module is retuned (gear_m 5.6 nominal → 5.384 effective, gear_m_nom
  keeps the input) to land the front root circle 1 mm inside Ro — teeth
  rise straight off the band's outer wall, and build_segment carves the
  band's outer 1.5 mm over the gear face (the "notch") so the spaces cut
  into the band edge instead of being filled back to full height (without
  it the pinion tips graze the band corner — 0.002 mm³ in the bracket's
  nominal check). PINION AXIS IS AXIAL — parallel to the halo axis at
  r=C=325.5, engaging from the TOP at 12 o'clock, counter-rotating
  (external pair). A RADIAL-axis 45/45 crossed pair CANNOT fit this
  build in either cone direction: the pinion's swept Ø81 disc spans ±40
  along the wall normal, vs 38 mm of standoff behind (the first
  outer-drive build had it 39 mm THROUGH THE DRYWALL — the bracket's
  wall check only tested the plate; it now includes the pinion) and the
  wafer field in front. The parallel-axis beveloid pair works because
  the cone radii complement slice-by-slice (ring loses 1 mm/mm of z,
  pinion gains it — centre-radius sum constant); conjugacy comes from
  CSG generation, mesh sweep 0.00000 mm³.
  BAND FACE = gear_F = 4.5 mm, NOT tmin — HARD CEILING ~4.86: the
  neighbour wafer's clearance plane dips to z_bot+4.86 over the leading
  ~15–20° of the sector (its rim crosses the tooth annulus at a≈14.6°),
  so a tmin-tall band gets its leading teeth planed by the MANDATORY
  clearance cut (Nick: "multiple heights + a strand" — the strand was
  the disc rim crossing a tooth at a grazing angle). main() GATES it:
  clearance cut must remove 0 mm³ of teeth or exit 1. TIP RELIEF IS
  RADIAL (cutter advanced dr=-0.3 toward the ring), NOT a z-shift — the
  old z-shifted relief left an uncut 0.3 mm shelf ring at the wall-face
  edge of the teeth (Nick: "a ring along the outside"). Segment is
  genus 1 now (keyhole only — the flipped slots form no closed tunnels).
  The old INNER flange and inner teeth are GONE — the bore is plain Ri
  with the idler groove. DEEP-BEVEL REV (2026-07-26, Nick: "the
  45-degree straight bevel I've always dreamed of… rather than what I
  believe is a spur gear"): gear_F 4.5 → 9.5 via tmin 10 → 15 (ceiling
  4.83 → 9.83, computed live by gear_F_ceiling()); tips r305.8 wall →
  r296.1 front, C 325.5 → 328.3, part at the 30 mm cap. Two joint-face
  traps fixed with it: the male tail is BUILT at dt_h via tail_poly
  (cut-down left a coincident joint face → 1e-6 phantom pair
  interference; the backed-off cut shed a µm sliver that broke the STEP
  round-trip), and band/slab sector faces back off 1e-5 rad like the
  tooth clip (exact-butt faces read float noise once taller) — pair
  measures exactly 0. Generation traps that stand: the sector clip backs off
  1e-5 rad (facet wobble reads as 1e-4 joint interference), build_segment
  drops <0.01 mm³ specks at source (phantom STEP solids), cutters
  overshoot both faces (over=0.5 — coplanar-cap sliver trap).
- CROSSED DRIVE (Rev B.5 2026-07-26 → B.6 low-profile 2026-07-27, Nick:
  "shaft perpendicular to the arc… pinion flipped… top bracket only
  exists when we want to drive it"; then "minimalist… ~2 rpm"): the 20T
  45° pinion sits on a RADIAL axis at 12 o'clock (shaft straight down,
  22PG-2430BL above it in a shell), ratio 108/20 = 5.4:1 — ~2 rpm from
  an ~11 rpm shaft (the retired Pololu #1596 at 5 V gave 2.006 exactly).
  Conjugacy is by CSG generation under the imposed motion (a true
  rolling 45/45 pair exists only at 1:1 — heavy sliding, mN·m loads,
  fine); mesh sweep 0.00000. SMALL pinion (pin_rho 8, tips Ø9.9→Ø25.3,
  face 7 engaging the OUTER 7 mm of the envelope): rho is FREE because
  generation owns conjugacy — the rolling-size first cut (Ø100) was
  Nick-rejected; floor is the 0.8 mm section module. The visible
  deep-bevel tooth pattern is restored by a COSMETIC parallel-axis
  sweep over the full face (extra removal only adds clearance, so the
  mesh gate is untouched; both patterns tile k*pitch so they align).
  Pinion stays 0.9 in FRONT of the wall face at rho 8 (the rho-12 rev
  dipped 1.2 behind; wall_gap 6 covers either) and bulges 26.2 in front
  (stand owns it). MOUNTS
  (2026-07-26, Nick: "wheels right underneath the motor… idling to
  preload the motor pinion… needs mounting slots"; idlers re-sized
  2026-07-27, Nick: printed Ø48 "way too unnecessarily big" → bought
  F625ZZ): DYNAMIC = ONE top unit — the ring HANGS on two F625ZZ
  flanged-bearing idlers (flanges in the INNER groove, axles at x ±50 /
  az ±11.7° directly under the motor: the bearings are the radial datum
  AT the mesh meridian so engagement can't breathe; M5 screws into
  captive printed M5 nuts), and the motor shell mounts on ±8 mm
  VERTICAL SLOTS (printed M6 + captive nuts at grid points ±25, 350) —
  slide to set pinion preload, clamp. STATIC = bottom saddle nesting in
  the OUTER groove (ogrv_*: z_bot+12, 10×2, chamfered roof; 52° arc —
  60° printed 348 wide vs the 340 bed). Internal engagement hangs,
  external rests — proven both ways numerically. Two drywall anchors
  inline vertical per mount; nothing behind the frame. HOLES ON THE
  25 mm GRID (2026-07-27, Nick: breadboard mockup): every anchor (top
  y 250/400, saddle y −325/−375 on a narrow strip — full width busts
  the r410 hide bound at the corners) and slot screw sits on 25 mm
  spacings; the WHEEL AXLES cannot (a bought OD pins them to the
  d_c circle — y 241.9 off-grid; grid-snapping both coords needs a
  custom printed wheel, Ø49 at (±50, 225), if ever wanted). The
  pre-grid saddle put its anchors at −296/−346 OUTSIDE its −334..−308
  plate — the holes subtracted NOTHING and it printed anchor-less
  (genus 0 was the tell; an assert now guards it). 12 bracket checks
  gate it; the hide check measures exact mesh vertices (bbox corners
  false-alarm on L-shaped parts).
- GEAR TOOTH COUNT MUST DIVIDE BY N or the pitch breaks at every joint.
  Module 5.6 nominal, N=9: 12T/segment = 108 (flush module 5.384) —
  every joint lands mid-space and the pattern tiles seamlessly.
  Calculator flags the fit live (r_gearok, hide check on the cone's
  front tips). 20T crossed pinion → 108/20 = 5.4:1, radial axis.
- DESIGN FORK RESOLVED (user's call): keep the one-piece wedge and add the
  gear flange. Rejected: two-piece planar-ring + bolted-saddle split (would
  have cut 124→67 g and raised joint margin to 2.7×, but adds a screw per
  station, breaking zero-hardware).
- Bond: ACRYLIC FOAM TAPE ONLY (2026-07-27, Nick: "no longer curing, just
  taping" — the SMP/liquid path is RETIRED; docs keep it marked retired).
  Gravity shear 0.13 kPa vs ~500 kPa capability (~4000×); governing load is
  thermal: ΔT=20 K × Δα≈57 ppm/K × L_max=96 mm ≈ 110 µm slip → 10 % shear
  strain on a 1.1 mm bondline ≈ 6.0 kPa, ~47× gravity. Rigid epoxy is banned
  — it puts that slip into the Si. Full-surface adhesive adds nothing:
  τ_th scales with distance from the land centroid, NOT with area, so a
  bigger patch is a worse patch. Tape gives ONE landing per wafer — no
  repositioning — which is why the jig became a drop funnel.
- Jig (bench, reusable): registers on the segment's own dovetail socket +
  edge rails; downhill R150.3 arc fence + push pad self-center the wafer;
  press over the LAND CENTROID, never the unsupported wafer center.
- TAPE JIG (OP 012, scripts/cure_jig_stl.py — filename kept for CI/docs
  continuity; 2026-07-27 tape rework, Nick: "simplify the jig"): the
  clamp drivetrain (rod tension, captive nuts, washer, knob, nut tower)
  is GONE — tape needs no cure hold, so nothing tightens. Two printed
  fences register on the segment over ONE printed Ø6.2 D-flat locating
  pin (331 mm, disc pull-head, prints lying on its flat, insert
  FLAT-DOWN; an M6 rod from the cure-jig era also fits, looser) passed
  radially THROUGH the Ø6.5 keyhole. Outboard fence nose butts the outer
  arc face, inboard fence prong butts the inner face above the gear
  flange; hand pressure holds them seated for the seconds the placement
  takes. ZERO bought hardware. ORDER FLIPPED vs the SMP flow: jig
  assembles FIRST (tape pads down, liners on → fences → pin → peel),
  wafer drops LAST — with tape the wafer cannot slide to a gravity seat
  after touchdown, so the FOUR CAPTURE PEGS (2026-07-25, Nick's call:
  pegs, not wall cutouts — X/Y only, gravity owns Z, part-agnostic,
  never overconstrained) act as a drop-in FUNNEL: the chamfered tips
  lead the wafer in and the flanks centre it on the way DOWN. Pegs: Ø8,
  two per fence at ±22° off the radial meridian, flanks at PROJECTED-rim
  + 0.15 — the tilted wafer's plan rim is an ELLIPSE (y semi-axis
  r·cosθ, 0.57 mm shy of r at θ=5), and pegs placed on a plain r+slack
  circle gap 0.23 instead of 0.15 and the y-window drifts with tilt;
  deriving each peg radius from the ellipse keeps flank gap = slack at
  any wafer Ø or tilt. Capture: x ±0.15, y ~±slack/sin(22°) = ±0.40.
  Lift is FREE by design (nothing overhangs the wafer). Inboard pegs sit
  ~215 from the halo axis, clear of the tooth tips by ~30. CENTRED ON
  THE WAFER by construction: the keyhole meridian (a=0) IS the
  wafer-centre meridian, checked numerically. BENCH HOLD-DOWNS on the
  25 mm grid (2026-07-27, Nick: breadboard mockup): Ø5.4 through +
  Ø10×3.5 counterbore pairs at y ±25 — outboard at x 325 (foot,
  widened +6) and 500 (rear block), inboard at x 175 (base back face
  moved to x_in−32 to fit it); both fences bolt to a 25 mm board AT
  their nominal working separation, fence_w 60→64 for counterbore
  wall. Pin shortened to 327 (tail at x_in−10, ~65 mm engaged — the
  full-back tail hit 347 vs the 340 bed). 14 boolean checks (incl.
  the 'wafer +5 z lifts FREE' probe and a pin-withdrawal sweep), script
  exits nonzero on any FAIL. Sliced PLA @10%: outboard 115.3 g/3h25,
  inboard 47.8 g/1h35, pin 7.4 g/20m (fences grew with the deep-bevel
  bridge deck — a lean pass is possible if Nick wants it).
- Bond sequence: one segment at a time flat on bench (tape jig, one
  landing each), then assemble ring.

## Statics (OP 015 in docs/engineering.html; solver validated against an
## independent Python model, all 20 readouts matching)
- Ø300 station: wafer 1.25 N over 96 cm² land. Gravity shear 0.13 kPa,
  peel 0.27 kPa. Both noise. Thermal (above) governs the bond.
- Land centroid sits at ρ=271 vs wafer CG at R=350 → 79 mm peel arm and
  197 mm of unsupported outboard wafer. Mounted droop 0.11 mm (fine vs the
  3 mm gap); flat-on-bench droop 0.61 mm.
- Silicon self-weight bending 0.60 MPa mounted / 3.4 MPa flat vs a ~30 MPa
  edge-flaw allowable. But a 2–3 N point load at the free edge hits that
  allowable — press over the LAND CENTROID only.
- ASSEMBLY (slicer-measured masses): θ=10 traveler build 2.35 kg / 23.0 N
  (9× 128 g Si + 9× 132.8 g PETG at 45% infill, gear flange included);
  current DEEP beveloid build (gear_F=9.5, tmin=15) 1.59 kg / 15.6 N at
  PLA @10% (48.6 g/segment; the PETG@45 deep bevel read 1.98 kg /
  19.4 N, the 4.5-face era 1.76 / 17.3). The old uniform-45% figures
  under-read every build — sliced G-code is the authority.
- TIGHTEST MARGIN IN THE BUILD: single centred dovetail on a one-point
  hang. M ≈ W·R/π = 2.6 N·m, S_joint = 6×16²/6 = 256 mm³ → 10.0 MPa vs
  ~20 MPa printed-PETG allowable = 2.0×. Everything else is 47–4000×.
  Fix via two dovetails per face, two hang points (±50°), or a ledge.
  (B.3 with S_joint 427 mm³: M = 1.9 N·m → 4.5×. With dt_h=5 the tail
  is 213 mm³ → 2.2× on this RETIRED single-point case; the shipped
  two-point idler hang has M well under it, margin >3×. Nick 2026-07-25:
  the full-tmin tail read too thick — dt_h trims the male only, the
  socket stays tmin-deep so segments still slide together in Z.)
- Centring the band under the wafer CG is NOT free: +23% mass, +30%
  thermal shear, and it drags the dovetail margin 2.0× → 1.6×.

## Verified from the solid model (scripts/segment_stl.py), not just formulas
- Rev B θ=10 segment 210.4 cm³ → 132.8 g SLICED at 45% infill (uniform-45%
  said 124 g); current B.3 segment 94.3 cm³ → 66.0 g sliced.
- PART IS 37.2 mm TALL, not the 44.5 mm the taper formula gives. That formula
  (tmin + 2·rise + bond) is the UN-CUT wedge; the clearance cut removes the top
  corner. Use the solid, not the formula, for print-height and bed checks.
- CLEARANCE DISC MUST BE OVERSIZED (clr_edge=2 mm). Cut at exactly the wafer
  radius and the cut wall lands tangent to the neighbour's rim → zero lateral
  clearance vs T6's ±0.5 mm centring + the wafer's ±0.2 mm diameter tol.
- The clearance cut is a DISC, never a half-space: a half-space removes
  material 300 mm outside the neighbour wafer's footprint (caught by a guard).
- Measured: T1 clearance exactly 3.000 mm, dovetail/socket interference 0 mm³.
- Dovetail is a prism only over the bottom `dt_h` (socket dt_h+0.5), open at the flat bottom so
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
- A 45° INTERNAL cone ring cannot mesh a perpendicular 45° pinion at 9:1:
  the pinion's wrap about its radial axis grows its plan radius into the
  concave root wings — 276–386 mm³ measured, phase-independent, not
  tunable. Curvature signs, not backlash. (This is why the drive is a face
  gear.) Also: cutting a 45°-leaning tooth with the ~5° clearance plane
  leaves orphaned tooth-tip crumbs (decompose() finds them; they masquerade
  as wrong genus because the crumb's Euler characteristic cancels the
  keyhole handle's).
- Face-slot cutters (and any cutter) must OVERSHOOT the face they break out
  of; ending exactly on the flange bore face left sliver faces that read
  as OPEN after the float32 weld.
- The pinion tip corners sweep trochoids past a straight rack flank near
  the face plane — the slot mouth needs the 1.6 mm flare or the mesh sweep
  shows ~9.5 mm³ of symmetric tip-corner interference.

## Glue area (measured, θ=5, one Ø300 station)
- Load: 1.247 N shear, 0.109 N peel, peel arm 80 mm → 8.73 N·mm.
- Governing area at 4× design factor: ~350 mm² = TWO 13×13 mm pads separated
  ~20 mm RADIALLY (radial separation is what resists the peel moment).
- That is ~3% of the available land. SHRINKING THE BOND IMPROVES IT: thermal
  stress scales with distance from the bond centroid, not area —
  full land 6.02 kPa → two 25×25 pads 2.04 → two 10×10 pads 0.70 kPa.
- So the land is free for interlocking/design features. Do not full-coverage.

## Test gates before printing ×9 (docs/production.html)
T1 neighbor clearance (2-segment print + disks, ≥3 mm), T2 dovetail coupons,
T3 adhesive shear + 10–30 °C thermal cycling (THE gate), T4 land flatness
≤0.15 mm, T5 taper min thickness, T6 centering repeatability ≤0.5 mm,
T7 dovetail hang (≥2× the 2.6 N·m joint moment, 24 h).

## Repo contents
- GEARS.md — DELETED by Nick 2026-07-31 (the bevel-gear clinic; it
  documented the crossed-bevel architecture the face drive replaces —
  recoverable from history if the bevel route returns).
- DESIGN.md — Nick's high-level design guide (recovered from an untracked
  root file 2026-07-25; his authorship, edit freely): H2S fabrication,
  spiral-bevel-rack drivetrain concept.
- docs/ split by ROLE (2026-07-24, PR #6 — the old single-page traveler is
  gone): index.html is a hub whose MAIN VISUAL IS the live parametric
  calculator (Nick 2026-07-25: one diagram, driven by the sliders, showing
  segments + wafers + coned gear band + retention groove + cure jig +
  bracket saddles — the static real-STL widget lives only on viewer.html
  now); engineering.html carries the same calculator plus OP 010 CAD
  steps, OP 015 §1–5, and motion analysis.
  The calculator (sliders → live geometry/statics/mass readouts, in-browser
  preview-STL download, live segment_stl.py command line; face-gear-aware,
  its mass model lands within 0.5% of the sliced 70.3 g) is SHARED code:
  docs/assets/calc.js, mounted on both pages via canvas#cviz (the viewer
  keeps canvas#viz — ids must not collide on the hub). design.html has the
  θ/knob decision content (old §6–§7); production.html has gates T1–T7,
  OP 020 bond, the full BOM. Shared chrome in docs/assets/site.css, the STL
  viewer widget in docs/assets/viewer.js (used by index.html +
  viewer.html). All need CDN for three.js r128.
- docs/spec-sheet.html — customer-facing capability & care spec.
- docs/cure-jig.html — plain-language illustrated OP 012 TAPE-JIG
  instructions (2026-07-27 rework, filename kept): 8 taping steps +
  one-time setup, each with a render; 3 embedded MP4s (turntable /
  explode / full assembly sequence — fences and pin FIRST, wafer drops
  LAST) in docs/media/ (~3.5 MB total). ALL media renders from the CAD
  via a matplotlib script (merged single Poly3DCollection with per-face
  lambert shading — separate collections z-sort wrongly). Regenerate with
  scripts/cure_jig_media.py (needs matplotlib + numpy + ffmpeg; --stills
  skips the videos, ~4 min with them); linked from engineering.html's
  OP 010 keyhole bullet.
- docs/onshape-variables.html — 46 copy-paste OnShape variable expressions,
  live recompute. Includes the CLOSED-FORM hide window (quadratic in rho after
  normalising by r) — the traveler solves it by bisection, OnShape need not.
- scripts/segment_stl.py — THE CAD. Parametric CSG -> watertight STLs
  (segment / pair / frame / assembly / pinion) + DXF sketch profiles in
  stl/dxf/ for OnShape. Needs `pip install manifold3d`. Every PARAMS entry is
  also a CLI flag. Run it before trusting any dimension. gear_drive =
  'bevel45' (default) | 'face' | 'spur' (legacy); the 3D mesh sweep AND a
  stray-shard decompose() count GATE the exit code (>0.05 mm³ or >1
  component fails). 'face' (2026-07-31, ported from the OnShape FS
  session): radial rack-slot teeth on a flange top OUTSIDE the band OD
  (gf 284–297, flush 288T, m 2.017, PA 25) + 13T spur pinion on a RADIAL
  axis (motor flat on the wall, Ø3.2 bore + 0.5 D-flat + motor-side hub),
  22.2:1 — sweep measures exactly 0 because the constant rack profile is
  conjugate at the flange middle and the ±6.5 mm band stays inside the
  0.15 backlash. Face-mode defaults (gear_m 2, pin_T 13, gear_pa 25,
  gear_bl 0.15, gear_F 6.5) apply only where the knob still sits at its
  bevel-era default. Artifacts committed under stl/face/. The DEFAULT
  stays 'bevel45' because bracket_stl / cure_jig / viewer_export still
  assume the crossed drive — flipping it drags the bracket redesign
  along. Generation traps encoded in gear_teeth_bevel45's
  docstring and comments: pattern phase is k*pitch from the joint (not
  k+0.5 — half off reads as ~156 mm³), tps+1 copies clipped to the sector
  (unclipped wedge overhang lands 232 mm³ inside the neighbour), the
  blank needs a front-inner relief chamfer (the cutter severs a 348 mm³
  top rim ring otherwise), and the mesh-check backing annulus must extend
  OUTWARD from the band (Ri+6 < g_fi puts a phantom ring in the pinion's
  path — 9.4 mm³).
- scripts/bracket_stl.py — TOP IDLER BRACKET (2026-07-25 rewrite, was two
  saddles; 2026-07-26 top-cluster; 2026-07-27 lean pass + 22PG + F625ZZ
  idlers + 25 mm grid): ONE part bolts to the wall at 12 o'clock; two
  BOUGHT F625ZZ flanged bearings (flange in the inner groove, M5 screws
  into captive printed M5 nuts, 8 AF) right under the motor, plus the
  slotted motor shell, all mount on it. build_wheel() models the
  bearing for the checks/viewer — it is NOT a print (bracket_wheel.stl
  deleted). The ring HANGS on the bearings (the OP 015
  two-hang-point case; dovetail S_joint 213 mm³ at dt_h=5) and is
  driven purely rotationally from the top by the 20T crossed pinion.
  MOTOR (2026-07-27, Nick's pick, replaces the Pololu #1596): 22PG-2430BL
  720:1 brushless planetary with INTEGRATED driver (PWM + direction +
  9 PPR FG), 24 V class — NOT USB 5 V. BRK params mot_D 24 / nose_D 22 /
  nose_L 20 / mot_L 65 / Ø4 D-shaft are (PINION BORE RETIRED 2026-08-09,
  Nick: the pinion shaft mount is ALWAYS the N20 3 mm D-shaft —
  build_pinion resolves pin_bore 3.2 / pin_flat 0.5 in EVERY drive mode;
  the 22PG's 4.2 bore is gone, which orphans this shell's Ø4 shaft)
  CATALOG-TYPICAL, NOT MEASURED (the RobotShop datasheet PDF is
  CDN-blocked; siblings 19:1@630 rpm and 1370:1@8 rpm interpolate 720:1
  to ~16 rpm no-load → ~3 rpm ring, PWM to ~2) — MEASURE the purchased
  unit before printing the shell. Round-motor shell: cylinder pocket
  (nose then body), open top for leads, Ø9 hub opening, slotted ears
  (±8 mm). Anchors span the unit inline-vertical on the 25 mm grid
  (anchors-above pushed plan r to 445 vs the 410 hide bound at the
  65 mm body; the grid'd saddle strip is narrow for the same reason).
  12 self-checks vs the full ring + wafers (seat, flange jam both ways
  incl. the tower stop pads, axial float, clocking sweep, wafer field,
  hidden ≤ r410 via exact mesh vertices, nothing behind the wall —
  INCLUDING THE PINION; the plate-only version let the old radial-axis
  pinion sail 39 mm through the drywall) — exits nonzero on FAIL.
- scripts/cure_jig_stl.py — OP 012 cure jig (see Frame design). Imports
  segment_stl for params/geometry, emits cure_jig_{outboard,inboard,pin}.stl
  print-ready plus cure_jig_fitcheck.stl (segment+wafer+fences+pin,
  view only), and self-verifies 14 interference/capture booleans — exits
  nonzero on any FAIL. CSG gotcha it caught: two cutters unioned cap-to-cap
  on the same plane leave a folded seam (dup mesh edges) — overlap cutters
  instead. Homebrew python is PEP-668-managed; manifold3d lives in a venv,
  not brew.
- scripts/printed_hardware_stl.py — printable ISO metric fasteners
  (2026-07-24): M5x0.8 and M6x1.0 knob-head screws + hex nuts, true 60°
  single-start threads via a radius-modulated cross-section swept with
  manifold's twist-extrude (one profile rotation per pitch). 0.25 mm radial
  clearance default; self-checks that the nut spins on at nominal AND that
  crests actually engage; exits nonzero on FAIL. TWO PHASE TRAPS the checks
  caught (do not reintroduce): the nut's bore cutter must be translated by
  a WHOLE PITCH (any other offset rotates the internal helix by offset/p
  turns), and the fit-check nut must sit at a pitch-multiple height (a real
  nut self-aligns in phase; arbitrary z reads as false interference —
  passed at M6 only because 24 mm happened to be 24 pitches). M5 is the
  FDM floor (0.24 mm crest overlap) — print vertical, chase the first fit;
  M6 threads by hand. Sliced 100%: m6 screw 2.2 g/21m, nut 0.4 g/9m;
  m5 screw 1.4 g/16m, nut 0.2 g/8m. NOT yet in the CI cad job.
- STEP export was built and then dropped at the user's call: it lands in
  OnShape as one dumb non-parametric solid, so DXF + the #variables is the
  route that stays editable. Do not rebuild it without being asked.
- scripts/slice.py — STL -> Bambu H2S G-code via OrcaSlicer's CLI
  (`brew install --cask orcaslicer`). Defaults: segment.stl + pinion.stl,
  Generic PETG, 45% infill, 0.20mm Standard, Textured PEI Plate. Emits
  gcode/<name>.gcode + <name>.gcode.3mf (the 3mf is what the printer's
  SD/Handy wants). Orca CLI does NOT resolve profile `inherits` chains —
  unflattened profiles silently slice PETG as PLA@200C; slice.py flattens
  them. Guard skips STLs that fit the 340×320 mm bed in neither
  orientation. `--infill PCT` and `--outdir DIR` exist for calibration
  runs (that's how the mass model below was fitted, on the X1C). Nick's
  printer: H2S, 0.4 nozzle (X1C before 2026-07-22; H2S defaults are
  "Bambu Lab H2S 0.4 nozzle" / "0.20mm Standard @BBL H2S" /
  "Generic PETG @BBL H2S", verified present in the installed Orca).
- MEASURED FROM SLICED G-CODE — supersedes every uniform-45% (ρ·V·0.45)
  mass figure in this file; that model under-reads ALL segments here because
  the solid skins dominate. Sliced mass is exactly linear in infill %:
  m ≈ ρ·(0.91 mm·A_surface + 0.92·infill·(V − skin)), validated ±2% over
  35–425 cm³ (Ø150 holdout: 26.1 g sliced vs 26.2 predicted; PETG-
  calibrated — PLA runs ~2% lighter still). CURRENT B.6
  build: 69.2 g/segment PLA @10% + 6 top shells (47.7 mm part), 2h20
  each, assembly 1.77 kg / 17.4 N (84.3 g at the 61 mm B.5 part;
  PETG@45 history: 91.8 deep bevel, 67.9 at the 4.5 face).
  Pinion 1.9 g / 18 min, top unit 48.4 g / 1h16 @15%, slotted shell
  27.1 g / 57 min, static saddle 79.0 g / 2h09 (idlers are BOUGHT
  F625ZZ bearings now, nothing printed), tape jig 115.3/47.8/7.4 g
  @10% (outboard/inboard/pin — grew with the grid hold-downs and the
  64-wide fences).
  Hanging on the two top idlers
  is the OP 015
  two-hang-point case: M well under the single-point 2.2 N·m, and the
  dovetail carries S_joint 213 mm³ (dt_h=5) — margin >3×. Traveler
  standard θ=10 build: 132.8 g/segment, 2.35 kg / 23.0 N, M = 2.6 N·m,
  dovetail 2.0×. The traveler solver + spec sheet now carry this calibrated
  model (T_SKIN=1.05 on the solver's cruder area estimate, K_INF=0.92) and
  the corrected static numbers throughout. An earlier note here claimed
  margins "only improve" — wrong baseline; measured mass is ~7% ABOVE the
  B.2 book values, so margins shaved, none governing.
- scripts/viewer_export.py — exports scene-coordinate STLs + manifest.json
  + models_data.js into docs/models/ for the Pages viewer (models_data.js
  is a base64 bundle: fetch() is blocked under file://, so a double-clicked
  index.html falls back to loading it via <script src>, which file://
  allows; --verify byte-gates it against the committed manifest + STLs), and gates every configuration it
  can show with boolean CSG: the tape-jig nominal suite, the jig open/close
  stroke swept in steps, the wafer placement drop, and the glued ring
  (adjacent segments/wafers + a bidirectional 2.95–3.05 mm depth-clearance
  probe on the neighbour-wafer cut). Exits nonzero on FAIL. `--verify` is
  the CI mode: re-runs the checks and compares part volumes against the
  committed manifest (volumes, not bytes — float last-bits differ across
  platforms; CI meshed the segment at 5,068 tris vs 5,062 on macOS) so
  docs/models/ can't go stale. stl/my_frame_segment.stl (Nick's OnShape
  rebuild) passes through byte-for-byte as a compare overlay, group
  'onshape': expected in SCENE orientation (same frame as segment.stl,
  Nick's call 2026-07-21); mis-orientation WARNS but never gates — it's
  hand CAD in progress. Verify byte-compares the copy (safe: no
  regeneration involved).
- docs/viewer.html — Pages CAD viewer for the REAL STLs in docs/models/
  (Pages serves master:/docs only, so stl/ is invisible to the site — that's
  why the models live in docs/models/ too). Presets for bare segment / jig
  open / wafer placed / curing / glued pair / full halo; sliders animate the
  jig stroke, wafer drop, station count, and a y-section plane; the manifest's
  check results render as a PASS/FAIL panel. Parses binary STL itself — no
  loader dependency beyond three.js r128.
- scripts/gearmotor_stl.py — PARKED (2026-07-24, Nick's call: drive train
  filed away). Models the pre-face-gear internal-SPUR drive concept and now
  PINS gear_drive='spur' so it stays a self-consistent record; its checks
  run against the legacy ring, NOT the shipped segment. Removed from CI.
  Its stl/drive_*.stl artifacts remain as the parked record; its STEP
  exports were dropped. When the drive returns: the spur pinion survives
  as-is (it IS the face-gear pinion), the worm-motor plate needs a new home
  ~26 mm behind the ring, saddles reprint at plate_t ≥ 32.
- scripts/step_export.py — STEP (AP214) export, REINSTATED at Nick's request
  2026-07-22 for viewing/archival (NOT editable CAD — DXF + #variables stays
  the editing route). Planar B-rep with coplanar-triangle merging; per-part
  .stp (segment / wafer / pinion / bracket_saddle) +
  halo_static_assembly.stp (20 named solids: ring + wafers + 2 saddles)
  into stl/step/. Parked drive parts no longer archived here. --verify
  round-trips every file through gmsh/OpenCASCADE and compares volumes.
  Mesh->brep traps it handles (do not regress): slit patches fall back to
  triangle faces, T-vertex seams healed by unmatched-edge chain substitution
  (NEVER blanket split-at-near-vertices — corrupts micron slivers), sub-µm
  duplicate vertices welded (5e-4), near-degenerate tris dropped. GitHub
  previews .stl in-repo but NOT .stp — browse stl/ for 3D, import .stp to CAD.
- scripts/manual_pdf.py — KISELRING IKEA-style assembly manual ->
  docs/kiselring-manual.pdf (9 pages A4). PARKED CONTENT: it documents the
  MOTORISED concept and pins gear_drive='spur' to stay self-consistent; a
  static-bracket manual is TODO. All 3D panels are line art rendered
  from the REAL solids: orthographic projection, triangle z-buffer hidden-line
  removal, silhouette + >25° crease edges only. Renderer gotcha: SKIP
  triangles with tiny projected area before z-buffering (their barycentric z
  is garbage and poisons silhouettes into false dashes). Scene z = wall
  normal, so wall-art views need azim −90 / high elev, not the bench-view
  camera. Needs numpy + matplotlib.
- CI (.github/workflows/ci.yml): `syntax` byte-compile + `cad` job that runs
  segment_stl.py, cure_jig_stl.py, bracket_stl.py, printed_hardware_stl.py,
  and viewer_export.py --verify on every PR (gearmotor_stl dropped when it
  was parked, 2026-07-24). STEP + manual are committed artifacts, not
  CI-gated.
- scripts/onshape/face_gear.fs — OnShape FeatureScript, REBUILT
  incrementally with Nick verifying every paste (2026-07-30..31; the
  one-shot wafer_halo_beveloid.fs + its README are deleted — history at
  69bbd86). ONE feature, "Arc Segment": FACE-GEAR ring sector — radial
  rack teeth cut into the front face (tooth depth along Height, tooth
  lines perpendicular to the arc), ISO 0.38 m root fillets, joints
  mid-slot, module DERIVED from the band middle — plus an optional
  meshing spur pinion on a RADIAL axis lying flat against the wall
  (D-flat bore for a 3 mm shaft, MOTOR-side hub, parity-based
  tooth-into-slot clocking). Backlash = total pitch-line play split
  evenly between the gears. The architecture walked 45° beveloid → ISO
  intersecting-axes (Nick's pick, made the ring a crown at 8:1/90°) →
  parallel-axis spur → FACE GEAR ("teeth extend with the height");
  ancestors in git history: ISO bevel/crown ed600bf, parallel spur
  5623c8c. PASTE-RULE LEDGER in the file header, learned from real
  Feature Studio errors — ASCII-only annotation strings,
  reportFeatureInfo (and no popup at all), opSphere not fSphere, a
  parameter group must IMMEDIATELY follow its driving parameter. Do not
  regress it.
- scripts/*.py — halo_gen.py, v3_dxf_gen.py (parametric; edit constants).
- NOTE: cad/ and tools/ do not exist in this repo. Everything else is
  tracked: README.md, docs/, scripts/, stl/, CLAUDE.md, TODO.md,
  .github/. gcode/ is gitignored. (Deleted by Nick 2026-07-31 in the
  face-drive cleanup, all recoverable from history: ONSHAPE_RECIPE.md
  the hand-CAD recipe — superseded by scripts/onshape/face_gear.fs —
  plus GEARS.md the bevel-gear clinic and V3_NOTES.md.)

## Conventions & preferences
- User (Nick) is technical; be direct, lead with problems, no praise
  padding. Structurally-sound-over-minimal on the frame. Quantify claims.
- Wafer handling: edges only, never flex, never acetone on the PRINT
  (crazes PETG/softens PLA; acetone on silicon is fine). Denatured alcohol
  or 91% IPA for prep.
- Adhesives on the shelf at Home Depot: Scotch-Mount Extreme (acrylic foam,
  ~1.1 mm) — THE bond (tape-only since 2026-07-27). Loctite PL Premium
  Max 9 oz (SMP) + mineral spirits were the retired liquid path.

## Likely next tasks
1. FIX THE DOVETAIL (2.0× margin) — two per face is the cheapest path.
   Everything else in the design has ≥47× margin.
2. Regenerate DXFs with Rev B params (scripts/v3_dxf_gen.py constants).
3. Port the calculator's segment surface function to a mesh/STEP generator
   (build123d or CadQuery) so parts export directly without OnShape.
4. Lock a Rev C traveler once θ is picked and the joint is fixed.
5. Motion: PARKED (2026-07-24, Nick's call). The 252-slot FACE gear is cut
   into every segment now (costs ~5 g, nothing structural), so motion stays
   a bracket-swap away: spur pinion on a radial axis 26 mm behind the wall
   face, ~3.3 mN·m needed. gearmotor_stl.py holds the parked spur-era
   module. The static bracket (DONE 2026-07-24, scripts/bracket_stl.py)
   already banks the compression-arch win — the single-point-hang dovetail
   case is retired either way. Rotation would make T3 cyclic (peel term
   reverses every rev). 2026-07-31: the FS session effectively REVIVED
   this concept front-side as gear_drive='face' (see the segment_stl
   bullet) — if motion returns, that mode plus a radial-axis motor
   bracket is the path.
