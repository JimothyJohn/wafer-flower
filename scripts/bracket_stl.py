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
    wheel_az = 12.0,   # idler azimuth, deg either side of TOP-dead-centre —
                       # tight under the motor (2026-07-26, Nick: "right
                       # underneath the motor… idling to preload the motor
                       # pinion"). The wheels fix the ring's radial datum
                       # AT the meshing meridian, so tooth engagement can't
                       # breathe.
    wheel_R  = 24.0,   # idler body radius: bodies on the BORE at Ri, rib
                       # in the INNER groove — internal engagement at the
                       # top HANGS the ring (external can only rest it)
    wheel_w  = 5.2,    # body width; rib rides the inner groove ledge
    rib_w    = 1.2,
    rib_h    = 1.6,
    axle_D   = 6.8,    # wheel bore: spins on a printed M6 screw shank
    slot_T   = 16.0,   # shell mounting-slot travel (radial) for preload
    arc_span = 52.0,   # static saddle arc, deg of groove it cradles
                       # (60 made the print 348 wide — H2S bed is 340)
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
        # wheel centres: bodies tangent to the bore at Ri, at +/-wheel_az
        # from TOP — the ring HANGS on them, right under the motor
        self.o_floor = cf.Ro - cf.ogrv_d                # (static saddle datum)
        self.d_c = cf.Ri - self.wheel_R
        self.wheels = []
        for s_ in (1, -1):
            a = math.radians(90.0 + s_ * self.wheel_az)
            self.wheels.append((self.d_c * math.cos(a), self.d_c * math.sin(a)))
        self.g0 = cf.z_bot + cf.grv_z0                  # inner groove floor z
        self.rib_lo = self.g0 + (cf.grv_h - self.rib_w) / 2.0
        self.w_lo = cf.z_bot + 0.3                      # body z start
        self.deck_z = cf.z_bot - 0.8                    # deck front face
        self.wall_z = cf.z_bot - self.wall_gap          # drywall plane
        # top drive: pinion axis is the vertical line x=0 at this z
        self.pin_z = cf.z_bot + self.bg['zax']
        self.hub_top = self.bg['x1'] + self.bg['hub_len']   # y of hub top


# ---------------------------------------------------------------------------
# bottom foot (shared plate + deck; wheels or saddle on top of it)
# ---------------------------------------------------------------------------
def build_foot(b):
    """STATIC mount only (the dynamic ring hangs from the top unit): an
    arc saddle nesting in the OUTER groove at 6 o'clock, everything else
    outside the tooth swing (r > 306)."""
    cf = b.cf
    ow = cf.ogrv_w - 0.4
    o_lo = cf.z_bot + cf.ogrv_z0 + 0.2
    a0 = math.radians(270.0 - b.arc_span / 2.0)
    a1 = math.radians(270.0 + b.arc_span / 2.0)
    x2 = 320.0 * math.sin(math.radians(b.arc_span / 2.0)) + 14.0
    y_out = -334.0
    body = box(-x2, x2, y_out, -308.0, b.wall_z, b.wall_z + b.back_t)
    body += box(-x2, x2, y_out, -308.0, b.wall_z, b.deck_z)
    ya = (y_out - 308.0) / 2.0
    for dy in (b.anchor_gap / 2.0, -b.anchor_gap / 2.0):
        body -= cyl(b.anchor_D / 2.0, b.back_t + 2.0, b.wall_z - 1.0,
                    0.0, ya + dy, fn=48)
    body += prism(arc(b.o_floor + 0.05, a0, a1, 96) +
                  arc(308.0 + 6.0, a1, a0, 96), o_lo, ow)
    body += prism(arc(308.0, a0, a1, 96) +
                  arc(308.0 + 6.0, a1, a0, 96),
                  b.deck_z - 0.1, o_lo - b.deck_z + 0.2)
    return body


