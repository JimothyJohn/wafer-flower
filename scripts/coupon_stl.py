#!/usr/bin/env python3
"""Small-batch TEST COUPONS cut from the REAL segment solid (2026-08-09,
Nick: "independent isolated models of key parts... that I can test in
small batch prints before doing the whole thing").

Every coupon is a boolean intersection of build_segment()'s production
geometry with a local clipping box — never a re-model — so a coupon that
fits on the bench validates the part that ships. The one exception is the
socket CLEARANCE VARIANTS (the whole point is geometry the shipped part
does not have); those come from a mini-model that is gated volume-identical
to the real segment at the shipping clearance before the variants are
trusted.

Coupons (default gear_drive='face' — the live N20 path; --gear_drive
bevel45 works and swaps the gear coupon to the crossed pair):
  dovetail_male.stl        grip + the full male tail (gate T2)
  dovetail_socket_cNNN.stl socket at clearance 0.NNN per side; edge
                           notches = position in the ascending clearance
                           list (1 notch = tightest)
  gear_sector.stl          ~12 deg of the real toothed flange at the
                           contact meridian — spin the pinion on it
  pinion.stl               the mating pinion, N20 3 mm D-bore
  keyhole_block.stl        the radial O6.5 bore in real wall thickness —
                           jig-pin (O6.2) slide fit, printed lying just
                           like the segment (bore horizontal)
  fitcheck_dovetail.stl    male + shipping-clearance socket mated (view)
  fitcheck_gear.stl        sector + pinion at nominal mesh (view)

Print flat-bottom-down, same profile as the real parts. All coupons are
gated: mated-pair interference, insertion sweep in Z per clearance,
mini-vs-real equality, pinion mesh sweep over a tooth pitch, single
component + watertight per body. Exits nonzero on any FAIL.
"""
import argparse
import copy
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from segment_stl import (Cfg, PARAMS, HAVE_MANIFOLD, arc, band_poly, box,
                         build_pinion, build_segment, bevel_pinion,
                         bevel_pinion_at, face_pinion, face_pinion_at,
                         keyhole_z, prism, report, rotated, socket_poly,
                         write_stl)

if HAVE_MANIFOLD:
    from manifold3d import Manifold

FAILS = []


def gate(ok, name, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name:34} {detail}")
    if not ok:
        FAILS.append(name)


# ----------------------------------------------------------------------------
# clipping frames
# ----------------------------------------------------------------------------
def joint_box(cf, z_top):
    """Box around the +half joint, axis-aligned in the joint-local frame
    (x radial, y tangential across the joint plane), rotated into world.
    Radial extent stays clear of the inner groove and the outer mount
    groove so the coupon is pure slab + dovetail geometry."""
    x0 = cf.rho_c - (cf.dt_tip / 2.0 + 4.0)
    x1 = cf.rho_c + (cf.dt_tip / 2.0 + 4.0)
    assert x0 > cf.Ri + cf.grv_d + 0.5, "coupon box hits the idler groove"
    assert x1 < cf.Ro - cf.ogrv_d - 0.5, "coupon box hits the mount groove"
    b = box(x0, x1, -20.0, 20.0, cf.z_bot - 1.0, z_top)
    return b.rotate([0.0, 0.0, math.degrees(cf.half)])


def joint_to_print(cf, s):
    """Joint-region solid -> print frame: joint plane onto x-z, flat
    bottom onto z=0, dovetail centreline onto x=0. Male body lands y<0
    (tail poking +y), female body y>0."""
    return (s.rotate([0.0, 0.0, -math.degrees(cf.half)])
             .translate([-cf.rho_c, 0.0, -cf.z_bot]))


def wedge(cf, r_in, r_out, half_deg, z0, z1):
    """Annular-sector prism at the a=0 contact meridian."""
    h = math.radians(half_deg)
    poly = arc(r_out, -h, h, 96) + arc(r_in, h, -h, 96)
    return prism(poly, z0, z1 - z0)


