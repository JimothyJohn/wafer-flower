#!/usr/bin/env python3
"""
Wafer Halo — STEP (AP214) export of every assembly component + the full
halo-with-drive assembly as one file.

The manifold3d solids are polyhedra (planar faces only — cylinders and
involutes are already faceted at the model's own resolution), so the export
is an EXACT planar B-rep of the same geometry the STLs carry: coplanar
triangles are merged back into polygonal ADVANCED_FACEs (with holes as inner
FACE_BOUND loops), edges are shared between faces, and each body becomes a
MANIFOLD_SOLID_BREP. This is the classic planar-face STEP every importer
reads — NOT the tessellated/faceted flavors with patchy support, and NOT a
parametric model: for editable CAD the DXF + onshape-variables route remains
the one that stays editable (this export exists for viewing, archival, and
assembly examination — Nick asked for it 2026-07-22).

Outputs (stl/step/):
    segment.stp  wafer.stp  drive_plate.stp  drive_clamp.stp
    drive_pinion.stp  motor_dummy.stp
    halo_drive_assembly.stp   — 9 segments + 9 wafers + the whole drive
                                module, every body named, in scene coords

Verification: --verify round-trips every emitted file through gmsh's
OpenCASCADE STEP reader and compares solid count and per-solid volume
against the manifold source (0.1 %). Exits nonzero on any mismatch.

    pip install manifold3d          # to write
    pip install gmsh                # to --verify
    python3 scripts/step_export.py --verify
"""
from __future__ import annotations
import math, os, sys, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from segment_stl import (PARAMS, Cfg, build_segment, build_wafer, build_ring,
                         to_arrays, Manifold, HAVE_MANIFOLD)
from gearmotor_stl import (DRIVE, Drive, build_plate, build_clamp,
                           build_motor_dummy, build_drive_pinion)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO, 'stl', 'step')


# ----------------------------------------------------------------------------
# planar-face reconstruction: triangles -> polygonal faces with hole loops
# ----------------------------------------------------------------------------
def tri_plane(V, t):
    a, b, c = (V[i] for i in t)
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
    L = math.sqrt(sum(c*c for c in n))
    if L < 1e-6:
        # degenerate or near-collinear sliver (float32-snapped): its normal is
        # noise and OCC rejects the face. Drop it — the seam it leaves is a
        # T-structure that reconcile_edges heals exactly.
        return None
    n = [c / L for c in n]
    d = sum(n[i] * a[i] for i in range(3))
    return n, d


