#!/usr/bin/env python3
"""
Wafer Halo — KISELRING assembly manual (IKEA-style), docs/kiselring-manual.pdf.

Every 3D panel is line art rendered FROM THE REAL CAD SOLIDS (segment_stl /
gearmotor_stl), not drawn by hand: orthographic projection, hidden lines
removed with a triangle z-buffer, and only feature edges drawn (silhouette
edges + creases over ~25 deg) — which is exactly the IKEA look. 2D pictograms
(the manual man, screws, arrows) are drawn with matplotlib primitives.

Scope: final wall assembly of the halo + gearmotor drive module. Wafer
bonding is OP 012 (docs/cure-jig.html) and is referenced, not duplicated.
The wall bracket is Nick's pre-installed part: the manual shows its two
#10-24 pan heads at the keyhole spacing this repo's drive plate prints.

    pip install manifold3d matplotlib numpy
    python3 scripts/manual_pdf.py            # -> docs/kiselring-manual.pdf
"""
from __future__ import annotations
import math, os, sys, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, FancyArrow, Rectangle, FancyArrowPatch, Arc
from matplotlib.lines import Line2D

from segment_stl import (PARAMS, Cfg, build_segment, build_wafer, build_ring,
                         to_arrays, rotated, Manifold, HAVE_MANIFOLD)
from gearmotor_stl import (DRIVE, Drive, build_plate, build_clamp,
                           build_motor_dummy, build_drive_pinion, box)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, 'docs', 'kiselring-manual.pdf')

INK = '#1a1a1a'          # the one drawing colour
PAPER = 'white'
A4 = (8.27, 11.69)


# ----------------------------------------------------------------------------
# 3D -> 2D line-art renderer
# ----------------------------------------------------------------------------
def view_basis(azim, elev):
    """Orthographic camera: returns right/up/forward unit rows (world->view)."""
    a, e = math.radians(azim), math.radians(elev)
    f = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a),
                  math.sin(e)])                  # from scene toward camera
    r = np.cross([0.0, 0.0, 1.0], f)
    r = r / (np.linalg.norm(r) or 1.0)
    u = np.cross(f, r)
    return np.array([r, u, f])


class Scene:
    """Collects solids, projects, z-buffers, and yields visible feature edges."""

    def __init__(self, solids, azim=-55.0, elev=18.0, crease_deg=25.0):
        self.M = view_basis(azim, elev)
        VV, TT = [], []
        off = 0
        for s in solids:
            V, T = to_arrays(s)
            VV.extend(V)
            TT.extend([(a + off, b + off, c + off) for a, b, c in T])
            off += len(V)
        self.V = np.array(VV)
        self.T = np.array(TT, dtype=np.int64)
        self.P = self.V @ self.M.T               # x,y = paper, z = toward camera
        self.crease = math.cos(math.radians(crease_deg))

    def bounds(self):
        return (self.P[:, 0].min(), self.P[:, 0].max(),
                self.P[:, 1].min(), self.P[:, 1].max())

    def edges(self, window=None, res=900):
        """Visible feature-edge segments inside `window` (x0,x1,y0,y1)."""
        P, T = self.P, self.T
        if window is None:
            x0, x1, y0, y1 = self.bounds()
            m = 0.03 * max(x1 - x0, y1 - y0)
            window = (x0 - m, x1 + m, y0 - m, y1 + m)
        x0, x1, y0, y1 = window
        scale = res / max(x1 - x0, y1 - y0)
        W, H = int((x1 - x0) * scale) + 2, int((y1 - y0) * scale) + 2

        tv = P[T]                                # (n,3,3)
        n = np.cross(tv[:, 1] - tv[:, 0], tv[:, 2] - tv[:, 0])
        area2 = n[:, 2]                          # signed, view space
        zmax_all = tv[:, :, 2].max(axis=1)

        # z-buffer: rasterize front-facing AND back-facing (solid occlusion)
        zb = np.full((H, W), -1e18)
        xs = (tv[:, :, 0] - x0) * scale
        ys = (tv[:, :, 1] - y0) * scale
        order = np.argsort(zmax_all)             # far -> near (cheap warm start)
        for i in order:
            # skip near-edge-on triangles: their barycentric z interpolation
            # divides by ~0 and poisons the z-buffer along silhouettes (the
            # symptom is IKEA-looking dashed lines, but the wrong kind)
            if abs(area2[i]) < 1e-4:
                continue
            X, Y = xs[i], ys[i]
            lox, hix = int(max(0, X.min())), int(min(W - 1, X.max()) + 1)
            loy, hiy = int(max(0, Y.min())), int(min(H - 1, Y.max()) + 1)
            if lox >= hix or loy >= hiy:
                continue
            gx, gy = np.meshgrid(np.arange(lox, hix) + 0.5,
                                 np.arange(loy, hiy) + 0.5)
            d = np.stack([ (X[(k+1)%3]-X[k])*(gy-Y[k]) - (Y[(k+1)%3]-Y[k])*(gx-X[k])
                           for k in range(3)])
            inside = (d >= -1e-9).all(axis=0) | (d <= 1e-9).all(axis=0)
            if not inside.any():
                continue
            # plane z at pixels
            v0, v1, v2 = tv[i]
            det = area2[i]
            l1 = ((gx / scale + x0 - v0[0]) * (v2[1] - v0[1])
                  - (gy / scale + y0 - v0[1]) * (v2[0] - v0[0])) / -det
            l2 = ((gy / scale + y0 - v0[1]) * (v1[0] - v0[0])
                  - (gx / scale + x0 - v0[0]) * (v1[1] - v0[1])) / -det
            z = v0[2] + l1 * (v1[2] - v0[2]) + l2 * (v2[2] - v0[2])
            z = np.clip(z, tv[i, :, 2].min(), tv[i, :, 2].max())
            sub = zb[loy:hiy, lox:hix]
            upd = inside & (z > sub)
            sub[upd] = z[upd]

        # feature edges
        emap = {}
        for ti, (a, b, c) in enumerate(T):
            for e in ((a, b), (b, c), (c, a)):
                emap.setdefault((min(e), max(e)), []).append(ti)
        wn = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-30)
        segs = []
        for (a, b), tris in emap.items():
            if len(tris) == 2:
                t1, t2 = tris
                front1, front2 = area2[t1] > 0, area2[t2] > 0
                if front1 == front2 and np.dot(wn[t1], wn[t2]) > self.crease:
                    continue                     # smooth interior edge
            pa, pb = P[a], P[b]
            L = np.linalg.norm(pb[:2] - pa[:2])
            if L * scale < 1.0:
                continue
            ns = max(4, min(64, int(L * scale / 6)))
            t = np.linspace(0.0, 1.0, ns + 1)
            px = pa[0] + t * (pb[0] - pa[0])
            py = pa[1] + t * (pb[1] - pa[1])
            pz = pa[2] + t * (pb[2] - pa[2])
            ix = ((px - x0) * scale).astype(int).clip(0, W - 1)
            iy = ((py - y0) * scale).astype(int).clip(0, H - 1)
            vis = pz >= zb[iy, ix] - max(2.0, 0.004 * float(np.ptp(self.P[:, 2])))
            run = None
            for k in range(ns + 1):
                if vis[k] and run is None:
                    run = k
                if (not vis[k] or k == ns) and run is not None:
                    k2 = k if not vis[k] else k
                    if k2 > run:
                        segs.append(((px[run], py[run]), (px[k2], py[k2])))
                    run = None
        return segs, window

    def project(self, xyz):
        return (np.array(xyz) @ self.M.T)[:2]


