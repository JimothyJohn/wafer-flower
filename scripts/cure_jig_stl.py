#!/usr/bin/env python3
"""
Wafer Halo — perpendicular cure jig (OP 012): holds the wafer centred over the
land while the adhesive cures (the SMP / PL Premium path; tape needs no cure
hold). Bench use, one segment at a time, flat on its bottom.

Two printed fences slide toward each other along ONE threaded rod that passes
RADIALLY THROUGH the segment's Ø6.5 keyhole:

  knob > [outboard fence]===(keyhole)===[inboard fence] < captive hex nut
              nose butts r=Ro          prong butts r=Ri

Tightening the knob draws BOTH fences onto the segment, so the closed force
loop is jig<->segment only. The wafer floats between four capture PEGS with
`slack` per side and carries ZERO clamp load — edges only, never flex.

ALIGNED WITH THE WAFER CENTRE, by construction and by check: the keyhole
meridian (a=0) is the wafer-centre meridian, so the rod axis lies in the
vertical plane through the wafer centre (R, 0), and the four peg flanks sit
at projected-rim + slack about that same centre — the captured position IS
the nominal wafer centre. The script verifies it numerically.

Capture, not clamp — PEGS ONLY (2026-07-25, Nick's call: constrain X/Y,
let gravity own Z, keep the jig part-agnostic and never overconstrained):
  x (radial):  +/-slack (0.15) — two pegs per fence, flanks at rim + slack
  y (tangent): ~ +/-slack/sin(peg_az) = 0.40 — pegs sit +/-22 deg off the
               radial meridian; on the tilted land the wafer settles
               DOWNHILL onto the two down-slope pegs (one per fence), and
               that two-point gravity seat IS the centring
  z (lift):    FREE. Nothing overhangs the wafer, nothing to snag on the
               way in or out — set it down between the peg chamfers, lift
               it straight off after cure

The ENTIRE drivetrain is modelled as solids and checked, not assumed: rod at
thread OD, captive hex nut on its pocket floor, M6 washer, and the printed
knob with its embedded hex nut. A wing nut is NOT usable at M6: it swings
~15 mm off the axis and the axis is only 13.35 above the bench (raising it
further would break the bore into the adhesive pocket). The knob (Ø20,
10 mm swing) or a plain hex nut + wrench both clear.

Hardware (Home Depot): M6x1.0 threaded rod (Ø6.0 — slides through the Ø6.5
keyhole as printed, no reaming), cut to ~350 mm from a 36" / 1 m stick, two
M6 hex nuts (one captive in the inboard tower, one embedded in the printed
knob), one M6 washer. #10-24 or M5 rod + nuts also drop through every bore,
loose. The rod is the one piece you must buy — it spans ~350 mm, far past
any printable screw (printed_hardware_stl.py covers the short stuff).

Needs the Rev B.3+ M6 THROUGH keyhole (segment_stl.py hole_D 6.5,
hole_dep >= bw). Segments printed with the old Ø5 keyhole: drill out to
6.5 mm from the outer face — the axis is tmin + 3.35 mm above the flat
bottom (was tmin + 2.6 at Ø5; a mis-height hole just needs the jig bores
redrilled to match, the fences don't care structurally).

Use: bond one segment flat on the bench; wet SMP beads in the pocket; set the
wafer by eye (+/-1 mm); slide the outboard fence in until its nose butts the
outer arc face, then the inboard fence; push the rod through from outboard,
thread it into the captive nut, spin the knob finger tight. The wafer
settles downhill onto the two down-slope pegs as everything seats. Leave
until cured, back the rod out, slide the fences apart radially — the wafer
lifts straight out, nothing overhangs it.

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
    rod_D    = 6.0,    # M6x1.0 threaded rod; #10-24 (4.83) / M5 also fit, loose
    bore_clr = 0.5,    # rod bore = rod_D + bore_clr (= the segment's Ø6.5 keyhole)
    nut_AF   = 10.0,   # M6 hex nut across flats (ISO 4032)
    nut_clr  = 0.45,   # pocket oversize on the across-flats
    nut_t    = 5.2,    # M6 hex nut thickness (ISO 4032)
    nut_deep = 9.0,    # hex pocket depth (nut is 5.2 thick; extra is rod room)
    slack    = 0.15,   # peg standoff per side from the nominal rim
    peg_D    = 8.0,    # capture peg diameter (2026-07-25, Nick: pegs, not
                       # wall cutouts — X/Y only, gravity owns Z, and the
                       # jig stops caring what wafer/tilt it holds)
    peg_az   = 22.0,   # peg azimuth, deg either side of the radial meridian
                       # (per fence). Sets the tangential capture window:
                       # y ~ +/- slack / sin(peg_az) = 0.40 at defaults
    peg_c    = 3.0,    # peg rise above the local rim top
    fence_w  = 60.0,   # tangential width of the fence cores
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
        az = math.radians(self.peg_az)
        # peg centres sit slack + peg radius outside the PROJECTED rim at
        # their own azimuth. The tilted wafer's plan rim is an ELLIPSE
        # (y semi-axis r*cos(theta), 0.57 mm shy of r at theta=5) — pegs on
        # a plain r+slack circle would gap 0.23 instead of 0.15 at 22 deg
        # and the capture window would drift with tilt. Deriving from the
        # ellipse keeps the flank gap = slack at every peg, any wafer, any
        # tilt. Only the peg FLANKS ever touch the wafer — X/Y only.
        r_ell = lambda phi: cf.r * math.hypot(math.cos(phi),
                                              math.cos(cf.th) * math.sin(phi))
        self.peg_rho = r_ell(az) + self.slack + self.peg_D / 2.0
        self.pegs_out = [(cf.R + self.peg_rho * math.cos(s_ * az),
                          self.peg_rho * math.sin(s_ * az)) for s_ in (1, -1)]
        self.pegs_in = [(cf.R - self.peg_rho * math.cos(s_ * az),
                         self.peg_rho * math.sin(s_ * az)) for s_ in (1, -1)]
        # pegs top out peg_c above the UPHILL rim top; z stays free above
        self.peg_top = cf.r * math.sin(az) * tn + cf.wafer_T / 2 + self.peg_c
        swing = self.w2 * tn                   # rim z swing across the fence core
        self.under_top = -(cf.wafer_T / 2 + swing + self.clr_und)   # rail/base top
        # peg support arms pass under the rim: clear the wafer underside at
        # the arm's worst in-footprint point (the rim itself, y = r sin az)
        self.arm_top = -(cf.wafer_T / 2 + cf.r * math.sin(az) * tn + self.clr_und)
        self.wall_top = swing + 5.0            # nut tower height (was lip roof)
        # 0.8 roof over the bore (was 1.5): the M6 axis sits 0.75 higher and
        # the wafer-underside clearance assert below is the hard ceiling.
        self.boss_top  = self.zc + self.bore_r + 0.8
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


def peg(j, px, py):
    """One capture peg: a vertical post from the bench to peg_top with a
    cone-chamfered tip (drop-in lead). The wafer rim can only ever touch
    its FLANK — in-plane (X/Y) constraint, nothing above the rim."""
    p = vcyl(j.peg_D / 2.0, j.cf.z_bot, j.peg_top - j.cf.z_bot, px, py, fn=64)
    tip = (Manifold.cylinder(3.0, j.peg_D / 2.0, j.peg_D / 2.0 - 2.0, 64)
           .translate([px, py, j.peg_top]))
    return p + tip


def hex_pocket(j, x0):
    R = j.nut_R   # vertex-up hexagon: flats vertical (nut can't spin), no bridge
    pts = [(R * math.cos(math.radians(60 * i)), R * math.sin(math.radians(60 * i)))
           for i in range(6)]
    return (prism(pts, 0.0, j.nut_deep + 0.5)
            .rotate([0.0, 90.0, 0.0]).translate([x0, 0.0, j.zc]))


# ---- the two fences ---------------------------------------------------------
def build_outboard(j):
    """Outboard fence, reworked for the EXTERNAL gear (2026-07-25): the
    outer spiral-bevel teeth now occupy r285..~318 over the bottom tmin, so
    the old bench-level nose foot would land on teeth. The fence became a
    BRIDGE: feet on the bench beyond the tooth tips, a deck spanning over
    the teeth 0.8 mm proud of their top face, and a nose FINGER reaching
    down to butt the band's outer face ABOVE the tooth band (that face is
    exposed from z1 up to the land). Pegs and the drivetrain are unchanged.
    Capture pegs only: X/Y held, gravity owns Z (see build_inboard)."""
    cf = j.cf
    tip_front = cf.g_tip * (cf.g_pitch + cf.tmin) / cf.g_pitch
    xf = tip_front + 4.0                    # feet start beyond the tooth tips
    x1 = j.x_out + 10.0
    deck_lo, deck_hi = cf.z1 + 0.8, -3.5    # over the teeth, under the wafer
    f  = box(cf.Ro, x1, -j.w2, j.w2, deck_lo, deck_hi)                      # deck
    f += box(xf, xf + 16.0, -j.w2, j.w2, cf.z_bot, deck_lo + 1.0)           # front foot
    f += box(j.x_out - 30.0, x1, -j.w2, j.w2, cf.z_bot, j.under_top)        # rear block
    for px, py in j.pegs_out:
        sy = 1.0 if py > 0 else -1.0
        f += box(px - 8.0, px + 8.0, sy * (j.w2 - 2.0), py + sy * 8.0,
                 cf.z_bot, j.arm_top)                                       # peg arm
        f += peg(j, px, py)
    # nose finger: butts the outer arc face above the tooth band. +0.05
    # standoff so the different chord phases of this 512-gon and the
    # segment's 160-point arc don't overlap.
    f -= vcyl(cf.Ro + 0.05, cf.z_bot - 1.0, 60.0)
    f -= xcyl(j.bore_r, cf.Ro - 2.0, x1 + 2.0, j.zc)
    return f


def build_inboard(j):
    """Sits in the central hole: nut tower at the back, TWO capture pegs
    just inside the rim (see build_outboard for the peg philosophy), low
    prong butting the band's inner face above the gear flange. Peg plan
    radius from the HALO axis is ~215 — the wings this replaces used to
    graze the gear teeth by 6 mm; the pegs clear the m5.6 spiral tips
    (r246) by ~30."""
    cf = j.cf
    x1 = j.x_in + 2.0
    x0 = j.x_in - 28.0                                                      # back face
    f  = box(x0, x1, -j.w2, j.w2, cf.z_bot, j.under_top)                    # base
    f += box(x0, x0 + 18.0, -j.w2, j.w2, cf.z_bot, j.wall_top)              # nut tower
    for px, py in j.pegs_in:
        sy = 1.0 if py > 0 else -1.0
        f += box(px - 8.0, px + 8.0, sy * (j.w2 - 2.0), py + sy * 8.0,
                 cf.z_bot, j.arm_top)                                       # peg arm
        f += peg(j, px, py)
    # datum prong: butts the band inner face (r=Ri) between gear flange and
    # land. The rod bore breaks 0.6 mm out of its underside over the last
    # stretch (prong floor is capped by the flange top) — an open guide
    # groove there is fine, the full round bore in the body does the guiding.
    prong = box(x0 + 6.0, cf.Ri + 2.0, -14.0, 14.0, j.prong_bot, j.prong_top)
    f += prong ^ vcyl(cf.Ri - 0.05, cf.z_bot - 1.0, 60.0)   # 0.05 datum standoff
    f -= xcyl(j.bore_r, x0 - 2.0, cf.Ri + 4.0, j.zc)
    f -= hex_pocket(j, x0 - 0.5)
    return f


def build_hardware(j):
    """The entire drivetrain as solids: rod at thread OD, captive M6 hex nut
    seated on its pocket floor, M6 washer (DIN 125: Ø12 x 1.6), and the
    printed knob with its embedded M6 nut as the outboard closure. A wing
    nut is deliberately NOT modelled or supported at M6: its wings swing
    ~15 mm off the axis and the axis is only 13.35 above the bench (the
    bench-swing check would fail — correctly). Nut and knob-nut bores are at
    the M6x1 tap drill (5.0), so their overlap with the rod is real thread
    engagement and is deliberately not an interference check."""
    cf = j.cf
    back  = j.x_out + 10.0                    # outboard fence rear face
    floor = (j.x_in - 28.0) + j.nut_deep      # hex pocket floor
    rod0, rod1 = floor - j.nut_t - 0.4, back + 1.6 + 12.0
    rod = xcyl(j.rod_D / 2, rod0, rod1, j.zc)
    R = j.nut_AF / math.sqrt(3.0)             # actual nut, no clearance
    hx = [(R * math.cos(math.radians(60 * i)), R * math.sin(math.radians(60 * i)))
          for i in range(6)]
    nut = (prism(hx, 0.0, j.nut_t).rotate([0.0, 90.0, 0.0])
           .translate([floor - j.nut_t, 0.0, j.zc]))
    nut -= xcyl(2.5, floor - j.nut_t - 1.0, floor + 1.0, j.zc)
    washer = (xcyl(6.0, back, back + 1.6, j.zc)
              - xcyl(3.2, back - 1.0, back + 3.0, j.zc))
    # knob: printed body against the washer, hex pocket opening inboard so
    # the embedded nut bears through the opening onto the washer.
    knob = (build_knob(j).rotate([0.0, 90.0, 0.0])
            .translate([back + 1.6, 0.0, j.zc]))
    knob_nut = (prism(hx, 0.0, j.nut_t).rotate([0.0, 90.0, 0.0])
                .translate([back + 1.8, 0.0, j.zc]))
    knob_nut -= xcyl(2.5, back + 1.0, back + 8.0, j.zc)
    return rod, nut, washer, knob, knob_nut, rod1 - rod0


def build_knob(j):
    """Printed thumb knob (Ø20 12-gon) with a captive M6 hex nut — the
    standard outboard closure. Anything swung on the rod must clear the
    bench: the axis is tmin+3.35 up, so 10 mm of knob swing clears by 3.35
    where a wing nut's ~15 would strike."""
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
def run_checks(j, seg, waf, fout, fin, rod, nut, washer, knob, knob_nut):
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
        ('knob nut vs its knob pocket', (knob_nut ^ knob).volume()),
        ('washer + knob vs outboard fence', ((washer + knob + knob_nut) ^ fout).volume()),
        ('knob swing vs bench', ((knob + knob_nut) ^ bench).volume()),
        ('nut/washer/knob vs segment & wafer',
         (((nut + washer + knob + knob_nut) ^ (seg + waf))).volume()),
    ]
    hit = [
        ('wafer +0.30 x meets outboard stop', (waf.translate([0.30, 0, 0]) ^ fout).volume(), True),
        ('wafer +0.10 x still free',          (waf.translate([0.10, 0, 0]) ^ fout).volume(), False),
        ('wafer -0.30 x meets inboard stop',  (waf.translate([-0.30, 0, 0]) ^ fin).volume(), True),
        ('wafer +0.60 y meets the pegs',      (waf.translate([0, 0.60, 0]) ^ fences).volume(), True),
        ('wafer +0.20 y still free',          (waf.translate([0, 0.20, 0]) ^ fences).volume(), False),
        ('wafer -0.60 y meets the pegs',      (waf.translate([0, -0.60, 0]) ^ fences).volume(), True),
        ('wafer +5.0 z lifts FREE (Z is gravity-held, by design)',
         (waf.translate([0, 0, 5.0]) ^ fences).volume(), False),
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

    ys = j.slack / math.sin(math.radians(j.peg_az))
    print(f"Cure jig OP 012  ·  theta={cf.theta}  keyhole z={j.zc:.2f} "
          f"({j.zc - cf.z_bot:.1f} above the bench)")
    print(f"  centre  rod axis lies in the wafer-centre plane (a=0 meridian): "
          f"crosses ({cf.R:.0f}, 0) at z={j.zc:.2f}, {abs(j.zc):.1f} below the "
          f"wafer mid-plane; all four peg flanks sit at rim + {j.slack}")
    print(f"  pegs    Ø{j.peg_D:.0f} at ±{j.peg_az:.0f}° per fence, tops at "
          f"z={j.peg_top:.1f} — X/Y only, Z is gravity's job (part-agnostic: "
          f"everything re-derives from wafer Ø/tilt)")
    print(f"  capture x ±{j.slack:.2f}  y ~±{ys:.2f} (settles downhill onto "
          f"the two down-slope pegs)  lift FREE")
    print(f"  swing   clearance over the bench for rotating hardware: "
          f"{j.zc - cf.z_bot:.1f} mm (M6 nut needs 5.8, knob 10 — an M6 "
          f"wing nut needs ~15 and does NOT clear)\n")

    seg  = build_segment(cf)
    waf  = build_wafer(cf, 0)
    fout = build_outboard(j)
    fin  = build_inboard(j)
    rod, nut, washer, knob, knob_nut, rod_len = build_hardware(j)

    print(f"  drivetrain (all modelled in the fitcheck): M6x1.0 rod cut to "
          f"{5 * math.ceil(rod_len / 5):.0f} mm from a 36\"/1 m stick, hex "
          f"nut captive in the inboard tower, M6 washer + printed knob with "
          f"its own captive M6 nut outboard\n")

    ok = run_checks(j, seg, waf, fout, fin, rod, nut, washer, knob, knob_nut)
    print()

    dz = -cf.z_bot                            # print with the bench face on the bed
    outs = [('cure_jig_outboard.stl', [fout.translate([0, 0, dz])], 'prints as-is'),
            ('cure_jig_inboard.stl',  [fin.translate([0, 0, dz])],  'prints as-is'),
            ('cure_jig_knob.stl',     [build_knob(j)],              'outboard closure, M6 nut inside'),
            ('cure_jig_fitcheck.stl',
             [seg, waf, fout, fin, rod, nut, washer, knob, knob_nut],
             'view only, full drivetrain')]
    for fname, solids, note in outs:
        bodies = write_stl(solids, os.path.join(a.out, fname))
        v = report(fname, solids, bodies, note)
        if 'fitcheck' not in fname and 'knob' not in fname:
            # 15% is the print setting for this jig — no real load path
            # through it; 45% shown for comparison with old figures.
            print(f"{'':24}mass  15% infill {v*1.27e-3*0.15:6.1f} g   "
                  f"45% {v*1.27e-3*0.45:6.1f} g   solid {v*1.27e-3:6.1f} g")

    print(f"\n{'ALL CHECKS PASS' if ok else 'CHECK FAILURES ABOVE — do not print'}")
    print(f"Wrote to {os.path.abspath(a.out)}/")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
