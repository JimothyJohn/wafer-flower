FeatureScript 1803;
import(path : "onshape/std/geometry.fs", version : "1803.0");

/*
    Wafer Halo — Beveloid Gear Features
    ===================================

    OnShape port of the KEY gear functions from scripts/segment_stl.py, in
    the idiom of Anthony Lu's "Gear Lab" FeatureScript (see the forum thread
    https://forum.onshape.com/discussion/18686 — parameter style, build-at-
    origin convention and the involute construction approach follow it, and
    Neil Cooke's Spur Gear FS before it).

    Two features:

      1. Halo Beveloid Band  — the EXTERNAL beveloid tooth band that lives
         at the outer edge of one frame segment: a 360/N degree ring sector,
         teeth on a 45-degree cone with the BIG END AT THE WALL (z=0) and
         the small end at the front (z=faceH), root circle landing flush on
         the band OD, spaces phased so every segment joint lands mid-space.
         Union it onto your segment body.

      2. Halo Crossed Pinion — the Rev B.5 drive pinion: a 45-deg cone
         (apex toward the halo centre) on a RADIAL axis — vertical at
         12 o'clock, motor above it, shaft straight down. 20 teeth
         against the 108T ring gives 5.4:1 — ~2 rpm at the ring from any
         ~11-16 rpm gearmotor (22PG-2430BL 720:1 with integrated driver,
         PWM-dialed). Hub and D-bore on the big (top) end.

      3. Halo Straight Bevel Arc — a CLASSICAL spherical-involute straight
         bevel gear for INTERSECTING shafts, cut to any arc angle (40 deg
         default for one frame segment; 360 = full gear). Gear Lab can
         only emit full-360 gears — this is the partial-arc counterpart:
         make the pinion in Gear Lab (or anywhere), make the segment's
         teeth here with the same module (big end), tooth counts, shaft
         angle and pressure angle, and the flanks are conjugate spherical
         involutes. Both arc ends land mid-space (the segment-joint
         convention). Built with the apex at the ORIGIN, axis +Z, big end
         up; mate so both apexes coincide at the shaft angle. The math
         mirrors scripts/bevel_calc_app.py, whose --selftest validates
         every relation used here (base cone sin(db)=sin(d)cos(a), roll
         arc cos(d)=cos(db)cos(phi), Ligata & Zhang eq. 1 flank).
         UI idioms borrowed from the real Gear Lab (its public wrapper is
         checked out at scripts/onshape/gearlab.fs — the implementation
         behind it lives in a private versioned Onshape module, which is
         WHY the arc feature is built here instead of patched there):
         placement by picked plane/vertex with flip, Adjust Angle to
         clock the teeth into mesh, root fillet as a module factor,
         involute-steps control, remember-previous-value hints, grouped
         advanced settings. The report line prints the Gear Lab settings
         to give the MATING pinion so the two stay conjugate.

    Why not Gear Lab directly? Gear Lab's bevel gears are spherical
    involutes for INTERSECTING shafts sized for true rolling — and a
    true-rolling 45/45 pair only exists at 1:1. The halo pair runs at
    5.4:1 with the flanks GENERATED conjugate to the imposed motion in
    the Python model (heavy sliding, mN.m loads — fine). These features
    build the same envelopes analytically for CAD work; the generated
    Python parts remain the authority for anything that prints.

    Construction here is ANALYTIC (lofted involute sections), where the
    Python model GENERATES the ring as the swept envelope of its cutter.
    The two agree at the mid-face and diverge by a few hundredths toward
    the faces; at this drive's ~mN.m loads that is cosmetic. Keep the
    backlash parameter >= 0.3 mm for printed parts (the repo ships 0.3 —
    at the pinion's 0.8 mm section module, 0.6 would halve the tooth).

    Parameter map (OnShape name -> segment_stl.py PARAMS):
      Segments N        -> N          (9)
      Band inner radius -> Ri         (255 mm)
      Band width        -> bw         (30 mm)
      Nominal module    -> gear_m     (5.6 mm; retuned to flush, see below)
      Face height       -> gear_F     (9.5 mm — must clear the neighbour
                                       wafer plane; the repo gates 9.83 at
                                       the deep-bevel base tmin=15)
      Spiral angle      -> gear_sp    (0 = straight)
      Pressure angle    -> gear_pa    (20 deg)
      Backlash          -> gear_bl    (0.3 mm, applied to the pinion)
      Pinion teeth      -> tps        (derived: teeth per segment)

    FLUSH MODULE: tooth count is quantised in steps of N, so the module
    (not the count) is retuned to land the front root circle 1 mm inside
    the band OD — the teeth rise straight off the band wall exactly as the
    printed parts do.
*/

// ---------------------------------------------------------------------------
// Shared math (mirrors Cfg + pinion_profile + bevel_geom in segment_stl.py)
// ---------------------------------------------------------------------------

// Tooth count and flush-retuned module for the ring.
export function haloGearSpec(segN is number, ri is ValueWithUnits,
                             bw is ValueWithUnits, mNom is ValueWithUnits,
                             faceH is ValueWithUnits) returns map
{
    const ro = ri + bw;
    // teeth per segment from the nominal module (Cfg: target just outside
    // the band; floor 6). MUST stay in sync with segment_stl.Cfg.
    const target = ro + 1.25 * mNom + 2 * millimeter;
    var tps = ceil(2 * target / mNom / segN);
    if (tps < 6) { tps = 6; }
    const teeth = tps * segN;
    // flush module: front root circle lands 1 mm inside the band OD
    const m = (ro - 1 * millimeter) / (teeth / 2 - 1.25);
    const pitchR = teeth * m / 2;              // FRONT face (small end)
    const kb = (pitchR + faceH) / pitchR;      // cone scale at the WALL
    return {
        "tps" : tps, "teeth" : teeth, "m" : m,
        "pitchR" : pitchR,
        "tipR" : pitchR + m, "rootR" : pitchR - 1.25 * m,
        "webIR" : ro - 2 * millimeter,         // web overlaps 2 mm into band
        "kb" : kb,
        "ringMid" : pitchR + faceH / 2,
        // crossed-drive pinion numbers (segment_stl Cfg, pin_T = 20,
        // pin_rho = 8, pin_face = 7): rho is FREE, not the rolling
        // value — conjugacy is by generation, so only the tooth count
        // is forced; 8 with 20T is the 0.8 mm section-module print floor
        "pinT" : 20,
        "rho" : 8 * millimeter,
        "face" : 7 * millimeter,
        "x1" : (pitchR + m) * kb,
        "x0" : (pitchR + m) * kb - 7 * millimeter,
        "apex" : (pitchR + m) * kb - 3.5 * millimeter - 8 * millimeter,
        "zax" : faceH / 2 + 8 * millimeter * 1.1
    };
}