def draw_scene(ax, solids, azim=-55.0, elev=18.0, window=None, lw=0.9,
               res=900, crease_deg=25.0):
    sc = Scene(solids, azim, elev, crease_deg)
    segs, window = sc.edges(window=window, res=res)
    for (p, q) in segs:
        ax.plot([p[0], q[0]], [p[1], q[1]], color=INK, lw=lw,
                solid_capstyle='round')
    ax.set_xlim(window[0], window[1])
    ax.set_ylim(window[2], window[3])
    ax.set_aspect('equal')
    ax.axis('off')
    return sc


# ----------------------------------------------------------------------------
# 2D pictogram helpers (axes in 0..1 coords unless noted)
# ----------------------------------------------------------------------------
def man(ax, x, y, s=1.0, arms='down', happy=True):
    """The manual man. s = height scale in axes units."""
    lw = 2.2 * s * 3
    h = 0.22 * s
    ax.add_patch(Circle((x, y + 0.78 * s), 0.11 * s, fill=False, color=INK,
                        lw=lw, transform=ax.transAxes))
    line = lambda xs, ys: ax.add_line(
        Line2D([x + a * s for a in xs], [y + b * s for b in ys], color=INK,
               lw=lw, solid_capstyle='round', transform=ax.transAxes))
    line([0, 0], [0.67, 0.30])                    # torso
    line([0, -0.13], [0.30, 0.0]); line([0, 0.13], [0.30, 0.0])   # legs
    if arms == 'up':
        line([0, -0.18], [0.60, 0.78]); line([0, 0.18], [0.60, 0.78])
    elif arms == 'shrug':
        line([0, -0.20], [0.58, 0.66]); line([0, 0.20], [0.58, 0.66])
    else:
        line([0, -0.15], [0.60, 0.40]); line([0, 0.15], [0.60, 0.40])
    if not happy:
        ax.text(x + 0.26 * s, y + 0.88 * s, '?', fontsize=26 * s * 3,
                color=INK, fontweight='bold', transform=ax.transAxes,
                ha='center')