# ----------------------------------------------------------------------------
# coupons
# ----------------------------------------------------------------------------
def socket_mini(cf, clearance, z_top):
    """The female joint region rebuilt from the same primitives
    build_segment uses: full annular sector minus the socket cut, at an
    arbitrary clearance. Valid only inside the joint box below z1 (no
    land trim, teeth, pocket, keyhole or grooves reach there) — which is
    exactly what the equality gate against the real segment proves."""
    c2 = copy.copy(cf)
    c2.dt_clear = clearance
    body = prism(band_poly(cf), cf.z_bot, (z_top - cf.z_bot) + 2.0)
    body = body - prism(socket_poly(c2), cf.z_bot - 0.5, cf.dt_h + 1.0)
    return rotated(body, 1, cf)      # segment B's -half face = the +half joint


def notch(cf, s, count):
    """Clearance ID notches on the female grip's far edge (y=+20 in the
    print frame), well clear of the socket."""
    for k in range(count):
        x = (k - (count - 1) / 2.0) * 5.0
        s = s - Manifold.cylinder(60.0, 1.2, 1.2, 32).translate([x, 20.0, -1.0])
    return s


def main():
    if not HAVE_MANIFOLD:
        sys.exit("needs manifold3d for STL output:  pip install manifold3d")
    ap = argparse.ArgumentParser(description="Wafer Halo — printable test coupons")
    ap.add_argument('-o', '--out', default='stl/coupons')
    ap.add_argument('--clearances', default='0.15,0.25,0.35',
                    help='socket clearance per side, mm, comma list')
    ap.add_argument('--gear_span', type=float, default=12.0,
                    help='gear coupon angular span, degrees total')
    for k, v in PARAMS.items():
        ap.add_argument(f'--{k}', type=type(v), default=None)
    a = ap.parse_args()
    kw = {k: getattr(a, k) for k in PARAMS if getattr(a, k) is not None}
    kw.setdefault('gear_drive', 'face')   # the live N20 path, not the repo default
    cf = Cfg(**kw)
    clears = sorted(float(c) for c in a.clearances.split(','))
    os.makedirs(a.out, exist_ok=True)

    print(f"Wafer Halo coupons  ·  gear_drive={cf.gear_drive}  "
          f"dovetail {cf.dt_neck:.0f}/{cf.dt_tip:.0f}×{cf.dt_depth:.0f} "
          f"dt_h {cf.dt_h:.0f}  shipping clearance {cf.dt_clear}  "
          f"variants {clears}")
    seg = build_segment(cf)
    seg_b = rotated(seg, 1, cf)

    # ---- dovetail: male from segment A, real female from segment B ----
    z_top = cf.z_bot + cf.dt_h + 5.0
    jb = joint_box(cf, z_top)
    male = seg ^ jb
    female_real = seg_b ^ jb
    gate((male ^ female_real).volume() < 0.02, 'mated pair interference',
         f"{(male ^ female_real).volume():.5f} mm3 at clearance {cf.dt_clear}")

    fem_mini_ship = socket_mini(cf, cf.dt_clear, z_top) ^ jb
    sym = ((female_real - fem_mini_ship) + (fem_mini_ship - female_real)).volume()
    gate(sym < 0.02, 'mini socket == real segment', f"symdiff {sym:.5f} mm3")

    females = {c: (female_real if abs(c - cf.dt_clear) < 1e-9
                   else socket_mini(cf, c, z_top) ^ jb) for c in clears}
    vols = [females[c].volume() for c in clears]
    gate(all(vols[i] > vols[i + 1] for i in range(len(vols) - 1)),
         'clearance monotonic', ' > '.join(f"{v:.0f}" for v in vols) + ' mm3')
    # assembly slides in Z through the OPEN flat bottom (the socket is
    # blind above — +z would drive the tail into the roof by design)
    for c in clears:
        worst = max((male.translate([0, 0, -t]) ^ females[c]).volume()
                    for t in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0))
        gate(worst < 0.02, f'insertion sweep c={c:.2f}', f"worst {worst:.5f} mm3")

    male_p = joint_to_print(cf, male)
    out = [('dovetail_male.stl', [male_p], 'grip + full tail, print as-is')]
    for i, c in enumerate(clears):
        f_p = notch(cf, joint_to_print(cf, females[c]), i + 1)
        parts = f_p.decompose()
        gate(len(parts) == 1, f'socket c={c:.2f} one component',
             f"{len(parts)} bodies after {i + 1} ID notch(es)")
        out.append((f"dovetail_socket_c{int(round(c * 100)):03d}.stl", [f_p],
                    f"clearance {c:.2f}/side — {i + 1} notch(es)"))
    out.append(('fitcheck_dovetail.stl',
                [male_p, joint_to_print(cf, females[cf.dt_clear])],
                'mated pair, view only'))

    # ---- gear sector + pinion at the a=0 contact meridian ----
    if cf.g_face:
        r_in, r_out = cf.gf_ri - 13.0, cf.gf_ro + 3.0
        gz_top = cf.z_bot + cf.gear_F + 2.0
    elif cf.g_bev:
        r_in, r_out = cf.g_web_i - 12.0, cf.g_tip * cf.g_kbig + 3.0
        gz_top = cf.z_bot + cf.gear_F + 2.0
    else:
        sys.exit("gear coupon supports 'face' and 'bevel45' only")
    gw = wedge(cf, r_in, r_out, a.gear_span / 2.0, cf.z_bot - 1.0, gz_top)
    sector = seg ^ gw
    pin, g = build_pinion(cf)
    pin_mesh, _ = (face_pinion(cf) if cf.g_face else bevel_pinion(cf))
    place = face_pinion_at if cf.g_face else bevel_pinion_at
    sec_mesh = sector.translate([0.0, 0.0, -cf.z_bot])   # into the mesh frame
    # ring rolls d WHILE the pinion spins ratio*d — same as check_mesh
    # (spinning only the pinion reads ~109 mm3 of phase-mismatch overlap)
    def _overlap(d):
        return (sec_mesh.rotate([0.0, 0.0, math.degrees(d)])
                ^ place(cf, pin_mesh, d)).volume()
    worst = max(_overlap((2 * math.pi / cf.teeth) * i / 24) for i in range(24))
    gate(worst < 0.05, 'pinion sweep vs sector',
         f"worst {worst:.5f} mm3 over one tooth pitch, "
         f"{g['T']}T at {cf.pin_ratio:.1f}:1")
    x_mid = (r_in + r_out) / 2.0
    sector_p = sector.translate([-x_mid, 0.0, -cf.z_bot])
    pin_fit = (place(cf, pin_mesh, 0.0).translate([-x_mid, 0.0, 0.0]))
    out += [('gear_sector.stl', [sector_p],
             f"{a.gear_span:.0f} deg of the real flange, teeth up"),
            ('pinion.stl', [pin], f"{g['T']}T, N20 O{cf.pin_bore} D-bore"),
            ('fitcheck_gear.stl', [sector_p, pin_fit], 'nominal mesh, view only')]

    # ---- keyhole bore block: real wall section, O6.2 pin slide fit ----
    if cf.hole_D > 0:
        z0 = cf.z1 - 3.0
        kb = box(cf.Ri - 3.0, cf.Ro + 3.0, -8.0, 8.0, z0, cf.z1 + 12.0)
        key = (seg ^ kb).translate([-cf.rho_c, 0.0, -z0])
        out.append(('keyhole_block.stl', [key],
                    f"O{cf.hole_D} radial bore at its real height, print as-is"))

    print()
    total = 0.0
    for fname, solids, note in out:
        bodies = write_stl(solids, os.path.join(a.out, fname))
        total += report(fname, solids, bodies, note)
    print(f"\n  batch volume {total / 1000:.1f} cm3 "
          f"(~{total * 1.24e-3:.0f} g solid PLA; slice for the real number)")
    print(f"  notch legend: " + ', '.join(
        f"{i + 1}={c:.2f}" for i, c in enumerate(clears)))

    if FAILS:
        print(f"\nFAILED: {', '.join(FAILS)}")
        return 1
    print("\nall coupon gates pass")
    return 0


if __name__ == '__main__':
    sys.exit(main())
