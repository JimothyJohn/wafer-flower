#!/usr/bin/env python3
"""
Wafer Halo — KISELRING assembly manual (IKEA-style) -> docs/kiselring-manual.pdf.

REBUILT 2026-08-16 for the CANONICAL architecture (Nick: the old one
documented the parked motorised-spur concept — "rebuild the IKEA
instructions to be dramatically better"). Every 3D panel is line art
rendered from NICK'S REAL MESHES (stl/mine) + synthesised wafers:
orthographic projection, hidden lines removed with a triangle z-buffer,
silhouette + crease edges only — the IKEA look, from the actual parts.

Assembly story: tape a wafer to each tower (one landing) -> lap the nine
segments into a ring -> saddle + motor dock on the wall (25 mm grid) ->
ring rests in the saddle -> glue the pinion to the N20, dock the motor ->
USB power, one revolution every four minutes.

Needs numpy + matplotlib only (reads binary STLs itself; no CAD deps):
    python3 scripts/manual_pdf.py            # -> docs/kiselring-manual.pdf

Renderer gotchas inherited from the legacy manual (do not regress): skip
near-edge-on triangles before z-buffering (their barycentric z poisons
silhouettes into false dashes); scene z = wall normal, so wall-art views
want high elev / azim near -90.
"""

from __future__ import annotations
import math, os, struct, sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, Rectangle, FancyArrowPatch
from matplotlib.lines import Line2D

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "docs", "kiselring-manual.pdf")
MINE = os.path.join(REPO, "stl", "mine")

INK = "#1a1a1a"
A4 = (8.27, 11.69)

N, R, WR, WT, TILT = 9, 350.0, 150.0, 0.775, math.radians(3.0)
LAND_C, BOND = 38.8, 1.1
SEG = 2 * math.pi / N


# ----------------------------------------------------------------------------
# meshes: (V, T) numpy pairs
# ----------------------------------------------------------------------------
def stl_read(path):
    with open(path, "rb") as f:
        data = f.read()
    n = struct.unpack("<I", data[80:84])[0]
    raw = np.frombuffer(data[84 : 84 + n * 50], dtype=np.uint8).reshape(n, 50)
    tris = raw[:, 12:48].copy().view("<f4").reshape(n * 3, 3).astype(float)
    V, inv = np.unique(np.round(tris, 4), axis=0, return_inverse=True)
    return V, inv.reshape(n, 3)


def tx(mesh, M=None, t=(0, 0, 0)):
    V, T = mesh
    V2 = V @ np.array(M).T if M is not None else V.copy()
    return V2 + np.array(t, float), T


def rotz(mesh, ang):
    c, s = math.cos(ang), math.sin(ang)
    return tx(mesh, [[c, -s, 0], [s, c, 0], [0, 0, 1]])


def disc(r, t, nseg=96):
    """Closed cylinder (a wafer)."""
    a = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    ring0 = np.stack([r * np.cos(a), r * np.sin(a), np.zeros(nseg)], 1)
    V = np.vstack([ring0, ring0 + [0, 0, t], [[0, 0, 0]], [[0, 0, t]]])
    lo, hi = 2 * nseg, 2 * nseg + 1
    T = []
    for i in range(nseg):
        j = (i + 1) % nseg
        T += [
            (i, j, nseg + j),
            (i, nseg + j, nseg + i),
            (j, i, lo),
            (nseg + i, nseg + j, hi),
        ]
    return V, np.array(T)


def boxm(x0, x1, y0, y1, z0, z1):
    V = np.array(
        [[x, y, z] for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)], float
    )
    Q = [
        (0, 1, 3, 2),
        (4, 6, 7, 5),
        (0, 4, 5, 1),
        (2, 3, 7, 6),
        (0, 2, 6, 4),
        (1, 5, 7, 3),
    ]
    T = []
    for a, b, c, d in Q:
        T += [(a, b, c), (a, c, d)]
    return V, np.array(T)


