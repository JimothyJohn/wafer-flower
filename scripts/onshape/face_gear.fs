FeatureScript 1803;
import(path : "onshape/std/geometry.fs", version : "1803.0");

/*
    Face-gear arc generator (2026-07-31, Nick's layout): the ring segment
    carries FACE teeth - radial slots cut into the FRONT face, tooth depth
    along Height, tooth lines perpendicular to the arc - and the motor's
    SPUR pinion lies flat against the wall on a RADIAL axis, meshing down
    onto the face. This is the classic face-gear drive (and the halo
    repo's parked motion concept). Prior generators live in git history:
    spur ring + parallel-axis pinion at 5623c8c, the full ISO straight
    bevel / crown generator at ed600bf.

    Geometry: reference radius rRef = (Ro + Ri) / 2 (mid tooth band);
    module m = 2 rRef / zFull, zFull = teeth * 360 / arc. Ring slots are a
    rack tooth-space profile (straight flanks at the pressure angle, root
    fillet 0.38 m) swept radially with CONSTANT cross-section - exactly
    conjugate to the spur pinion at rRef, approximate off it (linear pitch
    grows with radius; keep the tooth band and pinion face modest, which
    a 30 mm band on a 285 mm rRef is). Pitch plane z = Height - m; slot
    root z = Height - 2.25 m; pinion axis height = pitch plane + pinion
    pitch radius, giving the standard 0.25 m root clearance. Sector joint
    faces land mid-slot (halo tiling rule). Clocking pairs a pinion tooth
    with a ring slot at the +X contact meridian. Ratio = zFull / pinion
    teeth; coprime counts hunt (wear-even). Backlash = total pitch-line
    play, split evenly (each gear's slots widen by half, a quarter per
    flank). Pinion bore takes an optional D-flat (chord cut, depth from
    the round wall).

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
    "Feature Type Description" : "Face-gear ring sector: radial teeth cut into the front face (tooth depth along Height, tooth lines perpendicular to the arc), plus an optional meshing spur pinion on a radial axis lying flat against the wall. Module is derived: m = 2 * (Ro + Ri) / 2 / (teeth * 360 / arc)."
}
export const arcSegment = defineFeature(function(context is Context, id is Id, def is map)
    precondition
    {
        annotation { "Name" : "Outer radius", "Description" : "Outer edge of the segment and of the tooth band." }
        isLength(def.outerRadius, { (millimeter) : [1, 300, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Inner radius", "Description" : "Bore radius; also the inner edge of the tooth band." }
        isLength(def.innerRadius, { (millimeter) : [0, 270, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Height", "Description" : "Segment thickness. Teeth are cut 2.25 m deep into the front (top) face." }
        isLength(def.height, { (millimeter) : [0.1, 15, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Arc angle", "Description" : "360 divided by the number of segments in the full ring (9 wafers -> 40 deg). 360 makes the full gear." }
        isAngle(def.arcAngle, { (degree) : [0.1, 40, 360] } as AngleBoundSpec);

        annotation { "Name" : "Teeth", "Description" : "Number of teeth ON THIS ARC (joint faces land mid-slot). Full-circle equivalent = teeth * 360 / arc angle." }
        isInteger(def.teeth, { (unitless) : [1, 32, 1000] } as IntegerBoundSpec);

        annotation { "Name" : "Pressure angle", "Description" : "ISO standardizes 20 and 25 deg. 25 (the default) avoids undercut on small pinions (under ~14 teeth). Rack-flank limit here is ~32 deg." }
        isAngle(def.pressureAngle, { (degree) : [5, 25, 30] } as AngleBoundSpec);

        annotation { "Name" : "Backlash", "Description" : "Total circumferential play at the pitch line, split evenly between ring and pinion slots. 0 = theoretical tight mesh; 0.1-0.2 mm is typical for FDM." }
        isLength(def.backlash, { (millimeter) : [0, 0.15, 2] } as LengthBoundSpec);

        annotation { "Name" : "Mating pinion", "Default" : true, "Description" : "Also generate the meshing spur pinion in place: radial axis lying flat against the wall, tangent to the ring's pitch plane, tooth facing slot at the +X meridian." }
        def.mate is boolean;
        if (def.mate)
        {
            annotation { "Group Name" : "Mating Pinion", "Driving Parameter" : "mate", "Collapsed By Default" : false }
            {
                annotation { "Name" : "Pinion teeth", "Description" : "Ratio = ring full-circle count / pinion teeth. Coprime counts wear best (hunting tooth)." }
                isInteger(def.pinionTeeth, { (unitless) : [4, 13, 200] } as IntegerBoundSpec);

                annotation { "Name" : "Pinion height", "Description" : "Pinion face width, which runs RADIALLY here. Keep it inside the tooth band; centered on the band middle." }
                isLength(def.pinionHeight, { (millimeter) : [0.1, 10, 1000] } as LengthBoundSpec);

                annotation { "Name" : "Pinion bore radius", "Description" : "0 = solid. 1.5 mm suits a 3 mm motor shaft (print-fit may want +0.1)." }
                isLength(def.pinionBore, { (millimeter) : [0, 1.5, 100] } as LengthBoundSpec);

                annotation { "Name" : "Bore flat depth", "Description" : "D-shaft flat: cut depth from the round bore wall. 0 = plain round bore. A 3 mm D-shaft typically wants 0.5 mm." }
                isLength(def.pinionFlat, { (millimeter) : [0, 0.5, 10] } as LengthBoundSpec);

                annotation { "Name" : "Hub length", "Description" : "Hub boss around the bore on the MOTOR side (outer radius face): spacer off the gearbox nose plus extra bore engagement. 0 = none." }
                isLength(def.pinionHubLength, { (millimeter) : [0, 3, 100] } as LengthBoundSpec);

                annotation { "Name" : "Hub radius", "Description" : "Must stay under the pinion pitch radius minus one module so it clears the ring's tooth tips - the guard reports the exact limit." }
                isLength(def.pinionHubRadius, { (millimeter) : [0.1, 4.5, 100] } as LengthBoundSpec);
            }
        }
    }
    {
        buildFaceRing(context, id + "ring", {
            "outerRadius" : def.outerRadius,
            "innerRadius" : def.innerRadius,
            "height" : def.height,
            "arcAngle" : def.arcAngle,
            "teeth" : def.teeth,
            "pressureAngle" : def.pressureAngle,
            "backlash" : def.backlash,
            "boreFlat" : 0 * millimeter,
            "hubLength" : 0 * millimeter,
            "hubRadius" : 0 * millimeter
        });

        if (def.mate)
        {
            // Shared module from the ring's reference radius. The pinion is
            // a plain spur; its axis is RADIAL (+X), tangent to the ring's
            // pitch plane, face centered on the middle of the tooth band.
            const zFull = def.teeth * (360 * degree) / def.arcAngle;
            const rRef = (def.outerRadius + def.innerRadius) / 2;
            const m = 2 * rRef / zFull;
            const zp = def.pinionTeeth;
            const rPp = m * zp / 2;

            if (def.pinionHubLength > 0 * millimeter)
            {
                // The hub sweeps past the ring face as the pinion turns; it
                // must clear the ring's tooth tips (pitch radius less one
                // module of addendum, less 0.5 mm running clearance).
                const hubMax = rPp - m - 0.5 * millimeter;
                if (def.pinionHubRadius > hubMax)
                    throw regenError("Hub radius collides with the ring's tooth tips - maximum here is "
                        ~ (floor(hubMax / millimeter * 100) / 100) ~ " mm.");
                if (def.pinionHubRadius <= def.pinionBore)
                    throw regenError("Hub radius must exceed the pinion bore radius.");
            }

            buildGear(context, id + "pinion", {
                "outerRadius" : m * (zp + 2) / 2,
                "innerRadius" : def.pinionBore,
                "height" : def.pinionHeight,
                "arcAngle" : 360 * degree,
                "teeth" : zp,
                "pressureAngle" : def.pressureAngle,
                "backlash" : def.backlash,
                "boreFlat" : def.pinionFlat,
                "hubLength" : def.pinionHubLength,
                "hubRadius" : def.pinionHubRadius
            });

            // Clocking: after the tilt the pinion's own +X meridian points
            // DOWN at the ring face. The ring presents a slot at the +X
            // contact meridian when its count is even; the pinion presents
            // one there when ITS count is even. Mesh needs tooth-facing-
            // slot, so pre-rotate half a pitch when the parities match.
            var preRot = 0 * degree;
            if (def.teeth % 2 == def.pinionTeeth % 2)
                preRot = 180 * degree / zp;
            const zAxis = line(vector(0, 0, 0) * millimeter, vector(0, 0, 1));
            const yAxis = line(vector(0, 0, 0) * millimeter, vector(0, 1, 0));
            const place = transform(vector(
                    rRef - def.pinionHeight / 2,
                    0 * millimeter,
                    def.height - m + rPp))
                * rotationAround(yAxis, 90 * degree)
                * rotationAround(zAxis, preRot);
            opTransform(context, id + "placePinion", {
                "bodies" : qCreatedBy(id + "pinion", EntityType.BODY),
                "transform" : place
            });
        }
    });

// MOTOR ENVELOPE: a solid stand-in for the gearmotor, to design a housing
// around. Defaults are the 22PG-2430BL 720:1 brushless planetary (Nick's
// pick, 2026-07-27) exactly as the repo already carries it in the BRK block
// of scripts/bracket_stl.py: 24 mm can, 22 mm gearbox nose 20 long, 65
// overall INCLUDING the nose, 4 mm D-shaft with a 0.5 flat.
//
// THOSE ARE CATALOG-TYPICAL, NOT MEASURED - the RobotShop datasheet is
// CDN-blocked, and the shaft length was never published at all, so its
// default here is a placeholder rather than a spec. Measure the purchased
// unit and update the parameters before committing a housing to print.
// (Same caveat, same numbers, as bracket_stl.py and TODO.md.)
//
// Frame: the gearbox NOSE FACE - where the shaft exits - is the datum at
// z = 0. The can runs up +Z, the shaft down -Z. Position the body with a
// Transform or a mate connector; it takes no placement parameters.
annotation {
    "Feature Type Name" : "Motor Envelope",
    "Feature Type Description" : "Solid stand-in for the gearmotor, to design a housing around it. The gearbox nose face is the datum at z = 0: the can runs up +Z, the shaft down -Z. Defaults are the 22PG-2430BL, which are CATALOG-TYPICAL and NOT MEASURED - measure your unit. Clearance inflates every radius and the back of the can, so the body can be subtracted directly as a pocket."
}
export const motorEnvelope = defineFeature(function(context is Context, id is Id, def is map)
    precondition
    {
        annotation { "Name" : "Body diameter", "Description" : "Outside diameter of the motor can. 22PG-2430BL: 24 mm." }
        isLength(def.bodyDiameter, { (millimeter) : [0.1, 24, 1000] } as LengthBoundSpec);

        annotation { "Name" : "Overall length", "Description" : "Nose face to the back of the can, INCLUDING the gearbox nose and excluding the shaft. 22PG-2430BL: 65 mm." }
        isLength(def.totalLength, { (millimeter) : [0.2, 65, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Nose diameter", "Description" : "Gearbox nose diameter - the step in front of the can. 22PG-2430BL: 22 mm. Set it equal to the body diameter for a motor with no step." }
        isLength(def.noseDiameter, { (millimeter) : [0.1, 22, 1000] } as LengthBoundSpec);

        annotation { "Name" : "Nose length", "Description" : "Length of the gearbox nose, measured from the nose face. 22PG-2430BL: 20 mm." }
        isLength(def.noseLength, { (millimeter) : [0, 20, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Clearance", "Description" : "Added to every radius and to the back of the can. 0 is the true nominal envelope; 0.4 matches the pocket clearance the repo's printed motor shell already uses. Set it nonzero when this body will be subtracted to form a pocket." }
        isLength(def.clearance, { (millimeter) : [0, 0, 100] } as LengthBoundSpec);

        annotation { "Name" : "Include shaft", "Default" : true, "Description" : "Model the output shaft running down -Z from the nose face. Turn off for a housing that stops at the nose." }
        def.includeShaft is boolean;
        if (def.includeShaft)
        {
            annotation { "Group Name" : "Output Shaft", "Driving Parameter" : "includeShaft", "Collapsed By Default" : false }
            {
                annotation { "Name" : "Shaft diameter", "Description" : "22PG-2430BL: 4 mm." }
                isLength(def.shaftDiameter, { (millimeter) : [0.1, 4, 1000] } as LengthBoundSpec);

                annotation { "Name" : "Shaft length", "Description" : "Exposed length in front of the nose face. PLACEHOLDER: this dimension is in no repo file and was never published - measure it." }
                isLength(def.shaftLength, { (millimeter) : [0.1, 12, 10000] } as LengthBoundSpec);

                annotation { "Name" : "Shaft flat depth", "Description" : "D-flat depth from the shaft wall, running the full exposed length. 0 = plain round shaft. 22PG-2430BL: 0.5 mm." }
                isLength(def.shaftFlat, { (millimeter) : [0, 0.5, 100] } as LengthBoundSpec);
            }
        }
    }
    {
        if (def.noseLength >= def.totalLength)
            throw regenError("Nose length must be shorter than the overall length - the overall length includes the nose.");

        const c = def.clearance;
        const rBody = def.bodyDiameter / 2 + c;
        const rNose = def.noseDiameter / 2 + c;
        const zBack = def.totalLength + c;
        const hasShaft = def.includeShaft;
        const rShaft = hasShaft ? def.shaftDiameter / 2 + c : 0 * millimeter;
        const zTip = hasShaft ? -def.shaftLength : 0 * millimeter;

        if (hasShaft && def.shaftFlat >= rShaft)
            throw regenError("Shaft flat depth must be smaller than the shaft radius.");

        // One revolved silhouette builds the whole stepped body - no
        // booleans, so none of the step faces are boolean seams. Points run
        // up the outside from the shaft tip; the closing edge is the axis
        // itself (on the axis is fine for opRevolve, across it is not).
        var sil = [];
        if (hasShaft)
        {
            sil = append(sil, vector(0 * millimeter, zTip));
            sil = append(sil, vector(rShaft, zTip));
            sil = append(sil, vector(rShaft, 0 * millimeter));
        }
        else
        {
            sil = append(sil, vector(0 * millimeter, 0 * millimeter));
        }
        sil = append(sil, vector(rNose, 0 * millimeter));
        sil = append(sil, vector(rNose, def.noseLength));
        sil = append(sil, vector(rBody, def.noseLength));
        sil = append(sil, vector(rBody, zBack));
        sil = append(sil, vector(0 * millimeter, zBack));

        // Drop coincident neighbours before sketching: a zero-length segment
        // fails skSolve, and both degenerate inputs are legitimate - a nose
        // the same diameter as the can, or a nose length of 0.
        var pts = [];
        for (var i = 0; i < size(sil); i += 1)
        {
            if (size(pts) == 0 || norm(sil[i] - pts[size(pts) - 1]) > 1e-6 * millimeter)
                pts = append(pts, sil[i]);
        }

        var sk = newSketch(context, id + "silhouette", {
            "sketchPlane" : qCreatedBy(makeId("Front"), EntityType.FACE)
        });
        const nPts = size(pts);
        for (var e = 0; e < nPts; e += 1)
        {
            skLineSegment(sk, "edge" ~ e, {
                "start" : pts[e],
                "end"   : pts[(e + 1) % nPts]
            });
        }
        skSolve(sk);

        opRevolve(context, id + "revolve", {
            "entities" : qSketchRegion(id + "silhouette"),
            "axis" : line(vector(0, 0, 0) * millimeter, vector(0, 0, 1)),
            "angleForward" : 360 * degree
        });
        opDeleteBodies(context, id + "deleteSilhouette", {
            "entities" : qCreatedBy(id + "silhouette", EntityType.BODY)
        });

        // D-flat: a prism from below the shaft tip ending flush on the nose
        // face, so the flat runs the full exposed length and stops there.
        // It must NOT overshoot - past z = 0 it would carve a notch into the
        // nose, which is a much larger radius than the shaft.
        if (hasShaft && def.shaftFlat > 0 * millimeter)
        {
            const ov = 1 * millimeter;
            const xF = rShaft - def.shaftFlat;
            const yF = rShaft + ov;
            var flatSk = newSketchOnPlane(context, id + "flatProfile", {
                "sketchPlane" : plane(
                    vector(0 * millimeter, 0 * millimeter, zTip - ov),
                    vector(0, 0, 1),
                    vector(1, 0, 0))
            });
            const box = [vector(xF, -yF), vector(rShaft + ov, -yF),
                         vector(rShaft + ov, yF), vector(xF, yF)];
            for (var e = 0; e < 4; e += 1)
            {
                skLineSegment(flatSk, "edge" ~ e, {
                    "start" : box[e],
                    "end"   : box[(e + 1) % 4]
                });
            }
            skSolve(flatSk);
            opExtrude(context, id + "flatCut", {
                "entities" : qSketchRegion(id + "flatProfile"),
                "direction" : vector(0, 0, 1),
                "endBound" : BoundingType.BLIND,
                "endDepth" : def.shaftLength + ov
            });
            opBoolean(context, id + "subtractFlat", {
                "tools" : qCreatedBy(id + "flatCut", EntityType.BODY),
                "targets" : qCreatedBy(id + "revolve", EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
            });
            opDeleteBodies(context, id + "deleteFlatSketch", {
                "entities" : qCreatedBy(id + "flatProfile", EntityType.BODY)
            });
        }
    });

// Blank shared by both gears: pie/annulus (or full disc/ring) extruded up
// from the Top plane, with a revolved bore when innerRadius > 0.
// g: outerRadius, innerRadius, height, arcAngle.
function buildBlank(context is Context, id is Id, g is map)
{
    const Ro = g.outerRadius;
    const Ri = g.innerRadius;
    if (Ri >= Ro)
        throw regenError("Inner radius must be smaller than the outer radius.");

    // 3-point arcs degenerate as start/end converge, so anything within
    // 0.01 deg of a full turn builds the closed-circle path instead.
    const isFull = g.arcAngle >= 360 * degree - 0.01 * degree;
    const half = g.arcAngle / 2;
    const ov = 1 * millimeter;

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

    // Retention hub (pinion): a boss around the bore on the z = height
    // face - after placement that is the MOTOR side (outer radius), so it
    // spaces the gear off the gearbox nose and extends the D-bore
    // engagement toward the motor bearing. It starts 1 mm inside the body
    // so the union has no coplanar seam.
    if (g.hubLength > 0 * millimeter)
    {
        var hubSk = newSketchOnPlane(context, id + "hubProfile", {
            "sketchPlane" : plane(
                vector(0 * millimeter, 0 * millimeter, g.height - ov),
                vector(0, 0, 1),
                vector(1, 0, 0))
        });
        skCircle(hubSk, "hubCircle", {
            "center" : vector(0, 0) * millimeter,
            "radius" : g.hubRadius
        });
        skSolve(hubSk);
        opExtrude(context, id + "hubExtrude", {
            "entities" : qSketchRegion(id + "hubProfile"),
            "direction" : vector(0, 0, 1),
            "endBound" : BoundingType.BLIND,
            "endDepth" : g.hubLength + ov
        });
        opBoolean(context, id + "attachHub", {
            "tools" : qUnion([
                qCreatedBy(id + "extrude", EntityType.BODY),
                qCreatedBy(id + "hubExtrude", EntityType.BODY)
            ]),
            "operationType" : BooleanOperationType.UNION
        });
        opDeleteBodies(context, id + "deleteHubSketch", {
            "entities" : qCreatedBy(id + "hubProfile", EntityType.BODY)
        });
    }

    // Inner bore, cut through body AND hub. Round: a revolved rectangle
    // (edge ON the axis is fine for opRevolve; the profile must not CROSS
    // it). With a D-flat: an extruded D-profile (major arc + chord), flat
    // facing +X.
    if (Ri > 0 * millimeter)
    {
        const zHi = g.height + g.hubLength + ov;
        if (g.boreFlat >= Ri)
            throw regenError("Bore flat depth must be smaller than the bore radius.");
        if (g.boreFlat > 0 * millimeter)
        {
            const xF = Ri - g.boreFlat;
            const y0 = sqrt(Ri * Ri - xF * xF);
            var dSk = newSketchOnPlane(context, id + "boreProfile", {
                "sketchPlane" : plane(
                    vector(0 * millimeter, 0 * millimeter, -ov),
                    vector(0, 0, 1),
                    vector(1, 0, 0))
            });
            skArc(dSk, "round", {
                "start" : vector(xF, y0),
                "mid"   : vector(-Ri, 0 * millimeter),
                "end"   : vector(xF, -y0)
            });
            skLineSegment(dSk, "flat", {
                "start" : vector(xF, -y0),
                "end"   : vector(xF, y0)
            });
            skSolve(dSk);
            opExtrude(context, id + "boreCut", {
                "entities" : qSketchRegion(id + "boreProfile"),
                "direction" : vector(0, 0, 1),
                "endBound" : BoundingType.BLIND,
                "endDepth" : g.height + g.hubLength + 2 * ov
            });
        }
        else
        {
            var boreSk = newSketch(context, id + "boreProfile", {
                "sketchPlane" : qCreatedBy(makeId("Front"), EntityType.FACE)
            });
            skLineSegment(boreSk, "axisEdge", {
                "start" : vector(0 * millimeter, -ov),
                "end"   : vector(0 * millimeter, zHi)
            });
            skLineSegment(boreSk, "top", {
                "start" : vector(0 * millimeter, zHi),
                "end"   : vector(Ri, zHi)
            });
            skLineSegment(boreSk, "wall", {
                "start" : vector(Ri, zHi),
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
        }
        opBoolean(context, id + "subtractBore", {
            "tools" : qCreatedBy(id + "boreCut", EntityType.BODY),
            "targets" : qUnion([
                qCreatedBy(id + "extrude", EntityType.BODY),
                qCreatedBy(id + "hubExtrude", EntityType.BODY),
                qCreatedBy(id + "attachHub", EntityType.BODY)
            ]),
            "operationType" : BooleanOperationType.SUBTRACTION
        });
        opDeleteBodies(context, id + "deleteBoreSketch", {
            "entities" : qCreatedBy(id + "boreProfile", EntityType.BODY)
        });
    }
}

// Rotation-pattern the base slot cutter and subtract the lot in one
// boolean. nSlots includes the base cutter.
function cutSlots(context is Context, id is Id, nSlots, pitchAngle)
{
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
        "targets" : qUnion([
            qCreatedBy(id + "extrude", EntityType.BODY),
            qCreatedBy(id + "hubExtrude", EntityType.BODY),
            qCreatedBy(id + "attachHub", EntityType.BODY)
        ]),
        "operationType" : BooleanOperationType.SUBTRACTION
    });
    opDeleteBodies(context, id + "deleteSlotSketch", {
        "entities" : qCreatedBy(id + "slotSk", EntityType.BODY)
    });
    opDeleteBodies(context, id + "deleteSketch", {
        "entities" : qCreatedBy(id + "profile", EntityType.BODY)
    });
}

// FACE-GEAR ring: rack-profile slots (straight flanks at the pressure
// angle, filleted roots) cut into the TOP face, swept RADIALLY with
// constant cross-section, one per pitch, joints mid-slot.
// g: outerRadius, innerRadius, height, arcAngle, teeth, pressureAngle.
function buildFaceRing(context is Context, id is Id, g is map)
{
    buildBlank(context, id, g);

    const Ro = g.outerRadius;
    const Ri = g.innerRadius;
    const isFull = g.arcAngle >= 360 * degree - 0.01 * degree;
    const half = g.arcAngle / 2;
    const ov = 1 * millimeter;

    const zFull = g.teeth * (360 * degree) / g.arcAngle;
    const rRef = (Ro + Ri) / 2;                 // tooth band middle
    const m = 2 * rRef / zFull;                 // derived module
    const tanA = tan(g.pressureAngle);

    // Rack tooth-space cross-section in the (tangential, z) plane:
    // pitch line z = height - m, root z = height - 2.25 m, half-width
    // pi m / 4 at pitch growing at tanA per mm of z.
    const yRoot = g.height - 2.25 * m;
    const yTop = g.height + ov;
    // + backlash/4: the ring's half of the play, split over its two flanks.
    const hwPitch = PI * m / 4 + g.backlash / 4;
    const hwRoot = hwPitch - 1.25 * m * tanA;
    const hwTop = hwPitch + (m + ov) * tanA;
    if (hwRoot <= 0 * millimeter)
        throw regenError("Pressure angle too steep - the rack slot closes before the root (limit ~32 deg).");
    if (yRoot <= 0.5 * millimeter)
        throw regenError("Height must exceed the tooth depth: 2.25 m = "
            ~ (floor(2.25 * m / millimeter * 100 + 0.5) / 100)
            ~ " mm plus 0.5 mm of web. Raise Height or the tooth count.");

    // Right side of the slot profile, root -> top, with a tangent-arc
    // root fillet (radius 0.38 m, ISO rack tip radius, clamped to the
    // root land). Left side is the mirror.
    const uDir = vector(-1, 0);                             // along the root land
    const vDir = vector(sin(g.pressureAngle), cos(g.pressureAngle)); // up the flank
    const corner = vector(hwRoot, yRoot);
    const phiC = acos(dot(uDir, vDir));
    var rho = 0.38 * m;
    var tOff = rho / tan(phiC / 2);
    if (tOff > 0.9 * hwRoot)
    {
        rho = rho * 0.9 * hwRoot / tOff;
        tOff = 0.9 * hwRoot;
    }
    var rightSide = [];
    if (rho > 0.02 * millimeter)
    {
        const Tc = corner + uDir * tOff;
        const Tf = corner + vDir * tOff;
        var bis = uDir + vDir;
        bis = bis / norm(bis);
        const Cc = corner + bis * (rho / sin(phiC / 2));
        const a0 = atan2(Tc[1] - Cc[1], Tc[0] - Cc[0]);
        const a1 = atan2(Tf[1] - Cc[1], Tf[0] - Cc[0]);
        var sweep = a1 - a0;
        if (sweep > 180 * degree)
            sweep = sweep - 360 * degree;
        if (sweep < -180 * degree)
            sweep = sweep + 360 * degree;
        const kf = 5;
        rightSide = append(rightSide, Tc);
        for (var i = 1; i < kf; i += 1)
        {
            const a = a0 + sweep * i / kf;
            rightSide = append(rightSide, Cc + vector(cos(a), sin(a)) * rho);
        }
        rightSide = append(rightSide, Tf);
    }
    else
    {
        rightSide = append(rightSide, corner);
    }
    rightSide = append(rightSide, vector(hwTop, yTop));

    // Closed profile: left side top -> root (mirror, reversed), then
    // right side root -> top; the top edge closes it.
    var profilePts = [];
    for (var i = size(rightSide) - 1; i >= 0; i -= 1)
        profilePts = append(profilePts, vector(-rightSide[i][0], rightSide[i][1]));
    for (var i = 0; i < size(rightSide); i += 1)
        profilePts = append(profilePts, rightSide[i]);

    // Base slot centered on the leading joint (phi0 = -arc/2): sketch on
    // a plane whose normal is the RADIAL direction there (sketch x =
    // tangential, sketch y = world z), then extrude radially across the
    // band with overshoot at both edges.
    const phi0 = -half;
    const radDir = vector(cos(phi0), sin(phi0), 0);
    var slotSk = newSketchOnPlane(context, id + "slotSk", {
        "sketchPlane" : plane(
            radDir * (Ri - ov),
            radDir,
            vector(-sin(phi0), cos(phi0), 0))
    });
    const nPts = size(profilePts);
    for (var e = 0; e < nPts; e += 1)
    {
        skLineSegment(slotSk, "edge" ~ e, {
            "start" : profilePts[e],
            "end"   : profilePts[(e + 1) % nPts]
        });
    }
    skSolve(slotSk);
    opExtrude(context, id + "slotCutter", {
        "entities" : qSketchRegion(id + "slotSk"),
        "direction" : radDir,
        "endBound" : BoundingType.BLIND,
        "endDepth" : (Ro - Ri) + 2 * ov
    });

    var nSlots = g.teeth + 1;
    if (isFull)
        nSlots = g.teeth;
    cutSlots(context, id, nSlots, g.arcAngle / g.teeth);
}

// SPUR gear (the pinion): transverse involute, exact. Same blank, slots
// are prisms along the axis.
// g: outerRadius, innerRadius, height, arcAngle, teeth, pressureAngle.
function buildGear(context is Context, id is Id, g is map)
{
    buildBlank(context, id, g);

    const Ro = g.outerRadius;
    const Ri = g.innerRadius;
    const isFull = g.arcAngle >= 360 * degree - 0.01 * degree;
    const half = g.arcAngle / 2;
    const ov = 1 * millimeter;

    const zFull = g.teeth * (360 * degree) / g.arcAngle;
    const m = 2 * Ro / (zFull + 2);             // derived module (tips at Ro)
    const rPitch = Ro - m;
    const rRoot = Ro - 2.25 * m;
    if (rRoot <= Ri && Ri > 0 * millimeter)
        throw regenError("Tooth slots cut through to the bore - shrink the bore or raise the tooth count.");

    // Slot half-angle at radius r: tau/4 - inv(alpha) + inv(alpha_r),
    // alpha_r = acos(rb / r), inv(x) = tan(x) - x. Below the base circle
    // the flank drops radially at the base-circle angle.
    const rb = rPitch * cos(g.pressureAngle);
    const tau = 2 * PI / zFull;
    const invAlpha = tan(g.pressureAngle) - g.pressureAngle / radian;
    // The pinion's half of the backlash: each flank rotates out by a
    // quarter of the total play, taken as an angle at the pitch radius.
    const blAng = g.backlash / 4 / rPitch;
    var slotHalfAngle = function(r)
    {
        var a = tau / 4 - invAlpha + blAng;
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

    // Canonical frame: slot centered on +X, root chord parallel to Y.
    const phi0 = -half;
    const K = 10;
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

    // Root fillet, 0.38 m, clamped to the root land.
    var plusPts = flankPts;
    const pf0 = flankPts[0];
    const uDir = vector(0, -1);
    var vDir = flankPts[1] - pf0;
    vDir = vDir / norm(vDir);
    const phiC = acos(dot(uDir, vDir));
    var rho = 0.38 * m;
    var tOff = rho / tan(phiC / 2);
    if (tOff > 0.9 * pf0[1])
    {
        rho = rho * 0.9 * pf0[1] / tOff;
        tOff = 0.9 * pf0[1];
    }
    if (rho > 0.02 * millimeter)
    {
        const Tc = pf0 + uDir * tOff;
        const Tf = pf0 + vDir * tOff;
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
        const rJoin = norm(Tf);
        for (var i = 0; i < size(flankPts); i += 1)
        {
            if (norm(flankPts[i]) > rJoin + 0.01 * millimeter)
                pts = append(pts, flankPts[i]);
        }
        plusPts = pts;
    }

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

    var nSlots = g.teeth + 1;
    if (isFull)
        nSlots = g.teeth;
    cutSlots(context, id, nSlots, g.arcAngle / g.teeth);
}
