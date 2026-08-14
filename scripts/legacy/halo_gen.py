#!/usr/bin/env python3
"""
Wafer halo layout + fixture DXF generator.
Edit PARAMS, rerun, re-import into OnShape.
Outputs R12-flavored DXF (CIRCLE / LINE / TEXT entities, layer-tagged).
"""
import math

# ---------------- PARAMS ----------------
N          = 9        # number of wafers
R_PITCH    = 350.0    # mm, radius of circle wafer CENTERS sit on
TILT_DEG   = 20.0     # tilt about local tangent axis
WAFER_R    = 150.0    # 300 mm wafer
PUCK_D     = 60.0     # adhesive puck diameter
PUCK_T     = 6.0      # puck disk thickness
STEM_D     = 20.0     # stem diameter
STEM_L     = 35.0     # stem length (sets standoff from rear ring)
RING_W     = 40.0     # rear ring radial width (flat bar / plywood)
POCKET_CLR = 0.6      # jig pocket clearance over wafer dia
# ----------------------------------------

TILT = math.radians(TILT_DEG)

def dxf_header(f):
    f.write("0\nSECTION\n2\nENTITIES\n")

def dxf_footer(f):
    f.write("0\nENDSEC\n0\nEOF\n")

def circle(f, x, y, r, layer):
    f.write(f"0\nCIRCLE\n8\n{layer}\n10\n{x:.4f}\n20\n{y:.4f}\n30\n0.0\n40\n{r:.4f}\n")

def line(f, x1, y1, x2, y2, layer):
    f.write(f"0\nLINE\n8\n{layer}\n10\n{x1:.4f}\n20\n{y1:.4f}\n30\n0.0\n11\n{x2:.4f}\n21\n{y2:.4f}\n31\n0.0\n")

def text(f, x, y, h, s, layer):
    f.write(f"0\nTEXT\n8\n{layer}\n10\n{x:.4f}\n20\n{y:.4f}\n30\n0.0\n40\n{h:.4f}\n1\n{s}\n")

def poly_ellipse(f, cx, cy, a_rad, b_tan, ang, layer, segs=72):
    """approximate ellipse (radial semi-axis a, tangential b) rotated ang, as line segments"""
    pts = []
    for i in range(segs + 1):
        t = 2 * math.pi * i / segs
        ex, ey = a_rad * math.cos(t), b_tan * math.sin(t)
        rx = ex * math.cos(ang) - ey * math.sin(ang)
        ry = ex * math.sin(ang) + ey * math.cos(ang)
        pts.append((cx + rx, cy + ry))
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        line(f, x1, y1, x2, y2, layer)

# ---------- sanity math ----------
chord = 2 * R_PITCH * math.sin(math.pi / N)
overlap = 2 * WAFER_R - chord
halo_od = 2 * (R_PITCH + WAFER_R * math.cos(TILT))
z_swing = WAFER_R * math.sin(TILT)   # edge lift of each wafer
print(f"adjacent center distance : {chord:.1f} mm")
print(f"lateral overlap          : {overlap:.1f} mm  (must be > 0)")
print(f"halo OD (projected)      : {halo_od:.0f} mm")
print(f"edge z-swing from tilt   : +/-{z_swing:.1f} mm")
print(f"total wafer mass         : {N*0.128:.2f} kg")
assert overlap > 0, "wafers don't overlap - reduce R_PITCH or increase N"