// External involute half-angle at radius rad (pinion_profile.half).
function involuteHalf(rad is ValueWithUnits, rp is ValueWithUnits,
                      rb is ValueWithUnits, psiP is number, pa is number) returns number
{
    const inv = function(al is number) returns number { return tan(al * radian) - al; };
    if (rad <= rb)
        return psiP + inv(pa);
    const al = acos(clamp(rb / rad, -1, 1)) / radian;
    return psiP - (inv(al) - inv(pa));
}

// Sampled outline of external involute teeth spanning [aStart, aEnd] with
// tooth centres at aStart + (k + 0.5) * pitchAng — so both ends land
// mid-space, exactly the segment-joint convention. Returns 2D points
// (unitless mm) tracing root -> flank -> tip -> flank -> root per tooth.
function toothArcPoints(spec is map, nTeeth is number, aStart is number,
                        backlash is ValueWithUnits, flankSteps is number) returns array
{
    const rp = spec.pitchR / millimeter;
    const rb = rp * cos(spec.pa * degree);
    const ra = spec.tipR / millimeter;
    const rf = spec.rootR / millimeter;
    const mm = spec.m / millimeter;
    const bl = backlash / millimeter;
    const psiP = ((PI * mm / 2 - bl) / 2) / rp;
    const pitchAng = 2 * PI / spec.teeth;
    var pts = [];
    for (var k = 0; k < nTeeth; k += 1)
    {
        const ctr = aStart + (k + 0.5) * pitchAng;
        // trailing flank, root -> tip
        for (var i = 0; i <= flankSteps; i += 1)
        {
            const rad = rf + (ra - rf) * i / flankSteps;
            const ha = involuteHalf(rad * millimeter, rp * millimeter,
                                    rb * millimeter, psiP, spec.pa);
            pts = append(pts, vector(rad * cos(ctr - ha), rad * sin(ctr - ha)));
        }
        // leading flank, tip -> root
        for (var i = flankSteps; i >= 0; i -= 1)
        {
            const rad = rf + (ra - rf) * i / flankSteps;
            const ha = involuteHalf(rad * millimeter, rp * millimeter,
                                    rb * millimeter, psiP, spec.pa);
            pts = append(pts, vector(rad * cos(ctr + ha), rad * sin(ctr + ha)));
        }
    }
    return pts;
}

// Scale + optional twist a point array (beveloid section: the wall section
// is the front section scaled by kb and, for spiral teeth, rotated).
function sectionOf(pts is array, scale is number, twist is number) returns array
{
    var out = [];
    const c = cos(twist);
    const s = sin(twist);
    for (var p in pts)
        out = append(out, vector(scale * (p[0] * c - p[1] * s),
                                 scale * (p[0] * s + p[1] * c)));
    return out;
}

// ---------------------------------------------------------------------------
// Shared math — spherical-involute straight bevel (mirrors bevel_calc_app.py;
// that file's --selftest is the numeric authority for these relations).
// All angles in these helpers are PLAIN NUMBERS in radians; trig is called
// with an explicit * radian and inverse trig converted back with / radian.
// ---------------------------------------------------------------------------

// Roll arc phi to reach cone angle dx from the base cone db:
// cos(dx) = cos(db) * cos(phi); 0 below the base cone (roll_arc in the app).
function sphRollArc(dx is number, db is number) returns number
{
    const c = cos(dx * radian) / cos(db * radian);
    if (c >= 1)
        return 0;
    return acos(clamp(c, -1, 1)) / radian;
}

// Azimuth of the involute point about the gear axis, measured from the
// involute start meridian (involute_azimuth in the app):
// psi = phi/sin(db) - atan(tan(phi)/sin(db)).
function sphInvAzimuth(db is number, phi is number) returns number
{
    const sb = sin(db * radian);
    return phi / sb - atan2(tan(phi * radian) * meter, sb * meter) / radian;
}

// All critical angles for one straight bevel gear + its mate (solve_gear /
// solve_pair in the app, spherical base-cone formula only). sigma/alpha are
// radians; m is a length. Returns plain-radian angles and lengths.
export function haloBevelSpec(z is number, zMate is number, sigma is number,
                              m is ValueWithUnits, alpha is number,
                              haC is number, hfC is number) returns map
{
    // pitch cone split: tan(delta) = sin(sigma) / (zMate/z + cos(sigma))
    const delta = atan2(sin(sigma * radian) * meter,
                        (zMate / z + cos(sigma * radian)) * meter) / radian;
    const r = 0.5 * m * z;                        // big-end pitch radius
    const re = r / sin(delta * radian);           // outer cone distance
    const addAng = atan2((haC * (m / re)) * meter, 1 * meter) / radian;
    const dedAng = atan2((hfC * (m / re)) * meter, 1 * meter) / radian;
    const db = asin(sin(delta * radian) * cos(alpha * radian)) / radian;
    const da = delta + addAng;
    const df = delta - dedAng;
    const phiP = sphRollArc(delta, db);
    const phiA = sphRollArc(da, db);
    // mate shares Re (apexes meet) so it sees the same addendum angle
    const d2 = sigma - delta;
    const db2 = asin(sin(d2 * radian) * cos(alpha * radian)) / radian;
    const phiP2 = sphRollArc(d2, db2);
    const phiA2 = sphRollArc(d2 + addAng, db2);
    return {
        "delta" : delta, "db" : db, "da" : da, "df" : df,
        "r" : r, "re" : re,
        "psiP" : sphInvAzimuth(db, phiP),
        "rootBelowBase" : df < db,
        // Tredgold undercut limit (virtual spur): z/cos(delta) >= 2ha*/sin^2(a)
        "zv" : z / cos(delta * radian),
        "zvMate" : zMate / cos(d2 * radian),
        "zvMin" : 2 * haC / (sin(alpha * radian) * sin(alpha * radian)),
        // exact spherical contact ratio of the pair (contact_ratio_spherical)
        "eps" : (z * (phiA - phiP) / sin(db * radian)
                 + zMate * (phiA2 - phiP2) / sin(db2 * radian)) / (2 * PI)
    };
}