def screw_icon(ax, x, y, s=1.0, label=''):
    """Pan-head screw, side view, pointing down. Axes coords."""
    w = 0.018 * s
    ax.add_patch(Rectangle((x - 2.2 * w, y + 0.10 * s * 0.35), 4.4 * w,
                           0.018 * s, fill=False, color=INK, lw=1.6,
                           transform=ax.transAxes))
    ax.add_line(Line2D([x, x], [y - 0.05 * s, y + 0.035 * s], color=INK,
                       lw=3.2 * s, transform=ax.transAxes))
    for i in range(4):
        yy = y + 0.02 * s - i * 0.02 * s
        ax.add_line(Line2D([x - w, x + w], [yy, yy - 0.008 * s], color=INK,
                           lw=1.1, transform=ax.transAxes))
    if label:
        ax.text(x, y - 0.09 * s, label, fontsize=8, ha='center', color=INK,
                transform=ax.transAxes)


def screwdriver(ax, x, y, s=1.0, angle=-35.0):
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    P = lambda u, v: (x + (u * ca - v * sa) * s, y + (u * sa + v * ca) * s)
    hx = [P(0, 0), P(0.16, 0)]
    ax.add_line(Line2D([hx[0][0], hx[1][0]], [hx[0][1], hx[1][1]], color=INK,
                       lw=8 * s, solid_capstyle='round',
                       transform=ax.transAxes))
    tip = [P(0.16, 0), P(0.34, 0)]
    ax.add_line(Line2D([tip[0][0], tip[1][0]], [tip[0][1], tip[1][1]],
                       color=INK, lw=2.2, transform=ax.transAxes))


def check_or_cross(ax, ok):
    if ok:
        ax.add_line(Line2D([0.80, 0.86, 0.95], [0.82, 0.74, 0.92], color=INK,
                           lw=4.5, solid_capstyle='round',
                           transform=ax.transAxes))
    else:
        ax.add_line(Line2D([0.80, 0.95], [0.75, 0.92], color=INK, lw=4.5,
                           solid_capstyle='round', transform=ax.transAxes))
        ax.add_line(Line2D([0.80, 0.95], [0.92, 0.75], color=INK, lw=4.5,
                           solid_capstyle='round', transform=ax.transAxes))


def stepnum(ax, n, x=0.06, y=0.90):
    ax.add_patch(Circle((x, y), 0.055, fill=False, color=INK, lw=2.2,
                        transform=ax.transAxes))
    ax.text(x, y, str(n), fontsize=20, fontweight='bold', ha='center',
            va='center', color=INK, transform=ax.transAxes)


def panel(fig, rect, border=True):
    ax = fig.add_axes(rect)
    ax.set_xticks([]); ax.set_yticks([])
    if border:
        for sp in ax.spines.values():
            sp.set_linewidth(1.4); sp.set_color(INK)
    else:
        ax.axis('off')
    return ax


def arrow(ax, p, q, lw=2.4, style='-|>', mut=16):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=mut,
                                 lw=lw, color=INK,
                                 shrinkA=0, shrinkB=0))


def axes_arrow(ax, p, q, lw=2.4, mut=16):
    ax.add_patch(FancyArrowPatch(p, q, transform=ax.transAxes,
                                 arrowstyle='-|>', mutation_scale=mut,
                                 lw=lw, color=INK, shrinkA=0, shrinkB=0))


# ----------------------------------------------------------------------------
# scene kits
# ----------------------------------------------------------------------------
def wall_slab(d, half=380.0, cx=0.0, cy=0.0):
    return box(cx - half, cx + half, cy - half, cy + half,
               d.z_back - 8.0, d.z_back - 2.0)


def bracket_screws(d):
    """The two #10-24 pan heads standing proud of the wall, as solids."""
    out = []
    ex = d.cx + d.key_len / 2
    for s in (1.0, -1.0):
        sc = (Manifold.cylinder(10.0, 2.4, 2.4, 32)
              .translate([ex, s * d.key_y, d.z_back - 6.0]))
        sc += (Manifold.cylinder(2.5, 4.6, 4.6, 32)
               .translate([ex, s * d.key_y, d.z_back + 1.8]))
        out.append(sc)
    return out


def drive_solids(d, motor_dz=0.0, clamp_dz=0.0, pinion_dz=0.0, plate_dxz=(0, 0)):
    dxp, dzp = plate_dxz
    return [build_plate(d).translate([dxp, 0, dzp]),
            build_clamp(d).translate([0, 0, clamp_dz]),
            build_motor_dummy(d).translate([0, 0, motor_dz]),
            build_drive_pinion(d).translate([0, 0, pinion_dz])]