def cyl(r, L, axis="y", nseg=32):
    """Cylinder from origin along +axis (a motor body / shaft)."""
    a = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    ring = np.stack([r * np.cos(a), r * np.sin(a), np.zeros(nseg)], 1)
    V = np.vstack([ring, ring + [0, 0, L], [[0, 0, 0]], [[0, 0, L]]])
    lo, hi = 2 * nseg, 2 * nseg + 1
    T = []
    for i in range(nseg):
        j = (i + 1) % nseg
        T += [
            (i, j, nseg + j),
            (i, nseg + j, nseg + i),
            (j, i, lo),
            (nseg + i, nseg + j, hi),
        ]
    m = (np.array(V), np.array(T))
    if axis == "y":
        m = tx(m, [[1, 0, 0], [0, 0, 1], [0, -1, 0]])
    elif axis == "x":
        m = tx(m, [[0, 0, 1], [0, 1, 0], [-1, 0, 0]])
    return m


def wafer(k=0):
    m = disc(WR, WT)
    c, s = math.cos(TILT), math.sin(TILT)
    m = tx(m, [[1, 0, 0], [0, c, -s], [0, s, c]])  # tilt about radial x
    m = tx(m, t=(R, 0, LAND_C + BOND + WT / 2))
    return rotz(m, k * SEG)


_SEG = stl_read(os.path.join(MINE, "Segment - segment.stl"))
_PIN = stl_read(os.path.join(MINE, "Segment - pinion.stl"))
_MNT = stl_read(os.path.join(MINE, "MotorDoc - motorMount.stl"))
_BND = stl_read(os.path.join(MINE, "MotorDoc - mountingBand.stl"))
_SDL = stl_read(os.path.join(MINE, "BottomStaticBracket - staticBracket.stl"))


def segment(k=0):
    return rotz(_SEG, k * SEG)


def pinion_at_top():
    return rotz(_PIN, math.pi / 2)


def saddle_at_bottom():
    # export frame: x tangential, y wall depth (-12..0), z radial (290..343)
    return tx(_SDL, [[1, 0, 0], [0, 0, -1], [0, -1, 0]])


def dock_at_top():
    # plate: x across, y thickness (5..11), z vertical (-62..12)
    return tx(_MNT, [[1, 0, 0], [0, 0, 1], [0, 1, 0]], t=(0, 345, -5))


def band_at_top():
    return tx(_BND, [[1, 0, 0], [0, 0, 1], [0, 1, 0]], t=(0, 345, 8))


def n20_at_top():
    body = tx(boxm(-6, 6, 0, 24, 0, 10), t=(0, 352, 14))
    shaft = tx(cyl(1.5, 10, axis="y"), t=(0, 342, 19))
    return [body, shaft]


def wall(half=430.0):
    return boxm(-half, half, -half, half, -8.0, -2.0)


# ----------------------------------------------------------------------------
# 3D -> 2D line-art renderer (ported from the legacy manual — proven)
# ----------------------------------------------------------------------------
def view_basis(azim, elev):
    a, e = math.radians(azim), math.radians(elev)
    f = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
    r = np.cross([0.0, 0.0, 1.0], f)
    r = r / (np.linalg.norm(r) or 1.0)
    u = np.cross(f, r)
    return np.array([r, u, f])


