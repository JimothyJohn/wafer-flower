#!/usr/bin/env python3
"""
Wafer Halo — perpendicular cure jig (OP 012): holds the wafer centred over the
land while the adhesive cures (the SMP / PL Premium path; tape needs no cure
hold). Bench use, one segment at a time, flat on its bottom.

Two printed fences slide toward each other along ONE threaded rod that passes
RADIALLY THROUGH the segment's Ø5 keyhole:

  wing nut > [outboard fence]===(keyhole)===[inboard fence] < captive hex nut
                    nose butts r=Ro          prong butts r=Ri

Tightening the wing nut draws BOTH fences onto the segment, so the closed
force loop is jig<->segment only. The wafer floats between the two slot walls
with `slack` per side and carries ZERO clamp load — edges only, never flex.

ALIGNED WITH THE WAFER CENTRE, by construction and by check: the keyhole
meridian (a=0) is the wafer-centre meridian, so the rod axis lies in the
vertical plane through the wafer centre (R, 0) and crosses directly beneath
it. Both slot walls are arcs about (R, 0), so the captured position IS the
nominal wafer centre. The script verifies the plane-through-centre condition
numerically along with everything else.

Capture, not clamp (theta=5 defaults):
  x (radial):  +/-0.15 mm — wall faces at R +/- (r + slack)
  y (tangent): ~ +/- slack/sin(asin(wing_w2/r)) = 0.30 mm — full-height
               centring WINGS carry the wall arcs out to y=+/-75, wrapping
               32 deg of rim per side; gravity seats the wafer downhill
               against the same arcs every time
  z (lift):    slot lips overhang the rim 1.5 mm; ceiling 1.6 mm above the
               wafer top, floor ledge 1.6 below — it cannot walk out

The ENTIRE drivetrain is modelled as solids and checked, not assumed: rod at
thread OD, captive hex nut on its pocket floor, #10 washer, and a wing nut
with its wings VERTICAL — the worst orientation for bench clearance (this is
what forced the keyhole axis up to z1+2.6 in the first place).

The slot is cut with a wafer-COPLANAR disc, not a straight groove: across an
80 mm fence the tilted rim swings +/-3.5 mm in z, so a straight slot would
need a 9+ mm opening and give up all lift capture. Coplanar, the clearance is
a uniform 1.6 mm all round.

Hardware (Home Depot): #10-24 threaded rod (Ø4.83 — fits the Ø5 keyhole; ream
the printed hole with a 5 mm / 13/64" bit), cut to ~350 mm from a 36" stick,
one hex nut (captive in the inboard tower), one wing nut + washer outboard
(or print the included knob). M5 rod + nut also fits every bore.

Needs the Rev B.3 THROUGH keyhole (segment_stl.py hole_dep >= bw). Segments
printed with the old blind keyhole: drill on through from the outer face —
the new axis is tmin + 2.6 mm above the flat bottom.

Use: bond one segment flat on the bench; wet SMP beads in the pocket; set the
wafer by eye (+/-1 mm); slide the outboard fence in until its nose butts the
outer arc face, then the inboard fence; push the rod through from outboard,
thread it into the captive nut, spin the wing nut finger tight. The walls
nudge the wafer onto centre as they seat. Leave until cured, back the rod
out, slide the fences apart radially.

    pip install manifold3d
    python3 scripts/cure_jig_stl.py            # -> stl/
    python3 scripts/cure_jig_stl.py --help     # every PARAMS/JIG entry is a flag
"""
from __future__ import annotations
import math, os, sys, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from segment_stl import (PARAMS, Cfg, prism, build_segment, build_wafer,
                         write_stl, report, keyhole_z, Manifold, HAVE_MANIFOLD)

# ----------------------------------------------------------------------------
JIG = dict(
    rod_D    = 4.83,   # 10-24 threaded rod; M5 (4.9) also fits every bore
    bore_clr = 0.5,    # rod bore = rod_D + bore_clr
    nut_AF   = 9.53,   # 10-24 hex nut across flats (3/8"); M5 (8.0) drops in loose
    nut_clr  = 0.45,   # pocket oversize on the across-flats
    nut_deep = 7.0,    # hex pocket depth (nut is ~3.2 thick; extra is rod room)
    slack    = 0.15,   # wall standoff per side from the nominal rim
    slot_h   = 4.0,    # slot opening, centred on the wafer mid-plane, coplanar
    lip_over = 1.5,    # lip / floor overhang inboard of the nominal rim
    fence_w  = 80.0,   # tangential width of the fence cores
    wing_w2  = 75.0,   # centring wings reach to y=+/-wing_w2 (32 deg of rim
                       # per side); capped by the gear tooth tips at r=250
                       # on the inboard side
    clr_und  = 2.0,    # min clearance to the wafer underside (covers 0.6 droop)
    boss_w   = 12.0,   # rib that roofs the rod bore under the wafer overhang
)


