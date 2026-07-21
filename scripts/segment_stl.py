#!/usr/bin/env python3
"""
Wafer Halo — parametric solid model for the Rev B frame segment.

Builds the segment with CSG and exports watertight binary STLs.

    pip install manifold3d
    python3 scripts/segment_stl.py                 # -> stl/
    python3 scripts/segment_stl.py --theta 5 --Ri 270
    python3 scripts/segment_stl.py --help

Construction, in the order the solid is actually built:

  1. band          40 deg annular sector, extruded tall from the flat bottom
  2. land cut      trimmed by the own wafer's plane, offset down by t/2 + bondline
  3. slab          bottom tmin mm: band + inward gear teeth + male dovetail
  4. clearance cut a disc-shaped solid standing on the NEIGHBOUR's wafer plane is
                   subtracted. It is a disc, not a half-space, because the
                   neighbour's wafer is finite -- a half-space would wrongly eat
                   material 300 mm away from it.
  5. socket        female dovetail, blind from the bottom face
  6. bore          the jig screw hole, straight through

Everything traces to docs/index.html (OP 010, OP 015) and docs/onshape-variables.html.
"""
from __future__ import annotations
import math, struct, argparse, os, sys

try:
    from manifold3d import Manifold, CrossSection
    HAVE_MANIFOLD = True
except ImportError:                       # profiles/Cfg still import fine without it,
    Manifold = CrossSection = None        # which is how segment_step.py reuses them
    HAVE_MANIFOLD = False

# ----------------------------------------------------------------------------
# PARAMETERS — edit, rerun. Or override any of them on the command line.
# ----------------------------------------------------------------------------
PARAMS = dict(
    N        = 9,       # segment count
    wafer_D  = 300.0,   # wafer diameter
    wafer_T  = 0.775,   # wafer thickness
    theta    = 5.0,     # tilt about each wafer's radial axis, degrees
    R        = 350.0,   # pitch radius
    Ri       = 255.0,   # band inner radius (255 -> the clean 252-tooth gear)
    bw       = 30.0,    # band width  (30 mm cap)
    tmin     = 10.0,    # base thickness = dovetail height = gear flange thickness
    bond     = 1.1,     # bondline
    clr      = 3.0,     # neighbour clearance
    gear_m   = 2.0,     # gear module
    gear_pa  = 20.0,    # pressure angle, degrees
    gear_bl  = 0.4,     # tooth thinning for printed backlash
    hole_D   = 5.0,     # jig keyhole bore, RADIAL from the outer face
    hole_dep = 30.5,    # bw + 0.5: THROUGH the band, so the cure-jig rod can
                        # reach the inboard fence (was 15, blind, pre-jig)
    pocket_d = 1.0,     # adhesive pocket depth in the land
    pocket_m = 4.0,     # pocket inset from the band edges
    dt_neck  = 12.0,    # dovetail neck width
    dt_tip   = 16.0,    # dovetail tip width
    dt_depth = 8.0,     # dovetail depth
    dt_clear = 0.25,    # socket clearance per side
    clr_edge = 2.0,     # extra radius on the clearance disc, past the wafer rim
    facets   = 512,     # circular resolution for the big cuts
)