// One flank of one tooth, root -> tip, as [rUnit, halfAngle] pairs on the
// UNIT transverse plane z = 1: a flank point at cone angle dx projects to
// radius tan(dx) at azimuth (tooth centre -/+ halfAngle). Straight-bevel
// flanks are cones through the apex, so EVERY transverse section is this
// profile scaled by its plane's z — the loft edges lie exactly on the
// apex rays and the flank surfaces come out exact, not approximated.
function bevelFlankSamples(spec is map, halfTooth is number, steps is number) returns array
{
    const sb = sin(spec.db * radian);
    const betaLo = sphRollArc(max(spec.df, spec.db), spec.db) / sb;
    const betaHi = sphRollArc(spec.da, spec.db) / sb;
    var flank = [];
    if (spec.rootBelowBase)  // non-involute strip: radial drop to the root cone
        flank = append(flank, [tan(spec.df * radian), halfTooth + spec.psiP]);
    for (var i = 0; i <= steps; i += 1)
    {
        const beta = betaLo + (betaHi - betaLo) * i / steps;
        const phi = beta * sb;
        const dx = acos(cos(phi * radian) * cos(spec.db * radian)) / radian;
        const psi = beta - atan2(tan(phi * radian) * meter, sb * meter) / radian;
        flank = append(flank, [tan(dx * radian), halfTooth - (psi - spec.psiP)]);
    }
    return flank;
}

// Chain nTeeth teeth on the unit plane, centres at aStart + (k+0.5)*pitch —
// both ends land mid-space, the segment-joint convention (as toothArcPoints).
function bevelToothArc(flank is array, teeth is number, nTeeth is number,
                       aStart is number) returns array
{
    const pitchAng = 2 * PI / teeth;
    var pts = [];
    for (var k = 0; k < nTeeth; k += 1)
    {
        const ctr = aStart + (k + 0.5) * pitchAng;
        for (var f in flank)                        // trailing flank, root -> tip
            pts = append(pts, vector(f[0] * cos((ctr - f[1]) * radian),
                                     f[0] * sin((ctr - f[1]) * radian)));
        for (var i = size(flank) - 1; i >= 0; i -= 1)  // leading, tip -> root
        {
            const f = flank[i];
            pts = append(pts, vector(f[0] * cos((ctr + f[1]) * radian),
                                     f[0] * sin((ctr + f[1]) * radian)));
        }
    }
    return pts;
}

// Uniform scale of a 2D point array (the homothetic transverse section).
function scalePts(pts is array, s is number) returns array
{
    var out = [];
    for (var p in pts)
        out = append(out, vector(p[0] * s, p[1] * s));
    return out;
}

// Root-fillet blend (Gear Lab-style fillet, approximate): replace each
// listed vertex P of a closed polyline with a sampled quadratic bezier
// from P1 = P + d toward the previous vertex to P2 = P + d toward the
// next, control point P. Distance is clamped to 45% of either neighbour
// segment so the outline stays simple. On the unit plane d scales with z
// like everything else — the fillet is conical from the apex, as a
// bevel-gear fillet should be.
function blendCorners(pts is array, idxs is array, d is number) returns array
{
    const n = size(pts);
    var mark = makeArray(n, false);
    for (var i in idxs)
        mark[i] = true;
    var out = [];
    for (var i = 0; i < n; i += 1)
    {
        if (mark[i] != true)
        {
            out = append(out, pts[i]);
            continue;
        }
        const p = pts[i];
        const va = pts[(i - 1 + n) % n] - p;
        const vb = pts[(i + 1) % n] - p;
        const la = norm(va);
        const lb = norm(vb);
        const p1 = p + va * (min(d, 0.45 * la) / la);
        const p2 = p + vb * (min(d, 0.45 * lb) / lb);
        for (var t = 0; t <= 4; t += 1)
        {
            const u = t / 4;
            out = append(out, (1 - u) * (1 - u) * p1 + 2 * u * (1 - u) * p + u * u * p2);
        }
    }
    return out;
}

// Draw a closed polyline region on a z-offset plane and return its region.
function sketchClosedPoly(context is Context, id is Id, name is string,
                          pts is array, z is ValueWithUnits) returns Query
{
    var sk = newSketchOnPlane(context, id + name,
        { "sketchPlane" : plane(vector(0, 0, z / millimeter) * millimeter,
                                vector(0, 0, 1)) });
    const n = size(pts);
    for (var i = 0; i < n; i += 1)
    {
        const a = pts[i];
        const b = pts[(i + 1) % n];
        skLineSegment(sk, "e" ~ i, {
            "start" : vector(a[0], a[1]) * millimeter,
            "end"   : vector(b[0], b[1]) * millimeter
        });
    }
    skSolve(sk);
    return qSketchRegion(id + name);
}