class Jig:
    def __init__(self, cf, **kw):
        p = dict(JIG); p.update(kw); self.p = p
        for k, v in p.items(): setattr(self, k, v)
        self.cf = cf
        tn = math.tan(cf.th)
        self.zc     = keyhole_z(cf)
        self.bore_r = (self.rod_D + self.bore_clr) / 2.0
        self.nut_R  = (self.nut_AF + self.nut_clr) / math.sqrt(3.0)
        self.w2     = self.fence_w / 2.0
        self.x_in   = cf.R - cf.r              # nominal rim, inboard / outboard
        self.x_out  = cf.R + cf.r
        self.r_wall = cf.r + self.slack        # radial stop = slot back face
        self.r_lip  = cf.r - self.lip_over     # lip & floor-ledge face
        swing = self.w2 * tn                   # rim z swing across the fence core
        self.under_top = -(cf.wafer_T / 2 + swing + self.clr_und)   # rail/base top
        self.wall_top  = swing + self.slot_h / 2 + 3.0              # lip roof
        self.wing_top  = self.wing_w2 * tn + self.slot_h / 2 + 3.0  # wing lip roof
        self.boss_top  = self.zc + self.bore_r + 1.5
        self.prong_top = -(cf.wafer_T / 2 + 14.0 * tn + 2.0)
        self.prong_bot = cf.z1 + 0.5           # 0.5 above the gear flange
        # sanity: bore roofed under the wafer, rib still clear of the wafer
        assert self.boss_top < -(cf.wafer_T / 2 + (self.boss_w / 2) * tn + 1.4), \
            "bore roof rib would touch the wafer underside"


# ---- solid helpers ----------------------------------------------------------
def box(x0, x1, y0, y1, z0, z1):
    return prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1 - z0)


def vcyl(r, z0, h, cx=0.0, cy=0.0, fn=512):
    return Manifold.cylinder(h, r, r, fn).translate([cx, cy, z0])


def xcyl(r, x0, x1, z, fn=96):
    return (Manifold.cylinder(x1 - x0, r, r, fn)
            .rotate([0.0, 90.0, 0.0]).translate([x0, 0.0, z]))


def coplanar(cf, solid_z, offset):
    """Place a +z-extruded solid parallel to wafer 0's plane at `offset`."""
    M, c, n = cf.wafer_frame(0)
    t = [c[i] + offset * n[i] for i in range(3)]
    return solid_z.transform([[M[0][0], M[0][1], M[0][2], t[0]],
                              [M[1][0], M[1][1], M[1][2], t[1]],
                              [M[2][0], M[2][1], M[2][2], t[2]]])


def slot_cuts(j):
    """One coplanar cutter serves both fences: the slot (back face = the
    radial stop at r_wall) plus a 45-degree bevel on the lip underside so a
    high-riding rim wedges in instead of jamming during the slide."""
    cf = j.cf
    slot = coplanar(cf, Manifold.cylinder(j.slot_h, j.r_wall, j.r_wall, cf.facets),
                    -j.slot_h / 2)
    # The cone starts 1 mm INSIDE the slot void, not exactly on the ceiling
    # plane: two cutters meeting cap-to-cap on the same plane leave a folded
    # seam in the union (74 duplicated mesh edges), overlap dissolves cleanly.
    bev = coplanar(cf, Manifold.cylinder(2.2, j.r_wall + 1.0, j.r_wall - 1.2, cf.facets),
                   +j.slot_h / 2 - 1.0)
    return slot + bev


def hex_pocket(j, x0):
    R = j.nut_R   # vertex-up hexagon: flats vertical (nut can't spin), no bridge
    pts = [(R * math.cos(math.radians(60 * i)), R * math.sin(math.radians(60 * i)))
           for i in range(6)]
    return (prism(pts, 0.0, j.nut_deep + 0.5)
            .rotate([0.0, 90.0, 0.0]).translate([x0, 0.0, j.zc]))