# ----------------------------------------------------------------------------
# pages
# ----------------------------------------------------------------------------
def page_cover(pdf, cf, d):
    fig = plt.figure(figsize=A4)
    ax = panel(fig, [0.08, 0.10, 0.84, 0.58], border=False)
    solids = build_ring(cf) + [build_wafer(cf, k) for k in range(cf.N)]
    solids += drive_solids(d) + [wall_slab(d)]
    draw_scene(ax, solids, azim=-90.0, elev=68.0, lw=0.55, res=1100)

    fig.text(0.07, 0.955, 'KISELRING', fontsize=54, fontweight='bold',
             color=INK, family='sans-serif')
    fig.text(0.07, 0.925, 'rotating silicon-wafer halo  ·  Ø1.0 m  ·  1.8 kg',
             fontsize=13, color=INK)
    fig.text(0.07, 0.895, 'kisel (Swedish): silicon', fontsize=10, color=INK,
             style='italic')
    axm = panel(fig, [0.70, 0.86, 0.24, 0.115], border=False)
    man(axm, 0.30, 0.05, s=0.28, arms='up')
    axm.text(0.62, 0.25, '×1', fontsize=16, fontweight='bold', color=INK,
             transform=axm.transAxes)
    fig.text(0.07, 0.685, '9 × Ø300 mm wafers   ·   252:28 = 9:1 internal drive'
             '   ·   no tools on the frame', fontsize=11, color=INK)
    fig.text(0.5, 0.025, 'wafer-flower  ·  Rev B.3', fontsize=9, color=INK,
             ha='center')
    pdf.savefig(fig); plt.close(fig)


def page_warnings(pdf, cf, d):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.955, '!', fontsize=40, fontweight='bold', ha='center',
             color=INK)
    boxes = [
        [0.06, 0.62, 0.42, 0.28], [0.52, 0.62, 0.42, 0.28],
        [0.06, 0.30, 0.42, 0.28], [0.52, 0.30, 0.42, 0.28],
        [0.06, 0.04, 0.42, 0.22], [0.52, 0.04, 0.42, 0.22],
    ]
    # 1: hold wafers by the EDGES (check)
    ax = panel(fig, boxes[0])
    ax.add_patch(Circle((0.5, 0.45), 0.30, fill=False, color=INK, lw=2.5,
                        transform=ax.transAxes))
    ax.add_line(Line2D([0.13, 0.20], [0.45, 0.45], color=INK, lw=5,
                       transform=ax.transAxes, solid_capstyle='round'))
    ax.add_line(Line2D([0.80, 0.87], [0.45, 0.45], color=INK, lw=5,
                       transform=ax.transAxes, solid_capstyle='round'))
    check_or_cross(ax, True)
    ax.text(0.5, 0.06, 'edges only', fontsize=10, ha='center', color=INK,
            transform=ax.transAxes)
    # 2: never press the middle (cross)
    ax = panel(fig, boxes[1])
    ax.add_patch(Circle((0.5, 0.45), 0.30, fill=False, color=INK, lw=2.5,
                        transform=ax.transAxes))
    axes_arrow(ax, (0.5, 0.92), (0.5, 0.55), lw=3)
    check_or_cross(ax, False)
    ax.text(0.5, 0.06, 'never press the middle', fontsize=10, ha='center',
            color=INK, transform=ax.transAxes)
    # 3: no solvents on the print
    ax = panel(fig, boxes[2])
    ax.add_patch(Rectangle((0.40, 0.30), 0.20, 0.34, fill=False, color=INK,
                           lw=2.5, transform=ax.transAxes))
    ax.add_patch(Rectangle((0.46, 0.64), 0.08, 0.10, fill=False, color=INK,
                           lw=2.5, transform=ax.transAxes))
    ax.text(0.5, 0.44, 'ACE\nTONE', fontsize=8, ha='center', va='center',
            color=INK, transform=ax.transAxes)
    check_or_cross(ax, False)
    ax.text(0.5, 0.06, 'IPA on glass only — never on the frame', fontsize=10,
            ha='center', color=INK, transform=ax.transAxes)
    # 4: bond wafers FIRST with the cure jig
    ax = panel(fig, boxes[3])
    seg = build_segment(cf)
    waf = build_wafer(cf, 0)
    draw2 = panel(fig, [boxes[3][0] + 0.03, boxes[3][1] + 0.06, 0.36, 0.19],
                  border=False)
    draw_scene(draw2, [seg, waf], azim=-50, elev=22, lw=0.5, res=520)
    ax.text(0.5, 0.10, 'wafers already bonded?  see cure-jig manual (OP 012)',
            fontsize=9, ha='center', color=INK, transform=ax.transAxes)
    # 5: confused -> read the traveler
    ax = panel(fig, boxes[4])
    man(ax, 0.28, 0.18, s=0.55, arms='shrug', happy=False)
    ax.add_patch(Rectangle((0.60, 0.25), 0.22, 0.34, fill=False, color=INK,
                           lw=2.2, transform=ax.transAxes))
    for i in range(4):
        ax.add_line(Line2D([0.63, 0.79], [0.51 - i * 0.06] * 2, color=INK,
                           lw=1.2, transform=ax.transAxes))
    ax.text(0.5, 0.06, 'docs/index.html', fontsize=9, ha='center', color=INK,
            transform=ax.transAxes)
    # 6: tools
    ax = panel(fig, boxes[5])
    screwdriver(ax, 0.16, 0.55, s=0.9)
    ax.add_line(Line2D([0.55, 0.90], [0.62, 0.62], color=INK, lw=7,
                       transform=ax.transAxes, solid_capstyle='round'))
    ax.add_patch(Circle((0.725, 0.62), 0.012, color=PAPER, zorder=5,
                        transform=ax.transAxes))
    ax.text(0.725, 0.70, 'level', fontsize=8, ha='center', color=INK,
            transform=ax.transAxes)
    ax.text(0.30, 0.30, 'PH2', fontsize=10, ha='center', color=INK,
            transform=ax.transAxes)
    ax.text(0.5, 0.06, 'no hammer. ever.', fontsize=10, ha='center',
            color=INK, transform=ax.transAxes)
    pdf.savefig(fig); plt.close(fig)


