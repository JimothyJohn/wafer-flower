#!/usr/bin/env python3
"""Parametric generator for NICK'S architecture (stl/mine/, 2026-08-13).

Nick built his own segment + pinion in OnShape and dropped the exports in
stl/mine/ ("I'm not using what you've made — learn from what I'm doing and
either derive from it or reverse engineer it"). This script is that
reverse-engineering, split per his rule:

  ENGINEERED EXACTLY (drive-critical, fully measured from the STLs):
  - ring band Ri 320 -> Ro 350, inner slab [320,340] x z 0..9
  - FACE teeth on the outer annulus [340,350]: 80 slots/segment (720
    full circle), tip plane z=6, root z=3.84 = 6 - 2.25m with
    m = 2*345/720 = 0.95833 — Nick's OnShape build follows the FS
    "Arc Segment" math exactly (module from band middle, joints
    mid-slot, pinion axis z = tipplane - m + rp = 10.79, all verified
    against the mesh to ~0.01 mm)
  - 12T spur pinion, face 6 (x 342..348), plain Ø3.0 THROUGH bore —
    no D-flat in Nick's part (glued retention; supersedes the repo's
    3.2/0.5 D-bore rule for this architecture)
  - lap-tab joint: tab r 324.4..334.7, z 3..9, protruding 1.06 deg past
    the -20 deg face; clearance pocket in the +20 deg face

  COARSE (Nick's sculptural tower — his mesh in stl/mine/ stays the
  canonical part; this is the parametric approximation for previews):
  - tower arc +/-7.5 deg: twin walls [320,324.4] + [335.6,340] from the
    shoulder to a cap, central arch opening at y=0 closing at z=20.5,
    cap slab from z=33 trimmed by the LAND PLANE z = 38.8 + y*tan(3 deg)
    (the wafer tilt lives in the tower top — theta = 3 deg measured)
  - shoulder: base arc tapering 20 -> 7.5 deg over z 9..14 (stepped)
  - the interior X-brace lattice and oval wall windows are NOT
    reproduced — volume vs Nick's solid is reported, not gated

Assumptions clocked for verification: pressure angle 25 deg and backlash
0.15 (the FS defaults — flank-slope fit is consistent but not exact-
measured). Emits stl/mine_param/. Gates (exit nonzero): watertight single
component, teeth % N == 0, pinion mesh sweep <= 0.05 mm3, mated tab/
pocket pair interference == 0. The comparison vs stl/mine/ meshes
(volume, bbox, IoU when the STL welds into a manifold) is REPORTED.
"""
from __future__ import annotations
import math, os, struct, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from segment_stl import (HAVE_MANIFOLD, Manifold, arc, face_pt, prism,
                         signed_area, union_all, write_stl, report,
                         face_slot_cutter, face_teeth_flange, pinion_profile)

try:
    import numpy as np
except ImportError:
    np = None


# Measured from stl/mine/ (2026-08-13). Every entry is a CLI flag.
PARAMS = dict(
    N        = 9,
    Ri       = 320.0,   # band bore
    Ro       = 350.0,   # band OD = tooth annulus outer edge
    gri      = 340.0,   # tooth annulus inner edge (slab steps down here)
    base_h   = 9.0,     # inner slab height [Ri, gri]
    gear_F   = 6.0,     # tooth tip plane (annulus height)
    tps      = 80,      # slots per segment -> 720 full circle
    gear_pa  = 25.0,    # ASSUMED (FS default) — flank fit consistent
    gear_bl  = 0.15,    # ASSUMED (FS default) — pinion-side thinning
    tilt     = 3.0,     # wafer tilt, MEASURED off the tower top land
    land_c   = 38.8,    # land plane z at y=0 (plane rises with +y)
    tower_a  = 7.5,     # tower half-arc, deg
    shoulder = 14.0,    # arc taper 20 -> tower_a finishes here
    wall_t   = 4.4,     # tower wall thickness (each of the twin walls)
    arch_z   = 20.5,    # central arch closes here
    arch_w   = 2.4,     # arch half-width at y=0
    cap_z    = 33.0,    # cap slab starts (underside ~34.2 measured)
    tab_r0   = 324.4,   # lap tab radial extent
    tab_r1   = 334.7,
    tab_z0   = 3.0,
    tab_z1   = 9.0,
    tab_arc  = 1.06,    # deg past the -20 joint face
    tab_clr  = 0.2,     # pocket clearance, all round
    pin_T    = 12,      # -> 60:1 (15 rpm N20 -> 0.25 rpm ring)
    pin_face = 6.0,
    pin_bore = 3.0,     # PLAIN through bore — Nick's part has NO D-flat
    facets   = 512,
)