# ---- the two fences ---------------------------------------------------------
def build_outboard(j):
    """Rail on the bench under the wafer overhang, nose butting the outer arc
    face, slot wall just past the rim, wing-nut face at the back."""
    cf = j.cf
    x0, x1 = cf.Ro - 2.0, j.x_out + 10.0
    f  = box(x0, x1, -j.w2, j.w2, cf.z_bot, j.under_top)                    # rail
    f += box(x0, x1, -j.boss_w / 2, j.boss_w / 2, cf.z_bot, j.boss_top)     # bore roof
    walls = box(j.x_out - 8.0, x1, -j.w2, j.w2, j.under_top - 2.0, j.wall_top)
    # centring wings: full-height dumb boxes are safe because the lip-cylinder
    # subtraction below carves away everything plan-inside the rim ring — what
    # survives is only the wall band that follows the rim arc out to +/-wing_w2
    for s in (1.0, -1.0):
        walls += box(j.x_out - 28.0, x1, s * (j.w2 - 2.0), s * j.wing_w2,
                     cf.z_bot, j.wing_top)
    f += walls - vcyl(j.r_lip, cf.z_bot - 1.0, 60.0, cf.R, 0.0)
    # nose: butts the outer arc face. +0.05 standoff so the different chord
    # phases of this 512-gon and the segment's 160-point arc don't overlap.
    f -= vcyl(cf.Ro + 0.05, cf.z_bot - 1.0, 60.0)
    f -= slot_cuts(j)
    f -= xcyl(j.bore_r, x0 - 2.0, x1 + 2.0, j.zc)
    return f


def build_inboard(j):
    """Sits in the central hole: nut tower at the back, slot wall just inside
    the rim, low prong butting the band's inner face above the gear flange."""
    cf = j.cf
    x1 = j.x_in + 2.0
    x0 = j.x_in - 28.0                                                      # back face
    f  = box(x0, x1, -j.w2, j.w2, cf.z_bot, j.under_top)                    # base
    f += box(x0, x0 + 18.0, -j.w2, j.w2, cf.z_bot, j.wall_top)              # nut tower
    walls = box(j.x_in - 14.0, x1, -j.w2, j.w2, j.under_top - 2.0, j.wall_top)
    # centring wings, as on the outboard fence. Reach inward stops at
    # x_in + 32: the far corner sits at r=244 from the halo axis, 6 mm clear
    # of the gear tooth tips (r=250).
    for s in (1.0, -1.0):
        walls += box(x0, j.x_in + 32.0, s * (j.w2 - 2.0), s * j.wing_w2,
                     cf.z_bot, j.wing_top)
    f += walls - vcyl(j.r_lip, cf.z_bot - 1.0, 60.0, cf.R, 0.0)
    # datum prong: butts the band inner face (r=Ri) between gear flange and
    # land. The rod bore breaks 0.6 mm out of its underside over the last
    # stretch (prong floor is capped by the flange top) — an open guide
    # groove there is fine, the full round bore in the body does the guiding.
    prong = box(x0 + 6.0, cf.Ri + 2.0, -14.0, 14.0, j.prong_bot, j.prong_top)
    f += prong ^ vcyl(cf.Ri - 0.05, cf.z_bot - 1.0, 60.0)   # 0.05 datum standoff
    f -= slot_cuts(j)
    f -= xcyl(j.bore_r, x0 - 2.0, cf.Ri + 4.0, j.zc)
    f -= hex_pocket(j, x0 - 0.5)
    return f