def page_parts(pdf, cf, d):
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.955, 'in the box', fontsize=18, fontweight='bold',
             color=INK)
    fig.add_artist(Line2D([0.06, 0.94], [0.945, 0.945], color=INK, lw=1.5,
                          transform=fig.transFigure))
    items = [
        ([rotated(build_segment(cf), 0, cf)], '×9', 'frame segment', -50, 22),
        ([build_wafer(cf, 0)], '×9', 'Ø300 wafer (bonded)', -50, 35),
        ([build_plate(d).translate([-d.cx, 0, 0])], '×1', 'drive plate', -50, 30),
        ([build_drive_pinion(d).translate([-d.cx, 0, 0])], '×1',
         '28T pinion', -50, 30),
        ([build_clamp(d).translate([-d.cx, 0, 0])], '×1', 'motor clamp', -50, 30),
        ([build_motor_dummy(d).translate([-d.cx, 0, 0])], '×1',
         'N20 worm gearmotor', -50, 30),
    ]
    cells = [(r, c) for r in range(3) for c in range(2)]
    for (solids, count, label, az, el), (r, c) in zip(items, cells):
        y0 = 0.70 - r * 0.245
        ax = panel(fig, [0.06 + c * 0.46, y0, 0.40, 0.225])
        inner = panel(fig, [0.06 + c * 0.46 + 0.02, y0 + 0.045, 0.28, 0.16],
                      border=False)
        draw_scene(inner, solids, azim=az, elev=el, lw=0.55, res=520)
        ax.text(0.85, 0.80, count, fontsize=18, fontweight='bold', ha='center',
                color=INK, transform=ax.transAxes)
        ax.text(0.5, 0.045, label, fontsize=10, ha='center', color=INK,
                transform=ax.transAxes)
    ax = panel(fig, [0.06, 0.03, 0.88, 0.16])
    ax.text(0.05, 0.85, 'hardware', fontsize=12, fontweight='bold', color=INK,
            transform=ax.transAxes)
    screw_icon(ax, 0.16, 0.55, s=1.6, label='#10-24 pan  ×2\n(in your bracket)')
    screw_icon(ax, 0.42, 0.55, s=1.2, label='#6 × 1/2"  ×2')
    ax.add_patch(Circle((0.68, 0.55), 0.035, fill=False, color=INK, lw=2,
                        transform=ax.transAxes))
    ax.add_patch(Circle((0.68, 0.55), 0.013, fill=False, color=INK, lw=1.4,
                        transform=ax.transAxes))
    ax.text(0.68, 0.40, 'USB / 5 V DC  ×1', fontsize=8, ha='center', color=INK,
            transform=ax.transAxes)
    ax.text(0.05, 0.10, 'not included: wall bracket with two #10-24 pan heads, '
            '56 mm apart (see step 4)', fontsize=9, color=INK,
            transform=ax.transAxes)
    pdf.savefig(fig); plt.close(fig)


def page_motor(pdf, cf, d):
    fig = plt.figure(figsize=A4)
    # step 1: motor drops into pocket
    ax = panel(fig, [0.06, 0.52, 0.88, 0.42])
    stepnum(ax, 1)
    inner = panel(fig, [0.10, 0.55, 0.62, 0.36], border=False)
    solids = [build_plate(d), build_motor_dummy(d).translate([0, 0, 30])]
    sc = draw_scene(inner, solids, azim=-55, elev=48, lw=0.7, res=760)
    p = sc.project([d.cx, 8, d.shaft_z0 + 26])
    q = sc.project([d.cx, 8, d.shaft_z0 + 4])
    arrow(inner, tuple(p), tuple(q), lw=2.6)
    ax.text(0.5, 0.045, 'nose first, under the lip — then drop the tail',
            fontsize=10, ha='center', color=INK, transform=ax.transAxes)
    man_ax = panel(fig, [0.74, 0.79, 0.16, 0.13], border=False)
    man(man_ax, 0.5, 0.05, s=0.30)
    # step 2: clamp + two screws
    ax = panel(fig, [0.06, 0.05, 0.88, 0.42])
    stepnum(ax, 2)
    inner = panel(fig, [0.10, 0.08, 0.62, 0.36], border=False)
    solids = [build_plate(d), build_motor_dummy(d),
              build_clamp(d).translate([0, 0, 24])]
    sc = draw_scene(inner, solids, azim=-55, elev=48, lw=0.7, res=760)
    cy = d.clamp_cy()
    p = sc.project([d.cx, cy, d.z_front + 20])
    q = sc.project([d.cx, cy, d.z_front + 3])
    arrow(inner, tuple(p), tuple(q), lw=2.6)
    screw_icon(ax, 0.85, 0.62, s=1.4, label='#6 ×2')
    screwdriver(ax, 0.80, 0.30, s=0.7)
    ax.text(0.5, 0.045, 'snug only — the pocket does the holding',
            fontsize=10, ha='center', color=INK, transform=ax.transAxes)
    pdf.savefig(fig); plt.close(fig)


