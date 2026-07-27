#!/usr/bin/env python3
"""
Wafer Halo — wall mounts (2026-07-26 crossed-drive rework, Nick's spec:
"standoffs get higher, bottom bracket gets smarter, and top bracket only
exists when we want to drive this bad boy").

TWO INDEPENDENT MOUNTS, nothing behind the frame:

  BOTTOM (always): a compact foot at 6 o'clock — small wall plate with two
  drywall-anchor holes INLINE VERTICALLY, a forward deck under the ring's
  bore. Two variants, same plate:
    * dynamic: two printed idler wheels riding IN the ring's OUTER
      mount groove (segment ogrv_* — an internal engagement can only
      HANG a ring; resting needs the outer surface). The groove walls
      keep the ring on the wall axis; one wheel is a knife-edge balance,
      so it stays two (±wheel_az from bottom).
    * static: a printed arc ridge nesting in the same groove over
      arc_span degrees — the ring sits in it, held steady.

  TOP (dynamic only): the drive. A shell wraps the Pololu #1596 micro
  metal gearmotor (10x12x26 rect body) with its SHAFT POINTING DOWN — the
  radial axis at 12 o'clock — and the 10T 45-deg pinion below it on the
  3 mm D-shaft (press fit, Nick: "assume it will hold pressure"). The
  shell hangs from a solid arm reaching forward from a wall plate whose
  two anchor holes sit ABOVE it, inline vertically, taking the deflection
  torque (~10 N tooth force x ~55 mm arm ~ 0.6 N.m across two anchors).

  The pinion's lower-outer teeth swing ~15 mm BEHIND the ring's wall
  face, so the bottom foot holds the ring wall_gap (18) off the drywall —
  the wall-plane check (which includes the pinion) gates it.

Self-checks exit nonzero on FAIL. pip install manifold3d
"""
from __future__ import annotations
import math, os, sys, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from segment_stl import (PARAMS, Cfg, prism, box, arc, hex_poly, build_ring,
                         build_wafer, bevel_geom, build_pinion, write_stl,
                         report, Manifold, HAVE_MANIFOLD,
                         M6_NUT_AF, M6_NUT_CLR)

BRK = dict(
    wheel_az = 25.0,   # idler azimuth, deg either side of bottom-dead-centre
    wheel_R  = 34.0,   # idler body radius (rides the OUTER groove floor —
                       # an internal engagement can only HANG a ring, so
                       # the bottom rest is external, in the riser's ogrv).
                       # 34, not 24: the axle shank and boss must clear the
                       # TEETH plan swing (r<=305.8) below the groove.
    axle_D   = 6.8,    # wheel bore: spins on a printed M6 screw shank
    arc_span = 60.0,   # static saddle arc, deg of groove it cradles
    wall_gap = 6.0,    # ring wall face to drywall (the small pinion dips
                       # only ~1.2 behind the wall face)
    back_t   = 6.0,    # wall plate thickness
    anchor_D = 5.0,    # drywall-anchor screw clearance (#8/#10 pan)
    anchor_gap = 50.0, # the two anchors sit this far apart, inline vertical
    mot_w    = 10.0,   # Pololu #1596 micro metal body: 10 x 12 mm RECT
    mot_h    = 12.0,   # cross section x ~26 long incl. gearbox; 3 mm
    mot_L    = 26.0,   # D-shaft x9 (pinion bore 3.2 + 0.4 flat fits)
    mot_clr  = 0.4,    # pocket clearance per side
    shell_t  = 3.0,    # motor shell wall
    shaft_D  = 3.4,    # shaft pass-through bore
)


def cyl(r, h, z0, cx=0.0, cy=0.0, fn=128):
    return Manifold.cylinder(h, r, r, fn).translate([cx, cy, z0])


class Brk:
    def __init__(self, cf, **kw):
        p = dict(BRK); p.update(kw)
        for k, v in p.items(): setattr(self, k, v)
        self.cf = cf
        self.bg = bevel_geom(cf)
        # wheel centres: bodies tangent to the OUTER groove floor, at
        # +/-wheel_az from BOTTOM — the ring RESTS on them (external
        # contact; groove walls are the axial keeper)
        self.o_floor = cf.Ro - cf.ogrv_d
        self.d_c = self.o_floor + self.wheel_R
        self.wheels = []
        for s_ in (1, -1):
            a = math.radians(270.0 + s_ * self.wheel_az)
            self.wheels.append((self.d_c * math.cos(a), self.d_c * math.sin(a)))
        self.w_w = cf.ogrv_w - 0.4                      # body width in groove
        self.w_lo = cf.z_bot + cf.ogrv_z0 + 0.2         # body z start
        self.deck_z = cf.z_bot - 0.8                    # deck front face
        self.wall_z = cf.z_bot - self.wall_gap          # drywall plane
        # top drive: pinion axis is the vertical line x=0 at this z
        self.pin_z = cf.z_bot + self.bg['zax']
        self.hub_top = self.bg['x1'] + self.bg['hub_len']   # y of hub top