def build_hardware(j):
    """The entire drivetrain as solids: rod at thread OD, captive hex nut
    seated on its pocket floor, #10 washer, wing nut with the wings VERTICAL —
    the worst orientation for bench clearance. Nut and wing-nut bores are at
    the #10-24 tap drill (3.8), so their overlap with the rod is real thread
    engagement and is deliberately not an interference check."""
    cf = j.cf
    back  = j.x_out + 10.0                    # outboard fence rear face
    floor = (j.x_in - 28.0) + 7.0             # hex pocket floor
    rod0, rod1 = floor - 3.4, back + 1.2 + 5.5 + 3.0
    rod = xcyl(j.rod_D / 2, rod0, rod1, j.zc)
    R = j.nut_AF / math.sqrt(3.0)             # actual nut, no clearance
    hx = [(R * math.cos(math.radians(60 * i)), R * math.sin(math.radians(60 * i)))
          for i in range(6)]
    nut = (prism(hx, 0.0, 3.05).rotate([0.0, 90.0, 0.0])
           .translate([floor - 3.05, 0.0, j.zc]))
    nut -= xcyl(1.9, floor - 4.0, floor + 1.0, j.zc)
    washer = (xcyl(5.95, back, back + 1.2, j.zc)
              - xcyl(2.8, back - 1.0, back + 3.0, j.zc))
    wnut = xcyl(4.75, back + 1.2, back + 6.7, j.zc)
    wnut += box(back + 2.2, back + 5.7, -1.5, 1.5, j.zc - 11.0, j.zc + 11.0)
    wnut -= xcyl(1.9, back + 0.5, back + 7.5, j.zc)
    return rod, nut, washer, wnut, rod1 - rod0


def build_knob(j):
    """Optional printed thumb knob (Ø20 12-gon) if no wing nut is on hand.
    Anything swung on the rod must clear the bench: axis is tmin+2.6 up."""
    pts = [(10.0 * math.cos(math.radians(30 * i + 15)),
            10.0 * math.sin(math.radians(30 * i + 15))) for i in range(12)]
    R = j.nut_R
    hx = [(R * math.cos(math.radians(60 * i)), R * math.sin(math.radians(60 * i)))
          for i in range(6)]
    k = prism(pts, 0.0, 16.0)
    k -= prism(hx, -0.5, 8.5)
    k -= Manifold.cylinder(20.0, j.bore_r, j.bore_r, 96).translate([0, 0, -2.0])
    return k


# ---- verification -----------------------------------------------------------
def run_checks(j, seg, waf, fout, fin, rod, nut, washer, wnut):
    EPS = 1e-6
    cf = j.cf
    fences = fout + fin
    _, c, _ = cf.wafer_frame(0)
    bench = box(140, 600, -260, 260, cf.z_bot - 8.0, cf.z_bot)
    zero = [
        ('rod axis plane contains the wafer centre', abs(c[1])),
        ('outboard fence vs segment', (fout ^ seg).volume()),
        ('inboard fence vs segment',  (fin ^ seg).volume()),
        ('fences vs wafer, nominal',  (fences ^ waf).volume()),
        ('rod vs segment (keyhole through & clear of gear)', (rod ^ seg).volume()),
        ('rod vs fences (bores clear)', (rod ^ fences).volume()),
        ('hex nut vs its pocket walls', (nut ^ fin).volume()),
        ('washer + wing nut vs outboard fence', ((washer + wnut) ^ fout).volume()),
        ('wing-nut swing (wings vertical) vs bench', (wnut ^ bench).volume()),
        ('nut/washer/wing nut vs segment & wafer',
         (((nut + washer + wnut) ^ (seg + waf))).volume()),
    ]
    hit = [
        ('wafer +0.30 x meets outboard stop', (waf.translate([0.30, 0, 0]) ^ fout).volume(), True),
        ('wafer +0.10 x still free',          (waf.translate([0.10, 0, 0]) ^ fout).volume(), False),
        ('wafer -0.30 x meets inboard stop',  (waf.translate([-0.30, 0, 0]) ^ fin).volume(), True),
        ('wafer +0.60 y meets the wings',     (waf.translate([0, 0.60, 0]) ^ fences).volume(), True),
        ('wafer +0.20 y still free',          (waf.translate([0, 0.20, 0]) ^ fences).volume(), False),
        ('wafer -0.60 y meets the wings',     (waf.translate([0, -0.60, 0]) ^ fences).volume(), True),
        ('wafer +3.0 z meets the lips',       (waf.translate([0, 0, 3.0]) ^ fences).volume(), True),
        ('wafer +1.0 z still free',           (waf.translate([0, 0, 1.0]) ^ fences).volume(), False),
    ]
    ok = True
    print("  interference (must all be 0 mm3):")
    for name, v in zero:
        good = v < EPS; ok &= good
        print(f"    {'PASS' if good else 'FAIL':4}  {name:44} {v:10.4f}")
    print("  capture (contact where expected):")
    for name, v, want in hit:
        good = (v > EPS) == want; ok &= good
        print(f"    {'PASS' if good else 'FAIL':4}  {name:44} {v:10.4f}")
    return ok


