#!/usr/bin/env python3
"""Straight-bevel-gear critical-angle calculator (Streamlit).

Implements the spherical-involute pipeline from ZHY Gear's "Straight Bevel
Gears: Analysis and Applications" (Feb 2026), corrected and cross-checked
against the academic literature:

  [1] Litvin F.L., Fuentes A., "Gear Geometry and Applied Theory", 2nd ed.,
      Cambridge, 2004 (generation by imaginary crown gear; equation of
      meshing).
  [2] Vullo V., "Gears Vol. 1: Geometric and Kinematic Design", Springer,
      2020 (bevel geometry, Tredgold virtual spur, height modification).
  [3] Radzevich S.P., "Handbook of Practical Gear Design and Manufacture",
      2nd ed., CRC, 2012 (proportions, undercut limits, manufacture).
  [4] Ligata H., Zhang H.H., "Geometry Definition and Contact Analysis of
      Spherical Involute Straight Bevel Gears", IAJC-ASEE 2011 — source of
      the closed-form flank surface (eq. 1) and sin(delta_b) =
      sin(delta)*cos(alpha) (eq. 2) used here.
  [5] Shunmugam M.S., Subba Rao B., Jayaprakash V., "Establishing Gear Tooth
      Surface Geometry and Normal Deviation", Mech. Mach. Theory 33(5), 1998
      (normal-deviation inspection of the established surface).

Three errors in the ZHY article, demonstrated in --selftest, are NOT
reproduced (see the "References & article errata" tab):
  (a) base cone printed as arctan(tan d * cos a); spherical-involute truth
      is arcsin(sin d * cos a) [4, eq. 2],
  (b) roll angle printed as arccos(cos d_b / cos d) — argument > 1 for every
      valid gear (domain error); the spherical right triangle gives
      arccos(cos d / cos d_b),
  (c) its contact-ratio-from-unfolding-angles formula yields 0.025 on its
      own z=20/30 worked example (claimed 1.65); the exact spherical and
      Tredgold values are computed instead.

Run:       uv run --with streamlit streamlit run scripts/bevel_calc_app.py
Self-test: python3 scripts/bevel_calc_app.py --selftest   (stdlib only)

NOTE for this repo: the wafer-halo drive is a GENERATED crossed beveloid
pair (conjugacy by CSG generation, free cone angles — see GEARS.md). This
app covers classical intersecting-axis straight bevels; use it for sizing
studies and coupon pairs, not as a gate on the halo drive.
"""

import math
import sys

TAU = 2.0 * math.pi
D2R = math.pi / 180.0


# --------------------------------------------------------------------------
# Core spherical-involute relations (pure stdlib; angles in radians)
# --------------------------------------------------------------------------

def pitch_cone_angles(z1, z2, sigma):
    """Standard intersecting-axis split: tan d1 = sin S / (z2/z1 + cos S)."""
    d1 = math.atan2(math.sin(sigma), (z2 / z1) + math.cos(sigma))
    return d1, sigma - d1


def base_cone_angle(delta, alpha, formula="spherical"):
    """Base cone angle.

    'spherical'  : sin d_b = sin d * cos a   (Ligata & Zhang eq. 2; Litvin)
    'article'    : d_b = arctan(tan d * cos a)  (as printed in the ZHY page)
    """
    if formula == "article":
        if delta >= math.pi / 2:
            raise ValueError("article formula undefined at delta >= 90 deg")
        return math.atan(math.tan(delta) * math.cos(alpha))
    return math.asin(math.sin(delta) * math.cos(alpha))


def roll_arc(delta_x, delta_b):
    """Great-circle roll arc phi to reach cone angle delta_x from the base
    cone: cos(delta_x) = cos(delta_b) * cos(phi). Returns 0.0 when delta_x
    <= delta_b (point below the base cone — no involute there)."""
    c = math.cos(delta_x) / math.cos(delta_b)
    if c >= 1.0:
        return 0.0
    return math.acos(max(-1.0, c))


def unfold_theta(delta_b, phi):
    """Unfolding angle theta = arctan(sin d_b * tan phi) (article text form —
    its table prints a division, which diverges at phi -> 0; the product form
    is the one that is 0 at the base cone and monotonic)."""
    return math.atan(math.sin(delta_b) * math.tan(phi))


def involute_azimuth(delta_b, phi):
    """Azimuth of the involute point about the gear axis, measured from the
    involute start meridian: psi = phi/sin(d_b) - arctan(tan(phi)/sin(d_b)).
    (Spherical involute function — the planar inv(a) analog.)"""
    sb = math.sin(delta_b)
    return phi / sb - math.atan(math.tan(phi) / sb)


