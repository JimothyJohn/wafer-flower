FeatureScript 1803;
import(path : "onshape/std/geometry.fs", version : "1803.0");

/*
    Spur gear arc generator - simplified from the bevel/crown generator at
    Nick's call (2026-07-31): a right-angle gearmotor makes the 90-degree
    turn in hardware, so the pinion axis is PARALLEL to the ring axis and
    the pair is plain spur gears - teeth parallel to both axes, no cones.
    The full ISO straight-bevel / crown generator (Tredgold back-cone
    profiles, tip-circle anchoring, crown regime, apex-to-apex placement)
    lives in git history at commit ed600bf if the bevel route ever returns.

    "Arc Segment": ring sector (full gear at 360) with external involute
    teeth, tips flush at Ro, plus an optional meshing pinion at parallel
    axes. Teeth counts teeth ON THIS ARC; the module is DERIVED:
    m = 2 Ro / (zFull + 2), zFull = teeth * 360 / arc. Sector joint faces
    land mid-slot (halo tiling rule). Flanks are 10-facet transverse
    involutes; root fillet 0.38 m (ISO rack tip radius) clamped to the
    root land. Pair: center distance m (zFull + Zp) / 2, zero backlash by
    construction, clocked tooth-to-slot at the ring's +X meridian.
    Ratio = zFull / pinion teeth; coprime counts hunt (wear-even).

    Onshape paste rules learned the hard way (do not regress):
    - annotation strings must be printable ASCII (no em-dashes, no unicode minus)
    - reportFeatureInfo, not reportInfo (and no popup at all - Nick's call)
    - opSphere, not fSphere
    - a parameter group ("Group Name"/"Driving Parameter") must IMMEDIATELY
      follow its driving parameter's declaration - nothing in between, or
      precondition analysis fails on the whole feature
*/