def merge_faces(V, T):
    """Group triangles into maximal coplanar CONNECTED patches, then trace
    each patch's boundary into an outer loop + hole loops.

    Connectivity matters, not just coplanarity: two disjoint patches can lie
    in one plane (e.g. the plate front face ring around the pocket vs. an
    island), and each must become its own STEP face.
    """
    # plane key per triangle, quantized; float32-snapped verts make this exact
    # enough that faces of one prism land on one key while distinct involute
    # facets stay distinct
    keys = []
    for t in T:
        p = tri_plane(V, t)
        keys.append(None if p is None else
                    (tuple(round(c, 6) for c in p[0]), round(p[1], 4)))
    groups = {}
    for i, k in enumerate(keys):
        if k is not None:
            groups.setdefault(k, []).append(i)

    faces = []           # (normal, [outer_loop, hole1, ...]) as vertex-index loops
    for key, tris in groups.items():
        normal = key[0]
        # split the coplanar group into edge-connected components
        owner = {}
        adj = {i: [] for i in tris}
        emap = {}
        for i in tris:
            a, b, c = T[i]
            for e in ((a, b), (b, c), (c, a)):
                ue = (min(e), max(e))
                if ue in emap:
                    j = emap[ue]
                    adj[i].append(j); adj[j].append(i)
                else:
                    emap[ue] = i
        comps, seen = [], set()
        for i in tris:
            if i in seen:
                continue
            comp, stack = [], [i]
            seen.add(i)
            while stack:
                x = stack.pop(); comp.append(x)
                for y in adj[x]:
                    if y not in seen:
                        seen.add(y); stack.append(y)
            comps.append(comp)

        for comp in comps:
            # boundary = directed edges appearing without their reverse
            dedges = set()
            for i in comp:
                a, b, c = T[i]
                for e in ((a, b), (b, c), (c, a)):
                    if (e[1], e[0]) in dedges:
                        dedges.discard((e[1], e[0]))
                    else:
                        dedges.add(e)
            nxt = {}
            for a, b in dedges:
                nxt.setdefault(a, []).append(b)
            # non-simple boundary (a vertex with two outgoing boundary edges):
            # the patch touches itself along a slit — e.g. the dovetail socket
            # cut is tangent to the segment's radial end face. Chaining such a
            # boundary yields degenerate zero-width loops that break the shell
            # in OCC, so fall back to plain triangle faces for this patch;
            # they stay topologically stitched through the shared edge map.
            if any(len(v) > 1 for v in nxt.values()):
                for i in comp:
                    faces.append((normal, [list(T[i])]))
                continue
            loops = []
            while nxt:
                a0 = next(iter(nxt))
                loop, a = [], a0
                while True:
                    loop.append(a)
                    b = nxt[a].pop()
                    if not nxt[a]:
                        del nxt[a]
                    a = b
                    if a == a0:
                        break
                loops.append(loop)
            if not loops:
                continue
            # outer loop = largest |area|; the rest are holes of it
            def area2(loop):
                ax = [0.0, 0.0, 0.0]
                for k in range(len(loop)):
                    p, q = V[loop[k]], V[loop[(k + 1) % len(loop)]]
                    ax[0] += p[1]*q[2] - p[2]*q[1]
                    ax[1] += p[2]*q[0] - p[0]*q[2]
                    ax[2] += p[0]*q[1] - p[1]*q[0]
                return sum(ax[i] * normal[i] for i in range(3)) / 2.0
            loops.sort(key=lambda l: -abs(area2(l)))
            faces.append((normal, loops))
    return faces


# ----------------------------------------------------------------------------
# STEP writer
# ----------------------------------------------------------------------------
class StepFile:
    def __init__(self):
        self.lines = []
        self.n = 0

    def add(self, txt):
        self.n += 1
        self.lines.append(f"#{self.n}={txt};")
        return self.n

    def write(self, path, name):
        hdr = ("ISO-10303-21;\nHEADER;\n"
               "FILE_DESCRIPTION(('Wafer Halo'),'2;1');\n"
               f"FILE_NAME('{name}','2026-07-22T00:00:00',('wafer-flower'),"
               "('scripts/step_export.py'),'','','');\n"
               "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\n"
               "ENDSEC;\nDATA;\n")
        with open(path, 'w') as f:
            f.write(hdr)
            f.write("\n".join(self.lines))
            f.write("\nENDSEC;\nEND-ISO-10303-21;\n")


def fnum(x):
    return f"{x:.6f}".rstrip('0').rstrip('.') or '0.'