def spherical_involute_point(R, delta_b, beta):
    """Flank point, Ligata & Zhang (2011) eq. (1). beta is the base-cone
    rotation angle; the rolled great-circle arc is phi = beta*sin(delta_b).
    Gear axis = +z, involute starts (beta=0) on the base cone at azimuth 0."""
    sb, cb = math.sin(delta_b), math.cos(delta_b)
    phi = beta * sb
    x = R * (math.cos(phi) * sb * math.cos(beta) + math.sin(phi) * math.sin(beta))
    y = R * (math.cos(phi) * sb * math.sin(beta) - math.sin(phi) * math.cos(beta))
    z = R * math.cos(phi) * cb
    return x, y, z


# --------------------------------------------------------------------------
# Per-gear and pair solutions
# --------------------------------------------------------------------------

def solve_gear(z, m, alpha, delta, delta_a=None, delta_f=None,
               ha_c=1.0, hf_c=1.25, base_formula="spherical"):
    """All critical angles for one gear. Inputs in radians, module in mm."""
    g = {"z": z, "delta": delta}
    r = 0.5 * m * z                      # pitch radius at the outer end
    Re = r / math.sin(delta)             # outer cone distance
    g["r"], g["Re"] = r, Re
    g["rb"] = r * math.cos(alpha)

    if delta_a is None:
        delta_a = delta + math.atan(ha_c * m / Re)
    if delta_f is None:
        delta_f = delta - math.atan(hf_c * m / Re)
    g["delta_a"], g["delta_f"] = delta_a, delta_f
    g["theta_add"] = delta_a - delta
    g["theta_ded"] = delta - delta_f
    g["back_cone"] = math.pi / 2 - delta

    db = base_cone_angle(delta, alpha, base_formula)
    g["delta_b"] = db
    g["phi_p"] = roll_arc(delta, db)
    g["phi_a"] = roll_arc(delta_a, db)
    g["phi_f"] = roll_arc(delta_f, db)
    g["theta_p"] = unfold_theta(db, g["phi_p"])
    g["theta_a"] = unfold_theta(db, g["phi_a"])
    # Article step 6: start point of involute measurement.
    g["theta_s"] = g["theta_p"] + (g["phi_a"] - g["phi_p"]) - g["theta_a"]
    g["root_below_base"] = delta_f < db
    # Undercut limit via Tredgold virtual spur (Vullo/Radzevich):
    # z_v = z/cos(delta) must be >= 2*ha_c/sin^2(alpha).
    g["zv"] = z / math.cos(delta)
    g["zv_min"] = 2.0 * ha_c / (math.sin(alpha) ** 2)
    return g


def contact_ratio_article(g1, g2):
    """As printed on the ZHY page: (th_a1+th_a2-th_p1-th_p2)/(2*pi).
    Demonstrably wrong (~40x low on its own example) — shown for reference."""
    return (g1["theta_a"] + g2["theta_a"]
            - g1["theta_p"] - g2["theta_p"]) / TAU


def contact_ratio_spherical(g1, g2):
    """Exact spherical involute contact ratio: each gear turns
    d_beta = d_phi/sin(delta_b) while contact runs from the pitch point to
    its tip cone; sum both in units of the angular pitch 2*pi/z."""
    eps = 0.0
    for g in (g1, g2):
        dphi = g["phi_a"] - g["phi_p"]
        eps += g["z"] * dphi / math.sin(g["delta_b"]) / TAU
    return eps


def contact_ratio_tredgold(g1, g2, m, alpha):
    """Tredgold back-cone virtual spur pair (Vullo ch. 12; Radzevich).
    Addendum recovered from the (possibly overridden) tip cone angle."""
    rv, ra, rb = [], [], []
    for g in (g1, g2):
        rvi = g["r"] / math.cos(g["delta"])
        ha_mm = g["Re"] * math.tan(g["theta_add"])
        rv.append(rvi)
        ra.append(rvi + ha_mm)
        rb.append(rvi * math.cos(alpha))
    a = rv[0] + rv[1]
    path = (math.sqrt(max(0.0, ra[0] ** 2 - rb[0] ** 2))
            + math.sqrt(max(0.0, ra[1] ** 2 - rb[1] ** 2))
            - a * math.sin(alpha))
    return path / (math.pi * m * math.cos(alpha))


