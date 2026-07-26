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

      2. Halo Beveloid Pinion — the complementary cone (big end at the
         FRONT), full revolution, with a wall-side hub and a D-shaft bore
         for an N20 gearmotor. Its axis is PARALLEL to the ring axis at
         centre distance C (reported in a notice when the feature runs).

    Why not Gear Lab directly? Gear Lab's bevel gears are spherical
    involutes for INTERSECTING shafts. This drive deliberately uses a
    PARALLEL-AXIS beveloid pair (conical involute): the ring slice radius
    falls 1 mm per mm of z while the pinion's rises, so the centre-radius
    sum is constant across the face and the pinion axis can point straight
    out of the wall. A radial-axis bevel pinion cannot fit this build — its
    swept disc spans its full diameter along the wall normal, through
    either the drywall behind or the wafer field in front.

    Construction here is ANALYTIC (lofted involute sections), where the
    Python model GENERATES the ring as the swept envelope of its cutter.
    The two agree at the mid-face and diverge by a few hundredths toward
    the faces; at this drive's ~mN.m loads that is cosmetic. Keep the
    backlash parameter >= 0.4 mm for printed parts (the repo ships 0.6).

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
      Backlash          -> gear_bl    (0.6 mm, applied to the pinion)
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
        "pinMid" : (pitchR + faceH / 2) * tps / teeth,
        "C" : (pitchR + faceH / 2) * (1 + tps / teeth)  // centre distance
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
        annotation { "Name" : "Face height (gear_F)", "Description" : "Axial height of the tooth band. On the halo this must clear the neighbour wafer's clearance plane (~4.8 mm at the shipped build) — the Python gate is the authority." }
        isLength(definition.faceH, { (millimeter) : [2, 9.5, 14] } as LengthBoundSpec);
        annotation { "Name" : "Pressure angle" }
        isAngle(definition.pa, { (degree) : [14, 20, 28] } as AngleBoundSpec);
        annotation { "Name" : "Spiral angle", "Description" : "0 = straight. The wall section is rotated by tan(spiral)*face/pitchR — matches the Python twist-extrude." }
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

        reportInfo(context, id,
                   "Halo band: " ~ spec.teeth ~ "T (" ~ spec.tps ~ "/segment), "
                   ~ "flush module " ~ roundToPrecision(spec.m / millimeter, 3)
                   ~ " mm, tips r" ~ roundToPrecision(spec.tipR * spec.kb / millimeter, 1)
                   ~ " (wall) -> r" ~ roundToPrecision(spec.tipR / millimeter, 1)
                   ~ " (front). Pinion centre distance C = "
                   ~ roundToPrecision(spec.C / millimeter, 2) ~ " mm.");
    });

// ---------------------------------------------------------------------------
// Feature 2: the complementary pinion (axis parallel, big end at the front)
// ---------------------------------------------------------------------------
annotation {
    "Feature Type Name" : "Halo Beveloid Pinion",
    "Feature Type Description" : "The parallel-axis mate of the Halo Beveloid Band: cone big-at-front, wall-side hub with an N20 D-shaft bore. Build at origin; mate its axis parallel to the ring axis at the reported centre distance C."
}
export const haloBeveloidPinion = defineFeature(function(context is Context, id is Id, definition is map)
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
        annotation { "Name" : "Backlash", "Description" : "Tooth thinning for printed clearance; the repo ships 0.6 mm." }
        isLength(definition.backlash, { (millimeter) : [0, 0.6, 1.5] } as LengthBoundSpec);
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
        // pinion profile: tps teeth at the shared module, scaled so its
        // MID-face pitch complements the ring (bevel_geom.s_prof), then the
        // cone: small at the wall (z=0), big at the front (z=faceH)
        const rp0 = spec.tps * spec.m / 2;
        const sProf = spec.pinMid / rp0;
        var pSpec = {
            "teeth" : spec.tps, "m" : spec.m * sProf,
            "pitchR" : rp0 * sProf,
            "tipR" : (rp0 + spec.m) * sProf,
            "rootR" : (rp0 - 1.25 * spec.m) * sProf,
            "pa" : definition.pa / degree
        };
        var outline = toothArcPoints(pSpec, spec.tps, -PI, definition.backlash, 8);
        const sLo = (spec.pinMid - definition.faceH / 2) / spec.pinMid;
        const sHi = (spec.pinMid + definition.faceH / 2) / spec.pinMid;
        const twist = tan(definition.spiral) * (definition.faceH / spec.pinMid);
        const wall  = sketchClosedPoly(context, id, "wall",
                                       sectionOf(outline, sLo, 0), 0 * millimeter);
        const front = sketchClosedPoly(context, id, "front",
                                       sectionOf(outline, sHi, twist),
                                       definition.faceH);
        opLoft(context, id + "loft", {
            "profileSubqueries" : [wall, front],
            "bodyType" : ToolBodyType.SOLID
        });

        // wall-side hub
        if (definition.hubLen > 0)
        {
            fCylinder(context, id + "hub", {
                "topCenter" : vector(0, 0, 0.1) * millimeter,
                "bottomCenter" : vector(0, 0, -definition.hubLen / millimeter) * millimeter,
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

        reportInfo(context, id,
                   spec.tps ~ "T beveloid pinion, ratio " ~ definition.segN
                   ~ ":1. Mount its axis PARALLEL to the ring axis at C = "
                   ~ roundToPrecision(spec.C / millimeter, 2)
                   ~ " mm, big end toward the viewer; the motor points out of"
                   ~ " the wall.");
    });
