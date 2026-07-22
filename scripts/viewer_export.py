#!/usr/bin/env python3
"""
Wafer Halo — web viewer export + configuration interference gates.

The GitHub Pages viewer (docs/viewer.html) shows the REAL CAD, not a
re-derivation: this script exports every body in SCENE coordinates (halo axis
at the origin, bench at z_bot — the same frame cure_jig_fitcheck.stl uses)
into docs/models/, plus a manifest.json describing how the viewer may move
them: the jig open/close stroke, the wafer placement drop, and the 40-degree
station step for the glued ring.

Every configuration the viewer can show is CHECKED here first, on the real
solids, with boolean CSG — the script exits nonzero on any FAIL, and the
manifest carries the results so the page can display them:

  nominal    the full cure-jig suite from cure_jig_stl.run_checks (18 checks:
             drivetrain interference + capture)
  travel     fences / rod / hardware swept open -> closed in steps must never
             touch the segment or the wafer at ANY point of the stroke
  placement  the wafer lowered onto the land along its plane normal with the
             jig open must clear the fences and the segment the whole way
  assembly   adjacent glued stations: segment/segment (dovetail), segment vs
             both neighbour wafers, wafer/wafer — all zero interference — and
             the DEPTH gate: the segment must stay >= 2.95 mm below the
             neighbour wafer's underside but come within 3.05 mm of it, i.e.
             the Rev B clearance cut exists and is neither missing nor
             over-deep (the same 3.000 mm gate T1 measures on the print)

    pip install manifold3d
    python3 scripts/viewer_export.py             # -> docs/models/
    python3 scripts/viewer_export.py --verify    # CI: checks + staleness gate
"""
from __future__ import annotations
import json, math, os, sys, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from segment_stl import (PARAMS, Cfg, build_segment, build_wafer, write_stl,
                         report, wafer_cut, keyhole_z, Manifold, HAVE_MANIFOLD)
from cure_jig_stl import (JIG, Jig, build_outboard, build_inboard,
                          build_hardware, run_checks)

EPS = 1e-6
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'docs', 'models')

# Stroke lengths for the open/close animation, mm. Sized so every moving body
# fully clears the wafer footprint / keyhole; the travel sweep below PROVES it
# rather than trusting these numbers.
TRAVEL = dict(out=90.0, inboard=60.0, rod=130.0)
WAFER_LIFT = 40.0     # placement drop along the wafer plane normal
SWEEP_STEPS = 5       # positions checked across each stroke (incl. both ends)


def build_scene(cf, j):
    """All bodies in scene coordinates, keyed by manifest part name."""
    rod, nut, washer, wnut, _ = build_hardware(j)
    return {
        'segment':      (build_segment(cf),  'segment',  0xB9A87E),
        'wafer':        (build_wafer(cf, 0), 'wafer',    0x9AA6B2),
        'jig_outboard': (build_outboard(j),  'out',      0xD97742),
        'jig_inboard':  (build_inboard(j),   'inboard',  0x3E7CB1),
        'rod':          (rod,                'rod',      0x30343A),
        'hex_nut':      (nut,                'inboard',  0x4A5058),
        'washer':       (washer,             'rod',      0x6A7078),
        'wing_nut':     (wnut,               'rod',      0x4A5058),
    }


def motion_vectors(cf):
    """Displacement (full stroke) per motion group. The wafer lifts along its
    own plane normal; jig groups run radially on the rod axis (x at a=0)."""
    _, _, n = cf.wafer_frame(0)
    return {
        'out':     [TRAVEL['out'], 0.0, 0.0],
        'inboard': [-TRAVEL['inboard'], 0.0, 0.0],
        'rod':     [TRAVEL['rod'], 0.0, 0.0],
        'wafer':   [WAFER_LIFT * n[0], WAFER_LIFT * n[1], WAFER_LIFT * n[2]],
        'segment': [0.0, 0.0, 0.0],
    }


def moved(solid, vec, t):
    return solid.translate([vec[0] * t, vec[1] * t, vec[2] * t])