class Scene:
    def __init__(self, meshes, azim=-55.0, elev=18.0, crease_deg=25.0):
        self.M = view_basis(azim, elev)
        VV, TT, off = [], [], 0
        for V, T in meshes:
            VV.append(V)
            TT.append(np.asarray(T) + off)
            off += len(V)
        self.V = np.vstack(VV)
        self.T = np.vstack(TT).astype(np.int64)
        self.P = self.V @ self.M.T
        self.crease = math.cos(math.radians(crease_deg))

    def bounds(self):
        return (
            self.P[:, 0].min(),
            self.P[:, 0].max(),
            self.P[:, 1].min(),
            self.P[:, 1].max(),
        )

    def edges(self, window=None, res=900):
        P, T = self.P, self.T
        if window is None:
            x0, x1, y0, y1 = self.bounds()
            m = 0.03 * max(x1 - x0, y1 - y0)
            window = (x0 - m, x1 + m, y0 - m, y1 + m)
        x0, x1, y0, y1 = window
        scale = res / max(x1 - x0, y1 - y0)
        W, H = int((x1 - x0) * scale) + 2, int((y1 - y0) * scale) + 2
        tv = P[T]
        n = np.cross(tv[:, 1] - tv[:, 0], tv[:, 2] - tv[:, 0])
        area2 = n[:, 2]
        zb = np.full((H, W), -1e18)
        xs = (tv[:, :, 0] - x0) * scale
        ys = (tv[:, :, 1] - y0) * scale
        for i in np.argsort(tv[:, :, 2].max(axis=1)):
            if abs(area2[i]) < 1e-4:
                continue  # edge-on: poisons silhouettes
            X, Y = xs[i], ys[i]
            lox, hix = int(max(0, X.min())), int(min(W - 1, X.max()) + 1)
            loy, hiy = int(max(0, Y.min())), int(min(H - 1, Y.max()) + 1)
            if lox >= hix or loy >= hiy:
                continue
            gx, gy = np.meshgrid(np.arange(lox, hix) + 0.5, np.arange(loy, hiy) + 0.5)
            d = np.stack(
                [
                    (X[(k + 1) % 3] - X[k]) * (gy - Y[k])
                    - (Y[(k + 1) % 3] - Y[k]) * (gx - X[k])
                    for k in range(3)
                ]
            )
            inside = (d >= -1e-9).all(axis=0) | (d <= 1e-9).all(axis=0)
            if not inside.any():
                continue
            v0, v1, v2 = tv[i]
            det = area2[i]
            l1 = (
                (gx / scale + x0 - v0[0]) * (v2[1] - v0[1])
                - (gy / scale + y0 - v0[1]) * (v2[0] - v0[0])
            ) / -det
            l2 = (
                (gy / scale + y0 - v0[1]) * (v1[0] - v0[0])
                - (gx / scale + x0 - v0[0]) * (v1[1] - v0[1])
            ) / -det
            z = np.clip(
                v0[2] + l1 * (v1[2] - v0[2]) + l2 * (v2[2] - v0[2]),
                tv[i, :, 2].min(),
                tv[i, :, 2].max(),
            )
            sub = zb[loy:hiy, lox:hix]
            upd = inside & (z > sub)
            sub[upd] = z[upd]
        emap = {}
        for ti, (a, b, c) in enumerate(T):
            for e in ((a, b), (b, c), (c, a)):
                emap.setdefault((min(e), max(e)), []).append(ti)
        wn = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-30)
        segs = []
        tol = max(2.0, 0.004 * float(np.ptp(self.P[:, 2])))
        for (a, b), tris in emap.items():
            if len(tris) == 2:
                t1, t2 = tris
                if (area2[t1] > 0) == (area2[t2] > 0) and np.dot(
                    wn[t1], wn[t2]
                ) > self.crease:
                    continue
            pa, pb = P[a], P[b]
            L = np.linalg.norm(pb[:2] - pa[:2])
            if L * scale < 1.0:
                continue
            ns = max(4, min(64, int(L * scale / 6)))
            t = np.linspace(0.0, 1.0, ns + 1)
            px, py = pa[0] + t * (pb[0] - pa[0]), pa[1] + t * (pb[1] - pa[1])
            pz = pa[2] + t * (pb[2] - pa[2])
            ix = ((px - x0) * scale).astype(int).clip(0, W - 1)
            iy = ((py - y0) * scale).astype(int).clip(0, H - 1)
            vis = pz >= zb[iy, ix] - tol
            run = None
            for k in range(ns + 1):
                if vis[k] and run is None:
                    run = k
                if (not vis[k] or k == ns) and run is not None:
                    if k > run:
                        segs.append(((px[run], py[run]), (px[k], py[k])))
                    run = None
        return segs, window

    def project(self, xyz):
        return (np.array(xyz, float) @ self.M.T)[:2]


