FeatureScript 1803;
import(path : "onshape/std/geometry.fs", version : "1803.0");

/*
    Bevel gear generator - built incrementally, one verified piece at a time.

    Step 1: "Arc Segment" - a plain arc blank. Inputs: outer radius, inner
    radius (0 = solid, for the pinion blank), height, and arc ANGLE in
    degrees (360 / wafer count; 360 = full gear, for the pinion). Centered
    on the +X axis, flat on the Top plane, extruded +Z by the height.

    Step 2: cone angle - the outer wall is cut to a cone, BIG END AT THE
    BOTTOM (z = 0): Ro at z = 0 shrinking to Ro - height * tan(coneAngle)
    at the top. 0 deg = straight wall. The inner wall stays cylindrical.

    Step 3: tooth slots. Teeth counts the teeth ON THIS ARC (Nick's call -
    the whole model's teeth, not a per-circle abstraction); the full-circle
    equivalent zFull = teeth * 360 / arc drives the module, which is
    DERIVED, not input: m = 2 * Ro / (zFull + 2) (pitch radius Ro - m at
    the big end, addendum m, dedendum 1.25 m, slot depth 2.25 m).
    Each slot is defined in the big-end plane (z = 0) and lofted between
    two horizontal sections SCALED ABOUT THE CONE APEX (axis point
    z = Ro / tan(coneAngle)), so flank rulings pass through the apex and
    tooth width AND depth shrink toward the small end - straight bevel
    behavior. Cone angle 0 degenerates to equal sections (spur slots).
    Slots are phased so the sector's joint faces land mid-slot (halo rule:
    joints mid-space; keep teeth divisible by segment count).

    Step 4: involute flanks (10-facet polyline per side) replace the
    straight trapezoid sides - transverse involute at the big end, apex-
    scaled along the face (the Tredgold-style approximation; Gear Lab's
    spherical involute differs by hundredths of a mm at the face ends).
    Step 5: root fillet, radius 0.38 m (ISO rack tip radius), clamped to
    the root land - a 5-facet tangent arc rounding the slot cutter's root
    corners, apex-scaled with the profile. Not modeled yet vs Gear Lab:
    tip chamfer, undercut relief for low-tooth-count pinions.

    Onshape paste rules learned the hard way (do not regress):
    - annotation strings must be printable ASCII (no em-dashes, no unicode minus)
    - reportFeatureInfo, not reportInfo (and no popup at all - Nick's call)
    - opSphere, not fSphere
*/

