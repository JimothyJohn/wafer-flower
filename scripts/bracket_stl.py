#!/usr/bin/env python3
"""
Wafer Halo — static wall bracket (2026-07-24): hangs the assembled ring on
the wall with TWO identical printed saddles. No motor, no rollers — the
drive train is filed away; this is the minimal static mount.

How it carries:
  Two saddles sit at +/-50 deg either side of bottom-dead-centre. Each is a
  channel the ring drops into: a concave shelf at band-OD + 0.15 carries the
  weight radially (a V-block, so the ring cannot translate in-plane), the
  back plate face stops the ring's flat wall face, and a lip NOSE rides in
  the segment's circumferential RETENTION GROOVE (segment_stl grv_* params:
  2 deep in the outer arc face, straight ledge + 45-deg print chamfer).
  Pulling the ring off the wall jams the groove's front wall on the nose —
  positive +z retention at ANY clocking, because the groove runs the full
  360. The groove exists because nothing else can do this job: every other
  forward-facing surface on the ring is either bond land or within ~1 mm of
  the wafer underside at the worst clocking (the wafers dip to 6.8 mm above
  the wall face over the saddle footprint — measured from the wafer
  ellipse, and the whole saddle above the wall plate stays under 5 mm
  proud). Install: offer the ring to the plates slightly high, drop it in —
  the noses enter the groove over the last few mm. Lift ~5 mm to remove.
  Resting on shelves also puts the ring in compression (arch), which
  retires the single-point-hang dovetail case entirely (OP 015 §5 fix (c)),
  and the ring stays free to rotate in the cradles for clocking.

Mounting: two #10-24 pan heads (or M5 pans) per saddle into stud/anchor,
through keyhole slots in the plate tail below the rim — outside the ring's
silhouette, so the screws go in first and the bracket hooks on. Slot runs
radially outward = downhill at both saddle azimuths, so gravity seats it.

Hidden: everything stays under plan radius ~335 mm, far inside the wafer
disc coverage (hide window outer edge ~410 at these params) — asserted, and
wafer/bracket interference is boolean-checked, not assumed.

Standoff: plate_t sets how far the ring floats off the wall (default 6 mm).
The parked face-drive pinion would someday need its axis ~26 mm behind the
ring's wall face — when the drive returns, reprint with plate_t >= 32.

    pip install manifold3d
    python3 scripts/bracket_stl.py            # -> stl/, self-checking
"""
from __future__ import annotations
import math, os, sys, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from segment_stl import (PARAMS, Cfg, prism, build_ring, build_wafer,
                         write_stl, report, Manifold, HAVE_MANIFOLD)

BRK = dict(
    sad_ang  = 50.0,   # saddle azimuth, deg either side of bottom-dead-centre
    slack    = 0.15,   # radial gap shelf-to-band at nominal seat
    nose_r   = 1.6,    # lip nose reach into the groove (groove is 2.0 deep)
    nose_c   = 0.3,    # nose z-clearance per side inside the groove ledge
    plate_t  = 6.0,    # wall plate thickness = ring standoff off the wall
    width    = 64.0,   # tangential width of the saddle
    tail     = 34.0,   # plate tail beyond the band OD (carries the keyholes)
    key_gap  = 44.0,   # keyhole spacing, tangential
    key_d    = 5.5,    # keyhole slot width (#10 / M5 pan shank)
    key_D    = 11.0,   # keyhole entry (pan head passes)
    key_sink = 3.5,    # head pocket depth in the plate front face
)


def box(x0, x1, y0, y1, z0, z1):
    return prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1 - z0)


def vcyl(r, z0, h, cx=0.0, cy=0.0, fn=256):
    return Manifold.cylinder(h, r, r, fn).translate([cx, cy, z0])