def build_wheel(b):
    """Bore-riding idler: body on Ri, rib in the INNER groove (axial
    keeper). Local frame: wall side at z=0."""
    w = cyl(b.wheel_R, b.wheel_w, 0.0)
    w += cyl(b.wheel_R + b.rib_h, b.rib_w, b.rib_lo - b.w_lo)
    w -= cyl(b.axle_D / 2.0, b.wheel_w + 2.0, -1.0, fn=64)
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
    """The dynamic mount: ONE unit at 12 o'clock — wall plate (anchors
    above, inline vertical), two wheel towers reaching into the bore
    (the ring HANGS on the wheels, right under the motor), and a slide
    face with captive printed-M6 nuts that the slotted motor shell
    clamps to. Sliding the shell radially sets the pinion preload
    against the wheel datum."""
    cf = b.cf
    # wall plate spanning the wheel towers and reaching above the shell
    x2 = max(abs(w[0]) for w in b.wheels) + 18.0
    y_lo = min(w[1] for w in b.wheels) - 18.0
    ya = b.hub_top + b.mot_L + 10.0
    y_top = ya + b.anchor_gap + 8.0
    # wide plate over the wheels/shell, narrow anchor strip above — a
    # wide corner at y_top would poke past the hide radius (411 > 410)
    body = box(-x2, x2, y_lo, ya - 2.0, b.wall_z, b.wall_z + b.back_t)
    body += box(-16.0, 16.0, ya - 10.0, y_top, b.wall_z,
                b.wall_z + b.back_t)
    for dy in (0.0, b.anchor_gap):
        body -= cyl(b.anchor_D / 2.0, b.back_t + 2.0, b.wall_z - 1.0,
                    0.0, ya + dy, fn=48)
    # wheel towers: bosses from the plate forward, captive M6 nut pockets
    for cx, cy in b.wheels:
        body += cyl(10.0, b.w_lo + b.wheel_w + 2.0 - b.wall_z, b.wall_z,
                    cx, cy)
        body -= cyl(b.axle_D / 2.0, 60.0, b.wall_z - 1.0, cx, cy)
        body -= (prism(hex_poly(M6_NUT_AF, M6_NUT_CLR), 0.0, 6.0)
                 .translate([cx, cy, b.wall_z + 2.0]))
    # slide face for the shell ears: a deck at the meridian whose front
    # face sits just behind the shell's ear plane, with two captive M6
    # nuts; the ears' vertical slots ride on printed M6 screws
    ear_x = b.mot_w / 2.0 + b.mot_clr + b.shell_t + 8.0
    face_z = b.pin_z - (b.mot_h / 2.0 + b.mot_clr + b.shell_t) - 4.0
    # the deck starts ABOVE the tooth swing (teeth reach plan r 305.8)
    body += box(-ear_x - 8.0, ear_x + 8.0, 306.5,
                b.hub_top + b.mot_L + 6.0, b.wall_z, face_z)
    for sx_ in (ear_x, -ear_x):
        body -= cyl(3.4, 60.0, b.wall_z - 1.0, sx_, b.hub_top + b.mot_L / 2.0)
        body -= (prism(hex_poly(M6_NUT_AF, M6_NUT_CLR), 0.0, 6.0)
                 .translate([sx_, b.hub_top + b.mot_L / 2.0,
                             b.wall_z + 2.0]))
    return body


