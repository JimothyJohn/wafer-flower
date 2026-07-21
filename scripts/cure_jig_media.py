#!/usr/bin/env python3
"""Render cure-jig instruction media (PNGs + MP4s) from the CAD into docs/media/."""
import sys, os, math
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'scripts'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from segment_stl import Cfg, build_segment, build_wafer, prism, Manifold
from cure_jig_stl import Jig, build_outboard, build_inboard, build_hardware, xcyl

OUT = os.path.join(REPO, 'docs', 'media')
os.makedirs(OUT, exist_ok=True)

cf = Cfg(facets=128)
j = Jig(cf)

def tris(s):
    m = s.to_mesh()
    V = np.array([v[:3] for v in m.vert_properties])
    return V[np.array(m.tri_verts)]

def hexc(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i+2], 16) / 255 for i in (0, 2, 4)])

# ---- bodies -----------------------------------------------------------------
seg  = build_segment(cf)
waf  = build_wafer(cf, 0)
fout = build_outboard(j)
fin  = build_inboard(j)
rod, nut, washer, wnut, rod_len = build_hardware(j)

# glue: two squashed beads in the adhesive pocket near the land centroid
def bead(x):
    zl = -cf.landOff - cf.pocket_d          # pocket floor at y=0
    return Manifold.sphere(5.0, 48).scale([1.2, 1.2, 0.30]).translate([x, 0, zl + 0.4])
glue = bead(262.0) + bead(279.0)

C = dict(seg='#B9C0C7', waf='#8FB7E8', out='#1E9E8E', fin='#4457C4',
         rod='#2A2E33', nut='#7A4FC0', washer='#C2497B', wnut='#C2497B',
         glue='#C9A227', bench='#E8ECEF')

BODY = {k: tris(v) for k, v in dict(seg=seg, waf=waf, out=fout, fin=fin, rod=rod,
                                    nut=nut, washer=washer, wnut=wnut, glue=glue).items()}

# bench: grid of quads (small tiles sort better than one huge quad)
def bench_tris():
    z = cf.z_bot - 0.15
    xs = np.linspace(120, 590, 13); ys = np.linspace(-240, 240, 13)
    T = []
    for i in range(12):
        for k in range(12):
            a = (xs[i], ys[k], z); b = (xs[i+1], ys[k], z)
            c = (xs[i+1], ys[k+1], z); d = (xs[i], ys[k+1], z)
            T += [(a, b, c), (a, c, d)]
    return np.array(T)
BENCH = bench_tris()

LIGHT = np.array([0.35, -0.30, 0.89]); LIGHT /= np.linalg.norm(LIGHT)

def shade(T, base):
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    ln = np.linalg.norm(n, axis=1); ln[ln == 0] = 1
    lam = np.abs(n @ LIGHT) / ln
    col = base[None, :] * (0.42 + 0.58 * lam[:, None])
    return np.clip(col, 0, 1)

def render(ax, parts, elev=26, azim=-58, box=((120, 590), (-240, 240), (-30, 90)),
           bench=True):
    """parts: list of (key, offset_xyz). One merged collection -> good sorting."""
    allT, allC = [], []
    if bench:
        allT.append(BENCH); allC.append(np.tile(hexc(C['bench']) * 0.985, (len(BENCH), 1)))
    for key, off in parts:
        T = BODY[key] + np.asarray(off)[None, None, :]
        allT.append(T); allC.append(shade(T, hexc(C[key])))
    T = np.concatenate(allT); Ccol = np.concatenate(allC)
    pc = Poly3DCollection(T, facecolors=Ccol, edgecolor='none')
    ax.add_collection3d(pc)
    (x0, x1), (y0, y1), (z0, z1) = box
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_zlim(z0, z1)
    ax.set_box_aspect((x1 - x0, y1 - y0, (z1 - z0) * 1.9))
    ax.set_proj_type('ortho'); ax.view_init(elev=elev, azim=azim); ax.set_axis_off()

