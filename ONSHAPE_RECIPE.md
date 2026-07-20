# Build v3 in OnShape from the DXFs — 7 features

Import both DXFs as sketches on the Top plane (they share the same global
coordinate system; segment is centered on +X).

## The one construction that matters: the LAND PLANE
1. Sketch a line on Top along the TILT_AXIS layer (through wafer center
   (350,0), pointing radially).
2. Plane > Line Angle: through that line, 20 deg from Top. This is the
   WAFER MID-PLANE.
3. Offset plane: -0.887 mm below it (wafer half-thickness 0.3875 + 0.5
   bond line). This is the LAND PLANE.

## Segment (one part, pattern is implicit — print 9)
1. Extrude SECTOR profile DOWN 8 mm (base).
2. Extrude LAND_FOOTPRINT profile UP 40 mm, merge with base.
3. Split/Remove everything above the LAND PLANE (Boolean with a large
   extruded region, or Surface > Plane + Split part, delete upper body).
   The surviving ramped top face is the bonding land.
4. Dovetails: on the +20 deg radial end face sketch DT_MALE, extrude 8 out;
   on the -20 deg face sketch DT_FEMALE, extrude cut through.
5. Nubs: sketch 3x d4 circles ON THE LAND PLANE at (220,0), (235,±32.89)
   [plan coords — use the NUBS_D4 layer as reference], extrude UP 0.5 mm.
6. Keyhole: cut 3 deep into the bottom face from the KEYHOLE layer.

## Jig
1. Extrude RAIL_IN and RAIL_OUT down/up per notes (rails 13 tall total,
   dropping 8 below Top to straddle the segment base).
2. Registration dovetail: reuse DT_MALE minus ~0.05 on the -20 deg end.
3. Fences: extrude FENCE_* profiles from the LAND PLANE up ~5.5 mm
   (use Up to Next/offset from the tilted plane, not from Top — the fence
   top must parallel the wafer, not the bench).
4. Bridge: extrude BRIDGE_FOOTPRINT as a bar spanning the rails ~30 above
   Top; cut the M5 hole NORMAL TO THE WAFER MID-PLANE at plan (228, 0);
   hex nut pocket 8.1 AF x 4.2 on top.

## Numbers you'll want while modeling
- Wafer: d300 x 0.775. Halo: N9, pitch R350, tilt 20 about radial axis.
- Sector: 40 deg, Ri 175 / Ro 245, base 8. Dovetail 12/16 x 8, clr 0.25.
- Land margin inside wafer edge: 3. Bond line: 0.5 (nubs d4 x 0.5).
- Fence inner face at R150.3 from wafer center; walls 5 thick.
- Bond adhesive: MS-polymer (SikaFlex 252 / Loctite PL), not rigid epoxy.

## Sanity checks after modeling
- Section through the wafer mid-plane: wafer back should sit 0.5 above the
  land everywhere, kissing the three nubs.
- Assembly with 9 instances @ 40 deg: neighbor wafer clears this segment's
  land everywhere (it does at 20 deg tilt by ~50 mm; verify if you change
  tilt, R_pitch, or ring widths).
- Land must stay inside the wafer outline in front view (3 mm margin).