def draw_scene(ax, meshes, azim=-55.0, elev=18.0, window=None, lw=0.9, res=900):
    sc = Scene(meshes, azim, elev)
    segs, window = sc.edges(window=window, res=res)
    for p, q in segs:
        ax.plot([p[0], q[0]], [p[1], q[1]], color=INK, lw=lw, solid_capstyle="round")
    ax.set_xlim(window[0], window[1])
    ax.set_ylim(window[2], window[3])
    ax.set_aspect("equal")
    ax.axis("off")
    return sc


# ----------------------------------------------------------------------------
# pictograms (legacy, proven)
# ----------------------------------------------------------------------------
def man(ax, x, y, s=1.0, arms="down", happy=True):
    lw = 2.2 * s * 3
    ax.add_patch(
        Circle(
            (x, y + 0.78 * s),
            0.11 * s,
            fill=False,
            color=INK,
            lw=lw,
            transform=ax.transAxes,
        )
    )
    line = lambda xs, ys: ax.add_line(
        Line2D(
            [x + a * s for a in xs],
            [y + b * s for b in ys],
            color=INK,
            lw=lw,
            solid_capstyle="round",
            transform=ax.transAxes,
        )
    )
    line([0, 0], [0.67, 0.30])
    line([0, -0.13], [0.30, 0.0])
    line([0, 0.13], [0.30, 0.0])
    if arms == "up":
        line([0, -0.18], [0.60, 0.78])
        line([0, 0.18], [0.60, 0.78])
    else:
        line([0, -0.15], [0.60, 0.40])
        line([0, 0.15], [0.60, 0.40])
    if not happy:
        ax.text(
            x + 0.26 * s,
            y + 0.88 * s,
            "?",
            fontsize=26 * s * 3,
            color=INK,
            fontweight="bold",
            transform=ax.transAxes,
            ha="center",
        )


def stepnum(ax, n, x=0.06, y=0.90):
    ax.add_patch(
        Circle((x, y), 0.055, fill=False, color=INK, lw=2.2, transform=ax.transAxes)
    )
    ax.text(
        x,
        y,
        str(n),
        fontsize=20,
        fontweight="bold",
        ha="center",
        va="center",
        color=INK,
        transform=ax.transAxes,
    )


def panel(fig, rect, border=True):
    ax = fig.add_axes(rect)
    ax.set_xticks([])
    ax.set_yticks([])
    if border:
        for sp in ax.spines.values():
            sp.set_linewidth(1.4)
            sp.set_color(INK)
    else:
        ax.axis("off")
    return ax


def arrow(ax, p, q, lw=2.4, mut=16, axes=False):
    kw = dict(
        arrowstyle="-|>", mutation_scale=mut, lw=lw, color=INK, shrinkA=0, shrinkB=0
    )
    if axes:
        kw["transform"] = ax.transAxes
    ax.add_patch(FancyArrowPatch(p, q, **kw))


def nope(ax, x, y, s=0.09):
    ax.add_patch(
        Circle((x, y), s, fill=False, color=INK, lw=3.0, transform=ax.transAxes)
    )
    ax.add_line(
        Line2D(
            [x - s * 0.7, x + s * 0.7],
            [y - s * 0.7, y + s * 0.7],
            color=INK,
            lw=3.0,
            transform=ax.transAxes,
        )
    )


def count(ax, n, x=0.86, y=0.10):
    ax.text(
        x,
        y,
        f"×{n}",
        fontsize=17,
        fontweight="bold",
        color=INK,
        ha="center",
        transform=ax.transAxes,
    )


# ----------------------------------------------------------------------------
# pages
# ----------------------------------------------------------------------------
def ring_meshes(nseg=N, wafers=True):
    ms = [segment(k) for k in range(nseg)]
    if wafers:
        ms += [wafer(k) for k in range(nseg)]
    return ms


