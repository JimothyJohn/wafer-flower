#!/usr/bin/env python3
"""
Wafer Halo — low-profile gearmotor drive module.

Drives the 252T module-2 INTERNAL ring gear (the flange on the frame's flat
bottom) with the existing 28T pinion at 9:1, from an N20-class micro WORM
gearmotor. Worm output means two things: the motor body lies FLAT against the
wall plate (output shaft perpendicular to the body, so the module is as thin
as the plate), and the drive self-holds when unpowered — no detent current.

The whole module hides BEHIND the frame: every static part except the pinion
stays behind the plane z_bot - 1 (the frame's flat bottom, minus running
clearance), so it adds ZERO front profile to the piece. Only the pinion
crosses that plane, and only inside r < g_tip except at the mesh itself.

    wall | bracket | [plate: motor sunk flush, clamp bar] | pinion | ring gear
                      <-------- plate_t + 1 mm ------->

Mount interface (to Nick's pre-installed wall bracket, which does not exist
in this repo yet): TWO KEYHOLE SLOTS at y = +/-key_y, hanging on #10-24
pan-head screws. The slots run RADIALLY (x, toward the halo axis) so the
plate slides to set gear mesh depth / backlash, then the screws are
tightened. The bracket only needs two screws at the spacing this script
prints, in the plane z = plate back face.

Motor: generic "N20 worm gearbox" DC gearmotor (the flat 6 V units with a
3 mm D-shaft sticking out of the gearbox face — Greartisan/uxcell-style,
ubiquitous online). ALL envelope dims below are parameters: measure the unit
you actually bought and override on the CLI before printing. Torque needed
at the pinion is ~3.3 mN.m (OP 015) — any N20 gearbox clears that by 2-3
orders of magnitude. Halo speed = motor output speed / 9, so a 10 rpm motor
turns the halo ~1.1 rpm; buy the output speed you want to look at.

Printed parts: drive_plate.stl, drive_clamp.stl, drive_pinion.stl.
View only:    drive_fitcheck.stl (plate + motor dummy + clamp + pinion +
              full frame ring + wafers).

Booleans prove, not assume (exit nonzero on FAIL): the ring and wafers swept
through a full tooth pitch against every static part, the pinion rolled
against the ring (conjugacy, co-rotating), pocket fit, clamp capture, shaft
engagement, keyhole geometry.

    pip install manifold3d
    python3 scripts/gearmotor_stl.py           # -> stl/
    python3 scripts/gearmotor_stl.py --help    # every param is a flag
"""
from __future__ import annotations
import math, os, sys, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from segment_stl import (PARAMS, Cfg, prism, build_segment, build_wafer,
                         build_pinion, build_ring, check_mesh, write_stl,
                         report, rotated, Manifold, HAVE_MANIFOLD)

# ----------------------------------------------------------------------------
DRIVE = dict(
    # -- motor envelope: MEASURE YOUR UNIT, these are catalog-typical N20-worm
    mot_len   = 46.0,   # body length, along y (worm gearbox + can)
    mot_w     = 12.6,   # body width, along x
    mot_t     = 10.2,   # body thickness, along z (lies flat)
    shaft_d   = 3.0,    # output D-shaft diameter
    shaft_flat= 0.5,    # D-flat depth on the shaft
    shaft_len = 10.0,   # usable shaft length above the gearbox face
    shaft_off = 9.0,    # shaft axis distance from the FRONT (-y) end of the body
    # -- printed geometry
    plate_t   = 15.5,   # wall plate thickness (motor sinks in below flush)
    sink      = 2.0,    # motor top face recessed this far below the plate front
    plate_x2  = 34.0,   # plate half-length, x (radial)
    plate_y2  = 40.0,   # plate half-width, y (tangential)
    corner_r  = 8.0,    # plate corner radius
    gap       = 1.0,    # running clearance to the frame's flat bottom
    pock_clr  = 0.3,    # motor pocket clearance per side
    web_min   = 3.0,    # min web under the motor pocket
    clamp_t   = 2.0,    # clamp bar thickness (sits on the plate front face)
    clamp_w   = 8.0,    # clamp bar width (along y)
    clamp_scr = 2.9,    # clamp screw pilot bore (#6 x 1/2" self-tap into print)
    key_y     = 28.0,   # keyhole slots at y = +/-key_y
    key_entry = 11.0,   # keyhole entry hole diameter (#10 pan head drops in)
    key_slot  = 5.2,    # keyhole slot width (#10-24 shank slides)
    key_len   = 8.0,    # slot length = radial mesh adjustment range
    bore_clr  = 0.25,   # pinion bore oversize on the shaft diameter
    hub_d     = 12.0,   # pinion retention collar diameter
    hub_t     = 2.0,    # pinion retention collar height (below the teeth)
    wire_w    = 6.0,    # wire exit channel width, out the +y edge
)