def build_saddle(cf, b):
    """One saddle, LOCAL frame: ring centre at origin, saddle radially along
    +x (the ring's outer face is the r=Ro cylinder about the origin). Placed
    into the hanging scene by a z-rotation. The wall plate's inner edge at
    Ro - 22 bears on the flange's back annulus OUTSIDE the tooth-slot band
    (slots end at g_pitch + fw/2 + 2 = 258; boolean-checked, not assumed).
    The saddle body above the plate is a shelf ring spanning the groove's
    z-range plus a nose ring reaching nose_r into the groove; its concave
    faces are carved with the seat / nose bore cylinders. Everything above
    the plate stays under z_bot + grv_z0 + grv_h + nose_c + 1.2 — about
    5 mm proud of the ring's wall face, far below the wafers' worst dip."""
    w2 = b['width'] / 2.0
    r_seat = cf.Ro + b['slack']
    z_back = cf.z_bot
    z_wall = z_back - b['plate_t']
    x_out = cf.Ro + b['tail']
    # groove geometry from the segment CAD — single source of truth
    g0 = z_back + cf.grv_z0                      # groove floor z
    g1 = g0 + cf.grv_h                           # groove ledge (front wall) z
    n0, n1 = g0 + b['nose_c'], g1 - 0.15         # nose z-extent inside groove
                                                 # (0.15 nominal retention play)
    top = g1 + 1.2                               # saddle body roof
    p = box(cf.Ro - 22.0, x_out, -w2, w2, z_wall, z_back)                 # plate
    p += box(cf.Ro - 2.0, x_out, -w2, w2, z_back, top)                    # body
    # seat carve starts exactly at the plate top: starting below it would
    # eat the plate's bearing face (the ring's wall face rests on it)
    p -= vcyl(r_seat, z_back, top - z_back + 1.0, fn=cf.facets)           # seat
    # nose ring: reaches into the groove over the straight ledge only; its
    # outer boundary overlaps 3 mm into the body so the union welds clean
    nose = (vcyl(r_seat + 3.0, n0, n1 - n0, fn=cf.facets)
            - vcyl(cf.Ro - b['nose_r'], n0 - 0.5, n1 - n0 + 1.0, fn=cf.facets))
    p += nose ^ box(cf.Ro - b['nose_r'] - 1.0, x_out, -w2, w2, n0, n1)
    # keyholes in the plate tail: entry circle + slot running outward
    for s in (1.0, -1.0):
        ky = s * b['key_gap'] / 2.0
        kx = cf.Ro + b['tail'] - 12.0
        p -= vcyl(b['key_D'] / 2.0, z_wall - 1.0, b['plate_t'] + 2.0,
                  kx - 7.0, ky, fn=64)
        p -= box(kx - 7.0, kx + 6.0, ky - b['key_d'] / 2.0,
                 ky + b['key_d'] / 2.0, z_wall - 1.0, z_back + 1.0)
        p -= box(kx - 7.0, kx + 6.0, ky - b['key_D'] / 2.0,
                 ky + b['key_D'] / 2.0, z_wall + b['plate_t'] - b['key_sink'],
                 z_back + 1.0)
    return p


def place(solid, az_deg):
    return solid.rotate([0.0, 0.0, az_deg])


