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
    tmin     = 15.0,    # base thickness (gear face is gear_F). 15 (2026-07-26,
                        # the deep-bevel rev): the flat bottom drops 5 mm so
                        # the gear face can reach 9.5 under the neighbour-
                        # plane ceiling — part lands at the 30 mm cap.
    bond     = 1.1,     # bondline
    clr      = 3.0,     # neighbour clearance
    gear_m   = 5.6,     # NOMINAL gear module (sets tooth count); the
                        # effective module is retuned in Cfg so the root
                        # lands flush on the band OD.
    gear_sp  = 0.0,     # spiral angle, deg; 0 = straight. The cutter is
                        # twist-extruded, so the generated ring inherits the
                        # conjugate spiral. Spiral thrust would fight the
                        # idler groove (the only axial restraint) — keep 0.
    gear_pa  = 20.0,    # pressure angle, degrees
    pin_T    = 20,      # pinion tooth count. 108T ring / 20T = 5.4:1 —
                        # the Pololu #1596 at 5 V (10.83 no-load rpm) gives
                        # 2.01 rpm at the ring (2026-07-27, Nick: ~2 rpm is
                        # fine, minimalist profile beats exact-1; pin_T 10
                        # was the 1.00 rpm build). NOTE finer RACK teeth
                        # would RAISE the profile: more ring teeth needs
                        # more pinion teeth per ratio, and the pinion's
                        # size floor is its printable tooth module
                        # (2*pin_rho/pin_T >= ~0.8).
    pin_rho  = 8.0,     # pinion mid-face pitch radius. FREE, not the
                        # rolling value (conjugacy is by generation; only
                        # the COUNT is forced). 8 with pin_T 20 = 0.8 mm
                        # section module — the printable floor, and the
                        # low-profile knob: the standoff is ~2.25*rho +
                        # gear_F/2 + face/2 dominated.
    pin_face = 7.0,     # pinion face length along its axis: engages the
                        # OUTER pin_face mm of the tooth radial envelope.
    stand    = -1.0,    # extra wafer standoff from the wall, mm. The
                        # crossed-axis pinion's body bulges in front of
                        # the tooth band; the wafers must clear it.
                        # -1 = DERIVE the minimum (bulge + 3) in Cfg —
                        # 78.2 at B.5 -> part 108 tall. Override to taste.
    gear_bl  = 0.3,     # tooth thinning for printed backlash (the runner
                        # is the cutter minus this). 0.3, not the 0.6 of
                        # the module-5.4 pinion era: at the 20T/0.8-module
                        # pinion, 0.6 halves the tooth.
    gear_drive = 'bevel45', # 'bevel45': external beveloid ring, big end
                        # at the wall, generated conjugate to a parallel-
                        # axis pinion — see bevel_geom(). 'spur' is the
                        # parked legacy drive (gearmotor_stl pins it).
    gear_F   = 9.5,     # ring band face height — the visible 45-deg cone
                        # (9.5 face ~ the 12.1 tooth depth: the mixer look).
                        # HARD CEILING: must stay under the neighbour-wafer
                        # clearance plane (9.83 at tmin=15, recomputed live)
                        # or the clearance cut planes the leading teeth —
                        # gated in main().
    ogrv_z0  = 12.0,    # OUTER mount groove (2026-07-26, crossed-drive
    ogrv_w   = 10.0,    # rework): circumferential, in the band OD, riding
    ogrv_d   = 2.0,     # the BOTTOM foot's wheels/saddle. An internal
                        # engagement can only HANG a ring — resting it
                        # needs the outer surface, and the tall riser has
                        # 80 mm of bare cylinder for it. Chamfered top
                        # wall for printability. 0 width deletes it.
    grv_z0   = 2.5,     # idler retention groove in the INNER face at Ri
    grv_h    = 1.5,     # (2026-07-25, was outer): starts grv_z0 above the
    grv_d    = 2.0,     # flat bottom, straight ledge for grv_h, then a
                        # 45-deg chamfer roof for printability. The bracket's
                        # idler wheels carry a rib that rides in it — the
                        # ring HANGS on the wheels and the groove walls keep
                        # it on the wall axis. 0 depth deletes it. Clear of
                        # the keyhole and the dovetails.
    hole_D   = 6.5,     # jig keyhole bore, RADIAL from the outer face.
                        # M6 clearance: an M6 rod/screw (Ø6.0) slides without
                        # reaming. (Was 5.0 for #10-24 pre-2026-07-24.)
    pocket_d = 1.0,     # adhesive pocket depth in the land
    pocket_m = 4.0,     # pocket inset from the band edges
    dt_neck  = 12.0,    # dovetail neck width
    dt_tip   = 16.0,    # dovetail tip width
    dt_depth = 8.0,     # dovetail depth
    dt_h     = 5.0,     # dovetail height (male tail; socket cut is
                        # dt_h+0.5 so its roof stays printable). Both open
                        # at the flat bottom — segments slide in Z.
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
        # keyhole is THROUGH the band by definition — the cure-jig rod must
        # reach the inboard fence (was a frozen 30.5 literal that drifted
        # from bw)
        self.hole_dep = self.bw + 0.5
        # gear: tooth count must divide by N or the pitch breaks at every
        # joint. EXTERNAL now (2026-07-25): the pitch targets just outside
        # the band so the root cone clears the band OD (and the dovetail
        # zone) with a short web between them.
        self.g_bev   = (self.gear_drive == 'bevel45')
        if self.g_bev:
            target = self.Ro + 1.25 * self.gear_m + 2.0
            self.tps = max(6, int(math.ceil(2 * target / self.gear_m / self.N)))
        else:
            self.tps = max(6, round(2 * (self.Ri - 5.0) / self.gear_m / self.N))
        self.teeth   = self.tps * self.N
        # FLUSH MODULE: tooth count is quantised in steps of N, so the
        # module (not the count) is retuned to land the front root circle
        # 1 mm inside the band OD — teeth rise straight off the band wall.
        if self.g_bev:
            self.gear_m = (self.Ro - 1.0) / (self.teeth / 2.0 - 1.25)
        self.g_pitch = self.teeth * self.gear_m / 2.0
        self.g_tip   = (self.g_pitch + self.gear_m if self.g_bev
                        else self.g_pitch - self.gear_m)   # external: outward
        self.g_root  = (self.g_pitch - 1.25 * self.gear_m if self.g_bev
                        else self.g_pitch + 1.25 * self.gear_m)
        self.g_base  = self.g_pitch * math.cos(math.radians(self.gear_pa))
        # external beveloid: nominal radii at the FRONT face, scaled by
        # g_kbig toward the WALL (big end at the wall, cone faces the
        # viewer). Why parallel axes: see bevel_geom(). Band + web are
        # gear_F tall; the slab inner boundary is plain Ri.
        self.g_kbig  = (self.g_pitch + self.gear_F) / self.g_pitch
        self.g_web_i = self.Ro - 2.0                   # web overlap into band
        self.g_fi    = self.Ri if self.g_bev else self.g_root
        # CROSSED-AXIS drive numbers (2026-07-26, Nick: shaft points DOWN —
        # radial at 12 o'clock — and the wafers move forward to clear the
        # pinion). Rolling at the front pitch circle: pinion pitch radius
        # is x*/ratio, its 45-deg cone apex sits inboard, its axis stands
        # rho* above the contact. The front bulge of its big end sets the
        # wafer standoff.
        if self.g_bev:
            self.pin_ratio = self.teeth / self.pin_T
            # face engages the OUTER pin_face mm of the tooth envelope
            self.pin_x1    = self.g_tip * self.g_kbig
            self.pin_x0    = max(self.Ro + 2.0, self.pin_x1 - self.pin_face)
            xs             = (self.pin_x0 + self.pin_x1) / 2.0
            self.pin_apex  = xs - self.pin_rho               # 45-deg cone
            # axis height: mid-face tips dip to the tooth mid-height
            self.pin_zax   = (self.gear_F / 2.0
                              + self.pin_rho * (1 + 2.0 / self.pin_T))
            tip_big = (self.pin_x1 - self.pin_apex) * (1 + 2.0 / self.pin_T)
            self.pin_bulge = self.pin_zax + tip_big          # frontmost z
            gap0 = ((self.rise + self.landOff + self.tmin)
                    - (self.wafer_T / 2.0 + self.r * math.sin(self.th)))
            if self.stand < 0:
                self.stand = max(0.0, self.pin_bulge + 3.0 - gap0)
        else:
            self.stand = max(0.0, self.stand)
        self.z_bot  -= self.stand
        self.z1      = self.z_bot + self.tmin
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
    """Keyhole axis height, shared with cure_jig_stl.py. Constraints: bore
    bottom 0.1 above z1 (rod hardware must swing over the bench), and the
    axis cannot go higher (web under the pocket floor breaks out). Needs
    theta >= ~4 deg or the bore exits the band top at y=0."""
    return cf.z1 + cf.hole_r + 0.1


