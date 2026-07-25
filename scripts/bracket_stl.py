#!/usr/bin/env python3
"""
Wafer Halo — top-mount idler bracket (2026-07-25, Nick's rethink of the
drive mechanism): ONE bracket bolts to the wall at 12 o'clock; two printed
IDLER WHEELS and the gearmotor pinion bolt to it. The ring HANGS on the
wheels — their bodies carry the ring's inner bore (Ri) while a rib on each
wheel rides the segment's INNER retention groove, which is what keeps the
ring on the wall axis — and it is driven purely rotationally from the top
by the EXTERNAL spiral bevel pinion meshing the ring's outer teeth.

Load path:
  Two wheels at +/-wheel_az from top, wheel bodies rolling on the bore face
  (Ri). Hanging on two points near the top is the classic OP 015 case with
  the reduction for a second hang point; the dovetail keeps its full
  section (the gear left the band, so the joint never shares space with
  teeth). The groove rib carries only the ~0.5 N tip-off keeper load.

Standoff:
  The external bevel pinion's axis sits |z_p| behind the ring's wall face
  (bevel_geom), so the ring must float that far off the wall for the motor
  to fit in front of the drywall — plate_t defaults to 38. That standoff is
  the price of the outboard drive and is now the bracket's job.

Hardware: printed M6 screws (printed_hardware_stl) as wheel axles, threaded
into captive printed M6 nuts in the deck; wall mounting via two #10-24 pan
heads (or M5) through keyholes in the back plate. The N20-class worm
gearmotor (MEASURE the purchased unit; envelope parametric) drops into a
pocket with its output shaft pointing radially down, pinion on the shaft.

Self-checks (exits nonzero on FAIL): ring-on-wheels seat and settle, rib in
groove z-capture both ways, pinion mesh clearance at the hanging position,
wafer clearance across a full clocking sweep, hidden-radius bound, and
everything vs the wall plane.

    pip install manifold3d
    python3 scripts/bracket_stl.py            # -> stl/, self-checking
"""
from __future__ import annotations
import math, os, sys, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from segment_stl import (PARAMS, Cfg, prism, arc, build_ring, build_wafer,
                         bevel_geom, bevel_pinion, write_stl, report,
                         Manifold, HAVE_MANIFOLD)

BRK = dict(
    wheel_az = 25.0,   # idler azimuth, deg either side of top-dead-centre
    wheel_R  = 24.0,   # idler body radius (rolls on the bore face at Ri)
    wheel_w  = 5.2,    # idler body width in z
    rib_w    = 1.2,    # groove rib width  (groove ledge is grv_h = 1.5)
    rib_h    = 1.6,    # groove rib height (groove is grv_d = 2.0 deep)
    axle_D   = 6.8,    # wheel bore: spins on a printed M6 screw shank
    plate_t  = 38.0,   # bracket standoff wall-to-ring (see header)
    back_t   = 6.0,    # wall plate thickness
    key_gap  = 120.0,  # wall keyhole spacing, tangential
    key_d    = 5.5,    # keyhole slot width (#10 / M5 pan shank)
    key_D    = 11.0,   # keyhole entry (pan head passes)
    mot_D    = 12.5,   # N20 gearmotor body Ø (MEASURE the purchased unit)
    mot_L    = 26.0,   # N20 body length, gearbox included
    shaft_D  = 3.2,    # output shaft clearance bore
)


def box(x0, x1, y0, y1, z0, z1):
    return prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1 - z0)


def vcyl(r, z0, h, cx=0.0, cy=0.0, fn=256):
    return Manifold.cylinder(h, r, r, fn).translate([cx, cy, z0])


def zcyl_at(r, h, cx, cy, z0, fn=128):
    return Manifold.cylinder(h, r, r, fn).translate([cx, cy, z0])


class Brk:
    def __init__(self, cf, **kw):
        p = dict(BRK); p.update(kw); self.p = p
        for k, v in p.items(): setattr(self, k, v)
        self.cf = cf
        # wheel centres: bodies tangent to the bore face at Ri, at
        # +/-wheel_az from top (gravity -y, top = +y)
        self.d_c = cf.Ri - self.wheel_R                 # ring-centre distance
        self.wheels = []
        for s_ in (1, -1):
            a = math.radians(90.0 + s_ * self.wheel_az)
            self.wheels.append((self.d_c * math.cos(a), self.d_c * math.sin(a)))
        # groove z (scene coords: ring wall face at z_bot)
        self.g0 = cf.z_bot + cf.grv_z0                  # groove floor z
        self.g1 = self.g0 + cf.grv_h                    # ledge top
        # wheel body z-extent: from just off the ring back to under the
        # wafers' worst dip (clocking sweep checks it for real)
        self.w_lo = cf.z_bot + 0.3
        self.w_hi = self.w_lo + self.wheel_w
        self.rib_lo = self.g0 + (cf.grv_h - self.rib_w) / 2.0
        # deck the wheels/motor mount on, and the wall plate behind it
        self.deck_z = cf.z_bot - 0.8                    # deck front face
        self.wall_z = cf.z_bot - self.plate_t           # actual wall plane
        # pinion placement at 12 o'clock, from the shared bevel geometry
        bg = bevel_geom(cf)
        self.bg = bg
        self.pin_y0 = bg['x0']                          # big-end plane radius
        self.pin_z = cf.z_bot + bg['z_p']               # pinion axis z