class Cfg:
    def __init__(self, **kw):
        p = dict(PARAMS); p.update(kw); self.p = p
        for k, v in p.items(): setattr(self, k, v)
        self.r       = self.wafer_D / 2.0
        self.sector  = 2 * math.pi / self.N
        self.half    = self.sector / 2.0
        self.th      = math.radians(self.theta)
        self.Ro      = self.Ri + self.bw
        self.yMax    = self.Ro * math.sin(self.half)
        self.rise    = self.yMax * math.tan(self.th)
        self.landOff = self.wafer_T / 2.0 + self.bond
        self.clrOff  = self.wafer_T / 2.0 + self.clr
        # NOTE: landOff, not bond. The land sits at rise + wafer_T/2 + bond; using
        # bond alone leaves the slab poking wafer_T/2 above the land at the
        # trailing outer corner, i.e. pressing straight into the bondline.
        self.z_bot   = -(self.rise + self.landOff + self.tmin)
        self.z1      = self.z_bot + self.tmin
        self.rho_c   = self.Ri + self.bw / 2.0
        self.hole_r  = self.hole_D / 2.0
        # gear: tooth count must divide by N or the pitch breaks at every joint
        self.tps     = max(6, round(2 * (self.Ri - 5.0) / self.gear_m / self.N))
        self.teeth   = self.tps * self.N
        self.g_pitch = self.teeth * self.gear_m / 2.0
        self.g_tip   = self.g_pitch - self.gear_m
        self.g_root  = self.g_pitch + 1.25 * self.gear_m
        self.g_base  = self.g_pitch * math.cos(math.radians(self.gear_pa))
        self.tall    = 4 * self.r

    def wafer_frame(self, k=0):
        """Rotation (3x3, row-major) and centre of wafer k's plane."""
        a = k * self.sector
        ca, sa, ct, st = math.cos(a), math.sin(a), math.cos(self.th), math.sin(self.th)
        # Rz(a) @ Rx(theta)
        M = [[ca, -sa * ct,  sa * st],
             [sa,  ca * ct, -ca * st],
             [0.0, st,       ct]]
        c = (self.R * ca, self.R * sa, 0.0)
        n = (M[0][2], M[1][2], M[2][2])
        return M, c, n


def keyhole_z(cf):
    """Keyhole axis height, shared with cure_jig_stl.py.

    z1 + 2.6 rather than the old mid-slab z_bot + tmin/2: the cure-jig rod
    carries a wing nut / captive nut at each end, and at mid-slab the axis sat
    only tmin/2 = 5 mm above the bench -- under a #10 nut's 5.5 mm corner
    swing, so nothing could rotate on the rod. At z1 + 2.6 the axis is
    tmin + 2.6 above the bench (12.6 at Rev B.2), the Ø5 bore bottom stays
    0.1 mm above the gear flange (a 4.83 rod clears the root land by 0.19),
    and the bore roof keeps a 2.4 mm web under the adhesive pocket floor.
    Needs rise > zoff + hole_r + ~1.5, i.e. theta >= ~4 deg at Rev B.2
    geometry, or the bore breaks out of the band top at y=0.
    """
    return cf.z1 + 2.6