def gear_F_ceiling(cf, na=120):
    """Max printable gear band face: the min height of (neighbour wafer
    plane − clr) above the flat bottom, over the tooth annulus where the
    neighbour's disc overhangs it. The 4.86 that used to live in comments,
    computed instead of frozen."""
    M, c, n = cf.wafer_frame(1)
    cn = sum(ci * ni for ci, ni in zip(c, n))
    best = float('inf')
    for i in range(na + 1):
        a = cf.half * i / na
        for rr in (cf.g_web_i, cf.g_root, cf.g_tip, cf.g_tip * 1.05):
            x, y = rr * math.cos(a), rr * math.sin(a)
            d = (x - c[0], y - c[1], -c[2])
            ax = sum(di * ni for di, ni in zip(d, n))
            rad2 = sum(di * di for di in d) - ax * ax
            if rad2 <= (cf.r + cf.clr_edge) ** 2:
                z = (cn - cf.clrOff - x * n[0] - y * n[1]) / n[2]
                best = min(best, z - cf.z_bot)
    return best


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
    # the sector faces back off 1e-5 rad (~2.7 um) from the exact joint
    # plane: assembled neighbours BUTT here, and numerically coincident
    # faces read as ~1e-6 mm3 of phantom interference in the assembly
    # gates (same convention as the tooth sector clip)
    h = cf.half - 1e-5
    p  = [face_pt(-h, cf.Ri, 0.0)]
    p += arc(cf.Ro, -h, h, na)
    p += [face_pt(h, cf.Ri, 0.0)]
    p += arc(cf.Ri, h, -h, na)[1:-1]
    return p