def page_cover(pdf):
    fig = plt.figure(figsize=A4)
    ax = panel(fig, [0.07, 0.40, 0.86, 0.47], border=False)
    draw_scene(ax, ring_meshes(), azim=-78, elev=48, lw=0.7, res=1100)
    t = fig.add_axes([0, 0, 1, 1])
    t.axis("off")
    t.text(
        0.07,
        0.945,
        "KISELRING",
        fontsize=54,
        fontweight="bold",
        color=INK,
        family="DejaVu Sans",
    )
    t.text(
        0.07,
        0.905,
        "kinetic wall piece · nine silicon mirrors · one slow revolution",
        fontsize=13,
        color=INK,
    )
    t.text(
        0.07,
        0.335,
        "9 × Ø300 mm silicon  ·  9 printed towers  ·  1 motor  ·  0 visible hardware",
        fontsize=11,
        color=INK,
        family="monospace",
    )
    t.text(
        0.07,
        0.305,
        "assembly ≈ 45 min  ·  two people for the hang  ·  USB-C power",
        fontsize=11,
        color=INK,
        family="monospace",
    )
    man(t, 0.85, 0.13, 0.10, arms="up")
    t.text(
        0.07,
        0.06,
        "wafer-flower · KISELRING v2 · the canonical build (stl/mine)",
        fontsize=8,
        color=INK,
        family="monospace",
    )
    pdf.savefig(fig)
    plt.close(fig)


def page_rules(pdf):
    fig = plt.figure(figsize=A4)
    t = fig.add_axes([0, 0, 1, 1])
    t.axis("off")
    t.text(
        0.5,
        0.95,
        "READ ME, THEN BREATHE",
        fontsize=22,
        fontweight="bold",
        ha="center",
        color=INK,
    )
    # 1: edges only
    ax = panel(fig, [0.08, 0.64, 0.38, 0.24])
    d = panel(fig, [0.08, 0.64, 0.38, 0.24], border=False)
    draw_scene(ax, [disc(WR, WT)], azim=-60, elev=32, lw=0.8)
    arrow(ax := d, (0.15, 0.5), (0.32, 0.5), axes=True)
    d.text(
        0.5,
        0.06,
        "mirrors: EDGES ONLY · never flex",
        fontsize=10,
        ha="center",
        color=INK,
        transform=d.transAxes,
    )
    # 2: one landing
    ax = panel(fig, [0.54, 0.64, 0.38, 0.24])
    m2 = wafer(0)
    ax2 = panel(fig, [0.54, 0.64, 0.38, 0.24], border=False)
    draw_scene(ax, [segment(0), tx(m2, t=(0, 0, 55))], azim=-35, elev=16, lw=0.7)
    nope(ax2, 0.82, 0.78)
    ax2.text(
        0.82,
        0.62,
        "no do-overs",
        fontsize=9,
        ha="center",
        color=INK,
        transform=ax2.transAxes,
    )
    ax2.text(
        0.5,
        0.06,
        "tape bonds ONCE — the wafer lands and stays",
        fontsize=10,
        ha="center",
        color=INK,
        transform=ax2.transAxes,
    )
    # 3: IPA yes, acetone no
    d = panel(fig, [0.08, 0.36, 0.38, 0.24])
    d.text(
        0.5,
        0.62,
        "IPA ✓",
        fontsize=26,
        fontweight="bold",
        ha="center",
        color=INK,
        transform=d.transAxes,
    )
    d.text(
        0.5,
        0.34,
        "acetone ✗",
        fontsize=18,
        ha="center",
        color=INK,
        transform=d.transAxes,
    )
    d.text(
        0.5,
        0.08,
        "clean prints with alcohol — acetone eats PLA",
        fontsize=10,
        ha="center",
        color=INK,
        transform=d.transAxes,
    )
    # 4: cure the glue
    d = panel(fig, [0.54, 0.36, 0.38, 0.24])
    d.text(
        0.5,
        0.60,
        "glue tonight",
        fontsize=16,
        fontweight="bold",
        ha="center",
        color=INK,
        transform=d.transAxes,
    )
    d.text(
        0.5,
        0.42,
        "spin tomorrow",
        fontsize=16,
        fontweight="bold",
        ha="center",
        color=INK,
        transform=d.transAxes,
    )
    d.text(
        0.5,
        0.10,
        "pinion epoxy/CA takes the stall torque — full cure first",
        fontsize=10,
        ha="center",
        color=INK,
        transform=d.transAxes,
    )
    man(t, 0.28, 0.10, 0.10)
    man(t, 0.72, 0.10, 0.10, happy=False)
    t.text(
        0.5,
        0.045,
        "two people for the hang. one for everything else.",
        fontsize=11,
        ha="center",
        color=INK,
    )
    pdf.savefig(fig)
    plt.close(fig)