class MCfg:
    """Duck-typed config exposing exactly what the reused segment_stl
    face-gear machinery reads (gear_m, gear_F, gear_pa, gear_bl, half,
    sector, tps, teeth, gf_ri, gf_ro, pin_T, pin_face)."""
    def __init__(self, **kw):
        p = dict(PARAMS); p.update(kw); self.p = p
        for k, v in p.items():
            setattr(self, k, v)
        self.sector = 2 * math.pi / self.N
        self.half   = self.sector / 2
        # conjugacy reference is the annulus middle (340+350)/2 — the
        # measured module. The BUILT flange starts 1 mm further out
        # (gf_ri) leaving a solid rim ring, and the slab overlaps 0.5 mm
        # into it: slot cutters overshoot into what is void at cut time
        # and the slab refills it, so slots end open-topped against the
        # slab wall instead of tunnelling under the taller slab rim
        # (the tunnels read as genus 161).
        self.g_ref  = (self.gri + self.Ro) / 2
        self.gf_ri  = self.gri + 1.0
        self.gf_ro  = self.Ro
        self.slab_ro = self.gri + 1.5
        self.teeth  = self.tps * self.N
        self.gear_m = 2 * self.g_ref / self.teeth      # 0.95833 at defaults
        self.rp     = self.pin_T * self.gear_m / 2
        self.zax    = self.gear_F - self.gear_m + self.rp   # 10.79
        self.x0     = self.g_ref - self.pin_face / 2        # 342
        self.th     = math.radians(self.tilt)
        self.ta     = math.radians(self.tower_a)


def garc(cf, rho, a0, a1):
    """Arc sampled on a GLOBAL angular grid (half/160 steps), endpoints
    exact. Stacked prisms sharing a cylinder wall then share their vertex
    columns, so the float32 STL weld closes the seams (free-running arc()
    puts T-vertices on the shared surface -> open edges)."""
    base = cf.half / 160.0
    lo, hi = (a0, a1) if a0 <= a1 else (a1, a0)
    ks = range(int(math.floor(lo / base)) + 1, int(math.ceil(hi / base)))
    angs = [lo] + [k * base for k in ks] + [hi]
    if a0 > a1:
        angs = angs[::-1]
    return [(rho * math.cos(t), rho * math.sin(t)) for t in angs]


def sector_prism(cf, r0, r1, z0, z1, a0=None, a1=None):
    a0 = -cf.half + 1e-5 if a0 is None else a0
    a1 = cf.half - 1e-5 if a1 is None else a1
    poly = garc(cf, r1, a0, a1) + garc(cf, r0, a1, a0)
    return prism(poly, z0, z1 - z0)


def tab_solid(cf, grow=0.0):
    """The lap tab past the -half joint face (grow>0 = pocket cutter)."""
    g = grow
    a1 = -cf.half + 0.3 / cf.g_ref            # rooted into the body
    a0 = -cf.half - math.radians(cf.tab_arc) - g / cf.g_ref
    return sector_prism(cf, cf.tab_r0 - g, cf.tab_r1 + g,
                        cf.tab_z0 - g, cf.tab_z1 + g, a0, a1)


def land_trim(cf, solid):
    """Keep z <= land_c + y*tan(tilt)."""
    t = math.tan(cf.th)
    return solid.trim_by_plane([0.0, t, -1.0], -cf.land_c)