def slab_poly(cf, na=160):
    """Band WITHOUT the male dovetail (tail_poly carries it at its own
    dt_h height; socket subtracted later). 'bevel45': inner boundary is
    plain Ri (g_fi); the generated teeth union on outside. 'spur':
    boundary at the root circle, gear_teeth unions inward."""
    ri = cf.g_fi
    h = cf.half - 1e-5          # joint-face setback, see band_poly
    p  = [face_pt(-h, ri, 0.0), face_pt(-h, cf.Ro, 0.0)]
    p += arc(cf.Ro, -h, h, na)[1:]
    p += [face_pt(h, ri, 0.0)]
    p += arc(ri, h, -h, na)[1:-1]
    return p


def tail_poly(cf):
    """The male dovetail's plan profile, rooted 2 mm inside the joint face
    so the union with the slab is overlapped, never coplanar. Extruded
    dt_h tall by build_segment — the tail is built at height, not cut
    down from a full-height slab (cut-on-the-joint-plane left coincident
    faces that read as ~1e-6 assembled interference, and the backed-off
    variant shed a um sliver strip that broke the STEP round-trip)."""
    dtn, dtt, dtd = cf.dt_neck / 2, cf.dt_tip / 2, cf.dt_depth
    return [face_pt(cf.half, cf.rho_c + dtn, -2.0),
            face_pt(cf.half, cf.rho_c + dtn, 0.0),
            face_pt(cf.half, cf.rho_c + dtt, dtd),
            face_pt(cf.half, cf.rho_c - dtt, dtd),
            face_pt(cf.half, cf.rho_c - dtn, 0.0),
            face_pt(cf.half, cf.rho_c - dtn, -2.0)]


def gear_teeth(cf, z0=0.0):
    """'spur' legacy: the internal involute teeth as a straight prism,
    z0..z0+tmin, outer boundary overlapping 2 mm past the root circle into
    the slab so the union is clean."""
    teeth = [(rad * math.cos(a), rad * math.sin(a)) for rad, a in tooth_profile(cf)]
    outer = arc(cf.g_root + 2.0, cf.half, -cf.half, 64)
    return prism(teeth + outer, z0, cf.tmin)


def bevel_geom(cf):
    """Shared numbers for the CROSSED-AXIS generated pair (2026-07-26,
    Nick: "the shaft points down… the bottom piece will fit in the
    groove… top bracket only exists when we want to drive it"), in the
    MESH FRAME (ring wall face z=0, band z 0..gear_F, contact meridian on
    +x). The pinion is a 45-deg cone, apex INBOARD (toward the halo
    centre), axis RADIAL — vertical at 12 o'clock, the motor above it
    shaft-down. It rolls on the ring's front pitch circle: pitch radius
    rho = g_pitch/ratio with ratio = teeth/pin_T (108/10 = 10.8 — pairs
    the Pololu #1596 at 5 V to 1.00 rpm at the ring). The pinion axis
    stands rho above the contact; its big end bulges pin_bulge in front
    of the wall face, which is what sets Cfg's derived `stand` (the
    wafers move forward to clear it — Nick's call). Its lower-outer
    teeth also swing ~14 mm BEHIND the wall face: the bottom bracket's
    wall gap and wall-plane check own that. Conjugacy comes from the CSG
    generation sweep, not from bevel theory: a true rolling 45/45 pair
    only exists at 1:1, so the flanks are generated conjugate to the
    imposed 10.8:1 motion (heavy sliding, mN-m loads — fine).
    hub_len/hub_r: the pinion's BIG-END (motor-side) hub."""
    return dict(F=cf.gear_F, ratio=cf.pin_ratio, rho=cf.pin_rho,
                apex=cf.pin_apex, zax=cf.pin_zax,
                x0=cf.pin_x0, x1=cf.pin_x1, face=cf.pin_x1 - cf.pin_x0,
                rp0=cf.pin_T * cf.gear_m / 2.0,
                bulge=cf.pin_bulge, hub_len=6.0, hub_r=8.0)


def bevel_pinion(cf, backlash=None, over=0.0):
    """The crossed-drive pinion in its LOCAL frame: axis +z, apex toward
    -z, involute sections growing linearly at 45 deg (radius rho(x) =
    x - apex along the face). Local z=0 is the small end (maps to global
    x = pin_x0); the big end at z = face carries the motor hub (added by
    build_pinion). backlash=0 is the GENERATING cutter; the runner keeps
    gear_bl thinner teeth. over extends the cone past both faces
    (coplanar-cap sliver trap)."""
    bg = bevel_geom(cf)
    pts, g = pinion_profile(cf, cf.pin_T, backlash=backlash)
    rp0 = g['rp']
    s_lo = (bg['x0'] - over - bg['apex']) / rp0
    s_hi = (bg['x1'] + over - bg['apex']) / rp0
    pts = [(x * s_lo, y * s_lo) for x, y in pts]
    if signed_area(pts) < 0:
        pts = pts[::-1]
    tw = math.degrees((bg['face'] + 2 * over)
                      * math.tan(math.radians(cf.gear_sp)) / bg['rho'])
    p = Manifold.extrude(CrossSection([pts]), bg['face'] + 2 * over,
                         n_divisions=16, twist_degrees=tw,
                         scale_top=(s_hi / s_lo,) * 2)
    p = p.translate([0.0, 0.0, -over])
    g = {k: (v * bg['rho'] / rp0 if k != 'T' else v) for k, v in g.items()}
    return p, g


