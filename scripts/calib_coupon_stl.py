#!/usr/bin/env python3
"""Material-calibration coupon for scanner-verified FDM dial-in.

Built 2026-08-31 for the first PPA-CF runs on the H2S, verified with an
LMI Gocator 3210-class snapshot sensor (GoPxL). Self-contained on
purpose — no segment_stl import; this is printer/material calibration,
not halo geometry.

Design intent (every feature maps to a GoPxL surface tool):
  - 4 corner studs: center-to-center spans carry the XY scale (Surface
    Stud centers are immune to bead-width/flank offset, so span error is
    PURE shrinkage, split by axis).
  - center boss + stud diameters: flank offset (contour compensation)
    once the span scale is removed.
  - 3 blind holes (holes always print undersize): hole compensation.
  - 4-step staircase: Z scale (slope of measured-vs-nominal) with
    first-layer squish cancelling in the plane-to-plane deltas.
  - plate top quadrants: flatness / warp (Surface Plane).
  - one chamfered corner: clocking marker so +X/+Y are unambiguous in
    the scan.
All tops are scan-visible from above (no undercuts) and the part prints
flat with zero supports. Total height 16 mm — inside the 3210's 25 mm
measurement range. Footprint 96x132 stays inside the ~100x150 FOV with
margin.

  gen  -> stl/calib/calib_coupon.stl + calib_coupon_nominals.json
  fit  -> read a measurements JSON (template printed by gen) and emit
          Bambu/Orca compensation numbers (shrinkage %, contour comp,
          hole comp, Z scale).
"""

from __future__ import annotations
import argparse, json, math, os, struct, sys

PARAMS = dict(
    plate_w=96.0,  # X footprint
    plate_l=132.0,  # Y footprint
    plate_t=4.0,  # base plate thickness
    stud_d=12.0,
    stud_h=6.0,
    span_x=76.0,  # stud center-to-center span in X
    span_y=108.0,  # stud center-to-center span in Y
    boss_d=25.0,
    boss_h=6.0,
    hole_ds=(6.0, 10.0, 16.0),
    hole_dep=3.0,  # blind; floor stays plate_t - hole_dep
    hole_y=30.0,
    step_hs=(2.0, 4.0, 8.0, 12.0),  # above plate top
    step_w=18.0,  # plateau square
    step_y=-37.0,  # staircase row center
    marker=12.0,  # corner chamfer leg at (+x,+y)
    seg=144,  # circular segments (radius facet error <5 um at Ø25)
)


def build(P):
    from manifold3d import CrossSection, Manifold, set_circular_segments

    set_circular_segments(P["seg"])

    def cyl(d, h):
        return Manifold.cylinder(h, d / 2.0)

    def box(x0, y0, x1, y1, z0, z1):
        return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])

    w, l, t = P["plate_w"], P["plate_l"], P["plate_t"]
    plate = box(-w / 2, -l / 2, w / 2, l / 2, 0, t)

    # clocking marker: shear off the (+x,+y) corner with a triangular prism
    m = P["marker"]
    tri = Manifold.extrude(
        CrossSection([[(w / 2 - m, l / 2), (w / 2, l / 2 - m), (w / 2, l / 2)]]),
        t + 1,
    )
    plate -= tri.translate([0, 0, -0.5])

    solid = plate
    sx, sy = P["span_x"] / 2, P["span_y"] / 2
    for px in (-sx, sx):
        for py in (-sy, sy):
            solid += cyl(P["stud_d"], P["stud_h"]).translate([px, py, t])
    solid += cyl(P["boss_d"], P["boss_h"]).translate([0, 0, t])

    # blind holes, biggest outboard; positions keep >=6 mm ligament to
    # the boss, studs, and plate edge
    hx = {16.0: -28.0, 10.0: 0.0, 6.0: 24.0}
    for d in P["hole_ds"]:
        solid -= cyl(d, P["hole_dep"] + 0.5).translate(
            [hx[d], P["hole_y"], t - P["hole_dep"]]
        )

    # staircase: four plateaus in a row across X
    n = len(P["step_hs"])
    x0 = -n * P["step_w"] / 2
    for i, h in enumerate(P["step_hs"]):
        solid += box(
            x0 + i * P["step_w"],
            P["step_y"] - P["step_w"] / 2,
            x0 + (i + 1) * P["step_w"],
            P["step_y"] + P["step_w"] / 2,
            t,
            t + h,
        )
    return solid