def page_pinion_hang(pdf, cf, d):
    fig = plt.figure(figsize=A4)
    # step 3: pinion onto D-shaft
    ax = panel(fig, [0.06, 0.52, 0.88, 0.42])
    stepnum(ax, 3)
    inner = panel(fig, [0.08, 0.55, 0.56, 0.36], border=False)
    solids = [build_plate(d), build_motor_dummy(d), build_clamp(d),
              build_drive_pinion(d).translate([0, 0, 34])]
    sc = draw_scene(inner, solids, azim=-55, elev=42, lw=0.7, res=760)
    p = sc.project([d.cx, 0, cf.z_bot + 46])
    q = sc.project([d.cx, 0, cf.z_bot + 16])
    arrow(inner, tuple(p), tuple(q), lw=2.6)
    # detail circle: D-bore alignment
    det = panel(fig, [0.66, 0.62, 0.26, 0.184], border=False)
    det.add_patch(Circle((0.5, 0.5), 0.46, fill=False, color=INK, lw=1.8,
                         transform=det.transAxes))
    th = np.linspace(math.radians(50), math.radians(310), 60)
    r0 = 0.26
    det.plot(0.5 + r0 * np.cos(th), 0.5 + r0 * np.sin(th), color=INK, lw=2.6,
             transform=det.transAxes)
    ch = 0.5 + r0 * math.cos(th[0])
    det.add_line(Line2D([0.5 + r0 * math.cos(th[-1])] * 0 + [ch, ch],
                        [0.5 + r0 * math.sin(th[-1]), 0.5 + r0 * math.sin(th[0])],
                        color=INK, lw=2.6, transform=det.transAxes))
    det.text(0.5, 0.08, 'flat to flat', fontsize=9, ha='center', color=INK,
             transform=det.transAxes)
    det.set_xlim(0, 1); det.set_ylim(0, 1); det.axis('off')
    ax.text(0.5, 0.045, 'push on until the collar seats — no glue needed',
            fontsize=10, ha='center', color=INK, transform=ax.transAxes)
    # step 4: hang the plate on the bracket keyholes
    ax = panel(fig, [0.06, 0.05, 0.88, 0.42])
    stepnum(ax, 4)
    inner = panel(fig, [0.08, 0.08, 0.66, 0.36], border=False)
    solids = (drive_solids(d) + bracket_screws(d)
              + [wall_slab(d, half=90.0, cx=d.cx)])
    sc = draw_scene(inner, solids, azim=-75, elev=55, lw=0.7, res=760)
    ex = d.cx + d.key_len / 2
    for sy in (d.key_y, -d.key_y):
        p = sc.project([ex + 34, sy, d.z_front])
        q = sc.project([ex + 12, sy, d.z_front])
        arrow(inner, tuple(p), tuple(q), lw=2.2)
    ax.text(0.5, 0.13, 'hang on both screws · slide toward the centre · '
            'leave loose for now', fontsize=10, ha='center', color=INK,
            transform=ax.transAxes)
    ax.text(0.5, 0.05, 'bracket screws: #10-24 pan heads, 56 mm apart, '
            'heads 4 mm proud', fontsize=9, ha='center', color=INK,
            transform=ax.transAxes)
    pdf.savefig(fig); plt.close(fig)


def page_ring(pdf, cf, d):
    fig = plt.figure(figsize=A4)
    # step 5: dovetail two segments
    ax = panel(fig, [0.06, 0.52, 0.88, 0.42])
    stepnum(ax, 5)
    inner = panel(fig, [0.09, 0.55, 0.60, 0.37], border=False)
    seg0 = build_segment(cf)
    seg1 = rotated(seg0, 1, cf).translate([0, 0, 55.0])
    w0 = build_wafer(cf, 0)
    sc = draw_scene(inner, [seg0, w0, seg1], azim=-38, elev=26, lw=0.55,
                    res=820)
    a1 = 1.5 * cf.sector
    p = sc.project([cf.rho_c * math.cos(a1), cf.rho_c * math.sin(a1), 60])
    q = sc.project([cf.rho_c * math.cos(a1), cf.rho_c * math.sin(a1), 8])
    arrow(inner, tuple(p), tuple(q), lw=2.6)
    ax.text(0.83, 0.72, '×9', fontsize=22, fontweight='bold', ha='center',
            color=INK, transform=ax.transAxes)
    ax.text(0.5, 0.045, 'flat on the bench · slide straight down · '
            'edges only on the glass', fontsize=10, ha='center', color=INK,
            transform=ax.transAxes)
    # ring completion mini-sequence
    ax = panel(fig, [0.06, 0.05, 0.88, 0.42])
    for i, nseg in enumerate((3, 6, 9)):
        inner = panel(fig, [0.075 + i * 0.29, 0.10, 0.26, 0.30], border=False)
        solids = build_ring(cf, n=nseg)
        solids += [build_wafer(cf, k) for k in range(nseg)]
        draw_scene(inner, solids, azim=-90, elev=88, lw=0.4, res=560)
        inner.set_title(f'{nseg}/9', fontsize=11, color=INK)
    ax.text(0.5, 0.045, 'the last dovetail closes the circle — do not force; '
            'if it fights, a joint is not seated', fontsize=10, ha='center',
            color=INK, transform=ax.transAxes)
    pdf.savefig(fig); plt.close(fig)


