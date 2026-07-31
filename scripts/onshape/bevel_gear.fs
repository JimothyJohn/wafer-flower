FeatureScript 1803;
import(path : "onshape/std/geometry.fs", version : "1803.0");

/*
    Bevel gear generator - built incrementally, one verified piece at a time.

    Step 1: "Arc Segment" - a plain annular arc blank (no teeth). This is the
    stock the arced bevel rack will be cut from. Inputs: outer radius, segment
    width (outer radius - inner radius), height, and arc length. Arc length is
    measured along the OUTER radius. The segment is centered on the +X axis,
    flat on the Top plane, extruded +Z by the height.

    Onshape paste rules learned the hard way (do not regress):
    - annotation strings must be printable ASCII (no em-dashes, no unicode minus)
    - reportFeatureInfo, not reportInfo
    - opSphere, not fSphere
*/

annotation {
    "Feature Type Name" : "Arc Segment",
    "Feature Type Description" : "Step 1 of the bevel rack build: a plain annular arc blank. Arc length is measured along the outer radius; the segment is centered on the +X axis on the Top plane."
}
export const arcSegment = defineFeature(function(context is Context, id is Id, def is map)
    precondition
    {
        annotation { "Name" : "Outer radius" }
        isLength(def.outerRadius, { (millimeter) : [1, 300, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Segment width", "Description" : "Outer radius minus inner radius." }
        isLength(def.segWidth, { (millimeter) : [0.1, 30, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Height" }
        isLength(def.height, { (millimeter) : [0.1, 15, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Arc length", "Description" : "Measured along the outer radius." }
        isLength(def.arcLength, { (millimeter) : [0.1, 209.44, 100000] } as LengthBoundSpec);
    }
    {
        const Ro = def.outerRadius;
        const Ri = Ro - def.segWidth;
        if (Ri <= 0 * millimeter)
            throw regenError("Segment width must be smaller than the outer radius.");

        const theta = (def.arcLength / Ro) * radian;
        if (theta >= 360 * degree)
            throw regenError("Arc length wraps a full circle at this outer radius. Shorten it.");
        const half = theta / 2;

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

        // Leave only the solid behind.
        opDeleteBodies(context, id + "deleteSketch", {
            "entities" : qCreatedBy(id + "profile", EntityType.BODY)
        });

        reportFeatureInfo(context, id,
            "Arc segment: Ro " ~ toString(Ro / millimeter) ~ " mm, Ri " ~ toString(Ri / millimeter)
            ~ " mm, arc " ~ toString(theta / degree) ~ " deg.");
    });