def build_shell(b):
    """The slotted motor shell: wraps the Pololu #1596 (shaft down
    through the bottom opening onto the pinion hub) with two ears whose
    VERTICAL SLOTS (slot_T travel) clamp to the top unit's slide face —
    slide to set pinion-tooth preload, then tighten."""
    w2 = b.mot_w / 2.0 + b.mot_clr
    h2 = b.mot_h / 2.0 + b.mot_clr
    sx = w2 + b.shell_t
    sz = h2 + b.shell_t
    y_mot0 = b.hub_top + 0.5
    y_mot1 = y_mot0 + b.mot_L
    y_top = y_mot1 + b.shell_t
    shell = box(-sx, sx, y_mot0 - b.shell_t, y_top,
                b.pin_z - sz, b.pin_z + sz)
    shell -= box(-w2, w2, y_mot0, y_mot1 + 0.1, b.pin_z - h2, b.pin_z + h2)
    shell -= (Manifold.cylinder(b.shell_t + 2.0, 9.0, 9.0, 64)
              .rotate([-90.0, 0.0, 0.0])
              .translate([0.0, y_mot0 - b.shell_t - 1.0, b.pin_z]))
    # ears: vertical plates flanking the shell, slotted for the slide.
    # They OVERLAP the shell wall by 1 mm in x and z — cap-to-cap unions
    # on a shared plane weld OPEN (the coplanar-seam trap).
    ear_x = sx + 8.0
    ear_z0 = b.pin_z - sz - 4.0                  # against the slide face
    yc = b.hub_top + b.mot_L / 2.0
    for s_ in (1.0, -1.0):
        x_in, x_out = (sx - 1.0, ear_x + 6.0) if s_ > 0 else \
                      (-ear_x - 6.0, -sx + 1.0)
        ear = box(x_in, x_out, y_mot0 - b.shell_t, y_top,
                  ear_z0, b.pin_z - sz + 1.0)
        slot = (cyl(3.4, 8.0, ear_z0 - 1.0, s_ * ear_x, yc - b.slot_T / 2.0)
                + cyl(3.4, 8.0, ear_z0 - 1.0, s_ * ear_x, yc + b.slot_T / 2.0)
                + box(s_ * ear_x - 3.4, s_ * ear_x + 3.4,
                      yc - b.slot_T / 2.0, yc + b.slot_T / 2.0,
                      ear_z0 - 1.0, ear_z0 + 7.0))
        shell += ear - slot
    return shell


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
    assert cf.grv_d > 0, "segment has no inner groove for the idlers"
    assert b.rib_h < cf.grv_d - 0.2, "rib bottoms out in the inner groove"
    assert b.rib_w < cf.grv_h - 0.2, "rib wider than the groove ledge"

    foot_static = build_foot(b)
    wheels = [wheel_at(b, k) for k in (0, 1)]
    pin = pinion_at_top(cf, b)
    top = build_top(b)
    shell = build_shell(b)
    bodies = build_ring(cf)
    wafer_list = [build_wafer(cf, k) for k in range(cf.N)]
    ring_parts = bodies + wafer_list

    W = cf.N * (0.128 + 0.085) * 9.81  # N: Si + ~85 g/segment PLA@10
    print(f"Wafer Halo wall mounts  ·  dynamic: ONE top unit (ring hangs on "
          f"bore idlers right under the motor); static: bottom saddle")
    print(f"  top     wheels Ø{2*b.wheel_R:.0f} at ±{b.wheel_az:.0f}° from "
          f"top INSIDE the bore (preload datum at the mesh meridian); "
          f"Pololu #1596 shell on ±{b.slot_T/2:.0f} mm SLOTS for pinion "
          f"preload, shaft DOWN, ratio {cf.pin_ratio:.1f}:1 — 1.00 rpm @5 V; "
          f"ring hangs ~{W:.1f} N")
    dip = (b.bg['x1'] - b.bg['apex']) * 1.2 - b.bg['zax']
    print(f"  wall    drywall at z = {b.wall_z:.1f}; the pinion swings "
          f"{dip:.1f} behind the ring's wall face\n")

    EPS = 1e-6
    mv = lambda s_, v: s_.translate(list(v))
    ring = None
    checks = []
    def add(name, vol, want):
        checks.append((name, vol, want))

    both = wheels[0] + wheels[1]
    frame = sum(bodies[1:], bodies[0])
    hardware = pin + top + shell
    worst_n = max((p_ ^ hardware).volume() for p_ in ring_parts)
    add('ring nominal vs top unit + shell + pinion (wheels by design)',
        worst_n, False)
    add('ring nominal vs the STATIC foot (saddle 0.05 standoff)',
        max((p_ ^ foot_static).volume() for p_ in ring_parts), False)
    add('ring settles -0.3 onto both hanging wheels',
        min((mv(frame, (0, -0.3, 0)) ^ wheels[0]).volume(),
            (mv(frame, (0, -0.3, 0)) ^ wheels[1]).volume()), True)
    add('ring settles -0.3 into the static saddle',
        (mv(frame, (0, -0.3, 0)) ^ foot_static).volume(), True)
    add('ring lifted +0.5 comes free of the wheels',
        (mv(frame, (0, 0.5, 0)) ^ both).volume(), False)
    add('ring pulled +0.5 off wall: ribs jam the inner-groove ledge',
        (mv(frame, (0, 0, 0.5)) ^ both).volume(), True)
    add('ring pushed -0.8 to wall: rib ramp + towers stop it',
        (mv(frame, (0, 0, -0.8)) ^ (both + top)).volume(), True)
    add('ring +0.1 z still free (axial float)',
        (mv(frame, (0, 0, 0.1)) ^ both).volume(), False)
    worst_c = 0.0
    for i in range(1, 7):
        rr = frame.rotate([0, 0, i * (360.0 / cf.N) / 7.0])
        worst_c = max(worst_c, ((foot_static + top + shell) ^ rr).volume())
    add('clocking sweep (7 over a sector): mounts clear the ring', worst_c,
        False)
    waf = sum(wafer_list[1:], wafer_list[0])
    add('pinion + shell + top unit vs wafers',
        ((pin + top + shell) ^ waf).volume(), False)

    ok = True
    print("  checks:")
    for name, v, want in checks:
        good = (v > EPS) == want
        ok &= good
        print(f"    {'PASS' if good else 'FAIL':4}  {name:58} {v:10.4f}")

    HIDE_R_MAX = 410.0   # hide-window outer radius (~416) − margin
    solids = [foot_static, wheels[0], wheels[1], top, shell, pin]
    rmax = 0.0
    zmin = 1e9
    for s_ in solids:
        # exact max plan radius over the mesh — bbox corners false-alarm
        # on L-shaped parts (the corner can be empty air)
        for v in s_.to_mesh().vert_properties:
            rmax = max(rmax, math.hypot(v[0], v[1]))
        zmin = min(zmin, s_.bounding_box()[2])
    good = rmax <= HIDE_R_MAX
    ok &= good
    print(f"    {'PASS' if good else 'FAIL':4}  {'hidden: max plan radius':58} {rmax:10.1f}")
    good = zmin >= b.wall_z - 1e-6
    ok &= good
    print(f"    {'PASS' if good else 'FAIL':4}  "
          f"{'nothing behind the wall plane (incl. pinion)':58} {zmin:10.1f}")

    dz = -b.wall_z
    outs = [('bracket_bottom_static.stl', [foot_static.translate([0, 0, dz])],
             'static foot + arc saddle: print wall-face down'),
            ('bracket_top.stl', [top.translate([0, 0, dz])],
             'dynamic top unit: print wall-face down'),
            ('bracket_shell.stl', [shell.translate([0, 0, dz])],
             'slotted motor shell: print ears-down, slide to preload'),
            ('bracket_wheel.stl', [build_wheel(b)], 'print x2, flat'),
            ('bracket_fitcheck.stl',
             bodies + wafer_list + [foot_static, wheels[0], wheels[1],
                                    top, shell, pin],
             'view only, dynamic + static scene')]
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