def build_segment(cf):
    # exact: toothed outer annulus (reused FS-port machinery) + inner
    # slab overlapping 0.5 into the flange (see MCfg rim note)
    seg = face_teeth_flange(cf, 0.0)
    seg = seg + sector_prism(cf, cf.Ri, cf.slab_ro, 0.0, cf.base_h)
    # coarse: shoulder taper 20 -> tower_a over base_h..shoulder (4 steps)
    ns = 4
    for i in range(ns):
        f0, f1 = i / ns, (i + 1) / ns
        aa = cf.half + (cf.ta - cf.half) * f0   # arc at the slab bottom
        z0 = cf.base_h + (cf.shoulder - cf.base_h) * f0
        z1 = cf.base_h + (cf.shoulder - cf.base_h) * f1
        seg = seg + sector_prism(cf, cf.Ri, cf.gri, z0, z1, -aa + 1e-5, aa - 1e-5)
    # coarse tower: twin walls + cap, all trimmed by the tilted land plane
    top = cf.land_c + cf.gri * math.sin(cf.ta) * math.tan(cf.th) + 1.0
    walls = (sector_prism(cf, cf.Ri, cf.Ri + cf.wall_t, cf.shoulder, top,
                          -cf.ta, cf.ta)
             + sector_prism(cf, cf.gri - cf.wall_t, cf.gri, cf.shoulder, top,
                            -cf.ta, cf.ta))
    # central arch: box + half-round top, cut through both walls
    aw, az = cf.arch_w, cf.arch_z
    arch = (Manifold.cube([cf.gri - cf.Ri + 8.0, 2 * aw, az - aw - cf.shoulder + 2.0])
            .translate([cf.Ri - 4.0, -aw, cf.shoulder - 2.0]))
    arch = arch + (Manifold.cylinder(cf.gri - cf.Ri + 8.0, aw, aw, 48)
                   .rotate([0.0, 90.0, 0.0])
                   .translate([cf.Ri - 4.0, 0.0, az - aw]))
    walls = walls - arch
    cap = sector_prism(cf, cf.Ri, cf.gri, cf.cap_z, top, -cf.ta, cf.ta)
    seg = seg + land_trim(cf, walls + cap)
    # joint: tab past -half, clearance pocket in the +half face
    seg = seg + tab_solid(cf)
    seg = seg - tab_solid(cf, grow=cf.tab_clr).rotate(
        [0.0, 0.0, math.degrees(cf.sector)])
    parts = [c for c in seg.decompose() if c.volume() > 0.01]
    return sum(parts[1:], parts[0]) if len(parts) > 1 else parts[0]


def build_pinion(cf):
    pts, g = pinion_profile(cf, cf.pin_T)
    if signed_area(pts) < 0:
        pts = pts[::-1]
    p = prism(pts, 0.0, cf.pin_face)
    p = p - Manifold.cylinder(cf.pin_face + 2.0, cf.pin_bore / 2,
                              cf.pin_bore / 2, 64).translate([0, 0, -1.0])
    return p, g


def pinion_at(cf, pin, d):
    """Mesh frame: spin ratio*d about own axis (tps even -> phase 0, the
    ring presents a slot at the contact meridian), local +z onto +x."""
    ratio = cf.teeth / cf.pin_T
    return (pin.rotate([0.0, 0.0, math.degrees(d * ratio)])
               .rotate([0.0, 90.0, 0.0])
               .translate([cf.x0, 0.0, cf.zax]))


def check_mesh(cf, steps=24):
    ring = face_teeth_flange(cf, 0.0)
    pin, _ = build_pinion(cf)
    worst = 0.0
    for i in range(steps):
        d = (2 * math.pi / cf.teeth) * i / steps
        worst = max(worst, (ring.rotate([0, 0, math.degrees(d)])
                            ^ pinion_at(cf, pin, d)).volume())
    return worst