def nominals(P):
    t = P["plate_t"]
    return dict(
        span_x=P["span_x"],
        span_y=P["span_y"],
        stud_d=P["stud_d"],
        boss_d=P["boss_d"],
        hole_ds=list(P["hole_ds"]),
        hole_dep=P["hole_dep"],
        step_hs=list(P["step_hs"]),
        plate=[P["plate_w"], P["plate_l"], t],
        stud_top_z=t + P["stud_h"],
        boss_top_z=t + P["boss_h"],
        total_h=t + max(P["step_hs"]),
        stud_xy=[
            [sx * P["span_x"] / 2, sy * P["span_y"] / 2]
            for sx, sy in ((-1, -1), (-1, 1), (1, -1), (1, 1))
        ],
        hole_xy={
            "16": [-28.0, P["hole_y"]],
            "10": [0.0, P["hole_y"]],
            "6": [24.0, P["hole_y"]],
        },
    )


def checks(P, solid):
    mesh = solid.to_mesh()
    nv, nt = len(mesh.vert_properties), len(mesh.tri_verts)
    euler = nv - (3 * nt) // 2 + nt
    genus = (2 - euler) // 2
    parts = [c for c in solid.decompose() if c.volume() > 0.01]

    w, l, t = P["plate_w"], P["plate_l"], P["plate_t"]
    v_plate = w * l * t - P["marker"] ** 2 / 2 * t
    v_studs = 4 * math.pi * P["stud_d"] ** 2 / 4 * P["stud_h"]
    v_boss = math.pi * P["boss_d"] ** 2 / 4 * P["boss_h"]
    v_holes = sum(math.pi * d * d / 4 * P["hole_dep"] for d in P["hole_ds"])
    v_steps = sum(P["step_w"] ** 2 * h for h in P["step_hs"])
    v_nom = v_plate + v_studs + v_boss - v_holes + v_steps
    v = solid.volume()

    ok = True

    def gate(name, cond, msg):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}: {msg}")
        ok = ok and cond

    gate(
        "watertight",
        len(parts) == 1 and genus == 0,
        f"{len(parts)} body, genus {genus}",
    )
    gate(
        "volume",
        abs(v - v_nom) / v_nom < 0.01,
        f"{v / 1000:.1f} cm3 vs analytic {v_nom / 1000:.1f} (facet loss inside 1%)",
    )
    bb = solid.bounding_box()
    dims = [bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2]]
    gate(
        "bbox",
        all(abs(a - b) < 1e-6 for a, b in zip(dims, [w, l, t + max(P["step_hs"])])),
        f"{dims[0]:.2f} x {dims[1]:.2f} x {dims[2]:.2f}",
    )
    gate(
        "hole floor",
        t - P["hole_dep"] >= 1.0,
        f"{t - P['hole_dep']:.1f} mm ligament under holes",
    )
    margin_x = w / 2 - (P["span_x"] / 2 + P["stud_d"] / 2)
    margin_y = l / 2 - (P["span_y"] / 2 + P["stud_d"] / 2)
    gate(
        "stud margin",
        margin_x >= 2 and margin_y >= 2,
        f"{margin_x:.1f} / {margin_y:.1f} mm to plate edge",
    )
    gate(
        "z range",
        t + max(P["step_hs"]) <= 20.0,
        f"{t + max(P['step_hs']):.1f} mm tall vs 25 mm sensor range",
    )
    return ok


def write_stl(solid, path):
    mesh = solid.to_mesh()
    V, T = mesh.vert_properties, mesh.tri_verts
    with open(path, "wb") as f:
        f.write(struct.pack("<80sI", b"calib-coupon".ljust(80, b"\0"), len(T)))
        for tri in T:
            a, b, c = (V[i][:3] for i in tri)
            ux = [b[k] - a[k] for k in range(3)]
            vx = [c[k] - a[k] for k in range(3)]
            n = [
                ux[1] * vx[2] - ux[2] * vx[1],
                ux[2] * vx[0] - ux[0] * vx[2],
                ux[0] * vx[1] - ux[1] * vx[0],
            ]
            L = math.sqrt(sum(x * x for x in n)) or 1.0
            f.write(struct.pack("<12fH", *(x / L for x in n), *a, *b, *c, 0))


MEAS_TEMPLATE = dict(
    span_x=None,
    span_y=None,  # stud center-to-center, mm
    stud_d=None,  # mean of the 4 stud diameters
    boss_d=None,
    hole_d={"6": None, "10": None, "16": None},
    step_h={"2": None, "4": None, "8": None, "12": None},  # vs plate top
    flatness=None,  # plate-top plane deviation, mm
)