def bevel_pinion_at(cf, pin, d, dr=0.0):
    """Place the local-frame pinion into the mesh frame at ring roll d:
    spin +ratio*d about its own axis (matched surface speeds at the
    rolling point — the sweep gate is the arbiter of the sign), then
    rotate local +z onto global +x (the RADIAL axis; local +x lands on
    global -z, so the phase-0 tooth points DOWN into the ring), then
    onto the axis line at height zax. dr < 0 lowers the cutter toward
    the ring: radial tip relief, no shelf."""
    bg = bevel_geom(cf)
    return (pin.rotate([0.0, 0.0, math.degrees(d * bg['ratio'])])
               .rotate([0.0, 90.0, 0.0])
               .translate([bg['x0'], 0.0, bg['zax'] + dr]))


_TEETH_CACHE = {}   # the sweep is the most expensive op in the repo;
                    # one main() run needs the identical solid up to 7x


def gear_teeth_bevel45(cf, z0=0.0, steps=None, span_pitches=4.0):
    """EXTERNAL beveloid ring teeth, GENERATED: big end at the wall, flush
    root at the band OD, meshing the CROSSED radial-axis pinion (bevel_geom).
    Recipe: sweep the zero-backlash cutter through the meshing motion
    advanced 0.3 mm RADIALLY (dr=-0.3 — z-shifted relief leaves an uncut
    shelf ring at the wall edge), extract one pitch, pattern tps+1, clip
    to the sector (phase: the cutter cuts a SPACE at angle 0, so the
    pattern tiles k*pitch from the joint). Face = gear_F, gated in main()
    against the neighbour-wafer clearance plane."""
    key = (cf.teeth, cf.tps, cf.pin_T, cf.gear_m, cf.gear_F, cf.gear_sp,
           cf.gear_pa, cf.gear_bl, cf.half, cf.g_tip, cf.g_web_i, steps,
           span_pitches)
    if key in _TEETH_CACHE:
        return _TEETH_CACHE[key].translate([0.0, 0.0, z0])
    F = cf.gear_F
    big = cf.g_tip * cf.g_kbig + 1.0
    blank = prism(arc(big, -cf.half, cf.half, 200) +
                  arc(cf.g_web_i, cf.half, -cf.half, 200), 0.0, F)
    tipcone = (Manifold.cylinder(F + 0.2, cf.g_tip * cf.g_kbig + 0.1,
                                 cf.g_tip + 0.1, 512)
               .translate([0.0, 0.0, -0.1]))
    blank = blank ^ tipcone
    cutter_pin, _ = bevel_pinion(cf, backlash=0.0, over=0.5)
    # the crossed pinion turns ratio*span while a parallel one turned
    # ~N*span — finer steps keep the sweep scallop under the 0.3 relief
    n = steps or (48 * int(round(cf.gear_m)) + 1)
    span = span_pitches * (2.0 * math.pi / cf.teeth)
    cut = union_all([(bevel_pinion_at(cf, cutter_pin,
                                      -span / 2.0 + span * i / (n - 1), dr=-0.3)
                      .rotate([0, 0, -math.degrees(-span / 2.0
                                                   + span * i / (n - 1))]))
                     for i in range(n)])
    # COSMETIC pass: the small crossed pinion only carves the outer
    # pin_face of the envelope; the visible deep-bevel tooth pattern
    # (Rev B.4, Nick's "always dreamed of" look) is restored by ALSO
    # sweeping the old parallel-axis 12T beveloid cutter over the full
    # face. Extra removal can only add clearance — the mesh gate is
    # untouched — and both patterns tile k*pitch, so they align.
    ring_mid = cf.g_pitch + F / 2.0
    pin_mid = ring_mid / (cf.teeth / cf.tps)
    rp0c = cf.tps * cf.gear_m / 2.0
    pts, _ = pinion_profile(cf, cf.tps, backlash=0.0)
    s_lo = (pin_mid - F / 2.0 - 0.5) / rp0c
    s_hi = (pin_mid + F / 2.0 + 0.5) / rp0c
    cpts = [(x * s_lo, y * s_lo) for x, y in pts]
    if signed_area(cpts) < 0:
        cpts = cpts[::-1]
    cos_pin = Manifold.extrude(CrossSection([cpts]), F + 1.0,
                               n_divisions=16,
                               scale_top=(s_hi / s_lo,) * 2
                               ).translate([0.0, 0.0, -0.5])
    C = ring_mid + pin_mid
    nc = 30 * int(round(cf.gear_m)) + 1
    cut = cut + union_all([
        (cos_pin.rotate([0.0, 0.0, -math.degrees(d * cf.teeth / cf.tps)])
                .translate([C - 0.3, 0.0, 0.0])
                .rotate([0, 0, -math.degrees(d)]))
        for d in (-span / 2.0 + span * i / (nc - 1) for i in range(nc))])
    gen = blank - cut
    pitch = 360.0 / cf.teeth
    wedge = prism([(0.0, 0.0)] + arc(big + 100.0,
                                     math.radians(-pitch / 2 - 0.02),
                                     math.radians(pitch / 2 + 0.02), 16),
                  -1.0, F + 2.0)
    one = gen ^ wedge
    teeth = union_all([one.rotate([0.0, 0.0, -math.degrees(cf.half) + k * pitch])
                       for k in range(cf.tps + 1)])
    # the sector clip backs off a hair (~3 um at the tooth radius): clipping
    # exactly at +/-half leaves generated-facet wobble that reads as ~1e-4
    # of joint interference between assembled neighbours
    eps = 1e-5
    sector = prism([(0.0, 0.0)] + arc(big + 100.0, -cf.half + eps,
                                      cf.half - eps, 64), -1.0, F + 2.0)
    teeth = teeth ^ sector
    _TEETH_CACHE[key] = teeth
    return teeth.translate([0.0, 0.0, z0])