# ----------------------------------------------------------------------------
# 2D profiles
# ----------------------------------------------------------------------------
def arc(rho, a0, a1, n):
    return [(rho * math.cos(a0 + (a1 - a0) * i / n),
             rho * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def face_pt(ang, rho, s):
    """Point on a radial end face: rho along it, s perpendicular (toward +angle)."""
    return (rho * math.cos(ang) - s * math.sin(ang),
            rho * math.sin(ang) + s * math.cos(ang))


def tooth_profile(cf):
    """Internal involute teeth, phased so each joint lands mid-space."""
    inv = lambda al: math.tan(al) - al
    pa = math.radians(cf.gear_pa)
    psi_p = ((math.pi * cf.gear_m / 2.0 - cf.gear_bl) / 2.0) / cf.g_pitch
    def half_angle(rad):                      # an internal tooth widens with radius
        al = math.acos(max(-1.0, min(1.0, cf.g_base / rad)))
        return psi_p + (inv(al) - inv(pa))
    radii = [cf.g_tip + (cf.g_root - cf.g_tip) * i / 8.0 for i in range(9)]
    flank = [(rad, half_angle(rad)) for rad in radii]
    pitch_ang = cf.sector / cf.tps
    out = []
    for k in range(cf.tps):
        ctr = -cf.half + (k + 0.5) * pitch_ang
        for rad, ha in reversed(flank): out.append((rad, ctr - ha))
        for rad, ha in flank:           out.append((rad, ctr + ha))
    return out


def band_poly(cf, na=160):
    p  = [face_pt(-cf.half, cf.Ri, 0.0)]
    p += arc(cf.Ro, -cf.half, cf.half, na)
    p += [face_pt(cf.half, cf.Ri, 0.0)]
    p += arc(cf.Ri, cf.half, -cf.half, na)[1:-1]
    return p


def slab_poly(cf, na=160):
    """Band + inward gear teeth + male dovetail. Socket is subtracted later."""
    dtn, dtt, dtd = cf.dt_neck / 2, cf.dt_tip / 2, cf.dt_depth
    p  = [face_pt(-cf.half, cf.g_root, 0.0), face_pt(-cf.half, cf.Ro, 0.0)]
    p += arc(cf.Ro, -cf.half, cf.half, na)[1:]
    p += [face_pt(cf.half, cf.rho_c + dtn, 0.0),
          face_pt(cf.half, cf.rho_c + dtt, dtd),
          face_pt(cf.half, cf.rho_c - dtt, dtd),
          face_pt(cf.half, cf.rho_c - dtn, 0.0),
          face_pt(cf.half, cf.g_root, 0.0)]
    p += [(rad * math.cos(a), rad * math.sin(a)) for rad, a in reversed(tooth_profile(cf))]
    return p


def pocket_poly(cf, na=120):
    """Adhesive pocket: the band, inset all round.

    It meters the adhesive and gives a positive bondline stop. It does NOT
    locate the wafer -- the whole band lies under the wafer's interior, with the
    rim 55 mm inboard and 215 mm outboard, so no pocket edge here can ever touch
    it. Centring stays the jig's job.
    """
    m = cf.pocket_m
    # Angular inset must clear the dovetail zones. At the trailing end the band
    # above the socket ceiling is under 0.5 mm thick, so a 1 mm pocket punches
    # straight into the socket and turns the part into a tunnel (genus 1).
    # Keeping tape near the land centroid is what OP 015 wants anyway.
    da = (cf.dt_depth + cf.dt_clear + 5.0) / cf.rho_c
    ri, ro = cf.Ri + m, cf.Ro - m
    a0, a1 = -cf.half + da, cf.half - da
    return arc(ro, a0, a1, na) + arc(ri, a1, a0, na)


def socket_poly(cf):
    dtn, dtt, dtd, c = cf.dt_neck / 2, cf.dt_tip / 2, cf.dt_depth, cf.dt_clear
    return [face_pt(-cf.half, cf.rho_c - dtn - c, -0.001),
            face_pt(-cf.half, cf.rho_c - dtt - c, dtd + c),
            face_pt(-cf.half, cf.rho_c + dtt + c, dtd + c),
            face_pt(-cf.half, cf.rho_c + dtn + c, -0.001)]


# ----------------------------------------------------------------------------
# Solids
# ----------------------------------------------------------------------------
def signed_area(poly):
    s = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % len(poly)]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def prism(poly, z0, h):
    """Extrude a profile. Winding is forced CCW — a CW profile extrudes inverted,
    and subtracting an inverted solid silently deletes the whole model."""
    if signed_area(poly) < 0:
        poly = poly[::-1]
    return Manifold.extrude(CrossSection([poly]), h).translate([0.0, 0.0, z0])


def wafer_cut(cf, k, offset, height):
    """Disc-shaped solid standing `offset` from wafer k's mid-plane, extending +n.

    A disc and not a half-space: the neighbour's wafer is 300 mm across, so a
    half-space would remove material hundreds of mm outside its footprint.

    The disc is oversized by clr_edge. At exactly the wafer radius the cut wall
    lands tangent to the wafer's rim, leaving zero lateral clearance -- and T6
    only holds centring to 0.5 mm, with another 0.2 mm of diameter tolerance
    on the wafer itself.
    """
    M, c, n = cf.wafer_frame(k)
    rad = cf.r + cf.clr_edge
    cyl = Manifold.cylinder(height, rad, rad, cf.facets)
    t = [c[i] + offset * n[i] for i in range(3)]
    return cyl.transform([[M[0][0], M[0][1], M[0][2], t[0]],
                          [M[1][0], M[1][1], M[1][2], t[1]],
                          [M[2][0], M[2][1], M[2][2], t[2]]])


def build_segment(cf):
    tn = math.tan(cf.th)
    # 1-2. band, trimmed by its own wafer's land plane:  z <= y*tan(th) - landOff
    seg = prism(band_poly(cf), cf.z_bot, cf.tall)
    seg = seg.trim_by_plane([0.0, tn, -1.0], cf.landOff)
    # 3. bottom slab carrying the gear teeth and the male dovetail
    seg = seg + prism(slab_poly(cf), cf.z_bot, cf.tmin)
    # 4. neighbour clearance cut
    seg = seg - wafer_cut(cf, 1, -cf.clrOff, cf.tall)
    # 5. female socket, blind from the bottom face
    seg = seg - prism(socket_poly(cf), cf.z_bot - 0.5, cf.tmin + 0.5)
    # 6. adhesive pocket, recessed into the land face
    if cf.pocket_d > 0:
        pk = prism(pocket_poly(cf), cf.z_bot, cf.tall)
        pk = pk.trim_by_plane([0.0, -tn, 1.0], -(cf.landOff + cf.pocket_d))
        seg = seg - pk
    # 7. jig keyhole: RADIAL, THROUGH the band, in from the outer arc face.
    #    Through, not blind: the cure jig (scripts/cure_jig_stl.py) passes a
    #    threaded rod to a fence on the inboard side. The land face is still
    #    unbroken and the bore roof keeps a ~2.4 mm web under the adhesive
    #    pocket floor. A through hole makes the body genus 1 -- that is
    #    expected here, unlike the pocket-into-socket tunnel bug.
    if cf.hole_D > 0:
        zc = keyhole_z(cf)
        L = cf.hole_dep + 2.0
        key = (Manifold.cylinder(L, cf.hole_r, cf.hole_r, 64)
               .rotate([0.0, 90.0, 0.0])          # +z -> +x, i.e. radial at a=0
               .translate([cf.Ro - cf.hole_dep, 0.0, zc]))
        seg = seg - key
    return seg


def build_wafer(cf, k=0):
    M, c, n = cf.wafer_frame(k)
    cyl = Manifold.cylinder(cf.wafer_T, cf.r, cf.r, 256)
    off = -cf.wafer_T / 2.0
    t = [c[i] + off * n[i] for i in range(3)]
    return cyl.transform([[M[0][0], M[0][1], M[0][2], t[0]],
                          [M[1][0], M[1][1], M[1][2], t[1]],
                          [M[2][0], M[2][1], M[2][2], t[2]]])


def rotated(solid, k, cf):
    return solid.rotate([0.0, 0.0, math.degrees(k * cf.sector)])


def build_ring(cf, n=None, wafers=False):
    """Returns a LIST of solids, one per body.

    Kept separate rather than unioned: adjacent segments meet on coincident
    radial faces, and welding across that shared face makes non-manifold edges
    where four triangles meet. As separate bodies each one stays watertight,
    which is also what a slicer wants for a multi-part plate.
    """
    n = n or cf.N
    seg = build_segment(cf)
    parts = [rotated(seg, k, cf) for k in range(n)]
    if wafers:
        parts += [build_wafer(cf, k) for k in range(n)]
    return parts


# ----------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------
def to_arrays(solid):
    """Mesh, snapped to the float32 grid an STL actually stores, then welded.

    manifold3d emits an exact float64 manifold, but writing float32 re-splits
    vertices that quantise to the same point and leaves collapsed slivers behind,
    which is enough to make a slicer call the file non-manifold. Welding at the
    storage precision *before* writing is what keeps the exported file watertight.
    """
    m = solid.to_mesh()
    V = [tuple(struct.unpack('<3f', struct.pack('<3f', *v[:3]))) for v in m.vert_properties]
    index, uniq, remap = {}, [], []
    for v in V:
        if v not in index:
            index[v] = len(uniq); uniq.append(v)
        remap.append(index[v])
    tris = []
    for i0, i1, i2 in m.tri_verts:
        a, b, c = remap[i0], remap[i1], remap[i2]
        if a != b and b != c and c != a:
            tris.append((a, b, c))
    return uniq, tris


def check_watertight(verts, tris):
    """Each directed edge must appear exactly once, and its reverse must exist."""
    edges = {}
    for a, b, c in tris:
        for u, v in ((a, b), (b, c), (c, a)):
            edges[(u, v)] = edges.get((u, v), 0) + 1
    dup = sum(1 for n in edges.values() if n > 1)
    open_ = sum(1 for e in edges if (e[1], e[0]) not in edges)
    euler = len(verts) - len(edges) // 2 + len(tris)
    return dict(ok=(dup == 0 and open_ == 0), unmatched=open_, duplicated=dup,
                genus=(2 - euler) // 2 if (2 - euler) % 2 == 0 else None)


def write_stl(solids, path, name="wafer-halo"):
    """Write one or more bodies. Each is welded independently."""
    if not isinstance(solids, (list, tuple)):
        solids = [solids]
    bodies = [to_arrays(s) for s in solids]
    total = sum(len(T) for _, T in bodies)
    with open(path, 'wb') as f:
        f.write(struct.pack('<80sI', name.encode()[:80].ljust(80, b'\0'), total))
        for V, T in bodies:
            for i0, i1, i2 in T:
                a, b, c = V[i0], V[i1], V[i2]
                ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
                vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
                nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
                L = math.sqrt(nx*nx+ny*ny+nz*nz) or 1.0
                f.write(struct.pack('<12fH', nx/L, ny/L, nz/L, *a, *b, *c, 0))
    return bodies


def write_dxf(path, loops):
    """Minimal DXF with closed LWPOLYLINEs — OnShape imports these as sketches."""
    out = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1015",
           "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
    for i, pts in enumerate(loops):
        out += ["0", "LWPOLYLINE", "5", f"{100+i:X}", "100", "AcDbEntity", "8", "0",
                "100", "AcDbPolyline", "90", str(len(pts)), "70", "1"]
        for x, y in pts:
            out += ["10", f"{x:.6f}", "20", f"{y:.6f}"]
    out += ["0", "ENDSEC", "0", "EOF"]
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")
    return sum(len(p) for p in loops)


def report(name, solids, bodies, note=""):
    if not isinstance(solids, (list, tuple)):
        solids = [solids]
    lo = [min(s.bounding_box()[i] for s in solids) for i in range(3)]
    hi = [max(s.bounding_box()[i + 3] for s in solids) for i in range(3)]
    bbox = [round(hi[i] - lo[i], 1) for i in range(3)]
    vol = sum(s.volume() for s in solids)
    checks = [check_watertight(V, T) for V, T in bodies]
    bad = [c for c in checks if not c['ok']]
    genus = checks[0]['genus']
    flag = (f"{len(bodies)} body watertight, genus {genus}" if not bad
            else f"OPEN in {len(bad)}/{len(bodies)} bodies")
    tris = sum(len(T) for _, T in bodies)
    print(f"  {name:20} {tris:8,d} tris {vol/1000:8.1f} cm3  "
          f"bbox {str(bbox):23} {flag:30} {note}")
    return vol


def main():
    if not HAVE_MANIFOLD:
        sys.exit("needs manifold3d for STL output:  pip install manifold3d")
    ap = argparse.ArgumentParser(description="Wafer Halo Rev B — STL generator")
    ap.add_argument('-o', '--out', default='stl')
    for k, v in PARAMS.items():
        ap.add_argument(f'--{k}', type=type(v), default=None)
    a = ap.parse_args()
    cf = Cfg(**{k: getattr(a, k) for k in PARAMS if getattr(a, k) is not None})
    os.makedirs(a.out, exist_ok=True)

    print(f"Wafer Halo Rev B  ·  N={cf.N}  Ø{cf.wafer_D:.0f}×{cf.wafer_T}  θ={cf.theta}°  "
          f"band {cf.Ri:.0f}–{cf.Ro:.0f}")
    print(f"  gear    {cf.tps}T/seg × {cf.N} = {cf.teeth}T  module {cf.gear_m}  "
          f"pitch Ø{2*cf.g_pitch:.0f}  tip r{cf.g_tip:.1f}  root r{cf.g_root:.1f}")
    print(f"  z       flat bottom {cf.z_bot:.2f}   slab top {cf.z1:.2f}")
    print(f"  keyhole Ø{cf.hole_D} radial at a=0, z={keyhole_z(cf):.2f}, "
          f"{'THROUGH' if cf.hole_dep >= cf.bw else 'blind'} "
          f"({cf.hole_dep:.1f} deep from the outer face)\n")

    seg = build_segment(cf)
    bodies = write_stl(seg, os.path.join(a.out, 'segment.stl'))
    v = report('segment.stl', seg, bodies, 'one segment')
    print(f"{'':24}mass  45% infill {v*1.27e-3*0.45:6.1f} g   solid {v*1.27e-3:6.1f} g"
          f"   ×{cf.N} = {v*1.27e-3*0.45*cf.N/1000:.2f} kg\n")

    for fname, kw, note in (('segment_pair.stl', dict(n=2), 'gate T1'),
                            ('halo_frame.stl',   dict(), f'all {cf.N} segments'),
                            ('halo_assembly.stl', dict(wafers=True), 'frame + wafers, view only')):
        s = build_ring(cf, **kw)
        bodies = write_stl(s, os.path.join(a.out, fname))
        report(fname, s, bodies, note)

    # ---- mating pinion ----
    pin, g = build_pinion(cf)
    bodies = write_stl(pin, os.path.join(a.out, 'pinion.stl'))
    report('pinion.stl', pin, bodies, f"{g['T']}T, meshes at {cf.teeth/g['T']:.0f}:1")
    mesh = check_mesh(cf)
    print(f"{'':24}centre distance {mesh['centre']:.0f} mm, worst overlap over a full "
          f"tooth pitch {mesh['worst_overlap']:.5f} mm3\n")

    # ---- DXF sketch profiles for OnShape ----
    dxf = os.path.join(a.out, 'dxf'); os.makedirs(dxf, exist_ok=True)
    profiles = [
        ('01_band.dxf',      [band_poly(cf)],                        'extrude tall, trim to the land plane'),
        ('02_slab.dxf',      [slab_poly(cf)],                        f'extrude {cf.tmin} mm up from the flat bottom'),
        ('03_socket.dxf',    [socket_poly(cf)],                      f'cut {cf.tmin} mm from the flat bottom'),
        ('04_pocket.dxf',    [pocket_poly(cf)],                      f'cut {cf.pocket_d} mm down from the land plane'),
        ('05_ring_teeth.dxf',[[(r*math.cos(t), r*math.sin(t)) for r, t in tooth_profile(cf)]],
                                                                     f'{cf.tps}T of the {cf.teeth}T internal ring'),
        ('06_pinion.dxf',    [pinion_profile(cf, cf.tps)[0]],        f'{cf.tps}T pinion, extrude {cf.tmin} mm'),
    ]
    print("  DXF sketch profiles for OnShape:")
    for fn, loops, note in profiles:
        n = write_dxf(os.path.join(dxf, fn), loops)
        print(f"    dxf/{fn:20} {n:5,d} pts   {note}")

    print(f"\nWrote to {os.path.abspath(a.out)}/")



# ----------------------------------------------------------------------------
# Mating pinion for the internal ring gear
# ----------------------------------------------------------------------------
def pinion_profile(cf, T, backlash=None):
    """External involute profile. Below the base circle the flank runs radial."""
    m, pa = cf.gear_m, math.radians(cf.gear_pa)
    bl = cf.gear_bl if backlash is None else backlash
    rp = T * m / 2.0
    rb = rp * math.cos(pa)
    ra = rp + m                      # tip
    rf = rp - 1.25 * m               # root
    inv = lambda al: math.tan(al) - al
    psi_p = ((math.pi * m / 2.0 - bl) / 2.0) / rp
    def half(rad):
        if rad <= rb:
            return psi_p + inv(pa)
        al = math.acos(max(-1.0, min(1.0, rb / rad)))
        return psi_p - (inv(al) - inv(pa))
    lo = max(rf, 1e-6)
    radii = [lo + (ra - lo) * i / 12.0 for i in range(13)]
    flank = [(rad, half(rad)) for rad in radii]
    pitch = 2 * math.pi / T
    pts = []
    for k in range(T):
        ctr = k * pitch
        for rad, ha in flank:            # root -> tip, trailing side
            pts.append((rad * math.cos(ctr - ha), rad * math.sin(ctr - ha)))
        for rad, ha in reversed(flank):  # tip -> root, leading side
            pts.append((rad * math.cos(ctr + ha), rad * math.sin(ctr + ha)))
    return pts, dict(rp=rp, rb=rb, ra=ra, rf=rf, T=T)


def build_pinion(cf, T=None, face=None, bore=5.0, flat=0.5):
    """Pinion that meshes with the internal ring. T = teeth/segment gives ratio N:1."""
    T = T or cf.tps
    face = face or cf.tmin
    pts, g = pinion_profile(cf, T)
    p = prism(pts, 0.0, face)
    if bore:
        p = p - Manifold.cylinder(face * 3, bore / 2, bore / 2, 64).translate([0, 0, -face])
        if flat:                          # D-flat for a set screw / D-shaft
            w = bore
            p = p - prism([(bore/2 - flat, -w), (bore/2 - flat, w), (w, w), (w, -w)],
                          -face, face * 3)
    return p, g


def check_mesh(cf, T=None, steps=24):
    """Roll the pinion through one tooth pitch against the ring and measure overlap.

    Conjugate action means zero interference at every phase, not just one.
    """
    T = T or cf.tps
    face = cf.tmin
    ring_teeth = [(rad * math.cos(a), rad * math.sin(a)) for rad, a in tooth_profile(cf)]
    # a closed annulus carrying this segment's teeth
    outer = arc(cf.Ri + 6.0, -cf.half, cf.half, 200)
    ring = prism(outer + ring_teeth[::-1], 0.0, face)
    pin, g = build_pinion(cf, T, face=face, bore=0.0, flat=0.0)
    centre = cf.g_pitch - g['rp']
    worst = 0.0
    for i in range(steps):
        d = (2 * math.pi / cf.teeth) * i / steps          # ring rotates by d
        # An internal pair CO-ROTATES: ring and pinion turn the same way, unlike
        # an external pinion. Getting this sign wrong reads as 245 mm3 of
        # interference from a profile that is actually conjugate.
        pr = d * cf.teeth / T
        r2 = ring.rotate([0, 0, math.degrees(d)])
        p2 = pin.rotate([0, 0, math.degrees(pr)]).translate([centre, 0, 0])
        worst = max(worst, (r2 - (r2 - p2)).volume())
    return dict(centre=centre, ratio=cf.teeth / T, worst_overlap=worst, **g)


if __name__ == '__main__':
    main()