// ---------------------------------------------------------------------------
// Feature 1: the ring-sector tooth band at the segment edge
// ---------------------------------------------------------------------------
annotation {
    "Feature Type Name" : "Halo Beveloid Band",
    "Feature Type Description" : "External beveloid tooth band for one Wafer Halo frame segment: a 360/N ring sector, teeth on a 45-deg cone big-at-wall, flush root, joints mid-space. Build at origin (wall face on the XY plane, sector centred on +X); union onto the segment."
}
export const haloBeveloidBand = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Segments (N)" }
        isInteger(definition.segN, { (unitless) : [3, 9, 36] } as IntegerBoundSpec);
        annotation { "Name" : "Band inner radius (Ri)" }
        isLength(definition.ri, { (millimeter) : [50, 255, 2000] } as LengthBoundSpec);
        annotation { "Name" : "Band width (bw)" }
        isLength(definition.bw, { (millimeter) : [10, 30, 200] } as LengthBoundSpec);
        annotation { "Name" : "Nominal module" }
        isLength(definition.mNom, { (millimeter) : [1, 5.6, 12] } as LengthBoundSpec);
        annotation { "Name" : "Face height (gear_F)", "Description" : "Axial height of the tooth band. On the halo this must clear the neighbour wafer's clearance plane (~4.8 mm at the shipped build) - the Python gate is the authority." }
        isLength(definition.faceH, { (millimeter) : [2, 9.5, 14] } as LengthBoundSpec);
        annotation { "Name" : "Pressure angle" }
        isAngle(definition.pa, { (degree) : [14, 20, 28] } as AngleBoundSpec);
        annotation { "Name" : "Spiral angle", "Description" : "0 = straight. The wall section is rotated by tan(spiral)*face/pitchR - matches the Python twist-extrude." }
        isAngle(definition.spiral, { (degree) : [-45, 0, 45] } as AngleBoundSpec);
        annotation { "Name" : "Full ring (all N sectors)", "UIHint" : UIHint.DISPLAY_SHORT }
        definition.fullRing is boolean;
    }
    {
        var spec = haloGearSpec(definition.segN, definition.ri, definition.bw,
                                definition.mNom, definition.faceH);
        spec.pa = definition.pa / degree;

        const nT = definition.fullRing ? spec.teeth : spec.tps;
        const half = PI / definition.segN;
        const aStart = definition.fullRing ? -PI : -half;

        // outer tooth chain (front-face nominal), closed through the web bore
        var outline = toothArcPoints(spec, nT, aStart, 0 * millimeter, 8);
        const webR = spec.webIR / millimeter;
        const aEnd = aStart + nT * 2 * PI / spec.teeth;
        if (definition.fullRing)
        {
            // full ring: separate inner circle would need a second loop; use
            // a near-closed annulus (1e-4 rad seam), same as a printed part
            for (var i = 0; i <= 256; i += 1)
            {
                const a = aEnd - 1e-4 - (2 * PI - 2e-4) * i / 256;
                outline = append(outline, vector(webR * cos(a), webR * sin(a)));
            }
        }
        else
        {
            // sector: radial edge in, web arc back, radial edge out
            for (var i = 0; i <= 64; i += 1)
            {
                const a = aEnd - (aEnd - aStart) * i / 64;
                outline = append(outline, vector(webR * cos(a), webR * sin(a)));
            }
        }

        // beveloid sections: front (z = faceH) nominal, wall (z = 0) scaled
        // by kb and twisted for spiral teeth
        const twist = tan(definition.spiral) * (definition.faceH / spec.ringMid);
        const front = sketchClosedPoly(context, id, "front", outline, definition.faceH);
        const wall  = sketchClosedPoly(context, id, "wall",
                                       sectionOf(outline, spec.kb, -twist),
                                       0 * millimeter);
        opLoft(context, id + "loft", {
            "profileSubqueries" : [wall, front],
            "bodyType" : ToolBodyType.SOLID
        });
        opDeleteBodies(context, id + "clean", {
            "entities" : qCreatedBy(id + "front", EntityType.BODY)->qBodyType(BodyType.WIRE)
        });

        reportFeatureInfo(context, id,
                   "Halo band: " ~ spec.teeth ~ "T (" ~ spec.tps ~ "/segment), "
                   ~ "flush module " ~ roundToPrecision(spec.m / millimeter, 3)
                   ~ " mm, tips r" ~ roundToPrecision(spec.tipR * spec.kb / millimeter, 1)
                   ~ " (wall) -> r" ~ roundToPrecision(spec.tipR / millimeter, 1)
                   ~ " (front). Crossed pinion: axis RADIAL, "
                   ~ roundToPrecision(spec.zax / millimeter, 1)
                   ~ " mm above the ring's wall plane.");
    });