def pocket_poly(cf, na=120):
    """Adhesive pocket: the band, inset all round.

    It meters the adhesive and gives a positive bondline stop. It does NOT
    locate the wafer -- the whole band lies under the wafer's interior, with the
    rim 55 mm inboard and 215 mm outboard, so no pocket edge here can ever touch
    it. Centring stays the jig's job.
    """
    m = cf.pocket_m
    # Angular inset must clear the dovetail zones. Historically load-bearing:
    # when the socket was tmin-tall its roof was <0.5 mm at the trailing end
    # and a 1 mm pocket punched through into it (genus tunnel). The dt_h
    # socket leaves ~4.5 mm under the pocket floor now, but the inset stays —
    # tape near the land centroid is what OP 015 wants anyway.
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


def box(x0, x1, y0, y1, z0, z1):
    return prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1 - z0)


def tube(h, r_out, r_in, z0=0.0, fn=512):
    """Annular cylinder: outer minus (overshooting) inner."""
    return (Manifold.cylinder(h, r_out, r_out, fn)
            - Manifold.cylinder(h + 2.0, r_in, r_in, fn).translate([0, 0, -1.0])
            ).translate([0.0, 0.0, z0])


def hex_poly(r_af, clr=0.0, phase=30.0):
    """Hex nut pocket profile from across-flats + clearance. phase=30 puts a
    vertex up (the printable orientation both the jig and bracket use)."""
    R = (r_af + clr) / math.sqrt(3.0)
    return [(R * math.cos(math.radians(60 * i + phase)),
             R * math.sin(math.radians(60 * i + phase))) for i in range(6)]


def union_all(parts):
    """Pairwise tree-reduce — a sequential `acc + p` over n parts is
    quadratic in accumulated mesh size; this is n·log n."""
    parts = list(parts)
    while len(parts) > 1:
        parts = [a + b for a, b in zip(parts[::2], parts[1::2])] +                 ([parts[-1]] if len(parts) % 2 else [])
    return parts[0]


# printed-M6 nut spec shared by the cure jig and the bracket (drifted as
# raw literals in both before)
M6_NUT_AF, M6_NUT_CLR = 10.0, 0.45


def wafer_cut(cf, k, offset, height, extra_r=0.0):
    """Disc-shaped solid standing `offset` from wafer k's mid-plane, extending +n.

    A disc and not a half-space: the neighbour's wafer is 300 mm across, so a
    half-space would remove material hundreds of mm outside its footprint.

    The disc is oversized by clr_edge. At exactly the wafer radius the cut wall
    lands tangent to the wafer's rim, leaving zero lateral clearance -- and T6
    only holds centring to 0.5 mm, with another 0.2 mm of diameter tolerance
    on the wafer itself.
    """
    rad = cf.r + cf.clr_edge + extra_r
    cyl = Manifold.cylinder(height, rad, rad, cf.facets)
    return on_wafer(cf, cyl, k, offset)