def solve_pair(m, z1, z2, sigma, alpha, ha_c=1.0, hf_c=1.25,
               base_formula="spherical", delta_override=None,
               delta_a_override=(None, None)):
    d1, d2 = pitch_cone_angles(z1, z2, sigma)
    if delta_override is not None:
        d1, d2 = delta_override
    g1 = solve_gear(z1, m, alpha, d1, delta_a_override[0], None,
                    ha_c, hf_c, base_formula)
    g2 = solve_gear(z2, m, alpha, d2, delta_a_override[1], None,
                    ha_c, hf_c, base_formula)
    pair = {
        "g1": g1, "g2": g2, "sigma": sigma, "ratio": z2 / z1,
        "eps_article": contact_ratio_article(g1, g2),
        "eps_spherical": contact_ratio_spherical(g1, g2),
        "eps_tredgold": contact_ratio_tredgold(g1, g2, m, alpha),
    }
    warnings = []
    if abs((g1["delta"] + g2["delta"]) - sigma) > 1e-9:
        warnings.append(
            f"δ1+δ2 = {(g1['delta'] + g2['delta']) / D2R:.3f}° ≠ Σ = "
            f"{sigma / D2R:.3f}° — cone apexes do not meet; the pair cannot "
            "mount at a common apex.")
    if abs(g1["Re"] - g2["Re"]) > 1e-6 * g1["Re"]:
        warnings.append(
            f"Outer cone distances differ (Re1 {g1['Re']:.3f} vs Re2 "
            f"{g2['Re']:.3f} mm) — apexes mismatch; check δ overrides.")
    for name, g in (("gear 1", g1), ("gear 2", g2)):
        if g["delta_a"] >= math.pi / 2:
            warnings.append(f"{name}: tip cone δa ≥ 90° — not a valid bevel.")
        if g["root_below_base"]:
            warnings.append(
                f"{name}: root cone ({g['delta_f'] / D2R:.2f}°) lies below "
                f"the base cone ({g['delta_b'] / D2R:.2f}°) — flank below "
                "the base cone is fillet/trochoid, not involute.")
        if g["zv"] < g["zv_min"]:
            warnings.append(
                f"{name}: undercut — virtual tooth count z_v = {g['zv']:.1f} "
                f"< {g['zv_min']:.1f} (Tredgold limit at this α, ha*).")
    if pair["eps_spherical"] < 1.0:
        warnings.append(
            f"Spherical contact ratio {pair['eps_spherical']:.3f} < 1.0 — "
            "motion is not continuous. Increase teeth/addendum or α.")
    elif pair["eps_spherical"] < 1.2:
        warnings.append(
            f"Spherical contact ratio {pair['eps_spherical']:.3f} < 1.2 — "
            "legal but noisy/fragile; conventional floor is 1.2.")
    pair["warnings"] = warnings
    return pair


# --------------------------------------------------------------------------
# Flank point cloud for CAD import
# --------------------------------------------------------------------------

def flank_point_cloud(g, face_width_frac=0.30, n_sections=5, n_profile=20,
                      backlash_half_angle=0.0):
    """Both flanks of one tooth as loft-ready sections.

    Rows: (flank, section, R, index, x, y, z). Sections at constant cone
    distance R from Re*(1-frac) to Re; profile sampled from
    max(root, base) cone to the tip cone. The tooth is centred on azimuth 0
    with half angular thickness pi/(2z) at the pitch cone (minus backlash).
    Import: one fitted spline per (flank, section), then loft; add the root
    fillet in CAD (see the guidance tab).
    """
    db = g["delta_b"]
    beta_lo = g["phi_f"] / math.sin(db)          # 0.0 if root below base
    beta_hi = g["phi_a"] / math.sin(db)
    psi_p = involute_azimuth(db, g["phi_p"])
    half_tooth = math.pi / (2.0 * g["z"]) - backlash_half_angle

    rows = []
    Re = g["Re"]
    for s in range(n_sections):
        R = Re * (1.0 - face_width_frac) + (Re * face_width_frac) * (
            s / (n_sections - 1) if n_sections > 1 else 1.0)
        for i in range(n_profile):
            beta = beta_lo + (beta_hi - beta_lo) * i / (n_profile - 1)
            x, y, z = spherical_involute_point(R, db, beta)
            psi = math.atan2(y, x)               # azimuth of the raw point
            rr = math.hypot(x, y)
            # place each flank's pitch point at -/+ half tooth angle about
            # the tooth centreline (azimuth 0); flank B mirrors flank A
            for flank in ("A", "B"):
                if flank == "A":
                    ang = (psi - psi_p) - half_tooth
                else:
                    ang = half_tooth - (psi - psi_p)
                rows.append((flank, s, R, i,
                             rr * math.cos(ang), rr * math.sin(ang), z))
    return rows


def point_cloud_csv(rows):
    out = ["flank,section,R_mm,i,x_mm,y_mm,z_mm"]
    for f, s, R, i, x, y, z in rows:
        out.append(f"{f},{s},{R:.6f},{i},{x:.6f},{y:.6f},{z:.6f}")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# Self-test (stdlib only): python3 scripts/bevel_calc_app.py --selftest
# --------------------------------------------------------------------------