// ---------------------------------------------------------------------------
// Feature 2: the crossed-drive pinion (radial axis, apex down, hub on top)
// ---------------------------------------------------------------------------
annotation {
    "Feature Type Name" : "Halo Crossed Pinion",
    "Feature Type Description" : "The Rev B.5 drive pinion: 20T 45-deg cone, apex toward the halo centre, on a RADIAL axis (vertical at 12 o'clock, motor above, shaft down). Built about +Z (apex at z=0, big end + hub up); mate its axis radial with the small end at the reported ring radius and the axis the reported height off the ring's wall plane. Analytic involute sections - the Python-generated parts are the authority for printing."
}
export const haloCrossedPinion = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Segments (N)" }
        isInteger(definition.segN, { (unitless) : [3, 9, 36] } as IntegerBoundSpec);
        annotation { "Name" : "Band inner radius (Ri)" }
        isLength(definition.ri, { (millimeter) : [50, 255, 2000] } as LengthBoundSpec);
        annotation { "Name" : "Band width (bw)" }
        isLength(definition.bw, { (millimeter) : [10, 30, 200] } as LengthBoundSpec);
        annotation { "Name" : "Nominal module" }
        isLength(definition.mNom, { (millimeter) : [1, 5.6, 12] } as LengthBoundSpec);
        annotation { "Name" : "Face height (gear_F)" }
        isLength(definition.faceH, { (millimeter) : [2, 9.5, 14] } as LengthBoundSpec);
        annotation { "Name" : "Pressure angle" }
        isAngle(definition.pa, { (degree) : [14, 20, 28] } as AngleBoundSpec);
        annotation { "Name" : "Spiral angle" }
        isAngle(definition.spiral, { (degree) : [-45, 0, 45] } as AngleBoundSpec);
        annotation { "Name" : "Backlash", "Description" : "Tooth thinning for printed clearance; the repo ships 0.3 mm." }
        isLength(definition.backlash, { (millimeter) : [0, 0.3, 1.5] } as LengthBoundSpec);
        annotation { "Name" : "Hub length" }
        isLength(definition.hubLen, { (millimeter) : [0, 5, 20] } as LengthBoundSpec);
        annotation { "Name" : "Bore diameter", "Description" : "3.2 for an N20 3 mm D-shaft." }
        isLength(definition.boreD, { (millimeter) : [0, 3.2, 10] } as LengthBoundSpec);
        annotation { "Name" : "D-flat depth" }
        isLength(definition.flat, { (millimeter) : [0, 0.4, 2] } as LengthBoundSpec);
    }
    {
        const spec = haloGearSpec(definition.segN, definition.ri, definition.bw,
                                  definition.mNom, definition.faceH);
        // pinion profile: pinT teeth at the ring's module; each section
        // along the axis is the profile scaled by (station - apex)/rp0 —
        // the 45-deg cone (segment_stl.bevel_pinion). Local frame: apex
        // toward z=0 (small end), big end + hub at the top.
        // profile at the ring module; the section SCALE (station-apex)/rp0
        // shrinks it to the small pinion — same trick as bevel_pinion
        const rp0 = spec.pinT * spec.m / 2;
        var pSpec = {
            "teeth" : spec.pinT, "m" : spec.m,
            "pitchR" : rp0,
            "tipR" : rp0 + spec.m,
            "rootR" : rp0 - 1.25 * spec.m,
            "pa" : definition.pa / degree
        };
        const face = spec.x1 - spec.x0;
        var outline = toothArcPoints(pSpec, spec.pinT, -PI, definition.backlash, 8);
        const sLo = (spec.x0 - spec.apex) / rp0;
        const sHi = (spec.x1 - spec.apex) / rp0;
        const twist = tan(definition.spiral) * (face / spec.rho);
        const small = sketchClosedPoly(context, id, "small",
                                       sectionOf(outline, sLo, 0), 0 * millimeter);
        const bigE  = sketchClosedPoly(context, id, "bigE",
                                       sectionOf(outline, sHi, twist), face);
        opLoft(context, id + "loft", {
            "profileSubqueries" : [small, bigE],
            "bodyType" : ToolBodyType.SOLID
        });

        // motor-side hub on the BIG (top) end
        if (definition.hubLen > 0)
        {
            fCylinder(context, id + "hub", {
                "topCenter" : vector(0, 0, (face + definition.hubLen) / millimeter) * millimeter,
                "bottomCenter" : vector(0, 0, face / millimeter - 0.1) * millimeter,
                "radius" : 8 * millimeter
            });
            opBoolean(context, id + "hubU", {
                "tools" : qUnion([qCreatedBy(id + "loft", EntityType.BODY),
                                  qCreatedBy(id + "hub", EntityType.BODY)]),
                "operationType" : BooleanOperationType.UNION
            });
        }

        // D-shaft bore through everything
        if (definition.boreD > 0)
        {
            const r = definition.boreD / 2 / millimeter;
            const f = definition.flat / millimeter;
            var sk = newSketchOnPlane(context, id + "boreSk",
                { "sketchPlane" : plane(vector(0, 0, -30) * millimeter,
                                        vector(0, 0, 1)) });
            skCircle(sk, "c", { "center" : vector(0, 0) * millimeter,
                                "radius" : r * millimeter });
            if (f > 0)
                skRectangle(sk, "d", {
                    "firstCorner" : vector(r - f, -r) * millimeter,
                    "secondCorner" : vector(r + 1, r) * millimeter
                });
            skSolve(sk);
            opExtrude(context, id + "bore", {
                "entities" : qSketchRegion(id + "boreSk", true),
                "direction" : vector(0, 0, 1),
                "endBound" : BoundingType.BLIND,
                "endDepth" : 60 * millimeter
            });
            opBoolean(context, id + "boreCut", {
                "tools" : qCreatedBy(id + "bore", EntityType.BODY),
                "targets" : qCreatedBy(id + (definition.hubLen > 0 ? "hubU" : "loft"),
                                       EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
            });
        }

        reportFeatureInfo(context, id,
                   spec.pinT ~ "T crossed pinion, ratio "
                   ~ roundToPrecision(spec.teeth / spec.pinT, 1)
                   ~ ":1 (~2 rpm, PWM-dialed). Mount its axis RADIAL — vertical"
                   ~ " at 12 o'clock, shaft down — with the small end at ring"
                   ~ " radius " ~ roundToPrecision(spec.x0 / millimeter, 1)
                   ~ " and the axis " ~ roundToPrecision(spec.zax / millimeter, 1)
                   ~ " mm in front of the ring's wall plane.");
    });