def build_segment(cf):
    tn = math.tan(cf.th)
    # 1-2. band, trimmed by its own wafer's land plane:  z <= y*tan(th) - landOff
    seg = prism(band_poly(cf), cf.z_bot, cf.tall)
    seg = seg.trim_by_plane([0.0, tn, -1.0], cf.landOff)
    # 3. bottom slab; the male dovetail unions on at ITS OWN dt_h height
    #    (see tail_poly for why it is built, not cut down)
    seg = seg + prism(slab_poly(cf), cf.z_bot, cf.tmin)
    seg = seg + prism(tail_poly(cf), cf.z_bot, cf.dt_h)
    if cf.g_bev:
        t = gear_teeth_bevel45(cf, cf.z_bot)
        # the tooth SPACES must stay open below the band OD (flush root
        # sits inside Ro; the pinion tips sweep to ~Ro-0.1): carve the
        # band's outer 1.5 mm over the gear face so the generated blank
        # (from g_web_i) owns that annulus
        seg = seg - tube(cf.gear_F + 0.1, cf.g_tip * 2.0, cf.g_web_i + 0.5,
                         cf.z_bot - 0.05, cf.facets)
        # clearance-cut the teeth with a deeper, oversized disc: the ~5-deg
        # cut surface meets the 45-deg tooth lean at a shallow angle and can
        # strand a tip crumb right at the disc wall (masquerades as wrong
        # genus); the +0.2 depth / +0.5 radius swallows it
        seg = seg + (t - wafer_cut(cf, 1, -cf.clrOff - 0.2, cf.tall, extra_r=0.5))
    else:
        seg = seg + gear_teeth(cf, cf.z_bot)
    # 4. neighbour clearance cut
    seg = seg - wafer_cut(cf, 1, -cf.clrOff, cf.tall)
    # 5. female socket, blind from the bottom, dt_h + 0.5 tall — a
    #    tmin-tall cut leaves its roof <0.5 mm at the trailing edge.
    seg = seg - prism(socket_poly(cf), cf.z_bot - 0.5, cf.dt_h + 1.0)
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
    # 8. idler retention groove, circumferential in the INNER face at Ri
    #    (2026-07-25, was outer): straight walls over grv_h (the ledge the
    #    idler wheel ribs ride in), then a 45-deg chamfer roof so the
    #    vertical-face overhang prints clean. bracket_stl's wheels size to it.
    if cf.grv_d > 0:
        z0 = cf.z_bot + cf.grv_z0
        rg = cf.Ri + cf.grv_d
        grv = tube(cf.grv_h, rg, cf.Ri - 1.0, z0, cf.facets)
        cham = (Manifold.cylinder(cf.grv_d + 0.02, rg, cf.Ri - 0.02, cf.facets)
                .translate([0, 0, z0 + cf.grv_h - 0.01])) \
               - (Manifold.cylinder(cf.grv_d + 2.0, cf.Ri - 1.0, cf.Ri - 1.0,
                                    cf.facets)
                  .translate([0, 0, z0 + cf.grv_h - 1.0]))
        seg = seg - grv - cham
    # outer mount groove in the riser band OD: straight floor + walls,
    # 45-deg chamber on the UPPER wall (prints flat-bottom-down)
    if cf.ogrv_w > 0:
        oz = cf.z_bot + cf.ogrv_z0
        og = tube(cf.ogrv_w, cf.Ro + 2.0, cf.Ro - cf.ogrv_d, oz, cf.facets)
        # roof chamfer: big at the BOTTOM shrinking outward-up, so the
        # leftover wedge stays attached to the OD wall (the inverted cone
        # detaches a zero-seam taper ring — measured 394 mm3 orphan)
        ch = (Manifold.cylinder(cf.ogrv_d + 0.02, cf.Ro + 0.02,
                                cf.Ro - cf.ogrv_d, cf.facets)
              .translate([0, 0, oz + cf.ogrv_w - 0.01])) \
             - Manifold.cylinder(cf.ogrv_d + 2.0, cf.Ro - cf.ogrv_d,
                                 cf.Ro - cf.ogrv_d, cf.facets) \
                 .translate([0, 0, oz + cf.ogrv_w - 1.0])
        seg = seg - og - ch
    # drop zero-volume degenerate specks (glancing spiral-tooth/clearance
    # intersections shed them; they survive as phantom extra solids in the
    # STEP round-trip even though the STL weld absorbs them)
    parts = [c for c in seg.decompose() if c.volume() > 0.01]
    if len(parts) > 1:
        seg = sum(parts[1:], parts[0])
    elif parts:
        seg = parts[0]
    return seg


def on_wafer(cf, solid, k, offset):
    """Place a z-aligned solid onto wafer k's plane, offset along its normal."""
    M, c, n = cf.wafer_frame(k)
    t = [c[i] + offset * n[i] for i in range(3)]
    return solid.transform([[M[0][0], M[0][1], M[0][2], t[0]],
                            [M[1][0], M[1][1], M[1][2], t[1]],
                            [M[2][0], M[2][1], M[2][2], t[2]]])


def build_wafer(cf, k=0):
    cyl = Manifold.cylinder(cf.wafer_T, cf.r, cf.r, 256)
    return on_wafer(cf, cyl, k, -cf.wafer_T / 2.0)


def rotated(solid, k, cf):
    return solid.rotate([0.0, 0.0, math.degrees(k * cf.sector)])


