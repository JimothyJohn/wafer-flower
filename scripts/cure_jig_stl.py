#!/usr/bin/env python3
"""
Wafer Halo — tape placement jig (OP 012): guides the wafer onto its taped
land in ONE try. Bench use, one segment at a time, flat on its bottom.

TAPE-ONLY REWORK (2026-07-27, Nick: "I'm no longer curing and am just
taping it, simplify the jig"): acrylic foam tape grabs on first contact —
there is no cure hold, so the whole clamping drivetrain (threaded rod
tension, captive hex nut, washer, printed knob) is GONE. What tape needs
instead is accurate PRE-alignment, because the wafer cannot slide to its
seat after it touches: the four capture pegs become a drop-in FUNNEL.

Two printed fences register on the segment over ONE plain Ø6 pin passed
RADIALLY THROUGH the segment's Ø6.5 keyhole:

  [outboard fence]===(keyhole)===[inboard fence]
    nose butts r=Ro                prong butts r=Ri

The pin is a slip fit in all three bores — it registers the fences in y/z
while the butted faces give x. Nothing is tightened; the fences are only
hand-pressed against the segment for the seconds the placement takes.
The PIN IS PRINTED (Ø6 D-section, disc pull-head, lies flat on the bed) —
the jig is now ZERO bought hardware. An M6x1.0 threaded rod (Ø6.0) from
the old cure-jig days works identically if you have one.

ALIGNED WITH THE WAFER CENTRE, by construction and by check: the keyhole
meridian (a=0) is the wafer-centre meridian, so the pin axis lies in the
vertical plane through the wafer centre (R, 0), and the four peg flanks sit
at projected-rim + slack about that same centre — the funnelled position IS
the nominal wafer centre. The script verifies it numerically.

Capture, not clamp — PEGS ONLY (2026-07-25, Nick's call: constrain X/Y,
let gravity own Z, keep the jig part-agnostic and never overconstrained):
  x (radial):  +/-slack (0.15) — two pegs per fence, flanks at rim + slack
  y (tangent): ~ +/-slack/sin(peg_az) = 0.40 — pegs sit +/-22 deg off the
               radial meridian; the cone-chamfered tips lead the wafer in
               as it is lowered (with tape it must land aligned — the
               flanks centre it on the way DOWN, not after touchdown)
  z (lift):    FREE. Nothing overhangs the wafer, nothing to snag on the
               way in or out — lower it between the peg chamfers; after
               the press the fences slide apart and the jig lifts away

Needs the Rev B.3+ M6 THROUGH keyhole (segment_stl.py hole_D 6.5,
hole_dep >= bw). Segments printed with the old Ø5 keyhole: drill out to
6.5 mm from the outer face — the axis is tmin + 3.35 mm above the flat
bottom (was tmin + 2.6 at Ø5; a mis-height hole just needs the jig bores
redrilled to match, the fences don't care structurally).

Use: segment flat on the bench; press the tape pads onto the LAND (two
13x13 pads split radially — see the glue-area notes; leave the liners ON);
slide the outboard fence in until its nose butts the outer arc face, the
inboard fence until its prong butts the inner face, push the pin through;
peel the liners; lower the wafer between the peg chamfers until it rests
on the tape; press firmly OVER THE LAND CENTROID only (never the
unsupported wafer centre); slide the pin out, part the fences, lift the
jig away. One shot — the tape does not reposition.

    pip install manifold3d
    python3 scripts/cure_jig_stl.py            # -> stl/
    python3 scripts/cure_jig_stl.py --help     # every PARAMS/JIG entry is a flag
"""
from __future__ import annotations
import math, os, sys, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from segment_stl import (PARAMS, Cfg, box, build_segment,
                         build_wafer, write_stl, report, keyhole_z,
                         Manifold, HAVE_MANIFOLD)