def read_stl_manifold(path):
    """Binary STL -> welded Manifold (None if numpy missing or not manifold)."""
    if np is None:
        return None, None
    with open(path, 'rb') as f:
        data = f.read()
    n = struct.unpack('<I', data[80:84])[0]
    raw = np.frombuffer(data[84:84 + n * 50], dtype=np.uint8).reshape(n, 50)
    tris = raw[:, 12:48].copy().view('<f4').reshape(n * 3, 3)
    verts, inv = np.unique(np.round(tris, 4), axis=0, return_inverse=True)
    faces = inv.reshape(n, 3).astype(np.uint32)
    vol = float(np.einsum('ij,ij->i', tris[0::3],
                          np.cross(tris[1::3], tris[2::3])).sum() / 6.0)
    try:
        from manifold3d import Mesh
        man = Manifold(Mesh(vert_properties=verts.astype(np.float32),
                            tri_verts=faces))
        if man.volume() <= 0:
            man = None
    except Exception:
        man = None
    return man, vol


def main():
    if not HAVE_MANIFOLD:
        sys.exit("needs manifold3d:  pip install manifold3d")
    ap = argparse.ArgumentParser(description="Nick-architecture generator")
    ap.add_argument('-o', '--out', default='stl/mine_param')
    for k, v in PARAMS.items():
        ap.add_argument(f'--{k}', type=type(v), default=None)
    a = ap.parse_args()
    cf = MCfg(**{k: getattr(a, k) for k in PARAMS if getattr(a, k) is not None})
    os.makedirs(a.out, exist_ok=True)

    assert cf.teeth % cf.N == 0, "tooth count must divide by N"
    print(f"Nick architecture  ·  N={cf.N}  band {cf.Ri:.0f}-{cf.Ro:.0f}  "
          f"teeth {cf.tps}x{cf.N}={cf.teeth} (m {cf.gear_m:.5f}, tips z={cf.gear_F}, "
          f"roots z={cf.gear_F - 2.25 * cf.gear_m:.2f})")
    print(f"  pinion  {cf.pin_T}T spur, face {cf.pin_face}, plain Ø{cf.pin_bore} "
          f"bore, axis z={cf.zax:.2f} at x={cf.x0 + cf.pin_face / 2:.0f} — "
          f"ratio {cf.teeth / cf.pin_T:.0f}:1")
    print(f"  land    z = {cf.land_c} + y*tan({cf.tilt}°)  (tilt lives in the "
          f"tower top)\n")

    seg = build_segment(cf)
    bodies = write_stl(seg, os.path.join(a.out, 'segment.stl'))
    report('segment.stl', seg, bodies, 'parametric (tower COARSE)')
    pin, g = build_pinion(cf)
    bodies = write_stl(pin, os.path.join(a.out, 'pinion.stl'))
    report('pinion.stl', pin, bodies,
           f"{g['T']}T, tip Ø{2 * g['ra']:.2f} vs measured 13.42")

    fails = []
    if len([c for c in seg.decompose() if c.volume() > 0.01]) != 1:
        fails.append("segment not a single component")
    worst = check_mesh(cf)
    print(f"\n  gate    mesh sweep worst overlap {worst:.5f} mm3")
    if worst > 0.05:
        fails.append(f"mesh sweep {worst:.3f} mm3 > 0.05")
    pair = (seg ^ seg.rotate([0, 0, math.degrees(cf.sector)])).volume()
    print(f"  gate    mated tab/pocket pair interference {pair:.5f} mm3")
    if pair > 0.001:
        fails.append(f"tab/pocket pair interference {pair:.3f} mm3")

    # ---- comparison vs Nick's canonical meshes (REPORTED, not gated) ----
    for mine, ours in (('stl/mine/Segment - segment.stl', seg),
                       ('stl/mine/Segment - pinion.stl',
                        pinion_at(cf, pin, 0.0))):
        if not os.path.exists(mine):
            print(f"  compare {mine}: MISSING"); continue
        man, vol = read_stl_manifold(mine)
        dv = ours.volume()
        line = (f"  compare {os.path.basename(mine):28} vol {vol / 1000:7.2f} "
                f"vs param {dv / 1000:7.2f} cm3 ({(dv - vol) / vol * 100:+.1f}%)")
        if man is not None:
            inter = (man ^ ours).volume()
            union = vol + dv - inter
            line += f"  IoU {inter / union:.3f}"
        print(line)

    if fails:
        print("\nFAIL:", "; ".join(fails)); return 1
    print("\nALL GATES PASS")
    return 0


if __name__ == '__main__':
    sys.exit(main())
