FeatureScript 1803;
import(path : "onshape/std/geometry.fs", version : "1803.0");

/*
    Bevel gear generator - built incrementally, one verified piece at a time.

    Step 1: "Arc Segment" - a plain annular arc blank (no teeth). Inputs:
    outer radius, segment width (outer radius - inner radius), height, and
    arc ANGLE in degrees (the halo divides 360 by the wafer count, so the
    angle is the natural input - e.g. 9 wafers -> 40 deg). The segment is
    centered on the +X axis, flat on the Top plane, extruded +Z by the height.

    Step 2: cone angle - the outer wall is cut to a cone, BIG END AT THE
    BOTTOM (z = 0, the wall face): outer radius Ro at z = 0 shrinking to
    Ro - height * tan(coneAngle) at the top. 0 deg = step-1 prism unchanged.
    The inner wall stays cylindrical.

    Onshape paste rules learned the hard way (do not regress):
    - annotation strings must be printable ASCII (no em-dashes, no unicode minus)
    - reportFeatureInfo, not reportInfo
    - opSphere, not fSphere
*/

annotation {
    "Feature Type Name" : "Arc Segment",
    "Feature Type Description" : "Bevel rack blank: an annular arc segment whose outer wall is coned (big end at the bottom). Centered on the +X axis on the Top plane."
}
export const arcSegment = defineFeature(function(context is Context, id is Id, def is map)
    precondition
    {
        annotation { "Name" : "Outer radius", "Description" : "Outer radius at the bottom face (the cone's big end)." }
        isLength(def.outerRadius, { (millimeter) : [1, 300, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Segment width", "Description" : "Outer radius minus inner radius." }
        isLength(def.segWidth, { (millimeter) : [0.1, 30, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Height" }
        isLength(def.height, { (millimeter) : [0.1, 15, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Arc angle", "Description" : "360 divided by the number of segments in the full ring, e.g. 9 wafers -> 40 deg." }
        isAngle(def.arcAngle, { (degree) : [0.1, 40, 359.9] } as AngleBoundSpec);

        annotation { "Name" : "Cone angle", "Description" : "Angle of the outer wall from vertical. 0 = straight (cylindrical) wall. Big end is at the bottom face." }
        isAngle(def.coneAngle, { (degree) : [0, 45, 80] } as AngleBoundSpec);
    }
    {
        const Ro = def.outerRadius;
        const Ri = Ro - def.segWidth;
        if (Ri <= 0 * millimeter)
            throw regenError("Segment width must be smaller than the outer radius.");

        const half = def.arcAngle / 2;

        // Top-face outer radius after the cone cut; the cone must not eat
        // through the full segment width.
        const RoTop = Ro - def.height * tan(def.coneAngle);
        if (RoTop <= Ri)
            throw regenError("Cone angle consumes the full segment width at the top. Reduce cone angle or height, or widen the segment.");

        // Annular sector profile on the Top plane, symmetric about +X.
        var sk = newSketch(context, id + "profile", {
            "sketchPlane" : qCreatedBy(makeId("Top"), EntityType.FACE)
        });
        skArc(sk, "outerArc", {
            "start" : vector(Ro * cos(-half), Ro * sin(-half)),
            "mid"   : vector(Ro, 0 * millimeter),
            "end"   : vector(Ro * cos(half), Ro * sin(half))
        });
        skArc(sk, "innerArc", {
            "start" : vector(Ri * cos(-half), Ri * sin(-half)),
            "mid"   : vector(Ri, 0 * millimeter),
            "end"   : vector(Ri * cos(half), Ri * sin(half))
        });
        skLineSegment(sk, "sideA", {
            "start" : vector(Ri * cos(-half), Ri * sin(-half)),
            "end"   : vector(Ro * cos(-half), Ro * sin(-half))
        });
        skLineSegment(sk, "sideB", {
            "start" : vector(Ri * cos(half), Ri * sin(half)),
            "end"   : vector(Ro * cos(half), Ro * sin(half))
        });
        skSolve(sk);

        opExtrude(context, id + "extrude", {
            "entities" : qSketchRegion(id + "profile"),
            "direction" : vector(0, 0, 1),
            "endBound" : BoundingType.BLIND,
            "endDepth" : def.height
        });

        // Step 2: cone the outer wall. Cut with a revolved wedge - everything
        // outside the cone line r(z) = Ro - z * tan(coneAngle). The cutter
        // overshoots both end faces by 1 mm (coplanar-cap sliver trap).
        if (def.coneAngle > 0 * degree)
        {
            const ov = 1 * millimeter;
            const t = tan(def.coneAngle);
            const rBot = Ro + ov * t;                    // cone line at z = -ov
            const rTop = Ro - (def.height + ov) * t;     // cone line at z = height + ov
            const rMax = rBot + 5 * millimeter;

            // Front plane is world XZ: sketch x = radius, sketch y = world z.
            var cutSk = newSketch(context, id + "coneProfile", {
                "sketchPlane" : qCreatedBy(makeId("Front"), EntityType.FACE)
            });
            skLineSegment(cutSk, "cone", {
                "start" : vector(rBot, -ov),
                "end"   : vector(rTop, def.height + ov)
            });
            skLineSegment(cutSk, "top", {
                "start" : vector(rTop, def.height + ov),
                "end"   : vector(rMax, def.height + ov)
            });
            skLineSegment(cutSk, "outer", {
                "start" : vector(rMax, def.height + ov),
                "end"   : vector(rMax, -ov)
            });
            skLineSegment(cutSk, "bottom", {
                "start" : vector(rMax, -ov),
                "end"   : vector(rBot, -ov)
            });
            skSolve(cutSk);

            opRevolve(context, id + "coneCut", {
                "entities" : qSketchRegion(id + "coneProfile"),
                "axis" : line(vector(0, 0, 0) * millimeter, vector(0, 0, 1)),
                "angleForward" : 360 * degree
            });
            opBoolean(context, id + "subtractCone", {
                "tools" : qCreatedBy(id + "coneCut", EntityType.BODY),
                "targets" : qCreatedBy(id + "extrude", EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
            });
            opDeleteBodies(context, id + "deleteConeSketch", {
                "entities" : qCreatedBy(id + "coneProfile", EntityType.BODY)
            });
        }

        // Leave only the solid behind.
        opDeleteBodies(context, id + "deleteSketch", {
            "entities" : qCreatedBy(id + "profile", EntityType.BODY)
        });

        reportFeatureInfo(context, id,
            "Arc segment: Ro " ~ toString(Ro / millimeter) ~ " mm at bottom, "
            ~ toString(RoTop / millimeter) ~ " mm at top, Ri " ~ toString(Ri / millimeter)
            ~ " mm, arc " ~ toString(def.arcAngle / degree) ~ " deg, cone "
            ~ toString(def.coneAngle / degree) ~ " deg.");
    });