def still(path, parts, labels=(), labels2d=(), **kw):
    fig = plt.figure(figsize=(9.6, 6.4))
    ax = fig.add_subplot(111, projection='3d')
    render(ax, parts, **kw)
    for txt, (x, y, z) in labels:
        ax.text(x, y, z, txt, fontsize=11, fontweight='bold', color='#23272B',
                ha='center', bbox=dict(boxstyle='round,pad=0.28', fc='white',
                                       ec='#B9C0C7', alpha=0.92))
    for txt, (u, v) in labels2d:
        ax.text2D(u, v, txt, transform=ax.transAxes, fontsize=11,
                  fontweight='bold', color='#23272B', ha='center',
                  bbox=dict(boxstyle='round,pad=0.28', fc='white',
                            ec='#B9C0C7', alpha=0.92))
    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(os.path.join(OUT, path), dpi=105, facecolor='#FAFBFC')
    plt.close(fig)
    print('still', path)

Z = (0, 0, 0)
ASSEMBLED = [('seg', Z), ('glue', Z), ('waf', Z), ('out', Z), ('fin', Z),
             ('rod', Z), ('nut', Z), ('washer', Z), ('wnut', Z)]

# ---- stills -----------------------------------------------------------------
still('hero.png', ASSEMBLED)
still('step1_segment.png', [('seg', Z)],
      labels2d=[('keyhole faces you', (0.50, 0.20))],
      box=((180, 400), (-160, 160), (-30, 60)), azim=-40)
still('step2_glue.png', [('seg', Z), ('glue', Z)],
      labels=[('two short beads, in the pocket', (270, -110, 40))],
      box=((190, 360), (-140, 140), (-30, 55)), elev=38, azim=-52)
still('step3_wafer.png', [('seg', Z), ('glue', Z), ('waf', (0, 0, 26))],
      labels2d=[('set it down close - the jig centres it', (0.50, 0.82))],
      elev=22)
still('step4_outboard.png',
      [('seg', Z), ('glue', Z), ('waf', Z), ('out', (52, 0, 0))],
      labels2d=[('slide in until it stops', (0.80, 0.30))], azim=-50)
still('step5_inboard.png',
      [('seg', Z), ('glue', Z), ('waf', Z), ('out', Z),
       ('fin', (-52, 0, 0)), ('nut', (-70, 0, 0))],
      labels2d=[('nut drops in the tower', (0.24, 0.26)),
                ('slide in from the middle', (0.70, 0.76))], azim=-115)
still('step6_rod.png',
      [('seg', Z), ('glue', Z), ('waf', Z), ('out', Z), ('fin', Z), ('nut', Z),
       ('rod', (78, 0, 0)), ('washer', (95, 0, 0)), ('wnut', (108, 0, 0))],
      labels2d=[('rod goes fence-keyhole-fence,\nthen threads into the nut',
                 (0.50, 0.12))], azim=-48)
still('step7_tighten.png', ASSEMBLED,
      labels2d=[('wing nut: FINGER tight', (0.50, 0.84))],
      box=((380, 600), (-150, 150), (-30, 60)), azim=-38)

# parts overview, exploded with labels
EXP = [('seg', Z), ('waf', (0, 0, 55)), ('out', (85, 0, 0)), ('fin', (-70, 0, 0)),
       ('rod', (150, 0, 55)), ('nut', (-70, 0, 55)),
       ('washer', (170, 0, 55)), ('wnut', (185, 0, 55))]
still('parts.png', EXP,
      labels2d=[('wafer', (0.47, 0.78)), ('segment', (0.36, 0.36)),
                ('outboard fence', (0.66, 0.30)), ('inboard fence', (0.185, 0.55)),
                ('rod + washer + wing nut', (0.80, 0.62)), ('hex nut', (0.245, 0.70))],
      box=((80, 700), (-245, 245), (-35, 120)), elev=24, azim=-62, bench=False)

# ---- 2D sections (styled) ---------------------------------------------------
def section_fig(path, y, xlim, zlim, title, ann=()):
    def sec(s):
        slab = prism([(80, -0.02), (650, -0.02), (650, 0.02), (80, 0.02)], -60, 130).translate([0, y, 0])
        m = (s ^ slab).to_mesh()
        V = np.array([v[:3] for v in m.vert_properties])
        return V, np.array(m.tri_verts)
    fig, ax = plt.subplots(figsize=(11, 4.6))
    fig.patch.set_facecolor('#FAFBFC')
    for key, s in dict(seg=seg, waf=waf, out=fout, fin=fin, rod=rod, nut=nut,
                       washer=washer, wnut=wnut).items():
        V, F = sec(s)
        if len(F) == 0: continue
        for f in F:
            ax.fill(V[f][:, 0], V[f][:, 2], color=hexc(C[key]), lw=0)
    ax.axhspan(zlim[0], cf.z_bot, color='#E8ECEF', zorder=0)
    for txt, xy, xyt in ann:
        ax.annotate(txt, xy=xy, xytext=xyt, fontsize=10, fontweight='bold',
                    arrowprops=dict(arrowstyle='-', color='#5C6670', lw=1.1),
                    bbox=dict(boxstyle='round,pad=0.25', fc='white', ec='#D5DBE1'))
    ax.set_xlim(*xlim); ax.set_ylim(*zlim); ax.set_aspect('equal')
    ax.set_title(title, fontsize=11, fontfamily='monospace', color='#5C6670')
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_color('#D5DBE1')
    plt.tight_layout()
    fig.savefig(os.path.join(OUT, path), dpi=115, facecolor='#FAFBFC')
    plt.close(fig)
    print('section', path)