def reconcile_edges(V, faces):
    """Heal T-vertices so every loop edge is shared by exactly two faces.

    The welded mesh is watertight, but it can carry a long edge that passes
    exactly through another face's vertex (e.g. where the slab top meets the
    band's inner corner on a segment end face): one face walks the long edge,
    the neighbours walk it as two shorter collinear edges. STEP shell closure
    needs a 1:1 edge match, so each UNMATCHED long edge is replaced by the
    chain of unmatched shorter edges that covers it. Only unmatched edges are
    touched — a blanket split-at-nearby-vertices pass corrupts micron-scale
    sliver faces instead (tried, failed).
    """
    from collections import Counter
    for _ in range(3):                       # nested T-structures, if any
        use = Counter()
        for _, loops in faces:
            for loop in loops:
                for k in range(len(loop)):
                    a, b = loop[k], loop[(k + 1) % len(loop)]
                    use[(min(a, b), max(a, b))] += 1
        open_e = [e for e, c in use.items() if c == 1]
        if not open_e:
            break
        open_set = set(open_e)

        def seg_len(e):
            pa, pb = V[e[0]], V[e[1]]
            return sum((pa[k] - pb[k]) ** 2 for k in range(3))

        healed = 0
        for e in sorted(open_e, key=seg_len, reverse=True):
            if e not in open_set:
                continue
            a, b = e
            pa, pb = V[a], V[b]
            d = [pb[k] - pa[k] for k in range(3)]
            L2 = sum(c * c for c in d) or 1.0

            def t_of(i):
                p = V[i]
                t = sum((p[k] - pa[k]) * d[k] for k in range(3)) / L2
                dist2 = sum((pa[k] + t * d[k] - p[k]) ** 2 for k in range(3))
                return t if dist2 < 1e-6 else None
            # unmatched edges lying fully on this segment, chained a -> b
            mids = {}
            for o in open_set:
                if o == e:
                    continue
                ta, tb = t_of(o[0]), t_of(o[1])
                if ta is None or tb is None:
                    continue
                if -1e-6 < min(ta, tb) and max(ta, tb) < 1 + 1e-6:
                    for t, i in ((ta, o[0]), (tb, o[1])):
                        if i not in (a, b):
                            mids[i] = t
            chain = [a] + [i for i, _ in sorted(mids.items(), key=lambda x: x[1])] + [b]
            links = [(min(u, v), max(u, v)) for u, v in zip(chain, chain[1:])]
            if len(chain) < 3 or not all(l in open_set for l in links):
                continue
            # substitute the long edge, in whichever loop walks it
            done = False
            for _, loops in faces:
                for loop in loops:
                    for k in range(len(loop)):
                        u, w = loop[k], loop[(k + 1) % len(loop)]
                        if (min(u, w), max(u, w)) == e:
                            ins = chain[1:-1] if u == a else chain[-2:0:-1]
                            loop[k+1:k+1] = ins
                            done = True
                            break
                    if done:
                        break
                if done:
                    break
            if done:
                healed += 1
                open_set.discard(e)
                for l in links:
                    open_set.discard(l)
        if not healed:
            break
    return faces