# ---------------------------------------------------------------------------
# bottom foot (shared plate + deck; wheels or saddle on top of it)
# ---------------------------------------------------------------------------
def build_foot(b, static=False):
    cf = b.cf
    x2 = max(abs(w[0]) for w in b.wheels) + 20.0
    y_in = -(b.o_floor - 20.0)                   # top edge, above the groove
    y_out = -(b.d_c + b.wheel_R + 8.0)           # below the wheels
    body = box(-x2, x2, y_out, y_in, b.wall_z, b.wall_z + b.back_t)  # plate
    # deck: forward slab BELOW the ring's teeth plan radius, stopping just
    # behind the ring's wall face
    body += box(-x2, x2, y_out, -308.0, b.wall_z, b.deck_z)
    # anchor holes, INLINE VERTICALLY on the centreline
    ya = (y_out + -308.0) / 2.0
    for dy in (b.anchor_gap / 2.0, -b.anchor_gap / 2.0):
        body -= cyl(b.anchor_D / 2.0, b.back_t + 2.0, b.wall_z - 1.0,
                    0.0, ya + dy, fn=48)
    if static:
        # arc slab whose inner lip rides IN the outer groove (0.05 datum
        # standoff); everything else stays radially OUTSIDE the teeth
        # swing (r > 306) — the teeth sweep the annulus below the groove
        a0 = math.radians(270.0 - b.arc_span / 2.0)
        a1 = math.radians(270.0 + b.arc_span / 2.0)
        body += prism(arc(b.o_floor + 0.05, a0, a1, 96) +
                      arc(308.0 + 6.0, a1, a0, 96), b.w_lo, b.w_w)
        body += prism(arc(308.0, a0, a1, 96) +
                      arc(308.0 + 6.0, a1, a0, 96),
                      b.deck_z - 0.1, b.w_lo - b.deck_z + 0.2)
    else:
        # axle bosses (outside the tooth swing) with captive printed-M6
        # nut pockets from behind
        for cx, cy in b.wheels:
            body += cyl(10.0, b.w_lo + b.w_w + 2.0 - b.wall_z, b.wall_z,
                        cx, cy)
            body -= cyl(b.axle_D / 2.0, 60.0, b.wall_z - 1.0, cx, cy)
            body -= (prism(hex_poly(M6_NUT_AF, M6_NUT_CLR), 0.0, 6.0)
                     .translate([cx, cy, b.wall_z + 2.0]))
    return body


def build_wheel(b):
    w = cyl(b.wheel_R, b.w_w, 0.0)
    w -= cyl(b.axle_D / 2.0, b.w_w + 2.0, -1.0, fn=64)
    return w


def wheel_at(b, k):
    cx, cy = b.wheels[k]
    return build_wheel(b).translate([cx, cy, b.w_lo])


# ---------------------------------------------------------------------------
# top drive unit (dynamic only)
# ---------------------------------------------------------------------------
def pinion_at_top(cf, b, backlash=None):
    """The running pinion in the scene: mesh frame (axis radial on +x,
    tooth 0 pointing down at the ring) rotated to 12 o'clock, phase-shimmed
    to the ring space nearest the meridian for any tooth count."""
    pin, _ = build_pinion(cf, backlash=backlash)
    pitch = 360.0 / cf.teeth
    eps = (90.0 + math.degrees(cf.half)) % pitch
    if eps > pitch / 2.0:
        eps -= pitch
    return (pin.rotate([0.0, 0.0, eps * cf.pin_ratio])
               .rotate([0.0, 90.0, 0.0])
               .translate([b.bg['x0'], 0.0, cf.z_bot + b.bg['zax']])
               .rotate([0.0, 0.0, 90.0]))