// ---------------------------------------------------------------------------
// Feature 3: classical spherical-involute straight bevel gear, any arc angle
// ---------------------------------------------------------------------------
annotation {
    "Feature Type Name" : "Halo Straight Bevel Arc",
    "Feature Type Description" : "Classical spherical-involute straight bevel gear cut to an arc (40 deg default = one frame segment; 360 = full gear), both arc ends mid-space. Apex at the ORIGIN, axis +Z, big end up, arc centred on +X; spherical end faces about the apex. Mate a Gear Lab (or any spherical-involute) pinion with the same big-end module, tooth counts, shaft angle and pressure angle, apexes coincident. Math authority: scripts/bevel_calc_app.py --selftest."
}
export const haloStraightBevelArc = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        // placement picker in the Gear Lab manner (its buildManual_alignGeometry)
        annotation { "Name" : "Placement", "Filter" : GeometryType.PLANE || EntityType.VERTEX,
                     "MaxNumberOfPicks" : 1,
                     "Description" : "Optional: a plane or planar face (apex at its origin, axis along its normal) or a vertex (apex there, axis +Z). Leave empty to build with the apex at the world origin, axis +Z." }
        definition.placement is Query;
        annotation { "Name" : "Flip axis", "UIHint" : UIHint.OPPOSITE_DIRECTION }
        definition.placeFlip is boolean;

        annotation { "Name" : "Teeth (this gear)" }
        isInteger(definition.z, { (unitless) : [12, 108, 1000] } as IntegerBoundSpec);
        annotation { "Name" : "Mate teeth" }
        isInteger(definition.zMate, { (unitless) : [6, 20, 1000] } as IntegerBoundSpec);
        annotation { "Name" : "Module (big end)", "UIHint" : UIHint.REMEMBER_PREVIOUS_VALUE, "Description" : "Outer transverse module - must match the mate's. The halo flush module is 5.384 mm." }
        isLength(definition.m, { (millimeter) : [0.5, 5.384, 12] } as LengthBoundSpec);
        annotation { "Name" : "Shaft angle", "UIHint" : UIHint.REMEMBER_PREVIOUS_VALUE }
        isAngle(definition.sigma, { (degree) : [30, 90, 150] } as AngleBoundSpec);
        annotation { "Name" : "Pressure angle", "UIHint" : UIHint.REMEMBER_PREVIOUS_VALUE }
        isAngle(definition.pa, { (degree) : [14, 20, 28] } as AngleBoundSpec);
        annotation { "Name" : "Arc angle", "UIHint" : UIHint.REMEMBER_PREVIOUS_VALUE, "Description" : "Snapped to a whole number of teeth, ends mid-space. 40 deg = one halo segment (12 of 108 teeth); 360 = full gear." }
        isAngle(definition.arc, { (degree) : [2, 40, 360] } as AngleBoundSpec);
        annotation { "Name" : "Face width", "UIHint" : UIHint.REMEMBER_PREVIOUS_VALUE, "Description" : "Along the pitch-cone element (the halo band is 30 mm)." }
        isLength(definition.face, { (millimeter) : [2, 30, 150] } as LengthBoundSpec);
        annotation { "Name" : "Rim depth", "UIHint" : UIHint.REMEMBER_PREVIOUS_VALUE, "Description" : "Radial-on-sphere depth of solid rim kept below the root cone; the inner rim wall is a cone from the apex." }
        isLength(definition.rim, { (millimeter) : [0.5, 5, 60] } as LengthBoundSpec);
        annotation { "Name" : "Backlash", "UIHint" : UIHint.REMEMBER_PREVIOUS_VALUE, "Description" : "Tooth thinning at the big-end pitch circle. Repo convention keeps backlash on the PINION (band ships 0 on the ring) - leave 0 unless the pinion carries none." }
        isLength(definition.backlash, { (millimeter) : [0, 0, 1.5] } as LengthBoundSpec);

        annotation { "Name" : "Root fillet", "UIHint" : UIHint.REMEMBER_PREVIOUS_VALUE }
        definition.fillet is boolean;
        if (definition.fillet)
        {
            annotation { "Group Name" : "Fillet Settings", "Driving Parameter" : "fillet", "Collapsed By Default" : false }
            {
                annotation { "Name" : "Distance (x module)", "UIHint" : UIHint.REMEMBER_PREVIOUS_VALUE, "Description" : "Root-corner blend distance as a multiple of the module (approximate bezier blend; scales toward the apex, so it is conical like the flanks)." }
                isReal(definition.filletDf, { (unitless) : [0.05, 0.3, 0.45] } as RealBoundSpec);
            }
        }

        annotation { "Group Name" : "Advanced Settings" }
        {
            annotation { "Name" : "Adjust angle", "UIHint" : UIHint.REMEMBER_PREVIOUS_VALUE, "Description" : "Rotates the tooth pattern about the axis without moving the body - clock the teeth into mesh with the mate." }
            isAngle(definition.adjustAngle, { (degree) : [-360, 0, 360] } as AngleBoundSpec);
            annotation { "Name" : "Addendum factor (ha*)", "UIHint" : UIHint.REMEMBER_PREVIOUS_VALUE }
            isReal(definition.haC, { (unitless) : [0.6, 1.0, 1.5] } as RealBoundSpec);
            annotation { "Name" : "Dedendum factor (hf*)", "UIHint" : UIHint.REMEMBER_PREVIOUS_VALUE }
            isReal(definition.hfC, { (unitless) : [0.8, 1.25, 2.0] } as RealBoundSpec);
            annotation { "Name" : "Involute steps", "UIHint" : UIHint.REMEMBER_PREVIOUS_VALUE }
            isInteger(definition.invsteps, { (unitless) : [4, 8, 40] } as IntegerBoundSpec);
        }
    }
    {
        const spec = haloBevelSpec(definition.z, definition.zMate,
                                   definition.sigma / radian, definition.m,
                                   definition.pa / radian,
                                   definition.haC, definition.hfC);
        if (spec.da >= PI / 2)
            throw regenError("Tip cone angle is >= 90 deg — not a valid bevel. Reduce the tooth ratio, addendum factor, or shaft angle.");
        if (definition.face >= 0.9 * spec.re)
            throw regenError("Face width >= 90% of the outer cone distance ("
                             ~ roundToPrecision(spec.re / millimeter, 1)
                             ~ " mm) — the band would swallow the apex.");
        const dWeb = spec.df - (definition.rim / spec.re);
        if (dWeb <= 0.02)
            throw regenError("Rim depth reaches the gear axis — reduce it.");

        const halfTooth = PI / (2 * definition.z)
                          - (definition.backlash / 2) / spec.r;
        if (halfTooth <= 0)
            throw regenError("Backlash eats the whole tooth at this module/count — reduce it.");
        const flank = bevelFlankSamples(spec, halfTooth, definition.invsteps);

        // teeth in the arc: snapped to whole teeth, both ends mid-space;
        // adjustAngle clocks the pattern about the axis (Gear Lab idiom)
        var nT = floor(definition.z * (definition.arc / degree) / 360 + 0.5);
        if (nT < 1) { nT = 1; }
        if (nT > definition.z) { nT = definition.z; }
        const fullRing = nT == definition.z;
        const pitchAng = 2 * PI / definition.z;
        const aStart = (fullRing ? -PI : -nT * pitchAng / 2)
                       + definition.adjustAngle / radian;
        const aEnd = aStart + nT * pitchAng;
        var outline = bevelToothArc(flank, definition.z, nT, aStart);

        // close through the rim cone (unit-plane radius tan(dWeb))
        const rWeb = tan(dWeb * radian);
        if (fullRing)
        {
            // near-closed annulus seam (1e-4 rad), same as the band feature
            for (var i = 0; i <= 256; i += 1)
            {
                const a = aEnd - 1e-4 - (2 * PI - 2e-4) * i / 256;
                outline = append(outline, vector(rWeb * cos(a * radian),
                                                 rWeb * sin(a * radian)));
            }
        }
        else
        {
            // sector: radial edge in, rim arc back, radial edge out
            for (var i = 0; i <= 64; i += 1)
            {
                const a = aEnd - (aEnd - aStart) * i / 64;
                outline = append(outline, vector(rWeb * cos(a * radian),
                                                 rWeb * sin(a * radian)));
            }
        }

        // optional root fillet: blend the two root corners of every tooth
        // (tooth k's first and last outline points; the closure arcs were
        // appended after the teeth, so these indices are stable)
        if (definition.fillet)
        {
            const perTooth = 2 * size(flank);
            var corners = [];
            for (var k = 0; k < nT; k += 1)
            {
                corners = append(corners, k * perTooth);
                corners = append(corners, k * perTooth + perTooth - 1);
            }
            // module on the unit plane (module scales with cone distance)
            const mUnit = 2 * tan(spec.delta * radian) / definition.z;
            outline = blendCorners(outline, corners, definition.filletDf * mUnit);
        }

        // Cone-from-apex solid: loft two homothetic transverse sections that
        // OVERSHOOT the band both ways (cutter-overshoot idiom — transverse
        // planes cut a near-crown gear at a grazing angle, so the loft alone
        // would shear the band), then trim to the two spheres about the apex
        // for textbook spherical end faces at ANY cone angle.
        const zLo = 0.98 * (spec.re - definition.face) * cos(spec.da * radian);
        const zHi = 1.02 * spec.re * cos(dWeb * radian);
        const low  = sketchClosedPoly(context, id, "low",
                                      scalePts(outline, zLo / millimeter), zLo);
        const high = sketchClosedPoly(context, id, "high",
                                      scalePts(outline, zHi / millimeter), zHi);
        opLoft(context, id + "loft", {
            "profileSubqueries" : [low, high],
            "bodyType" : ToolBodyType.SOLID
        });
        opDeleteBodies(context, id + "clean", {
            "entities" : qUnion([
                qCreatedBy(id + "low", EntityType.BODY)->qBodyType(BodyType.WIRE),
                qCreatedBy(id + "high", EntityType.BODY)->qBodyType(BodyType.WIRE)])
        });

        // outer trim: subtract the shell beyond the outer sphere (radius Re)
        const rBig = zHi / cos(spec.da * radian) + 10 * millimeter;
        opSphere(context, id + "shellO", {
            "center" : vector(0, 0, 0) * millimeter, "radius" : rBig });
        opSphere(context, id + "shellI", {
            "center" : vector(0, 0, 0) * millimeter, "radius" : spec.re });
        opBoolean(context, id + "shell", {
            "tools" : qCreatedBy(id + "shellI", EntityType.BODY),
            "targets" : qCreatedBy(id + "shellO", EntityType.BODY),
            "operationType" : BooleanOperationType.SUBTRACTION
        });
        opBoolean(context, id + "trimO", {
            "tools" : qCreatedBy(id + "shellO", EntityType.BODY),
            "targets" : qCreatedBy(id + "loft", EntityType.BODY),
            "operationType" : BooleanOperationType.SUBTRACTION
        });
        // inner trim: subtract the inner sphere (radius Re - face)
        opSphere(context, id + "boreS", {
            "center" : vector(0, 0, 0) * millimeter,
            "radius" : spec.re - definition.face });
        opBoolean(context, id + "trimI", {
            "tools" : qCreatedBy(id + "boreS", EntityType.BODY),
            "targets" : qCreatedBy(id + "loft", EntityType.BODY),
            "operationType" : BooleanOperationType.SUBTRACTION
        });

        // optional placement on picked geometry (Gear Lab's alignment idiom):
        // plane/planar face -> apex at its origin, axis along its normal;
        // vertex -> apex there, axis +Z. Flip reverses the axis.
        if (size(evaluateQuery(context, definition.placement)) > 0)
        {
            var cSys = undefined;
            try silent
            {
                const pl = evPlane(context, { "face" : definition.placement });
                cSys = coordSystem(pl.origin, pl.x,
                                   definition.placeFlip ? -pl.normal : pl.normal);
            }
            if (cSys == undefined)
            {
                const pt = evVertexPoint(context, { "vertex" : definition.placement });
                cSys = coordSystem(pt, vector(1, 0, 0),
                                   definition.placeFlip ? vector(0, 0, -1) : vector(0, 0, 1));
            }
            opTransform(context, id + "place", {
                "bodies" : qCreatedBy(id + "loft", EntityType.BODY),
                "transform" : toWorld(cSys)
            });
        }

        var msg = "Straight bevel arc: " ~ nT ~ " of " ~ definition.z
            ~ " teeth (" ~ roundToPrecision(nT * 360 / definition.z, 2)
            ~ " deg), big-end module " ~ roundToPrecision(definition.m / millimeter, 3)
            ~ " mm. Pitch cone " ~ roundToPrecision(spec.delta * 180 / PI, 2)
            ~ " deg (base " ~ roundToPrecision(spec.db * 180 / PI, 2)
            ~ ", root " ~ roundToPrecision(spec.df * 180 / PI, 2)
            ~ ", tip " ~ roundToPrecision(spec.da * 180 / PI, 2)
            ~ "), outer cone distance " ~ roundToPrecision(spec.re / millimeter, 1)
            ~ " mm, big-end pitch r " ~ roundToPrecision(spec.r / millimeter, 1)
            ~ " mm. Apex at the placement origin (world origin if none), axis"
            ~ " along the placement normal — mate with apexes coincident. "
            ~ "Spherical contact ratio vs the " ~ definition.zMate ~ "T mate: "
            ~ roundToPrecision(spec.eps, 3) ~ ". Gear Lab settings for the mate:"
            ~ " Teeth " ~ definition.zMate
            ~ ", same Module/Pressure Angle, Bevel Angle "
            ~ roundToPrecision((definition.sigma / radian - spec.delta) * 180 / PI, 2)
            ~ " deg, Helix 0, Tooth Width "
            ~ roundToPrecision(definition.face / definition.m, 2) ~ " modules.";
        if (spec.eps < 1.2)
            msg = msg ~ " WARNING: contact ratio < 1.2 (below 1.0 motion is not continuous).";
        if (spec.zv < spec.zvMin)
            msg = msg ~ " WARNING: this gear undercuts (z_v " ~ roundToPrecision(spec.zv, 1)
                ~ " < " ~ roundToPrecision(spec.zvMin, 1) ~ ").";
        if (spec.zvMate < spec.zvMin)
            msg = msg ~ " WARNING: the MATE undercuts (z_v " ~ roundToPrecision(spec.zvMate, 1)
                ~ " < " ~ roundToPrecision(spec.zvMin, 1) ~ ") — Gear Lab may profile-shift it; match tip/root clearances by eye.";
        if (spec.rootBelowBase)
            msg = msg ~ " Note: root cone below base cone — the strip below the base circle is radial, not involute (fillet territory).";
        msg = msg ~ " Root is sharp — add a fillet in CAD if wanted (~0.25*m).";
        reportFeatureInfo(context, id, msg);
    });

