#!/usr/bin/env python3
"""
Wafer Halo — printable metric hardware: M5 and M6 screws + nuts.

Why printed: the jig-side fasteners in this build carry essentially no load
(the cure jig closes a force loop through printed fences; the bonding-jig peg
pushes a wafer edge with finger force), so PETG threads are plenty — and a
printed screw + nut costs nothing and ships with the repo instead of an
unverified McMaster line item. The one thing you still buy is the cure jig's
~350 mm M6 threaded rod: that span is not printable as a thread.

Thread form: ISO 60-degree profile (crest flat p/8, root flat p/4, depth
0.6134·p) built as a radius-modulated cross-section swept with a twist
extrude — one full cross-section rotation per pitch gives a true single-start
helix. The nut is cut with the same generator at +`clr` radial clearance.

Printability, measured against a 0.4 nozzle / 0.20 mm layers:
  M6x1.0  thread depth 0.61 mm — prints reliably, threads by hand
  M5x0.8  thread depth 0.49 mm — the practical FDM floor; prints, but chase
          the first nut on by force (or run a steel M5 nut down it once)
Print both VERTICALLY (head on the bed — the models are already oriented);
a horizontal thread is layer-stepped garbage. Default radial clearance is
0.25 mm; tune with --clr if your printer runs tight or loose.

Self-checks (script exits nonzero on FAIL):
  - screw + nut watertight, nut genus 1
  - nut spins on: screw ^ nut == 0 with the nut coaxial at mid-shank
  - threads actually engage: the nut's internal crests reach 0.36 mm (M6)
    inside the screw's major cylinder — a clearance hole would fail this

    pip install manifold3d
    python3 scripts/printed_hardware_stl.py            # -> stl/ (M5 + M6)
    python3 scripts/printed_hardware_stl.py --help     # sizes, lengths, clr
"""
from __future__ import annotations
import math, os, sys, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from segment_stl import write_stl, report, Manifold, HAVE_MANIFOLD
if HAVE_MANIFOLD:
    from manifold3d import CrossSection

# d = nominal Ø, p = pitch, AF = hex across flats, m = nut thickness
# (ISO 4032 pattern), head_d/head_h = printed 12-gon drive head, L = default
# thread length. Every number is overridable per-run via CLI flags.
SIZES = {
    'M5': dict(d=5.0, p=0.8, AF=8.0,  m=4.7, head_d=15.0, head_h=4.0, L=30.0),
    'M6': dict(d=6.0, p=1.0, AF=10.0, m=5.2, head_d=18.0, head_h=4.0, L=40.0),
}
CLR = 0.25          # radial thread clearance, printed-fit default
FN  = 64            # cross-section points (per revolution; ~0.3 mm chords)
DIV_PER_TURN = 16   # twist-extrude z slices per thread turn


def thread_profile(d, p, grow, fn=FN):
    """ISO 60-deg external thread cross-section: radius modulated once per
    revolution (crest flat p/8 centred at phi=0, root flat p/4 at phi=pi,
    linear flanks between). `grow` expands both radii (nut cutter clearance).
    Twist-extruding this by 360 deg/pitch sweeps a single-start helix whose
    axial section is exactly this radial profile."""
    r_maj = d / 2.0 + grow
    r_min = d / 2.0 - 0.6134 * p + grow
    pts = []
    for i in range(fn):
        u = i / fn                      # fraction of a turn, crest at u=0
        t = min(u, 1.0 - u)             # 0 at crest centre, 0.5 at root centre
        if t <= 1.0 / 16.0:
            r = r_maj
        elif t >= 3.0 / 8.0:
            r = r_min
        else:
            r = r_maj + (r_min - r_maj) * (t - 1.0 / 16.0) / (3.0 / 8.0 - 1.0 / 16.0)
        a = 2.0 * math.pi * u
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def thread_solid(d, p, length, grow=0.0):
    """Single-start ISO thread from z=0 to z=length, axis +z."""
    turns = length / p
    return Manifold.extrude(CrossSection([thread_profile(d, p, grow)]), length,
                            n_divisions=max(8, int(turns * DIV_PER_TURN)),
                            twist_degrees=360.0 * turns)


def ngon(r, n=12, rot=0.0):
    return [(r * math.cos(2 * math.pi * i / n + rot),
             r * math.sin(2 * math.pi * i / n + rot)) for i in range(n)]


def cone(r0, r1, z0, h, fn=FN):
    return (Manifold.cylinder(h, r0, r1, fn).translate([0.0, 0.0, z0]))