def page_parts(pdf):
    fig = plt.figure(figsize=A4)
    t = fig.add_axes([0, 0, 1, 1])
    t.axis("off")
    t.text(
        0.5, 0.95, "IN THE BOX", fontsize=22, fontweight="bold", ha="center", color=INK
    )
    cells = [
        ([segment(0)], 9, "tower segment", -35, 20),
        ([disc(WR, WT)], 9, "Ø300 silicon mirror", -60, 40),
        ([_PIN], 1, "12T pinion", -90, 4),
        ([_MNT], 1, "motor dock", -55, 16),
        ([_BND], 1, "motor band", -55, 26),
        ([_SDL], 1, "saddle", -55, 20),
    ]
    grid = [
        (0.07, 0.62),
        (0.52, 0.62),
        (0.07, 0.40),
        (0.52, 0.40),
        (0.07, 0.18),
        (0.52, 0.18),
    ]
    for (ms, n, label, azv, elv), (gx, gy) in zip(cells, grid):
        ax = panel(fig, [gx, gy, 0.41, 0.20])
        draw_scene(ax, ms, azim=azv, elev=elv, lw=0.8, res=700)
        ov = panel(fig, [gx, gy, 0.41, 0.20], border=False)
        count(ov, n)
        ov.text(0.05, 0.08, label, fontsize=10, color=INK, transform=ov.transAxes)
    t.text(
        0.07,
        0.115,
        "also: N20 motor (6 V · 15 rpm) ×1 · M5 flathead ×4 · M5 square nut ×4",
        fontsize=11,
        color=INK,
        family="monospace",
    )
    t.text(
        0.07,
        0.085,
        "acrylic foam tape · CA glue · USB-C cable · drywall anchors or a stud",
        fontsize=11,
        color=INK,
        family="monospace",
    )
    pdf.savefig(fig)
    plt.close(fig)


def page_tape(pdf):
    fig = plt.figure(figsize=A4)
    t = fig.add_axes([0, 0, 1, 1])
    t.axis("off")
    ax = panel(fig, [0.08, 0.30, 0.84, 0.56])
    w = tx(wafer(0), t=(0, 0, 70))
    sc = draw_scene(ax, [segment(0), w], azim=-28, elev=14, lw=0.8, res=1000)
    p_land = sc.project((330, 0, 45))
    p_waf = sc.project((350, 0, 95))
    arrow(ax, (p_waf[0], p_waf[1]), (p_land[0], p_land[1] + 12), lw=3.0, mut=22)
    ov = panel(fig, [0.08, 0.30, 0.84, 0.56], border=False)
    stepnum(ov, 1)
    count(ov, 9, x=0.90, y=0.90)
    ov.text(
        0.72,
        0.16,
        "tape pads on the tower top\nliners off · then the mirror",
        fontsize=10,
        color=INK,
        transform=ov.transAxes,
    )
    nope(ov, 0.14, 0.20)
    ov.text(
        0.14,
        0.08,
        "no sliding after touchdown",
        fontsize=9,
        ha="center",
        color=INK,
        transform=ov.transAxes,
    )
    t.text(
        0.5, 0.22, "ONE LANDING", fontsize=20, fontweight="bold", ha="center", color=INK
    )
    t.text(
        0.5,
        0.185,
        "lower by the edges, centred over the pad — gravity does the rest",
        fontsize=11,
        ha="center",
        color=INK,
    )
    man(t, 0.88, 0.06, 0.09)
    pdf.savefig(fig)
    plt.close(fig)