def build_wheel(b):
    """Idler wheel, local frame (axis +z, wall side at z=0): body cylinder
    with the groove rib, axle bore through. Print flat, no supports."""
    w = vcyl(b.wheel_R, 0.0, b.wheel_w, fn=128)
    rib_z0 = b.rib_lo - b.w_lo
    w += vcyl(b.wheel_R + b.rib_h, rib_z0, b.rib_w, fn=128)
    w -= vcyl(b.axle_D / 2.0, -1.0, b.wheel_w + 2.0, fn=64)
    return w


def wheel_at(b, k):
    cx, cy = b.wheels[k]
    return build_wheel(b).translate([cx, cy, b.w_lo])


def build_plate(b):
    """The one bracket: wall plate (keyholed) + standoff shell + front deck
    carrying the wheel axle bosses and the motor pocket at 12 o'clock."""
    cf = b.cf
    y0, y1 = cf.Ri - 45.0, b.pin_y0 + 18.0          # radial span at the top
    x2 = 118.0                                       # half-width, covers wheels
    sh = 6.0                                         # shell wall
    body = box(-x2, x2, y0, y1, b.wall_z, b.deck_z)
    body -= box(-x2 + sh, x2 - sh, y0 + sh, y1 - sh,
                b.wall_z + b.back_t, b.deck_z - sh)  # hollow the standoff
    # wheel axle bosses: deck-mounted, captive M6 nut pocket from behind
    for cx, cy in b.wheels:
        body += zcyl_at(12.0, b.deck_z - b.wall_z, cx, cy, b.wall_z)
        body -= zcyl_at(3.4, b.deck_z - b.wall_z + 2.0, cx, cy, b.wall_z - 1.0)
        R = (10.0 + 0.45) / math.sqrt(3.0)           # M6 nut pocket
        hx = [(R * math.cos(math.radians(60 * i + 30)),
               R * math.sin(math.radians(60 * i + 30))) for i in range(6)]
        body -= (prism(hx, 0.0, 6.0).translate([cx, cy, b.wall_z + 2.0]))
    # motor pocket: body horizontal (tangential), output shaft down through
    # the deck at the pinion axis radius
    pkt = (Manifold.cylinder(b.mot_L + 2.0, b.mot_D / 2.0 + 0.4,
                             b.mot_D / 2.0 + 0.4, 96)
           .rotate([0.0, 90.0, 0.0])
           .translate([-(b.mot_L + 2.0) / 2.0, b.pin_y0 - b.bg['face'] / 2.0,
                       b.pin_z]))
    body -= pkt
    body -= zcyl_at(b.shaft_D / 2.0, b.plate_t, 0.0,
                    b.pin_y0 - b.bg['face'] / 2.0, b.wall_z - 1.0, fn=48)
    # wall keyholes in the back plate, slots running upward (gravity seats)
    for sx in (1.0, -1.0):
        kx = sx * b.key_gap / 2.0
        body -= zcyl_at(b.key_D / 2.0, b.back_t + 2.0, kx, y1 - 26.0,
                        b.wall_z - 1.0, fn=48)
        body -= box(kx - b.key_d / 2.0, kx + b.key_d / 2.0,
                    y1 - 26.0, y1 - 12.0, b.wall_z - 1.0,
                    b.wall_z + b.back_t + 1.0)
    return body


def pinion_at_top(cf, b, backlash=None):
    """The running pinion in the hanging scene: bevel_geom's mesh frame
    (contact at plan angle 0, wall face z=0) rotated to 12 o'clock and
    dropped onto the ring's wall face."""
    pin, _ = bevel_pinion(cf, backlash=backlash)
    return (pin.rotate([0.0, -90.0, 0.0])
               .translate([b.bg['x0'], 0.0, cf.z_bot + b.bg['z_p']])
               .rotate([0.0, 0.0, 90.0]))