annotation {
    "Feature Type Name" : "Arc Segment",
    "Feature Type Description" : "Bevel gear / arc rack segment: coned blank (big end at bottom) with straight bevel tooth slots converging on the cone apex. Inner radius 0 fills it solid; arc angle 360 makes the full gear. Teeth counts the teeth on this arc; module is derived: m = 2 * Ro / (teeth * 360 / arc + 2)."
}
export const arcSegment = defineFeature(function(context is Context, id is Id, def is map)
    precondition
    {
        annotation { "Name" : "Outer radius", "Description" : "Outer (tooth tip) radius at the bottom face - the cone's big end." }
        isLength(def.outerRadius, { (millimeter) : [1, 300, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Inner radius", "Description" : "Bore radius. 0 fills the segment solid (pinion blank)." }
        isLength(def.innerRadius, { (millimeter) : [0, 270, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Height" }
        isLength(def.height, { (millimeter) : [0.1, 15, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Arc angle", "Description" : "360 divided by the number of segments in the full ring (9 wafers -> 40 deg). 360 makes the full gear." }
        isAngle(def.arcAngle, { (degree) : [0.1, 40, 360] } as AngleBoundSpec);

        annotation { "Name" : "Cone angle", "Description" : "Angle of the outer wall from vertical. 0 = straight (cylindrical) wall. Big end is at the bottom face." }
        isAngle(def.coneAngle, { (degree) : [0, 45, 80] } as AngleBoundSpec);

        annotation { "Name" : "Cut teeth", "Default" : true }
        def.cutTeeth is boolean;

        if (def.cutTeeth)
        {
            annotation { "Name" : "Teeth", "Description" : "Number of teeth ON THIS ARC (joint faces land mid-slot). Full-circle equivalent = teeth * 360 / arc angle - match the pinion to that for the ratio." }
            isInteger(def.teeth, { (unitless) : [1, 12, 1000] } as IntegerBoundSpec);

            annotation { "Name" : "Pressure angle" }
            isAngle(def.pressureAngle, { (degree) : [5, 20, 45] } as AngleBoundSpec);
        }
    }
    {
        const Ro = def.outerRadius;
        const Ri = def.innerRadius;
        if (Ri >= Ro)
            throw regenError("Inner radius must be smaller than the outer radius.");

        // 3-point arcs degenerate as start/end converge, so anything within
        // 0.01 deg of a full turn builds the closed-circle path instead.
        const isFull = def.arcAngle >= 360 * degree - 0.01 * degree;
        const half = def.arcAngle / 2;

        // Top-face outer radius after the cone cut; the cone must not eat
        // through to the bore (or past the center when solid).
        const RoTop = Ro - def.height * tan(def.coneAngle);
        if (RoTop <= Ri)
            throw regenError("Cone angle consumes the full wall at the top. Reduce cone angle or height, or shrink the inner radius.");

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
            "endDepth" : def.height
        });

        // Cutters overshoot both end faces by 1 mm (coplanar-cap sliver trap).
        const ov = 1 * millimeter;

        // Step 2: cone the outer wall. Cut with a revolved wedge - everything
        // outside the cone line r(z) = Ro - z * tan(coneAngle).
        if (def.coneAngle > 0 * degree)
        {
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

        // Inner bore: a revolved rectangle (edge on the axis is fine for
        // opRevolve; the profile must not CROSS the axis).
        if (Ri > 0 * millimeter)
        {
            var boreSk = newSketch(context, id + "boreProfile", {
                "sketchPlane" : qCreatedBy(makeId("Front"), EntityType.FACE)
            });
            skLineSegment(boreSk, "axisEdge", {
                "start" : vector(0 * millimeter, -ov),
                "end"   : vector(0 * millimeter, def.height + ov)
            });
            skLineSegment(boreSk, "top", {
                "start" : vector(0 * millimeter, def.height + ov),
                "end"   : vector(Ri, def.height + ov)
            });
            skLineSegment(boreSk, "wall", {
                "start" : vector(Ri, def.height + ov),
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

        // Step 3: tooth slots.
        if (def.cutTeeth)
        {
            const pitchAngle = def.arcAngle / def.teeth;
            const zFull = (360 * degree) / pitchAngle;  // full-circle tooth count (fractional is allowed)
            const m = 2 * Ro / (zFull + 2);             // derived module (tips at Ro)
            const rPitch = Ro - m;
            const rRoot = Ro - 2.25 * m;
            const rTipOv = Ro + ov;                     // overshoot beyond the cone face

            // Step 4: involute flanks (the "roundness" Gear Lab has). In the
            // big-end transverse plane the slot HALF-ANGLE at radius r is
            //   tau/4 - inv(alpha) + inv(alpha_r),  alpha_r = acos(rb / r)
            // (inv(x) = tan(x) - x). It grows with r: slots widen outward,
            // teeth thin toward the tip. Below the base circle the involute
            // does not exist; the flank drops radially at the base-circle
            // angle (standard approximation, relevant only at low counts).
            const rb = rPitch * cos(def.pressureAngle); // base circle
            const tau = 2 * PI / zFull;                 // angular pitch, radians
            const invAlpha = tan(def.pressureAngle) - def.pressureAngle / radian;
            var slotHalfAngle = function(r)             // returns radians as a number
            {
                var g = tau / 4 - invAlpha;
                if (r > rb)
                {
                    const ar = acos(rb / r);
                    g = g + tan(ar) - ar / radian;
                }
                return g;
            };
            const rStart = max(rRoot, rb);
            if (slotHalfAngle(rStart) <= 0)
                throw regenError("No slot width left at the root - lower the pressure angle or the tooth count.");

            // Section scale factors about the cone apex (z = Ro / tan(cone)).
            var s0 = 1;                                  // at z = -ov
            var s1 = 1;                                  // at z = height + ov
            if (def.coneAngle > 0 * degree)
            {
                const zApex = Ro / tan(def.coneAngle);
                if (zApex <= def.height + ov)
                    throw regenError("Cone apex lies inside the blank - teeth cannot be built. Reduce cone angle or height.");
                s0 = (zApex + ov) / zApex;
                s1 = (zApex - def.height - ov) / zApex;
            }
            if (rRoot * s1 <= Ri && Ri > 0 * millimeter)
            {
                // Largest module whose slot root still clears the bore at the
                // top face, and the tooth count that produces it.
                const mMax = (Ro - Ri / s1) / 2.25;
                var msg = "Tooth slots cut through to the bore: " ~ def.teeth
                    ~ " teeth on this arc give module "
                    ~ (floor(m / millimeter * 100 + 0.5) / 100) ~ " mm, slot depth "
                    ~ (floor(2.25 * m / millimeter * 100 + 0.5) / 100) ~ " mm. ";
                if (mMax > 0 * millimeter)
                    msg = msg ~ "This blank needs at least "
                        ~ ceil((2 * Ro / mMax - 2) * def.arcAngle / (360 * degree))
                        ~ " teeth on this arc, or a smaller inner radius.";
                else
                    msg = msg ~ "No tooth count fits this wall - thicken it or reduce the cone angle or height.";
                throw regenError(msg);
            }

            // Base slot centered on the leading joint face (phi = -arc/2) so
            // sector joints land mid-slot; slots then march by one pitch.
            const phi0 = -half;
            const K = 10;                               // involute facets per flank

            // Canonical frame: slot centered on the +X axis (rotated out to
            // phi0 at the end, mirrored for the -side). In this frame the
            // root chord is parallel to the Y axis. +side flank, root -> tip.
            var flankPts = [];
            if (rRoot < rb)
                flankPts = append(flankPts, vector(
                    rRoot * cos(slotHalfAngle(rb) * radian),
                    rRoot * sin(slotHalfAngle(rb) * radian)));
            for (var i = 0; i <= K; i += 1)
            {
                const r = rStart + (rTipOv - rStart) * i / K;
                const g = slotHalfAngle(r);
                flankPts = append(flankPts, vector(r * cos(g * radian), r * sin(g * radian)));
            }

            // Step 5: root fillet, radius 0.38 m (ISO rack tip radius),
            // clamped so the two corner arcs never overlap on the root land.
            // The sharp corner between the root chord and the near-straight
            // flank start becomes a 5-facet tangent arc; the CUTTER loses
            // area at the corner, so the TOOTH root gains the fillet. It
            // lives in the big-end profile, so it apex-scales with the rest.
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
                // Rejoin the involute above the arc (tiny kink, sub-print-scale).
                const rJoin = norm(Tf);
                for (var i = 0; i < size(flankPts); i += 1)
                {
                    if (norm(flankPts[i]) > rJoin + 0.01 * millimeter)
                        pts = append(pts, flankPts[i]);
                }
                plusPts = pts;
            }

            // Closed outline in world orientation: +side root -> tip, tip
            // chord, mirrored -side tip -> root, root chord closes it.
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

            const scales = [s0, s1];
            const zs = [-ov, def.height + ov];
            const nPts = size(outline);
            for (var j = 0; j < 2; j += 1)
            {
                var slotSk = newSketchOnPlane(context, id + ("slotSk" ~ j), {
                    "sketchPlane" : plane(
                        vector(0 * millimeter, 0 * millimeter, zs[j]),
                        vector(0, 0, 1),
                        vector(1, 0, 0))
                });
                for (var e = 0; e < nPts; e += 1)
                {
                    skLineSegment(slotSk, "edge" ~ e, {
                        "start" : outline[e] * scales[j],
                        "end"   : outline[(e + 1) % nPts] * scales[j]
                    });
                }
                skSolve(slotSk);
            }

            opLoft(context, id + "slotLoft", {
                "profileSubqueries" : [
                    qSketchRegion(id + "slotSk0", true),
                    qSketchRegion(id + "slotSk1", true)
                ],
                "bodyType" : BodyType.SOLID
            });

            // A slot at each joint face plus one per tooth between them; on a
            // full circle the last slot would duplicate the first.
            var nSlots = def.teeth + 1;
            if (isFull)
                nSlots = def.teeth;

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
                    "entities" : qCreatedBy(id + "slotLoft", EntityType.BODY),
                    "transforms" : transforms,
                    "instanceNames" : names
                });
            }

            opBoolean(context, id + "subtractSlots", {
                "tools" : qUnion([
                    qCreatedBy(id + "slotLoft", EntityType.BODY),
                    qCreatedBy(id + "slotPattern", EntityType.BODY)
                ]),
                "targets" : qCreatedBy(id + "extrude", EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
            });
            opDeleteBodies(context, id + "deleteSlotSketches", {
                "entities" : qUnion([
                    qCreatedBy(id + "slotSk0", EntityType.BODY),
                    qCreatedBy(id + "slotSk1", EntityType.BODY)
                ])
            });
        }

        // Leave only the solid behind.
        opDeleteBodies(context, id + "deleteSketch", {
            "entities" : qCreatedBy(id + "profile", EntityType.BODY)
        });
    });