# ----------------------------------------------------------------------------
JIG = dict(
    rod_D    = 6.0,    # locating pin Ø: printed D-section pin, or an M6x1.0
                       # threaded rod / #10-24 / M5 from the cure-jig era
    bore_clr = 0.5,    # pin bore = rod_D + bore_clr (= the segment's Ø6.5 keyhole)
    slack    = 0.15,   # peg standoff per side from the nominal rim
    peg_D    = 8.0,    # capture peg diameter (2026-07-25, Nick: pegs, not
                       # wall cutouts — X/Y only, gravity owns Z, and the
                       # jig stops caring what wafer/tilt it holds)
    peg_az   = 22.0,   # peg azimuth, deg either side of the radial meridian
                       # (per fence). Sets the tangential capture window:
                       # y ~ +/- slack / sin(peg_az) = 0.40 at defaults
    peg_c    = 3.0,    # peg rise above the local rim top
    fence_w  = 64.0,   # tangential width of the fence cores (widened 60->64
                       # 2026-07-27 so the Ø10 hold-down counterbores at
                       # y=±25 keep 2 mm of wall to the fence edge)
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
        self.w2     = self.fence_w / 2.0
        self.x_in   = cf.R - cf.r              # nominal rim, inboard / outboard
        self.x_out  = cf.R + cf.r
        self.x_back = self.x_out + 10.0        # outboard fence rear face
        self.x_bk   = self.x_in - 32.0         # inboard fence back face (was
                                               # -28 with the captive nut,
                                               # -16 after the tape rework;
                                               # -32 again so the grid
                                               # hold-down at x=175 fits)
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
        # 0.8 roof over the bore (was 1.5): the M6 axis sits 0.75 higher and
        # the wafer-underside clearance assert below is the hard ceiling.
        self.boss_top  = self.zc + self.bore_r + 0.8
        self.prong_top = -(cf.wafer_T / 2 + 14.0 * tn + 2.0)
        self.prong_bot = cf.z1 + 0.5           # 0.5 above the gear flange
        # sanity: bore roofed under the wafer, rib still clear of the wafer
        assert self.boss_top < -(cf.wafer_T / 2 + (self.boss_w / 2) * tn + 1.4), \
            "bore roof rib would touch the wafer underside"


# ---- solid helpers (box/hex_poly come from segment_stl) --------------------
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


def holddown(j, f, hx, top):
    """One pair of bench hold-down holes at (hx, ±25): Ø5.4 through, Ø10
    counterbore sunk 3.5 below the local top face. Every hold-down in the
    kit lands on the 25 mm grid (2026-07-27, Nick: breadboard mockup), so
    both fences bolt to a 25 mm-pitch board AT their nominal working
    separation."""
    cf = j.cf
    for sy in (25.0, -25.0):
        f -= vcyl(2.7, cf.z_bot - 1.0, top - cf.z_bot + 2.0, hx, sy, fn=48)
        f -= vcyl(5.0, top - 3.5, 4.0, hx, sy, fn=48)
    return f


def peg_arms(j, pegs):
    """Support arm + peg for each capture peg; arm half-width = the peg
    diameter so the peg never overhangs its own support."""
    f = None
    for px, py in pegs:
        sy = 1.0 if py > 0 else -1.0
        a = box(px - j.peg_D, px + j.peg_D, sy * (j.w2 - 2.0),
                py + sy * j.peg_D, j.cf.z_bot, j.arm_top) + peg(j, px, py)
        f = a if f is None else f + a
    return f


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
    tip_max = cf.g_tip * (cf.g_pitch + cf.gear_F) / cf.g_pitch  # big end (wall)
    xf = tip_max + 4.0                      # feet start beyond the tooth tips
    x1 = j.x_back
    deck_lo, deck_hi = cf.z1 + 0.8, -3.5    # over the teeth, under the wafer
    f  = box(cf.Ro, x1, -j.w2, j.w2, deck_lo, deck_hi)                      # deck
    f += box(xf, xf + 22.0, -j.w2, j.w2, cf.z_bot, deck_lo + 1.0)           # front foot
    f += box(j.x_out - 30.0, x1, -j.w2, j.w2, cf.z_bot, j.under_top)        # rear block
    f += peg_arms(j, j.pegs_out)
    # bench hold-downs on the 25 mm grid: one pair through the front foot,
    # one through the rear block (both capped by the deck at z -3.5)
    hx_f = 25.0 * math.ceil((xf + 5.0) / 25.0)
    hx_r = 25.0 * round((j.x_out - 10.0) / 25.0)
    assert xf + 5.0 <= hx_f <= xf + 17.0, f"foot hold-down x={hx_f} off the foot"
    assert j.x_out - 25.0 <= hx_r <= x1 - 5.0, f"rear hold-down x={hx_r} off the block"
    f = holddown(j, f, hx_f, deck_hi)
    f = holddown(j, f, hx_r, deck_hi)
    # nose finger: butts the outer arc face above the tooth band. +0.05
    # standoff so the different chord phases of this 512-gon and the
    # segment's 160-point arc don't overlap.
    f -= vcyl(cf.Ro + 0.05, cf.z_bot - 1.0, 60.0)
    f -= xcyl(j.bore_r, cf.Ro - 2.0, x1 + 2.0, j.zc)
    return f


def build_inboard(j):
    """Sits in the central hole: TWO capture pegs just inside the rim (see
    build_outboard for the peg philosophy), low prong butting the band's
    inner face above the gear flange. Peg plan radius from the HALO axis is
    ~215 — the wings this replaces used to graze the gear teeth by 6 mm;
    the pegs clear the tooth tips by ~30. No nut tower any more — the pin
    just slides through."""
    cf = j.cf
    x1 = j.x_in + 2.0
    x0 = j.x_bk                                                             # back face
    f  = box(x0, x1, -j.w2, j.w2, cf.z_bot, j.under_top)                    # base
    f += peg_arms(j, j.pegs_in)
    # datum prong: butts the band inner face (r=Ri) between gear flange and
    # land. The pin bore breaks 0.6 mm out of its underside over the last
    # stretch (prong floor is capped by the flange top) — an open guide
    # groove there is fine, the full round bore in the body does the guiding.
    prong = box(x0 + 2.0, cf.Ri + 2.0, -14.0, 14.0, j.prong_bot, j.prong_top)
    f += prong ^ vcyl(cf.Ri - 0.05, cf.z_bot - 1.0, 60.0)   # 0.05 datum standoff
    f -= xcyl(j.bore_r, x0 - 2.0, cf.Ri + 4.0, j.zc)
    # bench hold-downs on the 25 mm grid, through the base
    hx_i = 25.0 * math.floor((x1 - 5.0) / 25.0)
    assert x0 + 5.0 <= hx_i <= x1 - 5.0, f"inboard hold-down x={hx_i} off the base"
    return holddown(j, f, hx_i, j.under_top)


def build_pin(j):
    """The one loose piece: a plain locating pin through both fences and
    the segment keyhole. Slip fit everywhere (no clamp — tape needs no cure
    hold, the pin only registers the fences in y/z while the butted noses
    give x). PRINTED at Ø6.2 (0.15/side in the Ø6.5 bores — snugger than
    the old M6 rod) with a 0.5 mm D-flat so it prints lying down, and a
    Ø16 disc pull-head carrying the same flat: insert FLAT-DOWN (the head
    shows the orientation) and the side bearing keeps the 0.15 slack.
    Total ~330 mm — fits the bed straight. An M6x1.0 threaded rod (Ø6.0)
    from the cure-jig era works identically, a touch looser.
    Returns (pin_in_place, printable_pin, length)."""
    pr = j.bore_r - 0.15                       # Ø6.2 at the Ø6.5 bore
    x0 = j.x_in - 10.0                         # tail: ~65 mm engaged in the
                                               # inboard bore, and the pin
                                               # stays under the 340 mm bed
                                               # (x_bk moved back for the
                                               # grid hold-down)
    x1 = j.x_back + 3.0                        # proud of the outboard rear
    pin = xcyl(pr, x0, x1, j.zc) + xcyl(8.0, x1, x1 + 4.0, j.zc)
    flat = j.zc - (pr - 0.5)                   # 0.5 mm off the shaft bottom
    pin -= box(x0 - 1.0, x1 + 5.0, -10.0, 10.0, j.zc - 20.0, flat)
    printable = pin.translate([-x0, 0.0, -flat])
    return pin, printable, (x1 + 4.0) - x0


# ---- verification -----------------------------------------------------------
def run_checks(j, seg, waf, fout, fin, pin):
    EPS = 1e-6
    cf = j.cf
    fences = fout + fin
    _, c, _ = cf.wafer_frame(0)
    zero = [
        ('pin axis plane contains the wafer centre', abs(c[1])),
        ('outboard fence vs segment', (fout ^ seg).volume()),
        ('inboard fence vs segment',  (fin ^ seg).volume()),
        ('fences vs wafer, nominal',  (fences ^ waf).volume()),
        ('pin vs segment (keyhole through & clear of gear)', (pin ^ seg).volume()),
        ('pin vs fences (bores clear)', (pin ^ fences).volume()),
        ('pin withdrawn +60 x clears everything',
         (pin.translate([60.0, 0, 0]) ^ (seg + waf + fences)).volume()),
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
              f"the pin cannot reach the inboard fence. Regenerate the segment.")

    ys = j.slack / math.sin(math.radians(j.peg_az))
    print(f"Tape jig OP 012  ·  theta={cf.theta}  keyhole z={j.zc:.2f} "
          f"({j.zc - cf.z_bot:.1f} above the bench)")
    print(f"  centre  pin axis lies in the wafer-centre plane (a=0 meridian): "
          f"crosses ({cf.R:.0f}, 0) at z={j.zc:.2f}, {abs(j.zc):.1f} below the "
          f"wafer mid-plane; all four peg flanks sit at rim + {j.slack}")
    print(f"  pegs    Ø{j.peg_D:.0f} at ±{j.peg_az:.0f}° per fence, tops at "
          f"z={j.peg_top:.1f} — X/Y only, Z is gravity's job (part-agnostic: "
          f"everything re-derives from wafer Ø/tilt)")
    print(f"  funnel  x ±{j.slack:.2f}  y ~±{ys:.2f} — with tape the flanks "
          f"centre the wafer on the way DOWN (one shot, no repositioning)  "
          f"lift FREE")

    seg  = build_segment(cf)
    waf  = build_wafer(cf, 0)
    fout = build_outboard(j)
    fin  = build_inboard(j)
    pin, pin_print, pin_len = build_pin(j)

    print(f"  pin     printed Ø{2 * (j.bore_r - 0.15):.1f} D-flat x "
          f"{pin_len:.0f} mm, insert FLAT-DOWN (an M6x1.0 rod also works, "
          f"a touch looser). No nuts, no knob, no washer — nothing is "
          f"tightened, tape needs no cure hold\n")

    ok = run_checks(j, seg, waf, fout, fin, pin)
    print()

    dz = -cf.z_bot                            # print with the bench face on the bed
    outs = [('cure_jig_outboard.stl', [fout.translate([0, 0, dz])], 'prints as-is'),
            ('cure_jig_inboard.stl',  [fin.translate([0, 0, dz])],  'prints as-is'),
            ('cure_jig_pin.stl',      [pin_print],                  'locating pin, prints on its D-flat'),
            ('cure_jig_fitcheck.stl',
             [seg, waf, fout, fin, pin],
             'view only, pin inserted')]
    for fname, solids, note in outs:
        bodies = write_stl(solids, os.path.join(a.out, fname))
        v = report(fname, solids, bodies, note)
        if 'fitcheck' not in fname and 'pin' not in fname:
            # 15% is the print setting for this jig — no real load path
            # through it; 45% shown for comparison with old figures.
            print(f"{'':24}mass  10% PLA (rough) {v*1.24e-3*0.10:6.1f} g   "
                  f"solid {v*1.24e-3:6.1f} g")

    print(f"\n{'ALL CHECKS PASS' if ok else 'CHECK FAILURES ABOVE — do not print'}")
    print(f"Wrote to {os.path.abspath(a.out)}/")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
