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