def build_top(b):
    """Motor shell + arm + wall plate. Scene frame: the pinion axis is the
    vertical line (x=0, z=pin_z); the motor sits above the pinion hub,
    shaft down; the anchors sit above everything, inline vertically."""
    cf = b.cf
    w2 = b.mot_w / 2.0 + b.mot_clr               # pocket half-widths
    h2 = b.mot_h / 2.0 + b.mot_clr
    sx = w2 + b.shell_t                          # shell half-extents
    sz = h2 + b.shell_t
    y_mot0 = b.hub_top + 0.5                     # motor bottom face
    y_mot1 = y_mot0 + b.mot_L
    y_top = y_mot1 + b.shell_t                   # shell closed top
    # shell around the motor
    shell = box(-sx, sx, y_mot0 - b.shell_t, y_top,
                b.pin_z - sz, b.pin_z + sz)
    shell -= box(-w2, w2, y_mot0, y_mot1 + 0.1, b.pin_z - h2, b.pin_z + h2)
    # shaft/hub opening in the shell bottom
    shell -= (Manifold.cylinder(b.shell_t + 2.0, 9.0, 9.0, 64)
              .rotate([-90.0, 0.0, 0.0])
              .translate([0.0, y_mot0 - b.shell_t - 1.0, b.pin_z]))
    # arm: solid beam from the wall to the shell, above the motor top
    arm = box(-sx, sx, y_mot1 - 6.0, y_top, b.wall_z, b.pin_z - sz + 1.0)
    # wall plate with the two anchors ABOVE, inline vertical
    y_pl0 = y_top - 6.0
    y_pl1 = y_pl0 + b.anchor_gap + 24.0
    plate = box(-16.0, 16.0, y_pl0, y_pl1, b.wall_z, b.wall_z + b.back_t)
    ya = y_pl0 + 12.0
    for dy in (0.0, b.anchor_gap):
        plate -= cyl(b.anchor_D / 2.0, b.back_t + 2.0, b.wall_z - 1.0,
                     0.0, ya + dy, fn=48)
    # gusset tying arm to plate
    guss = box(-3.0, 3.0, y_mot1 - 6.0, y_pl1 - 4.0,
               b.wall_z, b.wall_z + 14.0)
    return shell + arm + plate + guss