annotation {
    "Feature Type Name" : "Arc Segment",
    "Feature Type Description" : "Spur gear ring sector with external involute teeth (tips flush at the outer radius) and an optional meshing pinion at parallel axes. Inner radius 0 fills it solid; arc angle 360 makes the full gear. Module is derived: m = 2 Ro / (teeth * 360 / arc + 2)."
}
export const arcSegment = defineFeature(function(context is Context, id is Id, def is map)
    precondition
    {
        annotation { "Name" : "Outer radius", "Description" : "Tooth tip radius." }
        isLength(def.outerRadius, { (millimeter) : [1, 300, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Inner radius", "Description" : "Bore radius. 0 fills the segment solid." }
        isLength(def.innerRadius, { (millimeter) : [0, 270, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Height", "Description" : "Face width." }
        isLength(def.height, { (millimeter) : [0.1, 15, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Arc angle", "Description" : "360 divided by the number of segments in the full ring (9 wafers -> 40 deg). 360 makes the full gear." }
        isAngle(def.arcAngle, { (degree) : [0.1, 40, 360] } as AngleBoundSpec);

        annotation { "Name" : "Teeth", "Description" : "Number of teeth ON THIS ARC (joint faces land mid-slot). Full-circle equivalent = teeth * 360 / arc angle." }
        isInteger(def.teeth, { (unitless) : [1, 32, 1000] } as IntegerBoundSpec);

        annotation { "Name" : "Pressure angle", "Description" : "ISO standardizes 20 and 25 deg. 25 (the default) avoids undercut on small pinions (under ~14 teeth) without profile shift." }
        isAngle(def.pressureAngle, { (degree) : [5, 25, 45] } as AngleBoundSpec);

        annotation { "Name" : "Mating pinion", "Default" : true, "Description" : "Also generate the meshing pinion in place: parallel axes, shared module, tooth facing slot at the ring's +X meridian." }
        def.mate is boolean;
        if (def.mate)
        {
            annotation { "Group Name" : "Mating Pinion", "Driving Parameter" : "mate", "Collapsed By Default" : false }
            {
                annotation { "Name" : "Pinion teeth", "Description" : "Ratio = ring full-circle count / pinion teeth. Coprime counts wear best (hunting tooth)." }
                isInteger(def.pinionTeeth, { (unitless) : [4, 13, 200] } as IntegerBoundSpec);

                annotation { "Name" : "Pinion height", "Description" : "Pinion face width. Match the ring height for full-face contact." }
                isLength(def.pinionHeight, { (millimeter) : [0.1, 15, 1000] } as LengthBoundSpec);

                annotation { "Name" : "Pinion bore radius", "Description" : "0 = solid. 1.5 mm suits a 3 mm motor shaft." }
                isLength(def.pinionBore, { (millimeter) : [0, 1.5, 100] } as LengthBoundSpec);
            }
        }
    }
    {
        buildGear(context, id + "ring", {
            "outerRadius" : def.outerRadius,
            "innerRadius" : def.innerRadius,
            "height" : def.height,
            "arcAngle" : def.arcAngle,
            "teeth" : def.teeth,
            "pressureAngle" : def.pressureAngle
        });

        if (def.mate)
        {
            // Shared module; parallel axes; center distance = sum of the
            // pitch radii. Both gears sit on the same z = 0 plane.
            const zFull = def.teeth * (360 * degree) / def.arcAngle;
            const m = 2 * def.outerRadius / (zFull + 2);
            const zp = def.pinionTeeth;
            const C = m * (zFull + zp) / 2;

            buildGear(context, id + "pinion", {
                "outerRadius" : m * (zp + 2) / 2,
                "innerRadius" : def.pinionBore,
                "height" : def.pinionHeight,
                "arcAngle" : 360 * degree,
                "teeth" : zp,
                "pressureAngle" : def.pressureAngle
            });

            // Clocking: the pinion presents a slot center on its -X meridian
            // (the side facing the ring). An even ring count puts a ring
            // SLOT at the contact meridian too, so the pinion pre-rotates
            // half a pitch to face it with a tooth; an odd ring count
            // already presents a ring tooth there.
            var preRot = 0 * degree;
            if (def.teeth % 2 == 0)
                preRot = 180 * degree / zp;
            const place = transform(vector(C, 0 * millimeter, 0 * millimeter))
                * rotationAround(line(vector(0, 0, 0) * millimeter, vector(0, 0, 1)), preRot);
            opTransform(context, id + "placePinion", {
                "bodies" : qCreatedBy(id + "pinion", EntityType.BODY),
                "transform" : place
            });
        }
    });

// The whole single-gear pipeline: blank, bore, involute tooth slots.
// g: outerRadius, innerRadius, height, arcAngle, teeth, pressureAngle.
// Bodies are created under the passed id.
function buildGear(context is Context, id is Id, g is map)
{
    const Ro = g.outerRadius;
    const Ri = g.innerRadius;
    if (Ri >= Ro)
        throw regenError("Inner radius must be smaller than the outer radius.");

    // 3-point arcs degenerate as start/end converge, so anything within
    // 0.01 deg of a full turn builds the closed-circle path instead.
    const isFull = g.arcAngle >= 360 * degree - 0.01 * degree;
    const half = g.arcAngle / 2;

    const zFull = g.teeth * (360 * degree) / g.arcAngle;    // full-circle equivalent count
    const m = 2 * Ro / (zFull + 2);             // derived module (tips at Ro)
    const rPitch = Ro - m;
    const rRoot = Ro - 2.25 * m;                // addendum m + dedendum 1.25 m
    const ov = 1 * millimeter;                  // cutter overshoot past both faces

    if (rRoot <= Ri && Ri > 0 * millimeter)
        throw regenError("Tooth slots cut through to the bore. This blank needs at least "
            ~ ceil((2 * Ro / ((Ro - Ri) / 2.25) - 2) * g.arcAngle / (360 * degree))
            ~ " teeth on this arc, or a smaller inner radius.");

    // Outer boundary on the Top plane, symmetric about +X.
    var sk = newSketch(context, id + "profile", {
        "sketchPlane" : qCreatedBy(makeId("Top"), EntityType.FACE)
    });
    if (isFull)
    {
        skCircle(sk, "outerCircle", {
            "center" : vector(0, 0) * millimeter,
            "radius" : Ro
        });
    }
    else
    {
        skArc(sk, "outerArc", {
            "start" : vector(Ro * cos(-half), Ro * sin(-half)),
            "mid"   : vector(Ro, 0 * millimeter),
            "end"   : vector(Ro * cos(half), Ro * sin(half))
        });
        skLineSegment(sk, "sideA", {
            "start" : vector(0, 0) * millimeter,
            "end"   : vector(Ro * cos(-half), Ro * sin(-half))
        });
        skLineSegment(sk, "sideB", {
            "start" : vector(Ro * cos(half), Ro * sin(half)),
            "end"   : vector(0, 0) * millimeter
        });
    }
    skSolve(sk);

    opExtrude(context, id + "extrude", {
        "entities" : qSketchRegion(id + "profile"),
        "direction" : vector(0, 0, 1),
        "endBound" : BoundingType.BLIND,
        "endDepth" : g.height
    });

    // Inner bore: a revolved rectangle (edge on the axis is fine for
    // opRevolve; the profile must not CROSS the axis).
    if (Ri > 0 * millimeter)
    {
        var boreSk = newSketch(context, id + "boreProfile", {
            "sketchPlane" : qCreatedBy(makeId("Front"), EntityType.FACE)
        });
        skLineSegment(boreSk, "axisEdge", {
            "start" : vector(0 * millimeter, -ov),
            "end"   : vector(0 * millimeter, g.height + ov)
        });
        skLineSegment(boreSk, "top", {
            "start" : vector(0 * millimeter, g.height + ov),
            "end"   : vector(Ri, g.height + ov)
        });
        skLineSegment(boreSk, "wall", {
            "start" : vector(Ri, g.height + ov),
            "end"   : vector(Ri, -ov)
        });
        skLineSegment(boreSk, "bottom", {
            "start" : vector(Ri, -ov),
            "end"   : vector(0 * millimeter, -ov)
        });
        skSolve(boreSk);
        opRevolve(context, id + "boreCut", {
            "entities" : qSketchRegion(id + "boreProfile"),
            "axis" : line(vector(0, 0, 0) * millimeter, vector(0, 0, 1)),
            "angleForward" : 360 * degree
        });
        opBoolean(context, id + "subtractBore", {
            "tools" : qCreatedBy(id + "boreCut", EntityType.BODY),
            "targets" : qCreatedBy(id + "extrude", EntityType.BODY),
            "operationType" : BooleanOperationType.SUBTRACTION
        });
        opDeleteBodies(context, id + "deleteBoreSketch", {
            "entities" : qCreatedBy(id + "boreProfile", EntityType.BODY)
        });
    }

    // Tooth slots. Transverse-plane involute (exact for spurs): the slot
    // HALF-ANGLE at radius r is tau/4 - inv(alpha) + inv(alpha_r) with
    // alpha_r = acos(rb / r), inv(x) = tan(x) - x. Below the base circle
    // the flank drops radially at the base-circle angle.
    const rb = rPitch * cos(g.pressureAngle);   // base circle
    const tau = 2 * PI / zFull;                 // angular pitch, radians
    const invAlpha = tan(g.pressureAngle) - g.pressureAngle / radian;
    var slotHalfAngle = function(r)             // radians as a number
    {
        var a = tau / 4 - invAlpha;
        if (r > rb)
        {
            const ar = acos(rb / r);
            a = a + tan(ar) - ar / radian;
        }
        return a;
    };
    const rStart = max(rRoot, rb);
    if (slotHalfAngle(rStart) <= 0)
        throw regenError("No slot width left at the root - lower the pressure angle or the tooth count.");

    // Canonical frame: slot centered on the +X axis (rotated out to the
    // leading joint at phi0 = -arc/2, mirrored for the -side). The root
    // chord is parallel to Y here. +side flank, root -> tip.
    const phi0 = -half;
    const K = 10;                               // involute facets per flank
    const rTipOv = Ro + ov;
    var flankPts = [];
    if (rRoot < rb)
        flankPts = append(flankPts, vector(
            rRoot * cos(slotHalfAngle(rb) * radian),
            rRoot * sin(slotHalfAngle(rb) * radian)));
    for (var i = 0; i <= K; i += 1)
    {
        const r = rStart + (rTipOv - rStart) * i / K;
        const a = slotHalfAngle(r);
        flankPts = append(flankPts, vector(r * cos(a * radian), r * sin(a * radian)));
    }

    // Root fillet, radius 0.38 m (ISO rack tip radius), clamped so the two
    // corner arcs never overlap on the root land: the sharp corner between
    // root chord and flank start becomes a 5-facet tangent arc. The CUTTER
    // loses area at the corner, so the TOOTH root gains the fillet.
    var plusPts = flankPts;
    const pf0 = flankPts[0];
    const uDir = vector(0, -1);                 // along the root chord, away from the corner
    var vDir = flankPts[1] - pf0;
    vDir = vDir / norm(vDir);                   // along the flank, away from the corner
    const phiC = acos(dot(uDir, vDir));
    var rho = 0.38 * m;
    var tOff = rho / tan(phiC / 2);
    if (tOff > 0.9 * pf0[1])                    // pf0[1] = half the root chord
    {
        rho = rho * 0.9 * pf0[1] / tOff;
        tOff = 0.9 * pf0[1];
    }
    if (rho > 0.02 * millimeter)
    {
        const Tc = pf0 + uDir * tOff;           // tangency on the root chord
        const Tf = pf0 + vDir * tOff;           // tangency on the flank
        var bis = uDir + vDir;
        bis = bis / norm(bis);
        const Cc = pf0 + bis * (rho / sin(phiC / 2));
        const a0 = atan2(Tc[1] - Cc[1], Tc[0] - Cc[0]);
        const a1 = atan2(Tf[1] - Cc[1], Tf[0] - Cc[0]);
        var sweep = a1 - a0;
        if (sweep > 180 * degree)
            sweep = sweep - 360 * degree;
        if (sweep < -180 * degree)
            sweep = sweep + 360 * degree;
        const kf = 5;
        var pts = [Tc];
        for (var i = 1; i < kf; i += 1)
        {
            const a = a0 + sweep * i / kf;
            pts = append(pts, Cc + vector(cos(a), sin(a)) * rho);
        }
        pts = append(pts, Tf);
        // Rejoin the involute above the arc (sub-print-scale kink).
        const rJoin = norm(Tf);
        for (var i = 0; i < size(flankPts); i += 1)
        {
            if (norm(flankPts[i]) > rJoin + 0.01 * millimeter)
                pts = append(pts, flankPts[i]);
        }
        plusPts = pts;
    }

    // Closed outline in world orientation: +side root -> tip, tip chord,
    // mirrored -side tip -> root, root chord closes it.
    var rot = function(p)
    {
        return vector(p[0] * cos(phi0) - p[1] * sin(phi0),
                      p[0] * sin(phi0) + p[1] * cos(phi0));
    };
    var outline = [];
    for (var i = 0; i < size(plusPts); i += 1)
        outline = append(outline, rot(plusPts[i]));
    for (var i = size(plusPts) - 1; i >= 0; i -= 1)
        outline = append(outline, rot(vector(plusPts[i][0], -plusPts[i][1])));

    // One slot cutter, extruded straight through (spur teeth are prisms),
    // then rotation-patterned and subtracted in a single boolean.
    var slotSk = newSketchOnPlane(context, id + "slotSk", {
        "sketchPlane" : plane(
            vector(0 * millimeter, 0 * millimeter, -ov),
            vector(0, 0, 1),
            vector(1, 0, 0))
    });
    const nPts = size(outline);
    for (var e = 0; e < nPts; e += 1)
    {
        skLineSegment(slotSk, "edge" ~ e, {
            "start" : outline[e],
            "end"   : outline[(e + 1) % nPts]
        });
    }
    skSolve(slotSk);
    opExtrude(context, id + "slotCutter", {
        "entities" : qSketchRegion(id + "slotSk"),
        "direction" : vector(0, 0, 1),
        "endBound" : BoundingType.BLIND,
        "endDepth" : g.height + 2 * ov
    });

    // A slot at each joint face plus one per tooth between them; on a
    // full circle the last slot would duplicate the first.
    const pitchAngle = g.arcAngle / g.teeth;
    var nSlots = g.teeth + 1;
    if (isFull)
        nSlots = g.teeth;
    if (nSlots > 1)
    {
        var transforms = [];
        var names = [];
        for (var k = 1; k < nSlots; k += 1)
        {
            transforms = append(transforms,
                rotationAround(line(vector(0, 0, 0) * millimeter, vector(0, 0, 1)), k * pitchAngle));
            names = append(names, "slot" ~ k);
        }
        opPattern(context, id + "slotPattern", {
            "entities" : qCreatedBy(id + "slotCutter", EntityType.BODY),
            "transforms" : transforms,
            "instanceNames" : names
        });
    }

    opBoolean(context, id + "subtractSlots", {
        "tools" : qUnion([
            qCreatedBy(id + "slotCutter", EntityType.BODY),
            qCreatedBy(id + "slotPattern", EntityType.BODY)
        ]),
        "targets" : qCreatedBy(id + "extrude", EntityType.BODY),
        "operationType" : BooleanOperationType.SUBTRACTION
    });
    opDeleteBodies(context, id + "deleteSlotSketch", {
        "entities" : qCreatedBy(id + "slotSk", EntityType.BODY)
    });

    // Leave only the solid behind.
    opDeleteBodies(context, id + "deleteSketch", {
        "entities" : qCreatedBy(id + "profile", EntityType.BODY)
    });
}