def build_ring(cf, n=None, wafers=False, seg=None):
    """Returns a LIST of solids, one per body.

    Kept separate rather than unioned: adjacent segments meet on coincident
    radial faces, and welding across that shared face makes non-manifold edges
    where four triangles meet. As separate bodies each one stays watertight,
    which is also what a slicer wants for a multi-part plate.
    """
    n = n or cf.N
    seg = seg if seg is not None else build_segment(cf)
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
    if cf.g_bev:
        bg = bevel_geom(cf)
        kbp = (cf.g_pitch + cf.gear_F) / cf.g_pitch
        print(f"  gear    EXTERNAL beveloid ring (generated, CROSSED drive): "
              f"{cf.tps}T/seg × {cf.N} = {cf.teeth}T, module {cf.gear_m:.3f} "
              f"(flush root r{cf.g_root:.1f} at the band wall Ro={cf.Ro:.0f}), "
              f"{cf.gear_sp:.0f}° spiral, face {cf.gear_F} mm, "
              f"tips r{cf.g_tip * kbp:.1f} (WALL) → r{cf.g_tip:.1f} (front); "
              f"pinion {cf.pin_T}T 45° cone on a RADIAL axis (shaft points "
              f"down at 12 o'clock), ratio {cf.pin_ratio:.1f}:1, axis "
              f"{bg['zax']:.1f} above the wall face, bulge {bg['bulge']:.1f} "
              f"— wafer standoff +{cf.stand:.1f} (derived)")

    else:
        print(f"  gear    {cf.tps}T/seg × {cf.N} = {cf.teeth}T  module {cf.gear_m}  "
              f"pitch Ø{2*cf.g_pitch:.0f}  tip r{cf.g_tip:.1f}  root r{cf.g_root:.1f}")
    print(f"  z       flat bottom {cf.z_bot:.2f}   slab top {cf.z1:.2f}")
    print(f"  keyhole Ø{cf.hole_D} radial at a=0, z={keyhole_z(cf):.2f}, "
          f"{'THROUGH' if cf.hole_dep >= cf.bw else 'blind'} "
          f"({cf.hole_dep:.1f} deep from the outer face)\n")

    seg = build_segment(cf)
    bodies = write_stl(seg, os.path.join(a.out, 'segment.stl'))
    v = report('segment.stl', seg, bodies, 'one segment')
    # rough book estimate only — slice.py is the mass authority (skins
    # dominate; the linear model under-reads at low infill)
    print(f"{'':24}mass  10% PLA (rough) {v*1.24e-3*0.10:6.1f} g   "
          f"solid {v*1.24e-3:6.1f} g\n")

    for fname, kw, note in (('segment_pair.stl', dict(n=2), 'gate T1'),
                            ('halo_frame.stl',   dict(), f'all {cf.N} segments'),
                            ('halo_assembly.stl', dict(wafers=True), 'frame + wafers, view only')):
        s = build_ring(cf, seg=seg, **kw)
        bodies = write_stl(s, os.path.join(a.out, fname))
        report(fname, s, bodies, note)

    # ---- mating pinion ----
    pin, g = build_pinion(cf)
    bodies = write_stl(pin, os.path.join(a.out, 'pinion.stl'))
    report('pinion.stl', pin, bodies, f"{g['T']}T, meshes at {cf.teeth/g['T']:.0f}:1")
    mesh = check_mesh(cf)
    if 'centre' in mesh:
        print(f"{'':24}centre distance {mesh['centre']:.0f} mm, worst overlap over a full "
              f"tooth pitch {mesh['worst_overlap']:.5f} mm3\n")
    else:
        print(f"{'':24}pinion axis {mesh['axis']}, {mesh['zax']:.1f} above "
              f"the wall face; worst overlap over a full tooth pitch "
              f"{mesh['worst_overlap']:.5f} mm3 (generated teeth — scallop only)\n")

    # ---- DXF sketch profiles for OnShape ----
    dxf = os.path.join(a.out, 'dxf'); os.makedirs(dxf, exist_ok=True)
    profiles = [
        ('01_band.dxf',      [band_poly(cf)],                        'extrude tall, trim to the land plane'),
        ('02_slab.dxf',      [slab_poly(cf)],                        f'extrude {cf.tmin} mm up from the flat bottom'),
        ('02b_tail.dxf',     [tail_poly(cf)],                        f'extrude {cf.dt_h} mm up from the flat bottom (male dovetail)'),
        ('03_socket.dxf',    [socket_poly(cf)],                      f'cut {cf.dt_h + 0.5} mm from the flat bottom'),
        ('04_pocket.dxf',    [pocket_poly(cf)],                      f'cut {cf.pocket_d} mm down from the land plane'),
    ]
    if cf.g_bev:
        bgd = bevel_geom(cf)
        sp = (bgd['x1'] - bgd['apex']) / bgd['rp0']   # big-end section scale
        cutter = [(x * sp, y * sp)
                  for x, y in pinion_profile(cf, cf.pin_T, backlash=0.0)[0]]
        profiles.append(('05_bevel_cutter.dxf', [cutter],
                         'GENERATED teeth have no 2D sketch — this is the '
                         'cutter pinion profile; sweep it per '
                         'segment_stl.gear_teeth_bevel45'))
    else:
        profiles.append(('05_ring_teeth.dxf',
                         [[(r * math.cos(t), r * math.sin(t))
                           for r, t in tooth_profile(cf)]],
                         f'{cf.tps}T of the {cf.teeth}T internal ring'))
    profiles.append(('06_pinion.dxf', [pinion_profile(cf, cf.tps)[0]],
                     f'{cf.tps}T pinion, extrude {cf.tmin} mm'))
    print("  DXF sketch profiles for OnShape:")
    for fn, loops, note in profiles:
        n = write_dxf(os.path.join(dxf, fn), loops)
        print(f"    dxf/{fn:20} {n:5,d} pts   {note}")

    print(f"\nWrote to {os.path.abspath(a.out)}/")
    # stray-shard guard: a disconnected crumb cancels the keyhole handle in
    # the Euler count and masquerades as genus 0 — count components instead
    # ignore zero-volume degenerate specks (glancing spiral-tooth/clearance
    # intersections shed them; they vanish in the float32 STL weld anyway)
    ncomp = len([c for c in seg.decompose() if c.volume() > 0.01])
    if ncomp != 1:
        print(f"FAIL: segment is {ncomp} components — orphaned crumb(s), "
              f"see the clearance-cut note in build_segment")
        return 1
    # the mesh sweep is a gate, not a printout: CI runs this script
    if mesh['worst_overlap'] > 0.05:
        print(f"FAIL: gear mesh overlap {mesh['worst_overlap']:.3f} mm3 > 0.05 "
              f"— raise gear_bl or fix the slot geometry")
        return 1
    # REGRESSION GATE: the neighbour-wafer clearance cut must remove ZERO
    # tooth material — a too-tall band gets its leading teeth planed and
    # sheds slivers at the disc rim. Every tooth of the ring is identical.
    if cf.g_bev:
        ceil_F = gear_F_ceiling(cf)
        t = gear_teeth_bevel45(cf, cf.z_bot)
        trimmed = (t ^ wafer_cut(cf, 1, -cf.clrOff - 0.2, cf.tall,
                                 extra_r=0.5)).volume()
        if trimmed > 0.001:
            print(f"FAIL: neighbour clearance cut removes {trimmed:.2f} mm3 "
                  f"of gear teeth — lower gear_F below the {ceil_F:.2f} "
                  f"ceiling (neighbour wafer plane − clr over the annulus)")
            return 1
        print(f"  gate    clearance cut removes {trimmed:.5f} mm3 of teeth "
              f"(gear_F {cf.gear_F} vs {ceil_F:.2f} ceiling) — all "
              f"{cf.teeth} teeth identical")
    return 0



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