# ---------------------------------------------------------------------------
def main():
    if not HAVE_MANIFOLD:
        sys.exit("needs manifold3d for STL output:  pip install manifold3d")
    ap = argparse.ArgumentParser(description="Wafer Halo — wall mounts")
    ap.add_argument('-o', '--out', default='stl')
    for k, v in {**PARAMS, **BRK}.items():
        ap.add_argument(f'--{k}', type=type(v), default=None)
    a = ap.parse_args()
    cf = Cfg(**{k: getattr(a, k) for k in PARAMS if getattr(a, k) is not None})
    b = Brk(cf, **{k: getattr(a, k) for k in BRK if getattr(a, k) is not None})
    os.makedirs(a.out, exist_ok=True)

    assert cf.ogrv_w > 0, "segment has no outer mount groove (ogrv_w=0)"
    assert b.w_w < cf.ogrv_w, "wheel body wider than the outer groove"

    foot = build_foot(b)
    foot_static = build_foot(b, static=True)
    wheels = [wheel_at(b, k) for k in (0, 1)]
    pin = pinion_at_top(cf, b)
    top = build_top(b)
    bodies = build_ring(cf)
    wafer_list = [build_wafer(cf, k) for k in range(cf.N)]
    ring_parts = bodies + wafer_list

    W = cf.N * (0.128 + 0.115) * 9.81  # N: Si + ~115 g/segment PLA@10 est
    print(f"Wafer Halo wall mounts  ·  ring rests on the bottom foot; the "
          f"drive hangs above (dynamic only)")
    print(f"  bottom  wheels Ø{2*b.wheel_R:.0f} at ±{b.wheel_az:.0f}° from "
          f"bottom (static: {b.arc_span:.0f}° arc saddle); 2 anchors inline "
          f"vertical, {b.anchor_gap:.0f} apart; ring carries ~{W:.1f} N")
    print(f"  top     Pololu #1596 shell ({b.mot_w:.0f}×{b.mot_h:.0f}×"
          f"{b.mot_L:.0f} pocket), shaft DOWN into the {cf.pin_T}T pinion at "
          f"z {b.pin_z:.1f}; ratio {cf.pin_ratio:.1f}:1 — 1.00 rpm at 5 V")
    dip = (b.bg['x1'] - b.bg['apex']) * 1.2 - b.bg['zax']
    print(f"  wall    drywall at z = {b.wall_z:.1f} (ring floats "
          f"{b.wall_gap:.0f} off it — the pinion swings {dip:.1f} behind "
          f"the ring's wall face)\n")

    EPS = 1e-6
    mv = lambda s_, v: s_.translate(list(v))
    ring = None
    checks = []
    def add(name, vol, want):
        checks.append((name, vol, want))

    both = wheels[0] + wheels[1]
    frame = sum(bodies[1:], bodies[0])
    hardware = foot + pin + top
    worst_n = max((p_ ^ hardware).volume() for p_ in ring_parts)
    add('ring nominal vs foot + pinion + top (wheels touch by design)',
        worst_n, False)
    add('ring nominal vs the STATIC foot (saddle 0.05 standoff)',
        max((p_ ^ foot_static).volume() for p_ in ring_parts), False)
    add('ring settles -0.3 onto both wheels',
        min((mv(frame, (0, -0.3, 0)) ^ wheels[0]).volume(),
            (mv(frame, (0, -0.3, 0)) ^ wheels[1]).volume()), True)
    add('ring settles -0.3 into the static saddle',
        (mv(frame, (0, -0.3, 0)) ^ foot_static).volume(), True)
    add('ring lifted +0.5 comes free of the wheels',
        (mv(frame, (0, 0.5, 0)) ^ both).volume(), False)
    add('ring pulled +0.5 off wall: groove roof jams the wheels',
        (mv(frame, (0, 0, 0.5)) ^ both).volume(), True)
    add('ring pushed -0.8 to wall: groove wall + deck stop it',
        (mv(frame, (0, 0, -0.8)) ^ (both + foot)).volume(), True)
    add('ring +0.1 z still free (axial float)',
        (mv(frame, (0, 0, 0.1)) ^ both).volume(), False)
    worst_c = 0.0
    for i in range(1, 7):
        rr = frame.rotate([0, 0, i * (360.0 / cf.N) / 7.0])
        worst_c = max(worst_c, ((foot + top) ^ rr).volume())
    add('clocking sweep (7 over a sector): foot+top clear the ring', worst_c,
        False)
    waf = sum(wafer_list[1:], wafer_list[0])
    add('pinion + top shell vs wafers', ((pin + top) ^ waf).volume(), False)

    ok = True
    print("  checks:")
    for name, v, want in checks:
        good = (v > EPS) == want
        ok &= good
        print(f"    {'PASS' if good else 'FAIL':4}  {name:58} {v:10.4f}")

    HIDE_R_MAX = 410.0   # hide-window outer radius (~416) − margin
    solids = [foot, foot_static, wheels[0], wheels[1], top, pin]
    rmax = 0.0
    zmin = 1e9
    for s_ in solids:
        bb = s_.bounding_box()
        rmax = max(rmax, math.hypot(bb[0], bb[1]), math.hypot(bb[3], bb[4]),
                   math.hypot(bb[0], bb[4]), math.hypot(bb[3], bb[1]))
        zmin = min(zmin, bb[2])
    good = rmax <= HIDE_R_MAX
    ok &= good
    print(f"    {'PASS' if good else 'FAIL':4}  {'hidden: max plan radius':58} {rmax:10.1f}")
    good = zmin >= b.wall_z - 1e-6
    ok &= good
    print(f"    {'PASS' if good else 'FAIL':4}  "
          f"{'nothing behind the wall plane (incl. pinion)':58} {zmin:10.1f}")

    dz = -b.wall_z
    outs = [('bracket_bottom.stl', [foot.translate([0, 0, dz])],
             'dynamic foot: print wall-face down'),
            ('bracket_bottom_static.stl', [foot_static.translate([0, 0, dz])],
             'static foot + arc saddle: print wall-face down'),
            ('bracket_top.stl', [top.translate([0, 0, dz])],
             'drive shell: print wall-face down, supports under the shell'),
            ('bracket_wheel.stl', [build_wheel(b)], 'print x2, flat'),
            ('bracket_fitcheck.stl',
             bodies + wafer_list + [foot, wheels[0], wheels[1], top, pin],
             'view only, dynamic scene')]
    for fname, solids_, note in outs:
        bod = write_stl(solids_, os.path.join(a.out, fname))
        v = report(fname, solids_, bod, note)
        if 'fitcheck' not in fname:
            print(f"{'':24}mass  15% PLA (rough) {v*1.24e-3*0.15:6.1f} g   "
                  f"solid {v*1.24e-3:6.1f} g")

    print(f"\n{'ALL CHECKS PASS' if ok else 'CHECK FAILURES ABOVE — do not print'}")
    print(f"Wrote to {os.path.abspath(a.out)}/")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