def main():
    if not HAVE_MANIFOLD:
        sys.exit("needs manifold3d for STL output:  pip install manifold3d")
    ap = argparse.ArgumentParser(description="Wafer Halo — static wall bracket")
    ap.add_argument('-o', '--out', default='stl')
    for k, v in {**PARAMS, **BRK}.items():
        ap.add_argument(f'--{k}', type=type(v), default=None)
    a = ap.parse_args()
    cf = Cfg(**{k: getattr(a, k) for k in PARAMS if getattr(a, k) is not None})
    b = dict(BRK)
    b.update({k: getattr(a, k) for k in BRK if getattr(a, k) is not None})
    os.makedirs(a.out, exist_ok=True)

    assert cf.grv_d > 0, "segment has no retention groove (grv_d=0) — " \
        "the saddle nose has nothing to lock into"
    assert b['nose_r'] < cf.grv_d - 0.2, "nose bottoms out in the groove"

    # hanging scene: gravity is -y, saddles at +/-sad_ang from bottom (270)
    az = [270.0 - b['sad_ang'], 270.0 + b['sad_ang']]
    sad = build_saddle(cf, b)
    saddles = [place(sad, q) for q in az]
    bodies = build_ring(cf)          # list of solids, one per segment
    frame = sum(bodies[1:], bodies[0])
    wafer_list = [build_wafer(cf, k) for k in range(cf.N)]
    wafers = sum(wafer_list[1:], wafer_list[0])
    ring = frame + wafers
    both = saddles[0] + saddles[1]

    W = 17.5  # N, face-gear build: 9 x (128 g Si + 70.3 g PETG sliced)
    Nn = W / (2.0 * math.cos(math.radians(b['sad_ang'])))
    print(f"Static bracket  ·  saddles at ±{b['sad_ang']:.0f}° from bottom, "
          f"seat r{cf.Ro + b['slack']:.2f}, nose {b['nose_r']:.1f} into the "
          f"{cf.grv_d:.1f}-deep groove")
    print(f"  load    {W:.1f} N assembly → {Nn:.1f} N per shelf normal; "
          f"2 screws/saddle, ≥95 N anchors → >10× on hardware")
    print(f"  hidden  bracket plan radius ≤ {cf.Ro + b['tail']:.0f} mm "
          f"(wafer coverage to ~410 at the joint meridians)")
    print(f"  wall    ring floats plate_t = {b['plate_t']:.0f} mm off the wall; "
          f"future face-drive pinion needs ~26+6 → reprint at plate_t ≥ 32\n")

    EPS = 1e-6
    mv = lambda s, v: s.translate(list(v))
    checks = [
        ('saddles vs frame, nominal seat', (both ^ frame).volume(), False),
        ('saddles vs wafers, nominal',     (both ^ wafers).volume(), False),
        ('ring dropped 0.4 meets both shelves, L',
         (mv(ring, (0, -0.4, 0)) ^ saddles[0]).volume(), True),
        ('ring dropped 0.4 meets both shelves, R',
         (mv(ring, (0, -0.4, 0)) ^ saddles[1]).volume(), True),
        ('ring pushed 0.4 to wall meets the plates',
         (mv(ring, (0, 0, -0.4)) ^ both).volume(), True),
        ('ring pulled 0.1 off wall still free (retention play)',
         (mv(ring, (0, 0, 0.1)) ^ both).volume(), False),
        ('ring pulled 0.5 off wall jams groove ledge on the noses',
         (mv(ring, (0, 0, 0.5)) ^ both).volume(), True),
        ('ring raised 5.0 frees the noses from the groove',
         (mv(ring, (0, 5.0, 0)) ^ both).volume(), False),
        ('ring raised 5.0 then pulled 4.0 lifts clear',
         (mv(ring, (0, 5.0, 4.0)) ^ both).volume(), False),
    ]
    # clocking sweep: the ring is free to rotate in the cradles, and the
    # wafer undersides sweep low over the saddle footprint — every clocking
    # must clear. 7 samples cover a full segment period (40 deg).
    worst_c = 0.0
    for i in range(1, 7):
        rr = (ring).rotate([0, 0, i * 40.0 / 7.0])
        worst_c = max(worst_c, (rr ^ both).volume())
    checks.append(('clocking sweep (7 over a sector): saddles clear wafers+frame',
                   worst_c, False))
    # install path: straight drop from above (back flush on the plates),
    # 5 steps — the noses ride into the groove without snagging
    worst = 0.0
    for i in range(1, 6):
        t = i / 5.0
        worst = max(worst, (mv(ring, (0, 8.0 * t, 0)) ^ both).volume())
    checks.append(('install: flush drop, up to +8, never snags', worst, False))

    ok = True
    print("  checks:")
    for name, v, want in checks:
        good = (v > EPS) == want
        ok &= good
        print(f"    {'PASS' if good else 'FAIL':4}  {name:58} {v:10.4f}")

    # plan-radius containment (scalar, from the solid's bounds)
    bb = both.bounding_box()
    rmax = max(math.hypot(bb[0], bb[1]), math.hypot(bb[3], bb[4]),
               math.hypot(bb[0], bb[4]), math.hypot(bb[3], bb[1]))
    good = rmax <= 410.0
    ok &= good
    print(f"    {'PASS' if good else 'FAIL':4}  {'hidden: max plan radius':58} {rmax:10.1f}")

    dz = -(cf.z_bot - b['plate_t'])  # wall face onto the print bed
    outs = [('bracket_saddle.stl', [sad.translate([0, 0, dz])],
             'print x2, wall face down, no supports'),
            ('bracket_fitcheck.stl',
             bodies + wafer_list + saddles, 'view only, hanging scene')]
    for fname, solids, note in outs:
        bodies = write_stl(solids, os.path.join(a.out, fname))
        v = report(fname, solids, bodies, note)
        if 'fitcheck' not in fname:
            print(f"{'':24}mass  30% infill {v*1.27e-3*0.30:6.1f} g   "
                  f"solid {v*1.27e-3:6.1f} g   (permanent part — don't starve it)")

    print(f"\n{'ALL CHECKS PASS' if ok else 'CHECK FAILURES ABOVE — do not print'}")
    print(f"Wrote to {os.path.abspath(a.out)}/")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
