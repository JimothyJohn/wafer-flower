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

Drive (2026-07-25 parallel-axis rework): the pinion is a BEVELOID on an
AXIAL axis — parallel to the halo axis, at centre distance C above the
ring at 12 o'clock, big end forward, meshing the ring's big-at-wall cone.
The N20 gearmotor sits in an AXIAL pocket behind it, output shaft pointing
out of the wall ("motor inline, i.e. perpendicular" — Nick). A radial-axis
bevel pinion is impossible here: its swept Ø90 disc spans +/-45 along the
wall normal vs the 38 mm standoff (it poked 39 mm through the drywall —
caught 2026-07-25 when the wall check finally included the pinion).

Standoff: plate_t = 76 (2026-07-25, Nick: twice the original 38 — room for
the motor) hides the wheels, the N20 body (26 long, MEASURE it) and the
pinion hub behind the ring with depth to spare for a longer gearmotor.

Hardware: printed M6 screws (printed_hardware_stl) as wheel axles, threaded
into captive printed M6 nuts in the deck; wall mounting via two #10-24 pan
heads (or M5) through keyholes in the back plate. The N20-class worm
gearmotor (MEASURE the purchased unit; envelope parametric) drops into the
axial pocket, D-shaft forward into the pinion hub.

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
from segment_stl import (PARAMS, Cfg, prism, box, hex_poly, build_ring,
                         build_wafer, bevel_geom, build_pinion, write_stl,
                         report, Manifold, HAVE_MANIFOLD,
                         M6_NUT_AF, M6_NUT_CLR)

BRK = dict(
    wheel_az = 25.0,   # idler azimuth, deg either side of top-dead-centre
    wheel_R  = 24.0,   # idler body radius (rolls on the bore face at Ri)
    wheel_w  = 5.2,    # idler body width in z
    rib_w    = 1.2,    # groove rib width  (groove ledge is grv_h = 1.5)
    rib_h    = 1.6,    # groove rib height (groove is grv_d = 2.0 deep)
    axle_D   = 6.8,    # wheel bore: spins on a printed M6 screw shank
    plate_t  = 76.0,   # bracket standoff wall-to-ring (2x, motor room; see header)
    back_t   = 6.0,    # wall plate thickness
    key_gap  = 120.0,  # wall keyhole spacing, tangential
    key_d    = 5.5,    # keyhole slot width (#10 / M5 pan shank)
    key_D    = 11.0,   # keyhole entry (pan head passes)
    mot_w    = 10.0,   # Pololu micro metal gearmotor body (#1596 1000:1
    mot_h    = 12.0,   # LP 6V, 13 rpm): 10 x 12 mm RECTANGULAR cross
    mot_L    = 26.0,   # section x ~26 long incl. gearbox — a round pocket
                       # can't hold it (15.6 mm diagonal). 3 mm D-shaft,
                       # 9 mm long; the pinion's 3.2 bore + 0.4 flat fits.
    mot_clr  = 0.4,    # pocket clearance per side
    shaft_D  = 3.2,    # output shaft clearance bore
)


def cyl(r, h, z0, cx=0.0, cy=0.0, fn=128):
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
        # wheel body z-extent: from just off the ring back to under the
        # wafers' worst dip (clocking sweep checks it for real)
        self.w_lo = cf.z_bot + 0.3
        self.rib_lo = self.g0 + (cf.grv_h - self.rib_w) / 2.0
        # deck the wheels/motor mount on, and the wall plate behind it
        self.deck_z = cf.z_bot - 0.8                    # deck front face
        self.wall_z = cf.z_bot - self.plate_t           # actual wall plane
        # pinion placement at 12 o'clock, from the shared beveloid geometry:
        # AXIAL axis at (0, C), teeth spanning the band z, Ø16 hub 5 mm deep
        # behind the wall face (the deck gets a recess for it), N20 in an
        # axial pocket behind the recess floor
        bg = bevel_geom(cf)
        self.pin_C = bg['C']                            # pinion axis radius
        self.recess_z = cf.z_bot - bg['hub_len'] - 0.5  # hub recess floor


def build_wheel(b):
    """Idler wheel, local frame (axis +z, wall side at z=0): body cylinder
    with the groove rib, axle bore through. Print flat, no supports."""
    w = cyl(b.wheel_R, b.wheel_w, 0.0)
    w += cyl(b.wheel_R + b.rib_h, b.rib_w, b.rib_lo - b.w_lo)
    w -= cyl(b.axle_D / 2.0, b.wheel_w + 2.0, -1.0, fn=64)
    return w


def wheel_at(b, k):
    cx, cy = b.wheels[k]
    return build_wheel(b).translate([cx, cy, b.w_lo])