def page_mount_mesh(pdf, cf, d):
    fig = plt.figure(figsize=A4)
    # step 6: ring onto its mount, meshing with the pinion
    ax = panel(fig, [0.06, 0.52, 0.88, 0.42])
    stepnum(ax, 6)
    inner = panel(fig, [0.08, 0.55, 0.64, 0.37], border=False)
    solids = build_ring(cf) + [build_wafer(cf, k) for k in range(cf.N)]
    solids += drive_solids(d) + [wall_slab(d)]
    sc = draw_scene(inner, solids, azim=-90, elev=62, lw=0.45, res=900)
    ax.text(0.5, 0.10, 'two people · hold by the frame, never the glass',
            fontsize=10, ha='center', color=INK, transform=ax.transAxes)
    ax.text(0.5, 0.04, 'ring support (rollers) per the traveler — this manual '
            'covers the drive', fontsize=8.5, ha='center', color=INK,
            transform=ax.transAxes)
    man_ax = panel(fig, [0.72, 0.80, 0.20, 0.12], border=False)
    man(man_ax, 0.30, 0.05, s=0.28, arms='up')
    man(man_ax, 0.70, 0.05, s=0.28, arms='up')
    man_ax.text(0.5, 0.85, '×2', fontsize=13, fontweight='bold', ha='center',
                color=INK, transform=man_ax.transAxes)
    # step 7: mesh close-up + backlash slide
    ax = panel(fig, [0.06, 0.05, 0.88, 0.42])
    stepnum(ax, 7)
    inner = panel(fig, [0.09, 0.09, 0.56, 0.34], border=False)
    ring_sector = [rotated(build_segment(cf), k, cf) for k in (8, 0)]
    solids = ring_sector + drive_solids(d)
    scz = Scene(solids, azim=-58, elev=24)
    c2 = scz.project([d.cx, 0, cf.z_bot])
    win = (c2[0] - 70, c2[0] + 70, c2[1] - 55, c2[1] + 55)
    draw_scene(inner, solids, azim=-58, elev=24, window=win, lw=0.8, res=820)
    p = scz.project([d.cx - 40, 0, cf.z_bot + 5])
    arrow(inner, (p[0] - 22, p[1]), (p[0] + 10, p[1]), lw=2.2)
    arrow(inner, (p[0] + 10, p[1] - 8), (p[0] - 22, p[1] - 8), lw=2.2)
    det = panel(fig, [0.68, 0.16, 0.24, 0.17], border=False)
    det.add_patch(Circle((0.5, 0.55), 0.42, fill=False, color=INK, lw=1.6,
                         transform=det.transAxes))
    det.text(0.5, 0.55, '~0.4 mm', fontsize=11, ha='center', color=INK,
             transform=det.transAxes)
    det.text(0.5, 0.02, 'a hair of backlash,\nnot a bite', fontsize=9,
             ha='center', color=INK, transform=det.transAxes)
    det.axis('off')
    ax.text(0.5, 0.045, 'slide the plate until the teeth just kiss, back off '
            'a hair, tighten both bracket screws', fontsize=10, ha='center',
            color=INK, transform=ax.transAxes)
    pdf.savefig(fig); plt.close(fig)