def sweep_checks(cf, scene, vecs):
    """Jig opening stroke and wafer placement drop: zero contact throughout."""
    seg, waf = scene['segment'][0], scene['wafer'][0]
    fixed = seg + waf
    checks = []
    groups = {}
    for name, (solid, group, _) in scene.items():
        if group in ('out', 'inboard', 'rod'):
            groups[group] = groups.get(group, None) + solid if group in groups else solid
    for group, solid in groups.items():
        worst = 0.0
        for i in range(SWEEP_STEPS):
            t = i / (SWEEP_STEPS - 1)
            worst = max(worst, (moved(solid, vecs[group], t) ^ fixed).volume())
        checks.append(('travel', f'{group} stroke ({TRAVEL[group]:.0f} mm) vs '
                       f'segment+wafer, {SWEEP_STEPS} steps', worst, worst < EPS))
    # wafer drop with the jig fully open
    jig_open = sum((moved(groups[g], vecs[g], 1.0) for g in groups),
                   Manifold())
    worst = 0.0
    for i in range(SWEEP_STEPS):
        t = i / (SWEEP_STEPS - 1)
        w = moved(waf, vecs['wafer'], t)
        worst = max(worst, (w ^ (seg + jig_open)).volume())
    checks.append(('placement', f'wafer drop ({WAFER_LIFT:.0f} mm) vs segment '
                   f'+ open jig, {SWEEP_STEPS} steps', worst, worst < EPS))
    return checks


def assembly_checks(cf, seg, waf):
    """Adjacent glued stations. Rotational symmetry: station 0 vs 1 (and the
    trailing side via seg1 vs waf0) covers every pair in the ring."""
    seg1 = seg.rotate([0.0, 0.0, math.degrees(cf.sector)])
    waf1 = build_wafer(cf, 1)
    zero = [
        ('segment vs next segment (dovetail joint)', (seg ^ seg1).volume()),
        ('segment vs leading neighbour wafer',       (seg ^ waf1).volume()),
        ('segment vs trailing neighbour wafer',      (seg1 ^ waf).volume()),
        ('wafer vs neighbour wafer',                 (waf ^ waf1).volume()),
    ]
    checks = [('assembly', n, v, v < EPS) for n, v in zero]
    # depth (z) clearance gate against the leading wafer's plane: material must
    # stay 2.95 mm clear of the wafer underside, yet exist within 3.05 mm —
    # proves the clearance cut is present and cut to depth (T1's 3.000 mm).
    probe = lambda d: (seg ^ wafer_cut(cf, 1, -(cf.wafer_T / 2 + d), cf.tall)).volume()
    v_clear, v_touch = probe(cf.clr - 0.05), probe(cf.clr + 0.05)
    checks.append(('assembly', f'depth clearance >= {cf.clr - 0.05:.2f} mm under '
                   'the neighbour wafer', v_clear, v_clear < EPS))
    checks.append(('assembly', f'clearance cut present (material within '
                   f'{cf.clr + 0.05:.2f} mm)', v_touch, v_touch > EPS))
    # the joint actually engages: nudge the neighbour 0.1 deg into station 0
    v_butt = (seg ^ seg1.rotate([0.0, 0.0, -0.1])).volume()
    checks.append(('assembly', 'segments butt at the joint (0.1 deg nudge '
                   'contacts)', v_butt, v_butt > EPS))
    return checks


def build_all(cf, j):
    scene = build_scene(cf, j)
    vecs = motion_vectors(cf)

    print('nominal: cure-jig suite (cure_jig_stl.run_checks)')
    seg, waf = scene['segment'][0], scene['wafer'][0]
    nominal_ok = run_checks(j, seg, waf, scene['jig_outboard'][0],
                            scene['jig_inboard'][0], scene['rod'][0],
                            scene['hex_nut'][0], scene['washer'][0],
                            scene['wing_nut'][0])
    checks = [('nominal', 'cure-jig drivetrain + capture suite (18 checks)',
               0.0 if nominal_ok else 1.0, nominal_ok)]
    checks += sweep_checks(cf, scene, vecs)
    checks += assembly_checks(cf, seg, waf)

    print('\ntravel / placement / assembly:')
    for grp, name, v, ok in checks[1:]:
        print(f"    {'PASS' if ok else 'FAIL':4}  [{grp}] {name:64} {v:10.4f}")
    return scene, vecs, checks