def build_plate(b):
    """The one bracket: wall plate (keyholed) + standoff shell + front deck
    carrying the wheel axle bosses and the motor pocket at 12 o'clock."""
    cf = b.cf
    y0, y1 = cf.Ri - 45.0, b.pin_C + 22.0            # radial span at the top
    x2 = 118.0                                       # half-width, covers wheels
    sh = 6.0                                         # shell wall
    body = box(-x2, x2, y0, y1, b.wall_z, b.deck_z)
    body -= box(-x2 + sh, x2 - sh, y0 + sh, y1 - sh,
                b.wall_z + b.back_t, b.deck_z - sh)  # hollow the standoff
    # wheel axle bosses: deck-mounted, captive M6 nut pocket from behind
    for cx, cy in b.wheels:
        body += cyl(12.0, b.deck_z - b.wall_z, b.wall_z, cx, cy)
        body -= cyl(b.axle_D / 2.0, b.deck_z - b.wall_z + 2.0,
                    b.wall_z - 1.0, cx, cy)
        body -= (prism(hex_poly(M6_NUT_AF, M6_NUT_CLR), 0.0, 6.0)
                 .translate([cx, cy, b.wall_z + 2.0]))
    # motor boss + AXIAL pocket at (0, C): solid boss through the shell,
    # front recess for the pinion hub, N20 body pocket behind it (shaft
    # pointing forward, out of the wall)
    boss_r = math.hypot(b.mot_w, b.mot_h) / 2.0 + 4.0
    body += cyl(boss_r, b.deck_z - b.wall_z, b.wall_z, 0.0, b.pin_C, fn=96)
    body -= cyl(10.5, b.deck_z - b.recess_z + 1.0, b.recess_z,
                0.0, b.pin_C, fn=96)                 # hub recess, open front
    # RECTANGULAR motor pocket (10x12 body flat against the shaft plane;
    # the wide face parallel to the wall)
    w2 = b.mot_w / 2.0 + b.mot_clr
    h2 = b.mot_h / 2.0 + b.mot_clr
    body -= box(-h2, h2, b.pin_C - w2, b.pin_C + w2,
                b.recess_z - b.mot_L - 1.0, b.recess_z + 0.5)
    # wall keyholes in the back plate, slots running upward (gravity seats)
    for sx in (1.0, -1.0):
        kx = sx * b.key_gap / 2.0
        body -= cyl(b.key_D / 2.0, b.back_t + 2.0, b.wall_z - 1.0,
                    kx, y1 - 26.0, fn=48)
        body -= box(kx - b.key_d / 2.0, kx + b.key_d / 2.0,
                    y1 - 26.0, y1 - 12.0, b.wall_z - 1.0,
                    b.wall_z + b.back_t + 1.0)
    return body


def pinion_at_top(cf, b, backlash=None):
    """The running pinion (with hub + D-bore) in the hanging scene:
    bevel_geom's mesh frame (axis at (C,0), teeth z 0..gear_F off the wall
    face) rotated to 12 o'clock, with a computed phase shim so the pinion
    meshes the ring space nearest 12 o'clock for ANY tooth count (spaces
    tile k*pitch from the joints; the shim is 0 whenever teeth/4 is an
    integer, as at B.3's 108T)."""
    pin, _ = build_pinion(cf, backlash=backlash)
    pitch = 360.0 / cf.teeth
    eps = (90.0 + math.degrees(cf.half)) % pitch
    if eps > pitch / 2.0:
        eps -= pitch
    return (pin.rotate([0.0, 0.0, eps * cf.teeth / cf.tps])
               .translate([b.pin_C, 0.0, cf.z_bot])
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
    W = cf.N * (0.128 + 0.049) * 9.81   # N: Si + 48.6 g/segment PLA@10 sliced
    print(f"Top idler bracket  ·  wheels Ø{2*b.wheel_R:.0f} at ±{b.wheel_az:.0f}° "
          f"from top, bodies on the bore at Ri={cf.Ri:.0f}, ribs in the groove")
    print(f"  hang    ring hangs on 2 wheels ({W:.1f} N est.); groove rib takes "
          f"only the tip-off keeper load")
    print(f"  drive   beveloid pinion at 12 o'clock, axis AXIAL at r={b.pin_C:.1f} "
          f"— motor points out of the wall, body + hub inside the "
          f"plate_t = {b.plate_t:.0f} standoff")
    print(f"  wall    back plate at z = {b.wall_z:.1f}; 2 keyholes {b.key_gap:.0f} "
          f"apart; motor pocket {b.mot_w + 2*b.mot_clr:.1f} x "
          f"{b.mot_h + 2*b.mot_clr:.1f} rect (Pololu #1596 micro metal)\n")

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
    HIDE_R_MAX = 410.0   # hide-window outer radius (~416 at B.3) − margin
    good = rmax <= HIDE_R_MAX
    ok &= good
    print(f"    {'PASS' if good else 'FAIL':4}  {'hidden: max plan radius':58} {rmax:10.1f}")
    # EVERYTHING vs the drywall — plate, wheels AND the pinion. The first
    # outer-drive build checked the plate only, and the radial-axis Ø90
    # pinion sailed 39 mm through the drywall unnoticed.
    zmin = min(s_.bounding_box()[2] for s_ in (plate, wheels[0], wheels[1], pin))
    good = zmin >= b.wall_z - 1e-6
    ok &= good
    print(f"    {'PASS' if good else 'FAIL':4}  "
          f"{'nothing behind the wall plane (incl. pinion)':58} {zmin:10.1f}")

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
            print(f"{'':24}mass  15% PLA (rough) {v*1.24e-3*0.15:6.1f} g   "
                  f"solid {v*1.24e-3:6.1f} g")

    print(f"\n{'ALL CHECKS PASS' if ok else 'CHECK FAILURES ABOVE — do not print'}")
    print(f"Wrote to {os.path.abspath(a.out)}/")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