def selftest():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")
        ok &= bool(cond)

    # -- identities on the ZHY worked example (z 20/30, m5, a20, d 30/60,
    #    da 32.5/62.5) --
    alpha = 20 * D2R
    p = solve_pair(5.0, 20, 30, 90 * D2R, alpha,
                   delta_override=(30 * D2R, 60 * D2R),
                   delta_a_override=(32.5 * D2R, 62.5 * D2R))
    g1, g2 = p["g1"], p["g2"]

    for name, g in (("g1", g1), ("g2", g2)):
        check(f"{name} base-cone identity sin(db)=sin(d)cos(a)",
              abs(math.sin(g["delta_b"])
                  - math.sin(g["delta"]) * math.cos(alpha)) < 1e-12)
        check(f"{name} roll identity cos(d)=cos(db)cos(phi_p)",
              abs(math.cos(g["delta"])
                  - math.cos(g["delta_b"]) * math.cos(g["phi_p"])) < 1e-12)
        check(f"{name} theta_s positive", g["theta_s"] > 0,
              f"theta_s={g['theta_s']:.6f} rad")

    # -- the article's own numbers do NOT satisfy its formulas --
    check("article eps formula collapses on its own example",
          p["eps_article"] < 0.05, f"eps_article={p['eps_article']:.4f} "
          "(article claims 1.65)")
    # With the article's assumed tips (32.5/62.5 deg, sub-standard addendum)
    # the two exact methods must agree closely with each other.
    check("spherical and Tredgold agree at the assumed tips",
          abs(p["eps_spherical"] - p["eps_tredgold"]) < 0.05,
          f"spherical={p['eps_spherical']:.3f} "
          f"tredgold={p['eps_tredgold']:.3f}")
    # With STANDARD addendum ha*=1 the pair reaches the article's claimed
    # magnitude (~1.65) — its assumed tips undercut its own claim.
    ps = solve_pair(5.0, 20, 30, 90 * D2R, alpha,
                    delta_override=(30 * D2R, 60 * D2R))
    check("standard-addendum Tredgold ~ 1.69 (article claimed 1.65)",
          abs(ps["eps_tredgold"] - 1.69) < 0.10,
          f"eps_tredgold={ps['eps_tredgold']:.3f}")

    # -- Ligata & Zhang eq. (1): point stays on the sphere of radius R --
    R, db = 100.0, g1["delta_b"]
    for beta in (0.0, 0.1, 0.3, 0.6):
        x, y, z = spherical_involute_point(R, db, beta)
        check(f"eq(1) |P|=R at beta={beta}",
              abs(math.sqrt(x * x + y * y + z * z) - R) < 1e-9)

    # eq. (1) agrees with the polar/azimuth derivation
    beta = 0.4
    x, y, z = spherical_involute_point(R, db, beta)
    phi = beta * math.sin(db)
    check("eq(1) polar angle matches cos(d)=cos(db)cos(phi)",
          abs(z - R * math.cos(db) * math.cos(phi)) < 1e-9)
    psi_expect = beta - math.atan(math.tan(phi) / math.sin(db))
    check("eq(1) azimuth matches beta - atan(tan(phi)/sin(db))",
          abs(math.atan2(y, x) - psi_expect) < 1e-9)

    # -- pressure-angle property: at the pitch cone the flank tangent makes
    #    angle alpha with the meridian (radial) direction --
    beta_p = g1["phi_p"] / math.sin(db)
    h = 1e-6
    p0 = spherical_involute_point(R, db, beta_p - h)
    p1 = spherical_involute_point(R, db, beta_p + h)
    t = [(b - a) / (2 * h) for a, b in zip(p0, p1)]
    pt = spherical_involute_point(R, db, beta_p)
    # meridian (polar) unit vector at pt: d/d(delta) of spherical coords
    rr = math.hypot(pt[0], pt[1])
    d = math.acos(pt[2] / R)
    psi = math.atan2(pt[1], pt[0])
    e_pol = (math.cos(d) * math.cos(psi), math.cos(d) * math.sin(psi),
             -math.sin(d))
    tn = math.sqrt(sum(v * v for v in t))
    cosang = abs(sum(a * b for a, b in zip(t, e_pol))) / tn
    ang = math.acos(min(1.0, cosang))
    check("flank tangent vs meridian at pitch = alpha",
          abs(ang - alpha) < 1e-4, f"measured {ang / D2R:.4f} deg")

    # -- tooth thickness: angle between flanks at the pitch cone = pi/z --
    g = solve_gear(20, 5.0, alpha, 30 * D2R)
    rows = flank_point_cloud(g, n_sections=2, n_profile=40)
    at_pitch = {}
    for f, s, Rr, i, x, y, z in rows:
        if s == 0:
            dd = math.acos(z / math.sqrt(x * x + y * y + z * z))
            key = (f, abs(dd - g["delta"]))
            if f not in at_pitch or key[1] < at_pitch[f][0]:
                at_pitch[f] = (key[1], math.atan2(y, x))
    span = abs(at_pitch["A"][1] - at_pitch["B"][1])
    check("flank-to-flank angle at pitch ~ pi/z",
          abs(span - math.pi / g["z"]) < 0.01,
          f"span={span:.5f} vs pi/z={math.pi / g['z']:.5f}")

    # -- halo defaults run clean --
    hp = solve_pair(5.384, 20, 108, 90 * D2R, alpha)
    check("halo default pair solves", 1.0 < hp["eps_spherical"] < 3.0,
          f"eps={hp['eps_spherical']:.3f}, d1={hp['g1']['delta'] / D2R:.2f} deg")

    print("\nSELF-TEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


# --------------------------------------------------------------------------
# Streamlit UI
# --------------------------------------------------------------------------

FORMULA_NOTES = """
**Corrections applied to the ZHY article** (each demonstrated in
`--selftest`):

1. **Base cone angle** — article prints `δb = arctan(tan δ · cos α)`. The
   spherical involute gives `sin δb = sin δ · cos α` (Ligata & Zhang eq. 2;
   Litvin §derivation via Clairaut's relation on the generating great
   circle). At δ=45°, α=20° the two differ by 1.6° — enough to matter for
   inspection. A sidebar toggle lets you reproduce the article's variant.
2. **Roll angles** — article prints `φ = arccos(cos δb / cos δ)`, whose
   argument exceeds 1 for every valid gear (δb < δ). The spherical right
   triangle (right angle at the tangency point) gives
   `cos δ = cos δb · cos φ`, i.e. the reciprocal argument.
3. **Contact ratio** — the article's `ε = (θa1+θa2−θp1−θp2)/2π` evaluates to
   ≈0.025 on its own z=20/30 worked example (it claims 1.65). This app
   reports the exact spherical value (gear rotations between pitch and tip
   contact, in units of the angular pitch) and the classical Tredgold
   virtual-spur value. With standard addendum (ha*=1) Tredgold gives 1.69
   on that example — the article's claimed magnitude; with the article's
   *assumed* tip angles (32.5°/62.5°, a sub-standard addendum) both exact
   methods agree at ε ≈ 1.40, i.e. the article's assumed tips contradict
   its own claimed contact ratio.
4. **Unfolding angle** — the article's text and its table disagree
   (`arctan(sin δb · tan φ)` vs `arctan(sin δb / tan φ)`). The product form
   is used: it is 0 at the base cone and monotonic in roll, which is what a
   measurement start point requires; the division form diverges to 90° at
   zero roll.
"""

CAD_GUIDANCE = """
### Procedurally generating straight bevel gear + pinion in CAD

Three routes, ordered by iteration speed. All three want the same parameter
vector: `(m, z1, z2, Σ, α, ha*, hf*, face width b, fillet)` — everything
else on the *Critical angles* tab derives from it.

**1. Analytic spherical-involute loft — fastest to iterate (this app feeds
it).** The flank is closed-form (Ligata & Zhang 2011, eq. 1): one spherical
involute per cone-distance section, both flanks positioned ± π/(2z) at the
pitch cone. Recipe:

- Download the flank point cloud below (5 sections × 20 points per flank by
  default). In OnShape/Fusion/SolidWorks: *fit spline through each
  (flank, section) row group* → **loft** flank A, flank B, tip-cone and
  root-cone surfaces → trim/knit → circular pattern `z×`, boolean with the
  gear blank (front cone + back cone + bore).
- Root fillet is **not** involute — add it in CAD as a rolling-ball fillet
  sized to the standard clearance (`c* · m = 0.25 m` here), or generate the
  true trochoid if you care about bending stress (Litvin ch. 6 treatment).
- Everything is a function of the sidebar sliders, so a parametric CAD
  model driven by these numbers (like this repo's
  `scripts/onshape/wafer_halo_beveloid.fs` FeatureScript, which lofts
  analytic involutes the same way) re-solves in seconds per iteration.

**2. Generation / virtual cutting — the ground truth (what this repo's
`segment_stl.py` does).** Litvin's crown-rack ("third member") principle
[1]: sweep an imaginary crown gear (pitch angle 90°, the bevel analog of
the rack) through the meshing motion and boolean-subtract every step from
the blank. Conjugacy is guaranteed *by construction* — even for
non-standard geometry (this repo's crossed beveloid pair at free cone
angles is exactly that). Slower per iterate (CSG sweep), but it is the
route that never lies; gate it with a mesh-sweep interference check
(target 0.000 mm³, as `segment_stl.py` enforces).

**3. Tredgold virtual spur — sizing only.** Develop each back cone into a
plane: virtual spur with `z_v = z / cos δ`, `r_v = r / cos δ` (Vullo [2],
Radzevich [3]). Use it to iterate contact ratio, undercut
(`z_v ≥ 2ha*/sin²α`), and Lewis bending *before* touching solid geometry —
it is three lines of arithmetic per candidate.

### Iterate-and-optimize loop that works

1. **Sweep parameters** with the pure-math core of this file (import it —
   the solver is stdlib-only, no Streamlit needed): grid over `z1, α, ha*`
   at fixed ratio; reject on the gates below. Milliseconds per candidate.
2. **Gates** (all computed on the *Critical angles* tab):
   ε_spherical ≥ 1.2 · no undercut (`z_v ≥ z_v,min`) · root above base cone
   if you want all-involute flanks · δa < 90° · apexes meet (δ1+δ2 = Σ) ·
   for FDM: root tooth section ≥ ~0.8 mm section-module (this repo's
   measured print floor).
3. **Generate the solid** for survivors (route 1 for speed, route 2 for
   truth) and run a boolean mesh sweep of the pair through one pitch —
   accept only 0-interference.
4. **Verify the surface** (Shunmugam et al. [5]): probe the printed/machined
   flank on a CMM against eq. (1) evaluated at the probe's (R, β) — the
   paper's normal-deviation method is exactly this comparison; the article's
   θs is where profile measurement starts.

**Load-bearing vs free parameters** (mirrors this repo's GEARS.md lesson):
tooth counts and Σ are load-bearing (ratio, apex closure, tiling); module
is pure scale; face width is packaging (keep b ≤ Re/3 per [2,3] or the toe
gets thin); addendum/dedendum trade contact ratio against undercut. If the
pair is *height-modified* (x1 = −x2, the standard bevel move [2,3]), pitch
and root cones stay put — raise pinion addendum / drop gear addendum to
balance sliding when z1 is small.
"""

REFERENCES_MD = """
### References

1. Litvin F.L., Fuentes A., *Gear Geometry and Applied Theory*, 2nd ed.,
   Cambridge University Press, 2004. — Generation theory: equation of
   meshing, imaginary crown gear, TCA.
2. Vullo V., *Gears Volume 1: Geometric and Kinematic Design*, Springer
   Series in Solid and Structural Mechanics, 2020. — Bevel geometry,
   Tredgold approximation, height modification.
3. Radzevich S.P., *Handbook of Practical Gear Design and Manufacture*,
   2nd ed., CRC Press, 2012. — Proportions, undercut limits, manufacturing
   methods (Revacycle/Coniflex vs generated).
4. Ligata H., Zhang H.H., "Geometry Definition and Contact Analysis of
   Spherical Involute Straight Bevel Gears", *IAJC-ASEE International
   Conference*, 2011. — Closed-form flank surface (eq. 1) and base-cone
   relation (eq. 2) implemented here.
   [PDF](https://ijme.us/cd_11/PDF/Paper%20163%20ENG%20107.pdf)
5. Shunmugam M.S., Subba Rao B., Jayaprakash V., "Establishing Gear Tooth
   Surface Geometry and Normal Deviation", *Mechanism and Machine Theory*,
   33(5), pp. 525–534, 1998. — Inspection: normal deviation of a measured
   flank from the established analytic surface.
6. ZHY Gear, "Straight Bevel Gears: Analysis and Applications", Feb 2026 —
   the pipeline structure (steps 1–6, θs, ε) followed here, with the
   corrections listed below.
"""


def _angle_rows(g):
    rows = [
        ("Pitch cone δ", g["delta"]),
        ("Base cone δb", g["delta_b"]),
        ("Tip (face) cone δa", g["delta_a"]),
        ("Root cone δf", g["delta_f"]),
        ("Back cone (90°−δ)", g["back_cone"]),
        ("Addendum angle θ_add", g["theta_add"]),
        ("Dedendum angle θ_ded", g["theta_ded"]),
        ("Pitch roll arc φp", g["phi_p"]),
        ("Tip roll arc φa", g["phi_a"]),
        ("Root roll arc φf", g["phi_f"]),
        ("Unfolding angle θp", g["theta_p"]),
        ("Unfolding angle θa", g["theta_a"]),
        ("Meas. start angle θs", g["theta_s"]),
    ]
    return [{"Angle": n, "deg": f"{v / D2R:.4f}", "rad": f"{v:.6f}"}
            for n, v in rows]


def _cone_chart_df(pair):
    import pandas as pd
    rows = []
    axes = {"gear 1 (pinion)": 0.0, "gear 2 (gear)": pair["sigma"]}
    styles = [("pitch", "delta"), ("base", "delta_b"),
              ("tip", "delta_a"), ("root", "delta_f")]
    for (gname, axis), g in zip(axes.items(), (pair["g1"], pair["g2"])):
        L = g["Re"]
        rows.append({"series": f"{gname} axis", "kind": "axis",
                     "x": 0.0, "y": 0.0, "order": 0})
        rows.append({"series": f"{gname} axis", "kind": "axis",
                     "x": 1.15 * L * math.cos(axis),
                     "y": 1.15 * L * math.sin(axis), "order": 1})
        for kind, key in styles:
            for sgn in (+1, -1):
                a = axis + sgn * g[key]
                s = f"{gname} {kind} {'+' if sgn > 0 else '−'}"
                rows.append({"series": s, "kind": kind,
                             "x": 0.0, "y": 0.0, "order": 0})
                rows.append({"series": s, "kind": kind,
                             "x": L * math.cos(a), "y": L * math.sin(a),
                             "order": 1})
    return pd.DataFrame(rows)


def main():
    import streamlit as st

    st.set_page_config(page_title="Straight Bevel Gear Angles",
                       page_icon="⚙️", layout="wide")
    st.title("Straight bevel gear — critical angle calculator")
    st.caption(
        "Spherical-involute pipeline after ZHY Gear (2026), corrected per "
        "Ligata & Zhang (2011) and Litvin & Fuentes (2004). This repo's "
        "halo drive is a *generated crossed beveloid* (GEARS.md) — use "
        "this for classical intersecting-axis pairs and sizing studies.")

    sb = st.sidebar
    sb.header("Pair parameters")
    m = sb.number_input("Module m (mm, outer end)", 0.1, 50.0, 5.384, 0.1,
                        format="%.3f")
    z1 = int(sb.number_input("Pinion teeth z1", 4, 200, 20, 1))
    z2 = int(sb.number_input("Gear teeth z2", 4, 400, 108, 1))
    sigma_d = sb.number_input("Shaft angle Σ (deg)", 10.0, 170.0, 90.0, 1.0)
    alpha_d = sb.number_input("Pressure angle α (deg)", 10.0, 30.0, 20.0, 0.5)
    ha_c = sb.number_input("Addendum coeff. ha*", 0.5, 1.5, 1.0, 0.05)
    hf_c = sb.number_input("Dedendum coeff. hf*", 0.6, 2.0, 1.25, 0.05)

    sb.header("Formula variant")
    base_formula = sb.radio(
        "Base cone δb", ["spherical", "article"],
        help="spherical: sin δb = sin δ·cos α (correct). "
             "article: arctan(tan δ·cos α) as printed on the ZHY page.")

    sb.header("Overrides")
    delta_override = None
    if sb.checkbox("Override pitch cone angles"):
        d1o = sb.number_input("δ1 (deg)", 1.0, 89.0, 30.0, 0.5)
        d2o = sb.number_input("δ2 (deg)", 1.0, 89.0, 60.0, 0.5)
        delta_override = (d1o * D2R, d2o * D2R)
    da_override = (None, None)
    if sb.checkbox("Override tip cone angles"):
        da1 = sb.number_input("δa1 (deg)", 1.0, 89.9, 32.5, 0.1)
        da2 = sb.number_input("δa2 (deg)", 1.0, 89.9, 62.5, 0.1)
        da_override = (da1 * D2R, da2 * D2R)

    sb.header("Flank export")
    fw = sb.slider("Face width / Re", 0.10, 0.40, 0.30, 0.01)
    n_sec = sb.slider("Loft sections", 2, 12, 5)
    n_pts = sb.slider("Points per flank curve", 8, 60, 20)

    try:
        pair = solve_pair(m, z1, z2, sigma_d * D2R, alpha_d * D2R, ha_c,
                          hf_c, base_formula, delta_override, da_override)
    except ValueError as e:
        st.error(f"Cannot solve: {e}")
        return
    g1, g2 = pair["g1"], pair["g2"]

    tabs = st.tabs(["Critical angles", "Contact ratio",
                    "Tooth geometry & CAD export", "CAD design guidance",
                    "References & article errata"])

    with tabs[0]:
        for w in pair["warnings"]:
            (st.error if "not continuous" in w or "≥ 90°" in w
             else st.warning)(w)
        c0, c1, c2, c3 = st.columns(4)
        c0.metric("Ratio z2/z1", f"{pair['ratio']:.3f}")
        c1.metric("Outer cone distance Re", f"{g1['Re']:.2f} mm")
        c2.metric("δ1 / δ2",
                  f"{g1['delta'] / D2R:.2f}° / {g2['delta'] / D2R:.2f}°")
        c3.metric("Virtual teeth z_v1 / z_v2",
                  f"{g1['zv']:.1f} / {g2['zv']:.1f}")
        colA, colB = st.columns(2)
        for col, name, g in ((colA, f"Gear 1 (pinion, z={z1})", g1),
                             (colB, f"Gear 2 (gear, z={z2})", g2)):
            with col:
                st.subheader(name)
                st.dataframe(_angle_rows(g), hide_index=True,
                             width="stretch")
        st.subheader("Cone cross-section (apex at origin)")
        try:
            import altair as alt
            df = _cone_chart_df(pair)
            chart = alt.Chart(df).mark_line().encode(
                x=alt.X("x:Q", scale=alt.Scale(zero=False)),
                y=alt.Y("y:Q", scale=alt.Scale(zero=False)),
                detail="series:N",
                color=alt.Color("kind:N", scale=alt.Scale(
                    domain=["axis", "pitch", "base", "tip", "root"],
                    range=["#999999", "#1f77b4", "#d62728", "#2ca02c",
                           "#ff7f0e"])),
                strokeDash=alt.StrokeDash("kind:N", scale=alt.Scale(
                    domain=["axis", "pitch", "base", "tip", "root"],
                    range=[[2, 2], [0], [1, 3], [6, 3], [6, 3]])),
                order="order:O",
            ).properties(height=450).interactive()
            st.altair_chart(chart, width="stretch")
            st.caption(
                "Both gears' pitch rays coincide along the common pitch "
                "line when δ1+δ2 = Σ — the visual apex-closure check.")
        except Exception as e:  # chart is decorative; never block numbers
            st.info(f"Chart unavailable: {e}")

    with tabs[1]:
        c1_, c2_, c3_ = st.columns(3)
        c1_.metric("ε — exact spherical", f"{pair['eps_spherical']:.3f}",
                   help="Gear rotations from pitch-point to tip contact, "
                        "both members, in units of the angular pitch.")
        c2_.metric("ε — Tredgold virtual spur",
                   f"{pair['eps_tredgold']:.3f}",
                   help="Back-cone development; the classical design value.")
        c3_.metric("ε — article formula (broken)",
                   f"{pair['eps_article']:.4f}",
                   help="(θa1+θa2−θp1−θp2)/2π as printed — fails its own "
                        "worked example by ~40×. Shown for traceability.")
        st.markdown(
            "Design to the **spherical** value; quote **Tredgold** when "
            "comparing against catalogs/standards (they agree within a few "
            "percent for sane geometry — here "
            f"{abs(pair['eps_spherical'] - pair['eps_tredgold']):.3f} "
            "apart). Floor: 1.2; comfortable: ≥ 1.4. The contact ratio "
            "varies slightly along the face width when apexes are offset — "
            "re-check at the toe by dropping the module to the toe value.")

    with tabs[2]:
        st.markdown("**Flank surface — Ligata & Zhang (2011), eq. (1)** "
                    "(gear axis = z, involute starts on the base cone):")
        st.latex(r"""\begin{aligned}
x &= R\left[\cos(\beta\sin\delta_b)\sin\delta_b\cos\beta
      + \sin(\beta\sin\delta_b)\sin\beta\right]\\
y &= R\left[\cos(\beta\sin\delta_b)\sin\delta_b\sin\beta
      - \sin(\beta\sin\delta_b)\cos\beta\right]\\
z &= R\,\cos(\beta\sin\delta_b)\cos\delta_b
\end{aligned}""")
        st.latex(r"\sin\delta_b = \sin\delta\,\cos\alpha \qquad "
                 r"\cos\delta_x = \cos\delta_b\,\cos(\beta_x\sin\delta_b)")
        st.markdown(
            "R = cone distance (mm), β = base-cone roll angle. Sections at "
            "constant R are loft-ready; the tooth is centred on azimuth 0 "
            "with half thickness π/(2z) at the pitch cone.")
        colA, colB = st.columns(2)
        for col, name, g in ((colA, "gear1_pinion", g1),
                             (colB, "gear2_gear", g2)):
            with col:
                st.subheader(name.replace("_", " "))
                rows = flank_point_cloud(g, fw, n_sec, n_pts)
                st.download_button(
                    f"Download {name} flank points "
                    f"({n_sec}×{n_pts} per flank, CSV)",
                    point_cloud_csv(rows),
                    file_name=f"bevel_{name}_flank_points.csv",
                    mime="text/csv")
                try:
                    import pandas as pd
                    import altair as alt
                    df = pd.DataFrame(
                        rows, columns=["flank", "section", "R", "i",
                                       "x", "y", "z"])
                    outer = df[df.section == df.section.max()]
                    ch = alt.Chart(outer).mark_line(point=True).encode(
                        x="x:Q", y="y:Q", color="flank:N",
                        order="i:O").properties(
                        height=320, title="outer section, plan view (mm)")
                    st.altair_chart(ch, width="stretch")
                except Exception as e:
                    st.info(f"Preview unavailable: {e}")

    with tabs[3]:
        st.markdown(CAD_GUIDANCE)

    with tabs[4]:
        st.markdown(REFERENCES_MD)
        st.markdown(FORMULA_NOTES)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    main()