// ---------------------------------------------------------------------------
// Feature 4: cut ANY full gear down to an arc — the Gear Lab companion.
// Gear Lab's implementation (GearLabMain.fs) lives in a private document,
// so partial arcs cannot be patched into it; instead, generate the full
// gear with Gear Lab and cut it here. The teeth stay exactly Gear Lab's —
// no gear math happens in this feature at all.
// ---------------------------------------------------------------------------
annotation {
    "Feature Type Name" : "Gear Arc Cut",
    "Feature Type Description" : "Keep only an arc of a full gear (or any body): intersects the selected body with a sector wedge about the world Z axis through the origin, centred on +X. Build the gear at the origin (Gear Lab manual build, no alignment geometry), cut, THEN transform/mate the result. Use Offset here (or Gear Lab's Adjust Angle) to land both cut planes mid-space between teeth."
}
export const gearArcCut = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Body to cut", "Filter" : EntityType.BODY, "MaxNumberOfPicks" : 1 }
        definition.gearBody is Query;
        annotation { "Name" : "Arc angle", "Description" : "Angular span to KEEP, centred on +X (plus Offset)." }
        isAngle(definition.arc, { (degree) : [1, 40, 359] } as AngleBoundSpec);
        annotation { "Name" : "Offset", "Description" : "Rotates the kept sector about Z - clock the cut planes into tooth gaps." }
        isAngle(definition.offset, { (degree) : [-360, 0, 360] } as AngleBoundSpec);
    }
    {
        if (size(evaluateQuery(context, definition.gearBody)) != 1)
            throw regenError("Select exactly one body to cut.");

        // sector wedge: origin + a big arc, extruded well past any gear
        const half = (definition.arc / radian) / 2;
        const mid = definition.offset / radian;
        const R = 2000;                       // mm — far outside any gear here
        var pts = [vector(0, 0)];
        for (var i = 0; i <= 64; i += 1)
        {
            const a = mid - half + 2 * half * i / 64;
            pts = append(pts, vector(R * cos(a * radian), R * sin(a * radian)));
        }
        sketchClosedPoly(context, id, "wedge", pts, -1000 * millimeter);
        opExtrude(context, id + "wex", {
            "entities" : qSketchRegion(id + "wedge"),
            "direction" : vector(0, 0, 1),
            "endBound" : BoundingType.BLIND,
            "endDepth" : 2000 * millimeter
        });
        opBoolean(context, id + "keep", {
            "tools" : qUnion([definition.gearBody,
                              qCreatedBy(id + "wex", EntityType.BODY)]),
            "operationType" : BooleanOperationType.INTERSECTION
        });
        opDeleteBodies(context, id + "clean", {
            "entities" : qCreatedBy(id + "wedge", EntityType.BODY)->qBodyType(BodyType.WIRE)
        });

        reportFeatureInfo(context, id,
            "Kept " ~ roundToPrecision(definition.arc / degree, 2)
            ~ " deg about world Z through the origin, centred "
            ~ roundToPrecision(definition.offset / degree, 2)
            ~ " deg off +X. For N teeth in the arc use arc = N*(360/z) and"
            ~ " clock Offset so both cut planes land mid-space. Cut BEFORE"
            ~ " transforming the gear off the origin.");
    });