def main():
    if not HAVE_MANIFOLD:
        sys.exit("needs manifold3d for STL output:  pip install manifold3d")
    ap = argparse.ArgumentParser(description="Wafer Halo — top idler bracket")
    ap.add_argument('-o', '--out', default='stl')
    for k, v in {**PARAMS, **BRK}.items():
        ap.add_argument(f'--{k}', type=type(v), default=None)
    a = ap.parse_args()
    cf = Cfg(**{k: getattr(a, k) for k in PARAMS if getattr(a, k) is not None})
    b = Brk(cf, **{k: getattr(a, k) for k in BRK if getattr(a, k) is not None})
    os.makedirs(a.out, exist_ok=True)

    assert cf.grv_d > 0, "segment has no inner groove (grv_d=0)"
    assert b.rib_h < cf.grv_d - 0.2, "rib bottoms out in the groove"
    assert b.rib_w < cf.grv_h - 0.2, "rib wider than the groove ledge"

    plate = build_plate(b)
    wheels = [wheel_at(b, k) for k in (0, 1)]
    pin = pinion_at_top(cf, b)
    bodies = build_ring(cf)
    frame = sum(bodies[1:], bodies[0])
    wafer_list = [build_wafer(cf, k) for k in range(cf.N)]
    wafers = sum(wafer_list[1:], wafer_list[0])
    ring = frame + wafers
    hardware = plate + wheels[0] + wheels[1] + pin

    W = 9 * (0.128 + 0.094) * 9.81  # N: 94 g/segment sliced at the outer drive
    print(f"Top idler bracket  ·  wheels Ø{2*b.wheel_R:.0f} at ±{b.wheel_az:.0f}° "
          f"from top, bodies on the bore at Ri={cf.Ri:.0f}, ribs in the groove")
    print(f"  hang    ring hangs on 2 wheels ({W:.1f} N est.); groove rib takes "
          f"only the tip-off keeper load")
    print(f"  drive   pinion at 12 o'clock, axis radial, {-b.bg['z_p']:.1f} behind "
          f"the ring's wall face — hence plate_t = {b.plate_t:.0f} standoff")
    print(f"  wall    back plate at z = {b.wall_z:.1f}; 2 keyholes {b.key_gap:.0f} "
          f"apart; motor pocket Ø{b.mot_D + 0.8:.1f} (MEASURE your N20)\n")

    EPS = 1e-6
    mv = lambda s_, v: s_.translate(list(v))
    checks = [
        ('ring nominal vs plate + pinion (wheels touch by design)',
         ((plate + pin) ^ ring).volume(), False),
        ('ring settles -0.3 onto both wheels',
         min((mv(ring, (0, -0.3, 0)) ^ wheels[0]).volume(),
             (mv(ring, (0, -0.3, 0)) ^ wheels[1]).volume()), True),
        ('ring lifted +0.5 comes free of the wheels',
         (mv(ring, (0, 0.5, 0)) ^ (wheels[0] + wheels[1])).volume(), False),
        ('ring pulled +0.5 off wall: ribs jam the groove ledge',
         (mv(ring, (0, 0, 0.5)) ^ (wheels[0] + wheels[1])).volume(), True),
        # -z has TWO stops: the groove's 45-deg chamfer roof is a ramp the
        # rib corner wedges against (~0.55 push), and the deck face backs it
        # up hard at 0.8 — probe past both
        ('ring pushed -0.8 to wall: rib ramp + deck stop it',
         (mv(ring, (0, 0, -0.8)) ^ (wheels[0] + wheels[1] + plate)).volume(), True),
        ('ring +0.1 z still free (axial float)',
         (mv(ring, (0, 0, 0.1)) ^ (wheels[0] + wheels[1])).volume(), False),
    ]
    # clocking sweep: the PLATE+WHEELS must clear frame+wafers at any ring
    # rotation. The pinion is excluded — its teeth only align at conjugate
    # phases, which segment_stl's gated mesh sweep already covers.
    worst_c = 0.0
    for i in range(1, 7):
        rr = ring.rotate([0, 0, i * (360.0 / cf.N) / 7.0])
        worst_c = max(worst_c, (plate ^ rr).volume())
    checks.append(('clocking sweep (7 over a sector): plate clears the ring',
                   worst_c, False))

    ok = True
    print("  checks:")
    for name, v, want in checks:
        good = (v > EPS) == want
        ok &= good
        print(f"    {'PASS' if good else 'FAIL':4}  {name:58} {v:10.4f}")

    bb = (plate + wheels[0] + wheels[1]).bounding_box()
    rmax = max(math.hypot(bb[0], bb[1]), math.hypot(bb[3], bb[4]),
               math.hypot(bb[0], bb[4]), math.hypot(bb[3], bb[1]))
    good = rmax <= 410.0
    ok &= good
    print(f"    {'PASS' if good else 'FAIL':4}  {'hidden: max plan radius':58} {rmax:10.1f}")
    good = plate.bounding_box()[2] >= b.wall_z - 1e-6
    ok &= good
    print(f"    {'PASS' if good else 'FAIL':4}  {'nothing behind the wall plane':58}")

    dz = -b.wall_z
    outs = [('bracket_plate.stl', [plate.translate([0, 0, dz])],
             'print wall-face down; M6 nut pockets from behind'),
            ('bracket_wheel.stl', [build_wheel(b)], 'print x2, flat, no supports'),
            ('bracket_fitcheck.stl',
             bodies + wafer_list + [plate, wheels[0], wheels[1], pin],
             'view only, hanging scene')]
    for fname, solids, note in outs:
        bod = write_stl(solids, os.path.join(a.out, fname))
        v = report(fname, solids, bod, note)
        if 'fitcheck' not in fname:
            print(f"{'':24}mass  30% infill {v*1.27e-3*0.30:6.1f} g   "
                  f"solid {v*1.27e-3:6.1f} g")

    print(f"\n{'ALL CHECKS PASS' if ok else 'CHECK FAILURES ABOVE — do not print'}")
    print(f"Wrote to {os.path.abspath(a.out)}/")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