def make_manifest(cf, scene, vecs, checks, volumes):
    return {
        'source': 'scripts/viewer_export.py',
        'params': {k: cf.p[k] for k in PARAMS},
        'sector_deg': math.degrees(cf.sector),
        'keyhole_z': keyhole_z(cf),
        'z_bot': cf.z_bot,
        'parts': [{'file': f'{name}.stl', 'name': name, 'group': group,
                   'color': f'#{color:06X}',
                   'volume_cm3': round(volumes[name] / 1000.0, 3)}
                  for name, (_, group, color) in scene.items()],
        'motion': {g: {'vector': [round(c, 4) for c in v]}
                   for g, v in vecs.items() if any(abs(c) > 0 for c in v)},
        'checks': [{'group': g, 'name': n, 'value_mm3': round(v, 4), 'pass': ok}
                   for g, n, v, ok in checks],
    }


def main():
    if not HAVE_MANIFOLD:
        sys.exit('needs manifold3d for STL output:  pip install manifold3d')
    ap = argparse.ArgumentParser(description='Wafer Halo — viewer model export')
    ap.add_argument('-o', '--out', default=OUT_DIR)
    ap.add_argument('--verify', action='store_true',
                    help='CI gate: run every check and compare against the '
                         'committed manifest instead of writing files')
    for k, v in {**PARAMS, **JIG}.items():
        ap.add_argument(f'--{k}', type=type(v), default=None)
    a = ap.parse_args()
    cf = Cfg(**{k: getattr(a, k) for k in PARAMS if getattr(a, k) is not None})
    j = Jig(cf, **{k: getattr(a, k) for k in JIG if getattr(a, k) is not None})

    scene, vecs, checks = build_all(cf, j)
    ok = all(c[3] for c in checks)
    volumes = {name: solid.volume() for name, (solid, _, _) in scene.items()}
    manifest = make_manifest(cf, scene, vecs, checks, volumes)

    if a.verify:
        mpath = os.path.join(a.out, 'manifest.json')
        try:
            with open(mpath) as f:
                committed = json.load(f)
        except FileNotFoundError:
            sys.exit(f'FAIL: {mpath} missing — run scripts/viewer_export.py')
        stale = []
        if committed.get('params') != manifest['params']:
            stale.append('params differ')
        want = {p['file'] for p in manifest['parts']}
        have = {p['file'] for p in committed.get('parts', [])}
        if want != have:
            stale.append(f'part list differs: {sorted(want ^ have)}')
        else:
            got = {p['name']: p['volume_cm3'] for p in committed['parts']}
            for p in manifest['parts']:
                ref = got.get(p['name'], 0.0)
                # volumes, not bytes: float last-bits differ across platforms
                if abs(ref - p['volume_cm3']) > max(0.002 * p['volume_cm3'], 0.005):
                    stale.append(f"{p['name']} volume {ref} vs {p['volume_cm3']}")
        for f in sorted(want):
            if not os.path.exists(os.path.join(a.out, f)):
                stale.append(f'{f} missing from {a.out}')
        print()
        if stale:
            print('STALE — docs/models does not match the scripts. '
                  'Rerun scripts/viewer_export.py and commit:')
            for s in stale:
                print(f'    {s}')
        print('ALL CHECKS PASS' if ok and not stale else 'FAILURES ABOVE')
        return 0 if ok and not stale else 1

    os.makedirs(a.out, exist_ok=True)
    print()
    for name, (solid, _, _) in scene.items():
        fname = f'{name}.stl'
        bodies = write_stl(solid, os.path.join(a.out, fname))
        report(fname, solid, bodies, f"group {scene[name][1]}")
    with open(os.path.join(a.out, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=1)
        f.write('\n')
    print(f"\n{'ALL CHECKS PASS' if ok else 'CHECK FAILURES ABOVE — do not publish'}")
    print(f'Wrote to {os.path.abspath(a.out)}/')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