# ---------- layout DXF (top view) ----------
with open("halo_layout.dxf", "w") as f:
    dxf_header(f)
    circle(f, 0, 0, R_PITCH, "PITCH_CIRCLE")
    # rear ring centered on pitch circle
    circle(f, 0, 0, R_PITCH - RING_W / 2, "REAR_RING")
    circle(f, 0, 0, R_PITCH + RING_W / 2, "REAR_RING")
    line(f, -30, 0, 30, 0, "CENTER_MARK")
    line(f, 0, -30, 0, 30, "CENTER_MARK")
    for i in range(N):
        a = 2 * math.pi * i / N
        cx, cy = R_PITCH * math.cos(a), R_PITCH * math.sin(a)
        # untilted footprint
        circle(f, cx, cy, WAFER_R, "WAFER_FOOTPRINT")
        # tilted projection: radial semi-axis compressed by cos(tilt)
        poly_ellipse(f, cx, cy, WAFER_R * math.cos(TILT), WAFER_R, a, "WAFER_PROJECTED")
        circle(f, cx, cy, PUCK_D / 2, "PUCK_POSITIONS")
    text(f, -halo_od/2, halo_od/2 + 20, 20,
         f"N={N} Rpitch={R_PITCH} tilt={TILT_DEG}deg OD~{halo_od:.0f}mm", "NOTES")
    dxf_footer(f)

# ---------- fixture profiles DXF ----------
with open("fixture_profiles.dxf", "w") as f:
    dxf_header(f)
    # --- puck side profile (revolve/extrude reference), origin at wafer face ---
    px = 0
    hw = PUCK_D / 2
    line(f, px - hw, 0, px + hw, 0, "PUCK_SIDE")                    # face on wafer
    line(f, px - hw, 0, px - hw, -PUCK_T, "PUCK_SIDE")
    line(f, px + hw, 0, px + hw, -PUCK_T, "PUCK_SIDE")
    line(f, px - hw, -PUCK_T, px - STEM_D/2, -PUCK_T, "PUCK_SIDE")
    line(f, px + STEM_D/2, -PUCK_T, px + hw, -PUCK_T, "PUCK_SIDE")
    # angled stem: stem axis tilted TILT from face normal
    sx = math.sin(TILT) * STEM_L
    sy = math.cos(TILT) * STEM_L
    for s in (-1, 1):
        line(f, px + s*STEM_D/2, -PUCK_T,
                px + s*STEM_D/2 + sx, -PUCK_T - sy, "PUCK_SIDE")
    line(f, px - STEM_D/2 + sx, -PUCK_T - sy,
            px + STEM_D/2 + sx, -PUCK_T - sy, "PUCK_SIDE")
    text(f, px - hw, 25, 8, f"PUCK: D{PUCK_D} x {PUCK_T}, stem D{STEM_D} x {STEM_L} @ {TILT_DEG}deg, M5 thru", "NOTES")

    # --- jig base tray (top view), offset right ---
    jx = 350
    tray_r = WAFER_R + 25
    pocket_r = WAFER_R + POCKET_CLR / 2
    circle(f, jx, 0, tray_r, "JIG_TRAY")
    circle(f, jx, 0, pocket_r, "JIG_POCKET")        # 2 mm deep pocket
    circle(f, jx, 0, WAFER_R, "JIG_FOAM_LINER")     # 1 mm EVA foam disc
    text(f, jx - tray_r, tray_r + 15, 8,
         f"TRAY: pocket D{2*pocket_r:.1f} x 2 deep, foam liner D{2*WAFER_R:.0f} x 1", "NOTES")

    # --- centering template ring (top view), offset further ---
    tx = 800
    circle(f, tx, 0, pocket_r - 0.1, "TEMPLATE")            # slips into pocket
    circle(f, tx, 0, PUCK_D / 2 + 0.2, "TEMPLATE")          # locates puck
    for k in range(3):                                       # finger cutouts
        a = 2 * math.pi * k / 3
        circle(f, tx + 100 * math.cos(a), 100 * math.sin(a), 25, "TEMPLATE_CUTOUTS")
    text(f, tx - pocket_r, pocket_r + 15, 8,
         f"TEMPLATE: OD {2*pocket_r - 0.2:.1f}, center hole D{PUCK_D + 0.4:.1f}, print 6 thick", "NOTES")
    dxf_footer(f)

print("wrote halo_layout.dxf, fixture_profiles.dxf")