def page_spin(pdf, cf, d):
    fig = plt.figure(figsize=A4)
    # step 8: hand spin one full turn
    ax = panel(fig, [0.06, 0.52, 0.88, 0.42])
    stepnum(ax, 8)
    inner = panel(fig, [0.14, 0.55, 0.50, 0.37], border=False)
    solids = build_ring(cf) + [build_wafer(cf, k) for k in range(cf.N)]
    solids += drive_solids(d)
    draw_scene(inner, solids, azim=-90, elev=80, lw=0.4, res=820)
    arc_ax = panel(fig, [0.14, 0.55, 0.50, 0.37], border=False)
    arc_ax.add_patch(Arc((0.5, 0.5), 0.95, 0.95, theta1=-30, theta2=200,
                         lw=2.6, color=INK, transform=arc_ax.transAxes))
    axes_arrow(arc_ax, (0.5 + 0.475 * math.cos(math.radians(-25)),
                        0.5 + 0.475 * math.sin(math.radians(-25))),
               (0.5 + 0.475 * math.cos(math.radians(-32)),
                0.5 + 0.475 * math.sin(math.radians(-32))), lw=2.4)
    arc_ax.set_xlim(0, 1); arc_ax.set_ylim(0, 1); arc_ax.axis('off')
    ax.text(0.5, 0.045, 'one slow lap by hand — smooth everywhere, '
            'no clicks, no rubs', fontsize=10, ha='center', color=INK,
            transform=ax.transAxes)
    # step 9: power on
    ax = panel(fig, [0.06, 0.05, 0.88, 0.42])
    stepnum(ax, 9)
    inner = panel(fig, [0.10, 0.10, 0.44, 0.33], border=False)
    draw_scene(inner, solids, azim=-90, elev=75, lw=0.4, res=760)
    ax.add_patch(Circle((0.70, 0.62), 0.045, fill=False, color=INK, lw=2,
                        transform=ax.transAxes))
    ax.text(0.70, 0.62, '5V', fontsize=10, ha='center', va='center',
            color=INK, transform=ax.transAxes)
    ax.add_line(Line2D([0.70, 0.70, 0.62], [0.575, 0.45, 0.38], color=INK,
                       lw=2, transform=ax.transAxes))
    man_ax = panel(fig, [0.70, 0.12, 0.22, 0.24], border=False)
    man(man_ax, 0.5, 0.05, s=0.42, arms='up')
    ax.text(0.5, 0.045, '~1 rpm of quiet, self-holding rotation · done',
            fontsize=10, ha='center', color=INK, transform=ax.transAxes)
    pdf.savefig(fig); plt.close(fig)


def page_care(pdf, cf, d):
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.955, 'care', fontsize=18, fontweight='bold', color=INK)
    fig.add_artist(Line2D([0.06, 0.94], [0.945, 0.945], color=INK, lw=1.5,
                          transform=fig.transFigure))
    ax = panel(fig, [0.06, 0.62, 0.42, 0.28])
    ax.add_patch(Circle((0.42, 0.5), 0.10, fill=False, color=INK, lw=2.5,
                        transform=ax.transAxes))
    ax.add_line(Line2D([0.50, 0.72], [0.55, 0.68], color=INK, lw=2.5,
                       transform=ax.transAxes))
    for adx in (0.0, 0.06, 0.12):
        axes_arrow(ax, (0.74 + adx, 0.66), (0.86 + adx, 0.60), lw=1.6, mut=10)
    check_or_cross(ax, True)
    ax.text(0.5, 0.06, 'dust: blower only', fontsize=10, ha='center',
            color=INK, transform=ax.transAxes)
    ax = panel(fig, [0.52, 0.62, 0.42, 0.28])
    ax.add_line(Line2D([0.35, 0.55], [0.35, 0.65], color=INK, lw=8,
                       transform=ax.transAxes, solid_capstyle='round'))
    ax.add_line(Line2D([0.52, 0.62], [0.62, 0.72], color=INK, lw=3,
                       transform=ax.transAxes))
    check_or_cross(ax, False)
    ax.text(0.5, 0.06, 'no cloths, no sprays on the glass', fontsize=10,
            ha='center', color=INK, transform=ax.transAxes)
    ax = panel(fig, [0.06, 0.32, 0.88, 0.26])
    inner = panel(fig, [0.30, 0.345, 0.40, 0.21], border=False)
    solids = build_ring(cf) + [build_wafer(cf, k) for k in range(cf.N)]
    draw_scene(inner, solids, azim=-90, elev=88, lw=0.35, res=700)
    ax.text(0.5, 0.05, 'it is a mirror, a clock with no hands, and 4.5 kg of '
            'sand that went to college', fontsize=10, ha='center', color=INK,
            style='italic', transform=ax.transAxes)
    fig.text(0.5, 0.10, 'KISELRING  ·  wafer-flower', fontsize=11, ha='center',
             color=INK)
    fig.text(0.5, 0.075, 'scripts/manual_pdf.py regenerates this document '
             'from the CAD', fontsize=8, ha='center', color=INK)
    pdf.savefig(fig); plt.close(fig)


def main():
    if not HAVE_MANIFOLD:
        sys.exit("needs manifold3d:  pip install manifold3d")
    ap = argparse.ArgumentParser(description='KISELRING IKEA-style manual')
    ap.add_argument('-o', '--out', default=OUT)
    a = ap.parse_args()
    cf = Cfg(facets=256)
    d = Drive(cf)
    pages = [page_cover, page_warnings, page_parts, page_motor,
             page_pinion_hang, page_ring, page_mount_mesh, page_spin,
             page_care]
    with PdfPages(a.out) as pdf:
        for i, fn in enumerate(pages):
            print(f"  page {i + 1}/{len(pages)}  {fn.__name__}")
            fn(pdf, cf, d)
        info = pdf.infodict()
        info['Title'] = 'KISELRING — rotating silicon wafer halo, assembly manual'
        info['Author'] = 'wafer-flower'
    print(f"Wrote {a.out}  ({os.path.getsize(a.out) / 1024:.0f} kB)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