def main():
    if not HAVE_MANIFOLD:
        sys.exit("needs manifold3d for STL output:  pip install manifold3d")
    ap = argparse.ArgumentParser(description="Wafer Halo — cure jig STL generator")
    ap.add_argument('-o', '--out', default='stl')
    for k, v in {**PARAMS, **JIG}.items():
        ap.add_argument(f'--{k}', type=type(v), default=None)
    a = ap.parse_args()
    cf = Cfg(**{k: getattr(a, k) for k in PARAMS if getattr(a, k) is not None})
    j = Jig(cf, **{k: getattr(a, k) for k in JIG if getattr(a, k) is not None})
    os.makedirs(a.out, exist_ok=True)

    if cf.hole_dep < cf.bw:
        print(f"WARNING: hole_dep {cf.hole_dep} < bw {cf.bw}: keyhole is BLIND, "
              f"the rod cannot reach the inboard fence. Regenerate the segment.")

    ys = j.slack / (j.wing_w2 / j.r_wall)     # sin(arc half-angle) ~ wing_w2/r
    print(f"Cure jig OP 012  ·  theta={cf.theta}  keyhole z={j.zc:.2f} "
          f"({j.zc - cf.z_bot:.1f} above the bench)")
    print(f"  centre  rod axis lies in the wafer-centre plane (a=0 meridian): "
          f"crosses ({cf.R:.0f}, 0) at z={j.zc:.2f}, {abs(j.zc):.1f} below the "
          f"wafer mid-plane; both slot walls are arcs about ({cf.R:.0f}, 0)")
    print(f"  walls   x = {cf.R - j.r_wall:.2f} / {cf.R + j.r_wall:.2f}  "
          f"(rim {j.x_in:.0f}/{j.x_out:.0f} + {j.slack} slack), wings wrap "
          f"{math.degrees(math.asin(j.wing_w2 / j.r_wall)):.0f} deg of rim per side")
    print(f"  capture x +/-{j.slack:.2f}  y ~+/-{ys:.2f} (gravity-seated)  "
          f"lift blocked at +{j.slot_h/2 - cf.wafer_T/2:.1f}")
    print(f"  swing   clearance over the bench for rotating hardware: "
          f"{j.zc - cf.z_bot:.1f} mm (#10 nut needs 5.5, wing nut ~11, knob 10)\n")

    seg  = build_segment(cf)
    waf  = build_wafer(cf, 0)
    fout = build_outboard(j)
    fin  = build_inboard(j)
    rod, nut, washer, wnut, rod_len = build_hardware(j)

    print(f"  drivetrain (all modelled in the fitcheck): #10-24 rod cut to "
          f"{5 * math.ceil(rod_len / 5):.0f} mm from a 36\" stick, hex nut "
          f"captive in the inboard tower, #10 washer + wing nut outboard "
          f"(or print the knob)\n")

    ok = run_checks(j, seg, waf, fout, fin, rod, nut, washer, wnut)
    print()

    dz = -cf.z_bot                            # print with the bench face on the bed
    outs = [('cure_jig_outboard.stl', [fout.translate([0, 0, dz])], 'prints as-is'),
            ('cure_jig_inboard.stl',  [fin.translate([0, 0, dz])],  'prints as-is'),
            ('cure_jig_knob.stl',     [build_knob(j)],              'optional, vs wing nut'),
            ('cure_jig_fitcheck.stl',
             [seg, waf, fout, fin, rod, nut, washer, wnut],
             'view only, full drivetrain')]
    for fname, solids, note in outs:
        bodies = write_stl(solids, os.path.join(a.out, fname))
        v = report(fname, solids, bodies, note)
        if 'fitcheck' not in fname and 'knob' not in fname:
            print(f"{'':24}mass  45% infill {v*1.27e-3*0.45:6.1f} g   "
                  f"solid {v*1.27e-3:6.1f} g")

    print(f"\n{'ALL CHECKS PASS' if ok else 'CHECK FAILURES ABOVE — do not print'}")
    print(f"Wrote to {os.path.abspath(a.out)}/")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
