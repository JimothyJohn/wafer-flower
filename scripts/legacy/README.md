# scripts/legacy — the pre-mine architecture (ARCHIVED 2026-08-14)

Nick's call ("Archive and grow mine_stl.py into the one pipeline"): these
generators describe the PREVIOUS architecture — the 255–285 band with
dovetails, keyhole, retention grooves, the tape jig, the idler bracket,
and the bevel/face/spur drive modes. The shipping design is Nick's
OnShape build in `stl/mine/`, generated parametrically by
`scripts/mine_stl.py`.

Still alive from here:

- `segment_stl.py` is imported by `mine_stl.py` as a LIBRARY (prism/arc
  helpers, the face-slot rack machinery, the involute profile, STL
  writer). When the legacy line is deleted outright, that machinery
  migrates into mine_stl first.
- `docs/models/` was exported by `viewer_export.py` and is FROZEN as
  committed until the viewer rebuild targets the mine architecture —
  regeneration is no longer wired into CI, so don't expect --verify to
  guard it.

Everything else (cure_jig, bracket, coupon, gearmotor, step_export,
manual_pdf, media renders, halo_gen, v3_dxf_gen, printed_hardware,
bevel_calc_app) runs where it stands if you need the old parts back —
each still self-checks and exits nonzero on FAIL. The CLAUDE.md bullets
describing them are historical record.