class Drive:
    def __init__(self, cf, **kw):
        p = dict(DRIVE); p.update(kw); self.p = p
        for k, v in p.items(): setattr(self, k, v)
        self.cf = cf
        _, g = build_pinion(cf, bore=0.0, flat=0.0)
        self.g = g                              # rp, rb, ra, rf, T of the pinion
        self.cx = cf.g_pitch - g['rp']          # pinion axis x: centre distance
        # z stack, wall side is -z. Pinion face spans the ring flange exactly.
        self.z_ring0 = cf.z_bot                 # ring teeth bottom
        self.z_ring1 = cf.z1                    # ring teeth top
        self.z_front = cf.z_bot - self.gap      # plate front face
        self.z_back  = self.z_front - self.plate_t
        # motor sunk BELOW flush by `sink`, so the retention lip and the clamp
        # feet both stay behind the plate front plane
        self.pock_z  = self.z_front - (self.mot_t + 0.2 + self.sink)
        # shaft base sits on the motor top face; engagement into the pinion bore
        self.shaft_z0 = self.pock_z + 0.2 + self.mot_t
        self.shaft_z1 = self.shaft_z0 + self.shaft_len
        self.engage   = self.shaft_z1 - cf.z_bot   # bore starts at the teeth
        web = self.pock_z - self.z_back
        assert web >= self.web_min, f"pocket web {web:.1f} < {self.web_min}"


# ---- solid helpers ----------------------------------------------------------
def box(x0, x1, y0, y1, z0, z1):
    return prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1 - z0)


def zcyl(r, z0, h, cx=0.0, cy=0.0, fn=96):
    return Manifold.cylinder(h, r, r, fn).translate([cx, cy, z0])