def build_pinion(cf, T=None, face=None, bore=4.2, flat=0.5, backlash=None):
    """The mating pinion. bevel45 (default): the beveloid pinion, big end
    at the front, axis PARALLEL to the halo axis, plus a Ø16 hub on the
    motor side for the 22PG-2430BL's 4 mm D-shaft (bore 4.2, 0.5 flat).
    'spur' legacy: straight spur. T = teeth/segment gives ratio N:1."""
    T = T or cf.tps
    if cf.g_bev and (T == cf.tps or T == cf.pin_T):
        p, g = bevel_pinion(cf, backlash=backlash)
        bg = bevel_geom(cf)               # hub dims shared with bracket_stl
        face = bg['face'] + bg['hub_len']
        p = p + Manifold.cylinder(bg['hub_len'] + 0.1, bg['hub_r'],
                                  bg['hub_r'], 96).translate(
            [0.0, 0.0, bg['face'] - 0.1])
        z_lo = 0.0
    else:
        face = face or cf.tmin
        pts, g = pinion_profile(cf, T, backlash=backlash)
        p = prism(pts, 0.0, face)
        z_lo = 0.0
    if bore:
        L = face - z_lo + 2.0
        p = p - Manifold.cylinder(L + 2.0, bore / 2, bore / 2, 64).translate(
            [0, 0, z_lo - 1.0])
        if flat:                          # D-flat for the N20 D-shaft
            w = bore
            p = p - prism([(bore/2 - flat, -w), (bore/2 - flat, w), (w, w), (w, -w)],
                          z_lo - 1.0, L + 2.0)
    return p, g


def check_mesh(cf, T=None, steps=24, backlash=None):
    """Roll the pinion through one ring tooth pitch and measure boolean overlap.

    'spur': the old planar internal mesh (co-rotating, same axis — an
    external-pair sign here reads as 245 mm3 of false interference).
    'bevel45': the CROSSED pair — radial-axis pinion spinning ratio*d,
    runner at the nominal axis height (the cutter ran 0.3 lower)."""
    T = T or cf.tps
    F = cf.tmin
    ratio = cf.teeth / T
    if not cf.g_bev:
        ring = gear_teeth(cf, 0.0) + prism(
            arc(cf.g_root + 1.0, -cf.half, cf.half, 120) +
            arc(cf.Ri + 6.0, cf.half, -cf.half, 120), 0.0, F)
        pin, g = build_pinion(cf, T, face=F, bore=0.0, flat=0.0, backlash=backlash)
        centre = cf.g_pitch - g['rp']
        worst = 0.0
        for i in range(steps):
            d = (2 * math.pi / cf.teeth) * i / steps
            pr = d * ratio                       # internal pair CO-ROTATES
            r2 = ring.rotate([0, 0, math.degrees(d)])
            p2 = pin.rotate([0, 0, math.degrees(pr)]).translate([centre, 0, 0])
            worst = max(worst, (r2 ^ p2).volume())
        return dict(centre=centre, ratio=ratio, worst_overlap=worst, axis='parallel', **g)
    # bevel45: roll the RUNNING pinion (gear_bl-thinned) against the
    # GENERATED teeth through one ring pitch. Crossed axes: the pinion
    # spins ratio*d about its radial axis at the nominal height (the
    # cutter ran 0.3 lower, dr=-0.3 — that IS the tip relief).
    F = cf.gear_F
    ring = gear_teeth_bevel45(cf, 0.0) + prism(
        arc(cf.g_fi, -cf.half, cf.half, 160) +
        arc(cf.g_fi + 12.0, cf.half, -cf.half, 160), 0.0, F)
    pin, g = bevel_pinion(cf, backlash=backlash)
    bg = bevel_geom(cf)
    worst = 0.0
    for i in range(steps):
        d = (2 * math.pi / cf.teeth) * i / steps
        r2 = ring.rotate([0, 0, math.degrees(d)])
        p2 = bevel_pinion_at(cf, pin, d)
        worst = max(worst, (r2 ^ p2).volume())
    return dict(ratio=cf.pin_ratio, worst_overlap=worst,
                axis='crossed (radial)', zax=bg['zax'], **g)


if __name__ == '__main__':
    sys.exit(main())