def weld_close(V, T, tol=5e-4):
    """Merge vertices closer than `tol` (CSG needle-triangle remnants sit
    sub-micron apart and leave unhealable seams once the needle is dropped).
    Smallest real feature spacing is ~0.05 mm, two orders above `tol`."""
    grid = {}
    rep = list(range(len(V)))
    t2 = tol * tol
    for i, v in enumerate(V):
        c = (int(v[0] // tol), int(v[1] // tol), int(v[2] // tol))
        hit = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((c[0]+dx, c[1]+dy, c[2]+dz), ()):
                        if sum((v[k] - V[j][k]) ** 2 for k in range(3)) < t2:
                            hit = j
                            break
                    if hit is not None:
                        break
                if hit is not None:
                    break
            if hit is not None:
                break
        if hit is not None:
            rep[i] = hit
        else:
            grid.setdefault(c, []).append(i)
    out = []
    for a, b, c in T:
        a, b, c = rep[a], rep[b], rep[c]
        if a != b and b != c and c != a:
            out.append((a, b, c))
    return out


def emit_brep(s, name, V, T):
    """One MANIFOLD_SOLID_BREP from a welded triangle mesh."""
    T = weld_close(V, T)
    faces = reconcile_edges(V, merge_faces(V, T))
    used = sorted({i for _, loops in faces for l in loops for i in l})
    pt, vx = {}, {}
    for i in used:
        p = s.add(f"CARTESIAN_POINT('',({fnum(V[i][0])},{fnum(V[i][1])},"
                  f"{fnum(V[i][2])}))")
        pt[i] = p
        vx[i] = s.add(f"VERTEX_POINT('',#{p})")
    ecurve = {}      # undirected edge -> EDGE_CURVE id (directed lo->hi)

    def edge_id(a, b):
        k = (min(a, b), max(a, b))
        if k not in ecurve:
            u, w = k
            d = [V[w][i] - V[u][i] for i in range(3)]
            L = math.sqrt(sum(c*c for c in d)) or 1.0
            dr = s.add(f"DIRECTION('',({fnum(d[0]/L)},{fnum(d[1]/L)},{fnum(d[2]/L)}))")
            vec = s.add(f"VECTOR('',#{dr},{fnum(L)})")
            ln = s.add(f"LINE('',#{pt[u]},#{vec})")
            ecurve[k] = s.add(f"EDGE_CURVE('',#{vx[u]},#{vx[w]},#{ln},.T.)")
        return ecurve[k]

    face_ids = []
    for normal, loops in faces:
        # plane axis: origin = first outer-loop vertex; ref dir = any
        # direction orthogonal to the normal
        o = loops[0][0]
        ax = [1.0, 0.0, 0.0] if abs(normal[0]) < 0.9 else [0.0, 1.0, 0.0]
        rd = [ax[1]*normal[2]-ax[2]*normal[1], ax[2]*normal[0]-ax[0]*normal[2],
              ax[0]*normal[1]-ax[1]*normal[0]]
        L = math.sqrt(sum(c*c for c in rd)) or 1.0
        nd = s.add(f"DIRECTION('',({fnum(normal[0])},{fnum(normal[1])},{fnum(normal[2])}))")
        rdd = s.add(f"DIRECTION('',({fnum(rd[0]/L)},{fnum(rd[1]/L)},{fnum(rd[2]/L)}))")
        a2 = s.add(f"AXIS2_PLACEMENT_3D('',#{pt[o]},#{nd},#{rdd})")
        pl = s.add(f"PLANE('',#{a2})")
        bounds = []
        for li, loop in enumerate(loops):
            oes = []
            for k in range(len(loop)):
                a, b = loop[k], loop[(k + 1) % len(loop)]
                ec = edge_id(a, b)
                fwd = '.T.' if a < b else '.F.'
                oes.append(s.add(f"ORIENTED_EDGE('',*,*,#{ec},{fwd})"))
            el = s.add(f"EDGE_LOOP('',({','.join(f'#{i}' for i in oes)}))")
            kind = 'FACE_OUTER_BOUND' if li == 0 else 'FACE_BOUND'
            bounds.append(s.add(f"{kind}('',#{el},.T.)"))
        face_ids.append(s.add(
            f"ADVANCED_FACE('',({','.join(f'#{i}' for i in bounds)}),#{pl},.T.)"))
    shell = s.add(f"CLOSED_SHELL('',({','.join(f'#{i}' for i in face_ids)}))")
    return s.add(f"MANIFOLD_SOLID_BREP('{name}',#{shell})")


def write_step(path, bodies):
    """bodies: [(name, solid)] — welded, one brep each, one shape rep."""
    s = StepFile()
    app = s.add("APPLICATION_CONTEXT('automotive design')")
    s.add(f"APPLICATION_PROTOCOL_DEFINITION('international standard',"
          f"'automotive_design',2010,#{app})")
    pctx = s.add(f"PRODUCT_CONTEXT('',#{app},'mechanical')")
    name = os.path.splitext(os.path.basename(path))[0]
    prod = s.add(f"PRODUCT('{name}','{name}','',(#{pctx}))")
    pdf = s.add(f"PRODUCT_DEFINITION_FORMATION('','',#{prod})")
    pdctx = s.add(f"PRODUCT_DEFINITION_CONTEXT('part definition',#{app},'design')")
    pd = s.add(f"PRODUCT_DEFINITION('design','',#{pdf},#{pdctx})")
    pds = s.add(f"PRODUCT_DEFINITION_SHAPE('','',#{pd})")
    lu = s.add("(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.))")
    au = s.add("(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.))")
    su = s.add("(NAMED_UNIT(*)SI_UNIT($,.STERADIAN.)SOLID_ANGLE_UNIT())")
    unc = s.add(f"UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-03),#{lu},"
                "'distance_accuracy_value','')")
    ctx = s.add(f"(GEOMETRIC_REPRESENTATION_CONTEXT(3)"
                f"GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#{unc}))"
                f"GLOBAL_UNIT_ASSIGNED_CONTEXT((#{lu},#{au},#{su}))"
                f"REPRESENTATION_CONTEXT('',''))")
    breps = []
    for bname, solid in bodies:
        V, T = to_arrays(solid)
        breps.append(emit_brep(s, bname, V, T))
    o = s.add("CARTESIAN_POINT('',(0.,0.,0.))")
    nz = s.add("DIRECTION('',(0.,0.,1.))")
    nx = s.add("DIRECTION('',(1.,0.,0.))")
    a2 = s.add(f"AXIS2_PLACEMENT_3D('',#{o},#{nz},#{nx})")
    rep = s.add(f"ADVANCED_BREP_SHAPE_REPRESENTATION('{name}',"
                f"({','.join(f'#{i}' for i in breps)},#{a2}),#{ctx})")
    s.add(f"SHAPE_DEFINITION_REPRESENTATION(#{pds},#{rep})")
    s.write(path, name)
    return len(bodies)


# ----------------------------------------------------------------------------
def build_everything(cf, d):
    """(filename, [(body name, solid)]) for every export."""
    seg   = build_segment(cf)
    waf   = build_wafer(cf, 0)
    plate = build_plate(d)
    clamp = build_clamp(d)
    motor = build_motor_dummy(d)
    pin   = build_drive_pinion(d)
    singles = [
        ('segment.stp',      [('segment', seg)]),
        ('wafer.stp',        [('wafer', waf)]),
        ('drive_plate.stp',  [('drive_plate', plate)]),
        ('drive_clamp.stp',  [('drive_clamp', clamp)]),
        ('drive_pinion.stp', [('drive_pinion', pin)]),
        ('motor_dummy.stp',  [('motor_dummy', motor)]),
    ]
    assembly = [(f'segment_{k+1}', s) for k, s in enumerate(build_ring(cf))]
    assembly += [(f'wafer_{k+1}', build_wafer(cf, k)) for k in range(cf.N)]
    assembly += [('drive_plate', plate), ('drive_clamp', clamp),
                 ('motor_dummy', motor), ('drive_pinion', pin)]
    return singles + [('halo_drive_assembly.stp', assembly)]


def verify(outputs, outdir):
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber('General.Terminal', 0)
    bad = []
    for fname, bodies in outputs:
        path = os.path.join(outdir, fname)
        want = sorted(b[1].volume() for b in bodies)
        gmsh.clear()
        try:
            gmsh.model.occ.importShapes(path)
            gmsh.model.occ.synchronize()
            vols = gmsh.model.getEntities(3)
            got = sorted(gmsh.model.occ.getMass(dim, tag) for dim, tag in vols)
        except Exception as e:
            bad.append(f"{fname}: OCC import failed: {e}")
            continue
        if len(got) != len(want):
            bad.append(f"{fname}: {len(got)} solids read, {len(want)} written")
            continue
        for w, g in zip(want, got):
            if abs(w - g) > max(1e-3, 1e-3 * w):
                bad.append(f"{fname}: volume {g:.3f} vs source {w:.3f}")
                break
        print(f"  VERIFY  {fname:28} {len(got):3d} solids, "
              f"{sum(got)/1000:9.1f} cm3  OCC read OK")
    gmsh.finalize()
    return bad


def main():
    if not HAVE_MANIFOLD:
        sys.exit("needs manifold3d:  pip install manifold3d")
    ap = argparse.ArgumentParser(description="Wafer Halo — STEP export")
    ap.add_argument('-o', '--out', default=OUT_DIR)
    ap.add_argument('--verify', action='store_true',
                    help='round-trip every file through the gmsh/OCC reader')
    for k, v in {**PARAMS, **DRIVE}.items():
        ap.add_argument(f'--{k}', type=type(v), default=None)
    a = ap.parse_args()
    cf = Cfg(**{k: getattr(a, k) for k in PARAMS if getattr(a, k) is not None})
    d = Drive(cf, **{k: getattr(a, k) for k in DRIVE if getattr(a, k) is not None})
    os.makedirs(a.out, exist_ok=True)

    outputs = build_everything(cf, d)
    for fname, bodies in outputs:
        path = os.path.join(a.out, fname)
        n = write_step(path, bodies)
        kb = os.path.getsize(path) / 1024
        print(f"  {fname:28} {n:3d} bodies  {kb:8.0f} kB")

    if a.verify:
        print()
        bad = verify(outputs, a.out)
        if bad:
            print("\nFAILURES:")
            for b in bad:
                print(f"  {b}")
            return 1
        print("\nALL STEP FILES VERIFIED (gmsh/OpenCASCADE round-trip)")
    print(f"Wrote to {os.path.abspath(a.out)}/")
    return 0


if __name__ == '__main__':
    sys.exit(main())