def page_ring(pdf):
    fig = plt.figure(figsize=A4)
    t = fig.add_axes([0, 0, 1, 1])
    t.axis("off")
    ax = panel(fig, [0.08, 0.52, 0.84, 0.36])
    s0 = segment(0)
    s1 = rotz(
        tx(rotz(_SEG, 0), t=(0, 60, 0)), SEG
    )  # neighbour, offset along its slide-in
    sc = draw_scene(ax, [s0, s1], azim=-30, elev=24, lw=0.8, res=1000)
    a0, a1 = (
        sc.project((335 * math.cos(SEG / 2), 335 * math.sin(SEG / 2) + 55, 6)),
        sc.project((335 * math.cos(SEG / 2), 335 * math.sin(SEG / 2) + 8, 6)),
    )
    arrow(ax, tuple(a0), tuple(a1), lw=3.0, mut=22)
    ov = panel(fig, [0.08, 0.52, 0.84, 0.36], border=False)
    stepnum(ov, 2)
    ov.text(
        0.70,
        0.10,
        "lap tab into pocket — slide until flush",
        fontsize=10,
        color=INK,
        transform=ov.transAxes,
    )
    ax2 = panel(fig, [0.22, 0.12, 0.56, 0.34])
    draw_scene(ax2, ring_meshes(wafers=False), azim=-78, elev=55, lw=0.6, res=900)
    ov2 = panel(fig, [0.22, 0.12, 0.56, 0.34], border=False)
    count(ov2, 9, x=0.88, y=0.86)
    t.text(
        0.5,
        0.085,
        "nine laps close the circle — mirrors face the room",
        fontsize=11,
        ha="center",
        color=INK,
    )
    pdf.savefig(fig)
    plt.close(fig)


def page_wall(pdf):
    fig = plt.figure(figsize=A4)
    t = fig.add_axes([0, 0, 1, 1])
    t.axis("off")
    # 2D wall with two 3D insets — a giant 3D wall slab flattens the view
    w = panel(fig, [0.14, 0.26, 0.72, 0.62], border=False)
    w.add_patch(Rectangle((0.02, 0.02), 0.96, 0.96, fill=False, color=INK,
                          lw=2.0, linestyle=(0, (6, 4)), transform=w.transAxes))
    ax1 = panel(fig, [0.30, 0.60, 0.40, 0.24], border=False)
    draw_scene(ax1, [dock_at_top(), band_at_top()], azim=-70, elev=24,
               lw=0.8, res=800)
    ax2 = panel(fig, [0.32, 0.30, 0.36, 0.20], border=False)
    draw_scene(ax2, [saddle_at_bottom()], azim=-70, elev=24, lw=0.8, res=700)
    ov = panel(fig, [0.14, 0.26, 0.72, 0.62], border=False)
    stepnum(ov, 3, x=0.08, y=0.92)
    ov.add_line(Line2D([0.5, 0.5], [0.56, 0.50], color=INK, lw=1.2,
                       linestyle=":", transform=ov.transAxes))
    ov.text(0.54, 0.53, "≈ 700 mm", fontsize=10, color=INK,
            family="monospace", transform=ov.transAxes)
    ov.text(0.5, 0.88, "motor dock — up top, level", fontsize=10, ha="center",
            color=INK, transform=ov.transAxes)
    ov.text(0.5, 0.26, "saddle — straight below it", fontsize=10, ha="center",
            color=INK, transform=ov.transAxes)
    ov.text(0.5, 0.06, "4 × M5 into square nuts · anchors, or a stud (better)",
            fontsize=10, ha="center", color=INK, transform=ov.transAxes)
    t.text(0.5, 0.20, "THE WALL CARRIES EVERYTHING", fontsize=18,
           fontweight="bold", ha="center", color=INK)
    t.text(0.5, 0.165, "two mounts on the 25 mm grid — nothing else ever touches the wall",
           fontsize=11, ha="center", color=INK)
    man(t, 0.88, 0.05, 0.09)
    pdf.savefig(fig)
    plt.close(fig)