def rounded_rect(x0, x1, y0, y1, r, n=12):
    """CCW rounded-rectangle profile."""
    cs = [(x1 - r, y1 - r, 0.0), (x0 + r, y1 - r, 90.0),
          (x0 + r, y0 + r, 180.0), (x1 - r, y0 + r, 270.0)]
    pts = []
    for cx, cy, a0 in cs:
        for i in range(n + 1):
            a = math.radians(a0 + 90.0 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# ---- parts ------------------------------------------------------------------
def build_motor_dummy(d):
    """Envelope solid for interference checks and the fitcheck view: body box
    lying flat, shaft up. Front (-y) end carries the worm gearbox and shaft."""
    m = (box(d.cx - d.mot_w / 2, d.cx + d.mot_w / 2,
             -d.shaft_off, d.mot_len - d.shaft_off,
             d.pock_z + 0.2, d.shaft_z0)
         + zcyl(d.shaft_d / 2, d.shaft_z0, d.shaft_len, d.cx, 0.0)
         - box(d.cx + d.shaft_d / 2 - d.shaft_flat, d.cx + d.shaft_d,
               -d.shaft_d, d.shaft_d, d.shaft_z0 + 1.0, d.shaft_z1 + 1.0))
    return m


def build_plate(d):
    cf = d.cf
    pl = prism(rounded_rect(d.cx - d.plate_x2, d.cx + d.plate_x2,
                            -d.plate_y2, d.plate_y2, d.corner_r),
               d.z_back, d.plate_t)
    # motor pocket, open on the front face
    c = d.pock_clr
    pl -= box(d.cx - d.mot_w / 2 - c, d.cx + d.mot_w / 2 + c,
              -d.shaft_off - c, d.mot_len - d.shaft_off + c,
              d.pock_z, d.z_front + 1.0)
    # wire exit channel out the +y edge, in the pocket floor
    pl -= box(d.cx - d.wire_w / 2, d.cx + d.wire_w / 2,
              0.0, d.plate_y2 + 1.0, d.pock_z, d.pock_z + 4.0)
    # retention lip over the gearbox (-y) end of the pocket: the motor slides
    # nose-first under it, then the tail drops. 0.1 above the motor top, and
    # entirely behind the plate front plane. Prints as a 14 mm bridge.
    pl += box(d.cx - d.mot_w / 2 - c - 0.5, d.cx + d.mot_w / 2 + c + 0.5,
              -d.shaft_off - c - 0.4, -d.shaft_off + 3.0,
              d.shaft_z0 + 0.1, d.z_front)
    # keyhole slots: entry at the OUTER (+x) end, slot runs -x so sliding the
    # plate toward the halo axis deepens the mesh. The #10 pan head rides in a
    # groove opening on the BACK face (between plate and bracket).
    for s in (1.0, -1.0):
        ex = d.cx + d.key_len / 2
        pl -= zcyl(d.key_entry / 2, d.z_back - 1.0, d.plate_t + 2.0, ex, s * d.key_y)
        pl -= box(ex - d.key_len, ex, s * d.key_y - d.key_slot / 2,
                  s * d.key_y + d.key_slot / 2, d.z_back - 1.0, d.z_front + 1.0)
        pl -= box(ex - d.key_len, ex, s * d.key_y - d.key_entry / 2,
                  s * d.key_y + d.key_entry / 2, d.z_back - 1.0, d.z_back + 4.0)
    # clamp screw pilots, in solid plate just outside the pocket walls
    for s in (1.0, -1.0):
        pl -= zcyl(d.clamp_scr / 2, d.z_front - 12.0, 13.0, d.cx + s * d.clamp_dx(),
                   d.clamp_cy())
    return pl


def _clamp_dx(d):
    return d.mot_w / 2 + d.pock_clr + 4.0


def _clamp_cy(d):
    # bar centre: past the pinion swing circle (ra + margin), still on the can
    return max(d.g['ra'] + 0.6 + d.clamp_w / 2 + 0.4,
               d.mot_len - d.shaft_off - d.clamp_w / 2 - 1.0 - 4.0)


Drive.clamp_dx = _clamp_dx
Drive.clamp_cy = _clamp_cy


def build_clamp(d):
    """Bar across the tail of the motor can, screwed to the plate with two
    #6 x 1/2" self-taps. It sits ON the plate front face, entirely OUTSIDE the
    pinion's swing circle (the gearbox end is held by the plate's printed
    lip); its feet drop through the pocket opening onto the motor body."""
    cy, dx = d.clamp_cy(), d.clamp_dx()
    bar = box(d.cx - dx - 5.0, d.cx + dx + 5.0, cy - d.clamp_w / 2,
              cy + d.clamp_w / 2, d.z_front, d.z_front + d.clamp_t)
    bar += box(d.cx - d.mot_w / 2, d.cx + d.mot_w / 2, cy - d.clamp_w / 2,
               min(cy + d.clamp_w / 2, d.mot_len - d.shaft_off),
               d.shaft_z0, d.z_front + 1.0)
    for s in (1.0, -1.0):
        bar -= zcyl(2.0, d.shaft_z0 - 1.0, d.mot_t + d.sink + d.clamp_t + 4.0,
                    d.cx + s * dx, cy)
    return bar


def build_drive_pinion(d):
    """The mating 28T pinion with a D-bore for the motor shaft and a grip
    collar ABOVE the teeth (a spur mesh has no axial force component, so the
    pinion only needs friction on the D-flat to stay put; the collar gives
    bore length and something to press on). Teeth span the ring flange."""
    cf = d.cf
    bore = d.shaft_d + d.bore_clr
    pin, _ = build_pinion(cf, bore=0.0, flat=0.0)
    hub = zcyl(d.hub_d / 2, cf.tmin, d.hub_t, 0.0, 0.0)
    pin += hub
    pin -= zcyl(bore / 2, -1.0, cf.tmin + d.hub_t + 2.0)
    pin -= prism([(bore / 2 - d.shaft_flat, -bore), (bore / 2 - d.shaft_flat, bore),
                  (bore, bore), (bore, -bore)], -1.0, cf.tmin + d.hub_t + 2.0)
    return pin.translate([d.cx, 0.0, cf.z_bot])   # assembly position


# ---- verification -----------------------------------------------------------
def run_checks(d, plate, clamp, motor, pinion, frame_parts, wafers):
    EPS = 1e-6
    cf = d.cf
    statics = plate + clamp + motor
    ok = True
    zero, hit = [], []

    # the ring is 9-fold symmetric with tps teeth/segment: sweeping ONE tooth
    # pitch covers every angular phase the frame can ever present
    pitch_deg = 360.0 / cf.teeth
    worst_f = worst_w = 0.0
    for i in range(5):
        a = pitch_deg * i / 4.0
        fr = sum((p.rotate([0, 0, a]) for p in frame_parts), Manifold())
        wf = sum((p.rotate([0, 0, a]) for p in wafers), Manifold())
        worst_f = max(worst_f, (fr ^ statics).volume())
        worst_w = max(worst_w, (wf ^ statics).volume())
    zero.append((f'frame swept 1 tooth pitch vs plate+clamp+motor', worst_f))
    zero.append((f'wafers swept 1 tooth pitch vs plate+clamp+motor', worst_w))

    # pinion spin envelope: tip cylinder over the full part height
    spin = zcyl(d.g['ra'] + 0.6, cf.z_bot - 0.5,
                d.cf.tmin + d.hub_t + 1.0, d.cx, 0.0, fn=256)
    zero.append(('pinion spin envelope vs plate+clamp', (spin ^ (plate + clamp)).volume()))
    zero.append(('pinion vs motor body', (pinion ^ motor).volume()))
    zero.append(('motor vs pocketed plate', (motor ^ plate).volume()))
    zero.append(('clamp vs plate', (clamp ^ plate).volume()))

    # mesh conjugacy, both directions of the roll (internal pair co-rotates)
    mesh = check_mesh(cf)
    zero.append((f"pinion/ring roll, 1 tooth pitch (centre {mesh['centre']:.0f})",
                 mesh['worst_overlap']))

    frame0 = sum(frame_parts, Manifold())
    hit.append(('pinion tip circle reaches into the ring teeth',
                (spin ^ frame0).volume(), True))
    hit.append(('clamp captures the motor (motor +1 z contacts)',
                (motor.translate([0, 0, 1.0]) ^ clamp).volume(), True))
    hit.append(('motor seated (motor -1 z contacts pocket floor)',
                (motor.translate([0, 0, -1.0]) ^ plate).volume(), True))

    print("  interference (must all be 0 mm3):")
    for name, v in zero:
        good = v < EPS; ok &= good
        print(f"    {'PASS' if good else 'FAIL':4}  {name:52} {v:10.4f}")
    print("  capture / engagement (contact where expected):")
    for name, v, want in hit:
        good = (float(v) > EPS) == want; ok &= good
        print(f"    {'PASS' if good else 'FAIL':4}  {name:52} {float(v):10.4f}")

    # scalar gates
    print("  scalars:")
    scal = [
        ('shaft engagement into pinion bore >= 6.5 mm', d.engage, d.engage >= 6.5),
        ('pocket web under motor >= web_min', d.pock_z - d.z_back,
         d.pock_z - d.z_back >= d.web_min),
        ('keyhole entry passes a #10 pan head (Ø>=9.5)', d.key_entry,
         d.key_entry >= 9.5),
    ]
    for name, v, good in scal:
        ok &= good
        print(f"    {'PASS' if good else 'FAIL':4}  {name:52} {v:10.2f}")
    return ok


def main():
    if not HAVE_MANIFOLD:
        sys.exit("needs manifold3d for STL output:  pip install manifold3d")
    ap = argparse.ArgumentParser(description="Wafer Halo — gearmotor drive module")
    ap.add_argument('-o', '--out', default='stl')
    for k, v in {**PARAMS, **DRIVE}.items():
        ap.add_argument(f'--{k}', type=type(v), default=None)
    a = ap.parse_args()
    cf = Cfg(**{k: getattr(a, k) for k in PARAMS if getattr(a, k) is not None})
    d = Drive(cf, **{k: getattr(a, k) for k in DRIVE if getattr(a, k) is not None})
    os.makedirs(a.out, exist_ok=True)

    print(f"Gearmotor drive  ·  {d.g['T']}T pinion / {cf.teeth}T internal ring = "
          f"{cf.teeth / d.g['T']:.0f}:1  ·  axis at r={d.cx:.0f}")
    print(f"  z stack  ring flange {d.z_ring0:.1f}..{d.z_ring1:.1f}  plate front "
          f"{d.z_front:.1f}  back (bracket face) {d.z_back:.1f}")
    print(f"  profile  module hides behind the frame: only the pinion crosses "
          f"z_bot, wall standoff = plate_t + gap = {d.plate_t + d.gap:.0f} mm + bracket")
    print(f"  mount    two #10-24 keyholes at ({d.cx + d.key_len / 2:.0f}, "
          f"+/-{d.key_y:.0f}), {d.key_len:.0f} mm radial adjustment")
    print(f"  motor    N20-worm envelope {d.mot_len:.0f}x{d.mot_w:.1f}x{d.mot_t:.1f}, "
          f"Ø{d.shaft_d} D-shaft — MEASURE YOURS, override on the CLI")
    print(f"  drive    needs ~3.3 mN.m at the pinion (OP 015); halo rpm = motor "
          f"rpm / {cf.teeth / d.g['T']:.0f}\n")

    plate  = build_plate(d)
    clamp  = build_clamp(d)
    motor  = build_motor_dummy(d)
    pinion = build_drive_pinion(d)
    frame  = build_ring(cf)
    wafers = [build_wafer(cf, k) for k in range(cf.N)]

    ok = run_checks(d, plate, clamp, motor, pinion, frame, wafers)
    print()

    dz = -d.z_back
    outs = [('drive_plate.stl',  [plate.translate([-d.cx, 0, dz])], 'prints back face down'),
            ('drive_clamp.stl',  [clamp.translate([-d.cx, 0, -d.z_front])
                                  .rotate([180.0, 0.0, 0.0])], 'prints top face down'),
            ('drive_pinion.stl', [pinion.translate([-d.cx, 0, -cf.z_bot])],
             'prints teeth down, collar up'),
            ('drive_fitcheck.stl', frame + wafers + [plate, clamp, motor, pinion],
             'view only, full assembly')]
    for fname, solids, note in outs:
        bodies = write_stl(solids, os.path.join(a.out, fname))
        v = report(fname, solids, bodies, note)
        if 'fitcheck' not in fname:
            print(f"{'':24}mass  45% infill {v*1.27e-3*0.45:6.1f} g   "
                  f"solid {v*1.27e-3:6.1f} g")

    print(f"\n{'ALL CHECKS PASS' if ok else 'CHECK FAILURES ABOVE — do not print'}")
    print(f"Wrote to {os.path.abspath(a.out)}/")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
