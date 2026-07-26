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
- 2026-07-26 drive axis ("shaft perpendicular to the arc, pinion flipped"):
  a true mixer-style crossed-axis pinion meshing the current
  viewer-facing cone must sit IN FRONT of the tooth band, and the wafer
  field owns all of that space (wafer undersides pass ~2 mm in front of
  the band face — measured, not a guess). Only two geometries close:
  (A) crossed radial shaft with the ring cone FLIPPED to face the wall
  (pinion nests from behind, fully inside the 76 mm standoff — but the
  visible cone then points away from the viewer, the look you rejected
  on 07-25), or (B) the current parallel-axis pair (pinion taper
  opposite the ring's is what makes parallel axes mesh — it is not a
  mistake, but it is not the mixer picture). Which trade do you want?
  A = mixer mechanics, hidden working faces; B = visible 45° ring cone,
  parallel shaft. Nothing shipped for the axis change yet.