def page_hang(pdf):
    fig = plt.figure(figsize=A4)
    t = fig.add_axes([0, 0, 1, 1])
    t.axis("off")
    ax = panel(fig, [0.10, 0.30, 0.80, 0.58], border=False)
    ms = ring_meshes() + [saddle_at_bottom()]
    sc = draw_scene(ax, ms, azim=-90, elev=84, lw=0.6, res=1100)
    p0 = sc.project((0, 0, 260))
    p1 = sc.project((0, 0, 60))
    ov = panel(fig, [0.10, 0.30, 0.80, 0.58], border=False)
    stepnum(ov, 4, x=0.06, y=0.92)
    arrow(ov, (0.5, 0.98), (0.5, 0.80), lw=3.2, mut=24, axes=True)
    ov.text(0.5, 0.02, "lower the ring into the saddle — it rests, nothing clamps",
            fontsize=11, ha="center", color=INK, transform=ov.transAxes)
    t.text(0.5, 0.22, "TWO PEOPLE. MIRROR EDGES ONLY.", fontsize=18,
           fontweight="bold", ha="center", color=INK)
    man(t, 0.30, 0.06, 0.09)
    man(t, 0.70, 0.06, 0.09)
    pdf.savefig(fig)
    plt.close(fig)


def page_motor(pdf):
    fig = plt.figure(figsize=A4)
    t = fig.add_axes([0, 0, 1, 1])
    t.axis("off")
    ax = panel(fig, [0.08, 0.44, 0.84, 0.42])
    ms = [pinion_at_top(), dock_at_top(), band_at_top()] + n20_at_top()
    draw_scene(ax, ms, azim=-60, elev=22, lw=0.8, res=1000)
    ov = panel(fig, [0.08, 0.44, 0.84, 0.42], border=False)
    stepnum(ov, 5)
    ov.text(0.64, 0.84, "one drop of glue on the shaft\npinion on · cure overnight",
            fontsize=10, color=INK, transform=ov.transAxes)
    ov.text(0.10, 0.14, "motor into the dock\nband over · two screws",
            fontsize=10, color=INK, transform=ov.transAxes)
    d = panel(fig, [0.20, 0.13, 0.60, 0.24])
    d.text(0.5, 0.66, "teeth touch — no squeeze", fontsize=14,
           fontweight="bold", ha="center", color=INK, transform=d.transAxes)
    d.text(0.5, 0.36, "slide the dock until the pinion just meshes the rim,\nthen tighten. it should spin by finger, silently.",
           fontsize=10, ha="center", color=INK, transform=d.transAxes)
    t.text(0.5, 0.075, "the joint sees full stall torque at takeoff — cure before power",
           fontsize=11, ha="center", color=INK)
    pdf.savefig(fig)
    plt.close(fig)


def page_spin(pdf):
    fig = plt.figure(figsize=A4)
    t = fig.add_axes([0, 0, 1, 1])
    t.axis("off")
    ax = panel(fig, [0.10, 0.34, 0.80, 0.52], border=False)
    draw_scene(ax, ring_meshes(), azim=-90, elev=74, lw=0.6, res=1100)
    ov = panel(fig, [0.10, 0.34, 0.80, 0.52], border=False)
    stepnum(ov, 6)
    ar = FancyArrowPatch(
        (0.30, 0.94),
        (0.70, 0.94),
        transform=ov.transAxes,
        arrowstyle="-|>",
        mutation_scale=22,
        lw=2.6,
        color=INK,
        connectionstyle="arc3,rad=-0.35",
    )
    ov.add_patch(ar)
    t.text(
        0.5,
        0.27,
        "PLUG IN. WALK AWAY.",
        fontsize=24,
        fontweight="bold",
        ha="center",
        color=INK,
    )
    t.text(
        0.5,
        0.225,
        "USB power · one revolution every four minutes · forever",
        fontsize=12,
        ha="center",
        color=INK,
    )
    man(t, 0.5, 0.06, 0.11, arms="up")
    pdf.savefig(fig)
    plt.close(fig)


def main():
    with PdfPages(OUT) as pdf:
        for page in (
            page_cover,
            page_rules,
            page_parts,
            page_tape,
            page_ring,
            page_wall,
            page_hang,
            page_motor,
            page_spin,
        ):
            print(" ", page.__name__)
            page(pdf)
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