section_fig('sec_drivetrain.png', 0.0, (150, 545), (-27, 14),
            'cut straight down the middle — everything on one axis, dead under the wafer centre',
            ann=[('hex nut', (177, -11), (200, -22)),
                 ('rod through the keyhole', (330, -7.5), (300, 8)),
                 ('washer + wing nut', (513, -12), (455, -22)),
                 ('wafer', (400, 0.4), (420, 8))])
section_fig('sec_capture.png', 0.0, (487, 517), (-14, 11),
            'the slot: wafer rim floats with 0.15 mm side gap, lip above, ledge below — nothing squeezes it',
            ann=[('lip', (499.4, 3.4), (492, 6.5)),
                 ('rim sits here', (499.2, 0.02), (491, -3.5)),
                 ('ledge', (499.4, -2.6), (492, -7)),
                 ('stop face', (500.4, 0.6), (505, 6.0))])

# ---- videos -----------------------------------------------------------------
def ease(u):
    u = min(1.0, max(0.0, u))
    return 0.5 - 0.5 * math.cos(math.pi * u)

def video(path, nframes, fps, frame_fn, figsize=(9.6, 6.4)):
    fig = plt.figure(figsize=figsize)
    w = FFMpegWriter(fps=fps, bitrate=2200,
                     extra_args=['-pix_fmt', 'yuv420p', '-movflags', '+faststart'])
    with w.saving(fig, os.path.join(OUT, path), dpi=100):
        for i in range(nframes):
            fig.clf()
            ax = fig.add_subplot(111, projection='3d')
            frame_fn(ax, i / (nframes - 1))
            fig.subplots_adjust(0, 0, 1, 1)
            fig.patch.set_facecolor('#FAFBFC')
            w.grab_frame(facecolor='#FAFBFC')
    plt.close(fig)
    print('video', path)

def assemble_frame(ax, t):
    wz  = 60 * (1 - ease((t - 0.02) / 0.16))
    ox  = 58 * (1 - ease((t - 0.24) / 0.18))
    ix  = -58 * (1 - ease((t - 0.48) / 0.18))
    rx  = 95 * (1 - ease((t - 0.72) / 0.20))
    parts = [('seg', Z), ('glue', Z), ('waf', (0, 0, wz)), ('out', (ox, 0, 0)),
             ('fin', (ix, 0, 0)), ('nut', (ix, 0, 0)), ('rod', (rx, 0, 0)),
             ('washer', (rx * 1.15, 0, 0)), ('wnut', (rx * 1.25, 0, 0))]
    render(ax, parts)

def explode_frame(ax, t):
    e = ease(2 * t) if t < 0.5 else ease(2 - 2 * t)     # out and back
    parts = [('seg', Z), ('glue', Z), ('waf', (0, 0, 55 * e)), ('out', (80 * e, 0, 0)),
             ('fin', (-65 * e, 0, 0)), ('nut', (-65 * e, 0, 45 * e)),
             ('rod', (135 * e, 0, 45 * e)), ('washer', (155 * e, 0, 45 * e)),
             ('wnut', (172 * e, 0, 45 * e))]
    render(ax, parts, box=((90, 660), (-245, 245), (-35, 115)))

def turntable_frame(ax, t):
    render(ax, ASSEMBLED, azim=-58 + 360 * t, elev=26)

if '--stills' not in sys.argv:
    video('assemble.mp4', 96, 12, assemble_frame)
    video('explode.mp4', 72, 12, explode_frame)
    video('turntable.mp4', 90, 12, turntable_frame)
print('ALL MEDIA DONE')