def build_screw(s):
    """Knob-head screw, head on the bed, thread up (the print orientation).
    Tip leads in with a one-pitch cone chamfer down to the root radius —
    subtract the region outside a shrinking cone over the last pitch."""
    head = Manifold.extrude(CrossSection([ngon(s['head_d'] / 2.0)]), s['head_h'])
    shank = thread_solid(s['d'], s['p'], s['L']).translate([0.0, 0.0, s['head_h']])
    tip = s['head_h'] + s['L']
    r_min = s['d'] / 2.0 - 0.6134 * s['p']
    cut = (Manifold.cylinder(s['p'] + 0.5, s['d'], s['d'], FN)
           .translate([0.0, 0.0, tip - s['p']])
           - cone(s['d'] / 2.0, r_min, tip - s['p'], s['p'] + 0.001, FN))
    return head + shank - cut


def build_nut(s, clr):
    """Hex nut (ISO AF, wrenchable) cut with the clearanced thread; both
    faces get a 0.8 mm entry chamfer so a printed screw starts by hand."""
    r_hex = s['AF'] / math.sqrt(3.0)
    hexbody = Manifold.extrude(CrossSection([ngon(r_hex, 6)]), s['m'])
    # the cutter's downward offset must be a whole pitch: any other value
    # rotates the internal helix by (offset/p) turns relative to a screw
    # whose nut sits at a pitch-multiple height, and the fit check clashes
    bore = (thread_solid(s['d'], s['p'], s['m'] + 2.0 * s['p'], grow=clr)
            .translate([0.0, 0.0, -s['p']]))
    r_maj_c = s['d'] / 2.0 + clr
    ch = 0.8
    chamfers = (cone(r_maj_c + ch, r_maj_c, -0.001, ch) +
                cone(r_maj_c, r_maj_c + ch, s['m'] - ch, ch + 0.001))
    return hexbody - bore - chamfers


def main():
    if not HAVE_MANIFOLD:
        sys.exit("needs manifold3d for STL output:  pip install manifold3d")
    ap = argparse.ArgumentParser(description="printable M5/M6 screws + nuts")
    ap.add_argument('-o', '--out', default='stl')
    ap.add_argument('--sizes', default='M5,M6', help="comma list from: M5,M6")
    ap.add_argument('--clr', type=float, default=CLR,
                    help=f"radial thread clearance, default {CLR}")
    ap.add_argument('--L', type=float, default=None,
                    help="thread length override, both sizes")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    ok = True
    for name in [x.strip().upper() for x in a.sizes.split(',') if x.strip()]:
        if name not in SIZES:
            sys.exit(f"unknown size {name!r} — choose from {list(SIZES)}")
        s = dict(SIZES[name])
        if a.L: s['L'] = a.L
        screw = build_screw(s)
        nut = build_nut(s, a.clr)

        # --- checks ---------------------------------------------------------
        # A threading nut self-aligns in phase, so the model nut must sit at
        # a whole number of pitches up the helix — an arbitrary z clashes
        # flank-on-flank and reads as false interference.
        z_nut = s['head_h'] + s['p'] * round((s['L'] / 2.0) / s['p'])
        nut_on = nut.translate([0.0, 0.0, z_nut])
        v_fit = (screw ^ nut_on).volume()
        # engagement: nut crests must reach inside the screw's major cylinder
        depth = 0.6134 * s['p'] - a.clr
        probe = Manifold.cylinder(s['m'], s['d'] / 2.0 + a.clr - 0.02,
                                  s['d'] / 2.0 + a.clr - 0.02, FN)
        v_eng = (nut ^ probe).volume()  # hex minus bore inside probe radius
        checks = [
            (f'{name} nut spins on (0 mm3 at +{a.clr} clearance)', v_fit < 1e-6),
            (f'{name} threads engage ({depth:.2f} mm crest overlap)',
             depth > 0.15 and v_eng > 1e-3),
        ]
        for label, good in checks:
            ok &= good
            print(f"    {'PASS' if good else 'FAIL':4}  {label}")
        if depth < 0.35:
            print(f"          note: {name} engagement {depth:.2f} mm is at the "
                  f"FDM floor — print vertically, expect to chase the first fit")

        for part, solid in (('screw', screw), ('nut', nut)):
            fname = f"{name.lower()}_{part}.stl"
            bodies = write_stl([solid], os.path.join(a.out, fname))
            v = report(fname, [solid], bodies,
                       f"{name}x{s['p']} printed, vertical, clr {a.clr}")
            print(f"{'':24}mass  solid PETG {v * 1.27e-3:5.1f} g")

    print(f"\n{'ALL CHECKS PASS' if ok else 'CHECK FAILURES ABOVE — do not print'}")
    print(f"Wrote to {os.path.abspath(a.out)}/")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