def fit(P, meas_path):
    N = nominals(P)
    with open(meas_path) as f:
        M = json.load(f)

    print("== XY scale (from stud spans — bead-offset-free) ==")
    scale_x = N["span_x"] / M["span_x"]
    scale_y = N["span_y"] / M["span_y"]
    print(
        f"  X: measured {M['span_x']:.3f} vs {N['span_x']:.3f}"
        f" -> scale {scale_x:.5f}  (shrinkage setting {scale_x * 100:.2f}%)"
    )
    print(
        f"  Y: measured {M['span_y']:.3f} vs {N['span_y']:.3f}"
        f" -> scale {scale_y:.5f}  (shrinkage setting {scale_y * 100:.2f}%)"
    )
    s = (scale_x + scale_y) / 2
    print(f"  If the slicer has one shrinkage field: {s * 100:.2f}%")

    print("== Contour offset (boss/stud diameter after removing scale) ==")
    errs = []
    for name, dm, dn in (
        ("boss", M.get("boss_d"), N["boss_d"]),
        ("stud", M.get("stud_d"), N["stud_d"]),
    ):
        if dm is None:
            continue
        e = dn - dm * s  # + means printed undersize
        errs.append(e)
        print(f"  {name} Ø{dn:g}: {e:+.3f} mm on diameter ({e / 2:+.3f} per side)")
    if errs:
        c = sum(errs) / len(errs) / 2
        print(
            f"  -> X-Y contour compensation ~{c:+.3f} mm"
            " (Orca offsets each perimeter; confirm sign on the reprint)"
        )

    print("== Hole compensation (residual after scale + contour) ==")
    ccomp = (sum(errs) / len(errs)) if errs else 0.0
    hs = []
    for k in ("6", "10", "16"):
        dm = M["hole_d"].get(k)
        if dm is None:
            continue
        e = float(k) - dm * s - ccomp  # + means hole still undersize
        hs.append(e)
        print(f"  Ø{k}: {e:+.3f} mm on diameter beyond the contour term")
    if hs:
        print(
            f"  -> X-Y hole compensation ~{sum(hs) / len(hs) / 2:+.3f} mm"
            " (per-side; small holes usually need the most)"
        )

    print("== Z (steps vs plate top — squish cancels) ==")
    pts = [(float(k), v) for k, v in M["step_h"].items() if v is not None]
    if len(pts) >= 2:
        n = len(pts)
        mx = sum(p[0] for p in pts) / n
        my = sum(p[1] for p in pts) / n
        slope = sum((x - mx) * (y - my) for x, y in pts) / sum(
            (x - mx) ** 2 for x, _ in pts
        )
        b0 = my - slope * mx
        print(
            f"  measured = {slope:.5f} * nominal {b0:+.3f}"
            f" -> Z shrinkage setting {100 / slope:.2f}%,"
            f" step offset {b0:+.3f} mm"
        )
    if M.get("flatness") is not None:
        print(
            f"== Flatness == {M['flatness']:.3f} mm plate-top deviation"
            " (>0.3 mm: slow the fan / raise chamber soak before"
            " trusting the XY numbers)"
        )


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    g = sub.add_parser("gen", help="emit STL + nominals + meas template")
    g.add_argument("--outdir", default="stl/calib")
    for k, v in PARAMS.items():
        if isinstance(v, (int, float)):
            g.add_argument(f"--{k}", type=type(v), default=v)
    f = sub.add_parser("fit", help="turn measured values into slicer numbers")
    f.add_argument("meas", help="filled-in measurements JSON")
    args = ap.parse_args()

    if args.cmd == "fit":
        fit(PARAMS, args.meas)
        return

    P = dict(PARAMS)
    if args.cmd == "gen":
        for k in P:
            if hasattr(args, k):
                P[k] = getattr(args, k)
    outdir = getattr(args, "outdir", "stl/calib")
    os.makedirs(outdir, exist_ok=True)

    solid = build(P)
    print("self-checks:")
    ok = checks(P, solid)
    path = os.path.join(outdir, "calib_coupon.stl")
    write_stl(solid, path)
    print(f"wrote {path}")
    with open(os.path.join(outdir, "calib_coupon_nominals.json"), "w") as fh:
        json.dump(nominals(P), fh, indent=2)
    print(f"wrote {outdir}/calib_coupon_nominals.json")
    tpl = os.path.join(outdir, "measurements_template.json")
    if not os.path.exists(tpl):
        with open(tpl, "w") as fh:
            json.dump(MEAS_TEMPLATE, fh, indent=2)
        print(f"wrote {tpl} (fill in and run: calib_coupon_stl.py fit {tpl})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
