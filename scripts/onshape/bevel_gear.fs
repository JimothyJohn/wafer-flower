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
    corners, mapped with the profile.

    Step 6 (Nick's pair-architecture pick: ISO intersecting-axes bevel):
    Tredgold geometry. For coned gears the profile is drawn on the
    developed BACK CONE (virtual spur: Zv = zFull / cos(delta) teeth at
    slant Rv = rPitch / cos(delta)), addendum m / dedendum 1.25 m measured
    ALONG the back cone, then wrapped (development angle compresses by
    cos(delta)) and projected through the PITCH apex onto the loft planes.
    The visible wall is the TIP cone: pitch angle + theta_a where
    tan(theta_a) = 2 sin(delta) / zFull (ISO 23509 standard taper), so the
    wall reads slightly steeper than the input cone angle. Pitch radius
    from the wall anchor: rP = Ro / kBlank, module m = 2 rP / zFull.
    Cone angle 0 keeps the exact transverse spur construction with
    m = 2 Ro / (zFull + 2). Not modeled yet vs Gear Lab: tip chamfer,
    undercut relief for low-tooth-count pinions.

    Step 7: pair mode ("Mating pinion"). Both cone angles derive from the
    tooth counts and shaft angle S (tan(delta_ring) = sin(S)/(Zp/Zr +
    cos(S)), delta_pinion = S - delta_ring; the Cone angle input is
    ignored). The single-gear pipeline moved into buildGear(); the pinion
    is built as a full 360 gear sized off the shared module (rPp = m Zp/2,
    blank anchor via blankK) and parked apex-to-apex: pre-rotate half a
    pitch when the ring count is even (contact meridian must pair a tooth
    with a slot), tilt -S about Y, translate the apex onto the ring's.
    Ratio = ring full-circle count / pinion teeth.

    Onshape paste rules learned the hard way (do not regress):
    - annotation strings must be printable ASCII (no em-dashes, no unicode minus)
    - reportFeatureInfo, not reportInfo (and no popup at all - Nick's call)
    - opSphere, not fSphere
    - a parameter group ("Group Name"/"Driving Parameter") must IMMEDIATELY
      follow its driving parameter's declaration - nothing in between, or
      precondition analysis fails on the whole feature
*/

// Maps the wall anchor Ro (tip radius at z = 0) to the big-end pitch
// radius: rPitch = Ro / blankK(delta, zFull). See the step 6 notes.
function blankK(delta, zF)
{
    const thetaA = atan(2 * sin(delta) / zF);
    return 1 + (2 / zF) * (cos(delta) + sin(delta) * tan(delta + thetaA));
}

annotation {
    "Feature Type Name" : "Arc Segment",
    "Feature Type Description" : "ISO straight bevel gear / arc rack segment (Tredgold profiles, root fillets, ISO taper). Inner radius 0 fills it solid; arc angle 360 makes the full gear. Teeth counts the teeth on this arc. Tick Mating pinion to also generate the meshing pinion in place - cone angles derive from the tooth counts and shaft angle."
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

        annotation { "Name" : "Teeth", "Description" : "Number of teeth ON THIS ARC (joint faces land mid-slot). Full-circle equivalent = teeth * 360 / arc angle - match the pinion to that for the ratio." }
        isInteger(def.teeth, { (unitless) : [1, 32, 1000] } as IntegerBoundSpec);

        annotation { "Name" : "Pressure angle", "Description" : "ISO standard is 20 deg. Use 25 deg on BOTH gears when the pinion has under ~14 teeth - it avoids undercut without profile shift." }
        isAngle(def.pressureAngle, { (degree) : [5, 20, 45] } as AngleBoundSpec);

        annotation { "Name" : "Mating pinion", "Description" : "Also generate the meshing pinion. ISO pair: BOTH cone angles are then derived from the tooth counts and shaft angle, and the Cone angle input is ignored." }
        def.mate is boolean;
        if (def.mate)
        {
            annotation { "Group Name" : "Mating Pinion", "Driving Parameter" : "mate", "Collapsed By Default" : false }
            {
                annotation { "Name" : "Shaft angle", "Description" : "Angle between the two gear axes. 90 deg puts the motor along the wall." }
                isAngle(def.shaftAngle, { (degree) : [10, 90, 170] } as AngleBoundSpec);

                annotation { "Name" : "Pinion teeth", "Description" : "Ratio = ring full-circle count / pinion teeth. Coprime counts wear best (hunting tooth)." }
                isInteger(def.pinionTeeth, { (unitless) : [4, 13, 200] } as IntegerBoundSpec);

                annotation { "Name" : "Pinion height", "Description" : "Axial face width of the pinion. It meshes over this depth from the big end inward." }
                isLength(def.pinionHeight, { (millimeter) : [0.1, 10, 1000] } as LengthBoundSpec);

                annotation { "Name" : "Pinion bore radius", "Description" : "0 = solid. 1.5 mm suits a 3 mm motor shaft." }
                isLength(def.pinionBore, { (millimeter) : [0, 1.5, 100] } as LengthBoundSpec);
            }
        }
        else
        {
            annotation { "Name" : "Cone angle", "Description" : "Angle of the outer wall from vertical. 0 = straight (cylindrical) wall. Big end is at the bottom face." }
            isAngle(def.coneAngle, { (degree) : [0, 45, 80] } as AngleBoundSpec);
        }
    }
    {
        // Step 7 pair mode: cone angles are DERIVED from the tooth counts
        // and shaft angle (ISO: tan(delta_ring) = sin(S)/(Zp/Zr + cos(S)),
        // delta_pinion = S - delta_ring); the Cone angle input drives
        // standalone gears only.
        var ringCone = def.coneAngle;
        var deltaP = 0 * degree;
        if (def.mate)
        {
            const zr = def.teeth * (360 * degree) / def.arcAngle;
            ringCone = atan2(sin(def.shaftAngle),
                def.pinionTeeth / zr + cos(def.shaftAngle));
            deltaP = def.shaftAngle - ringCone;
            if (ringCone <= 0 * degree || deltaP <= 0 * degree)
                throw regenError("Shaft angle and tooth counts give no valid cone pair.");
        }

        buildGear(context, id + "ring", {
            "outerRadius" : def.outerRadius,
            "innerRadius" : def.innerRadius,
            "height" : def.height,
            "arcAngle" : def.arcAngle,
            "coneAngle" : ringCone,
            "teeth" : def.teeth,
            "pressureAngle" : def.pressureAngle
        });

        if (def.mate)
        {
            // Shared module sizes the pinion blank; the pair shares its
            // pitch apex, so the pinion is parked apex-to-apex, tilted by
            // the shaft angle about Y, contacting at the ring's +X meridian.
            const zr = def.teeth * (360 * degree) / def.arcAngle;
            const zp = def.pinionTeeth;
            const rPr = def.outerRadius / blankK(ringCone, zr);
            const mMod = 2 * rPr / zr;
            const rPp = mMod * zp / 2;
            const zAr = rPr / tan(ringCone);
            const zAp = rPp / tan(deltaP);

            buildGear(context, id + "pinion", {
                "outerRadius" : rPp * blankK(deltaP, zp),
                "innerRadius" : def.pinionBore,
                "height" : def.pinionHeight,
                "arcAngle" : 360 * degree,
                "coneAngle" : deltaP,
                "teeth" : zp,
                "pressureAngle" : def.pressureAngle
            });

            // Clocking: after the tilt the pinion presents its own -X
            // meridian, which always carries a slot center. An even ring
            // count also puts a ring SLOT at the contact meridian, so the
            // pinion pre-rotates half a pitch to face it with a tooth; an
            // odd ring count already presents a ring tooth there.
            var preRot = 0 * degree;
            if (def.teeth % 2 == 0)
                preRot = 180 * degree / zp;
            const zAxis = line(vector(0, 0, 0) * millimeter, vector(0, 0, 1));
            const yAxis = line(vector(0, 0, 0) * millimeter, vector(0, 1, 0));
            const place = transform(vector(
                    zAp * sin(def.shaftAngle),
                    0 * millimeter,
                    zAr - zAp * cos(def.shaftAngle)))
                * rotationAround(yAxis, -def.shaftAngle)
                * rotationAround(zAxis, preRot);
            opTransform(context, id + "placePinion", {
                "bodies" : qCreatedBy(id + "pinion", EntityType.BODY),
                "transform" : place
            });
        }
    });

// The whole single-gear pipeline (blank, wall cone, bore, tooth slots).
// g: outerRadius, innerRadius, height, arcAngle, coneAngle, teeth,
// pressureAngle. Bodies are created under the passed id.
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

    // Tooth-count geometry needed by both the wall cut and the teeth.
    const zFull = g.teeth * (360 * degree) / g.arcAngle;    // full-circle equivalent count
    // Step 6 (ISO taper): the visible wall is the TIP cone, steeper than
    // the pitch cone by the addendum angle theta_a = atan(2 sin(d)/zFull)
    // (addendum over the outer cone distance, ISO 23509 standard taper).
    // kBlank maps the wall anchor Ro (tip radius at z = 0) back to the
    // big-end pitch radius.
    var wallTan = tan(g.coneAngle);
    var kBlank = 1;
    if (g.coneAngle > 0 * degree)
    {
        kBlank = blankK(g.coneAngle, zFull);
        wallTan = tan(g.coneAngle + atan(2 * sin(g.coneAngle) / zFull));
    }

    // Top-face outer radius after the wall cut; the wall must not eat
    // through to the bore (or past the center when solid).
    const RoTop = Ro - g.height * wallTan;
    if (RoTop <= Ri)
    {
        var msg = "Wall cone ("
            ~ (floor(atan(wallTan) / degree * 10 + 0.5) / 10)
            ~ " deg) crosses the bore before the top face";
        if (wallTan > 0)
            msg = msg ~ " - the tallest blank this geometry allows is "
                ~ (floor((Ro - Ri) / wallTan / millimeter * 100) / 100) ~ " mm";
        msg = msg ~ ". Reduce Height, widen the wall (outer minus inner radius), or flatten the cone (standalone: Cone angle; pair mode: the derived angle falls with a smaller ratio or a smaller shaft angle).";
        throw regenError(msg);
    }

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

    // Cutters overshoot both end faces by 1 mm (coplanar-cap sliver trap).
    const ov = 1 * millimeter;

    // Step 2: cone the outer wall. Cut with a revolved wedge - everything
    // outside the wall line r(z) = Ro - z * wallTan (the ISO tip cone).
    if (g.coneAngle > 0 * degree)
    {
        const rBot = Ro + ov * wallTan;                    // wall line at z = -ov
        const rTop = Ro - (g.height + ov) * wallTan;     // wall line at z = height + ov
        const rMax = rBot + 5 * millimeter;

        // Front plane is world XZ: sketch x = radius, sketch y = world z.
        var cutSk = newSketch(context, id + "coneProfile", {
            "sketchPlane" : qCreatedBy(makeId("Front"), EntityType.FACE)
        });
        skLineSegment(cutSk, "cone", {
            "start" : vector(rBot, -ov),
            "end"   : vector(rTop, g.height + ov)
        });
        skLineSegment(cutSk, "top", {
            "start" : vector(rTop, g.height + ov),
            "end"   : vector(rMax, g.height + ov)
        });
        skLineSegment(cutSk, "outer", {
            "start" : vector(rMax, g.height + ov),
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

    // Steps 3-6: tooth slots. The profile is drawn as an EQUIVALENT SPUR
    // in a flat "drawing plane", then mapped into place:
    // - coneAngle 0: the drawing plane IS the transverse plane; pure
    //   rotation to phi0 (exact spur involute).
    // - coneAngle > 0 (step 6, ISO/Tredgold): the drawing plane is the
    //   developed BACK CONE - a virtual spur with zFull / cos(delta)
    //   teeth at slant radius rPitch / cos(delta), addendum m and
    //   dedendum 1.25 m measured ALONG the back cone. Each point wraps
    //   onto the back cone (development angle compresses by cos(delta))
    //   and projects through the PITCH APEX onto the two loft planes,
    //   so flank rulings pass through the apex and the whole tooth
    //   vanishes there - a true straight bevel per Tredgold.
    const pitchAngle = g.arcAngle / g.teeth;
    const invAlpha = tan(g.pressureAngle) - g.pressureAngle / radian;
    const phi0 = -half;                         // slot centered on the leading joint
    const K = 10;                               // involute facets per flank
    const zs = [-ov, g.height + ov];

    // Equivalent-spur parameters (radii in the drawing plane).
    var mMod;                                   // derived module
    var eqPitch;
    var eqRoot;
    var eqTipOv;
    var eqTeeth;                                // fractional is fine
    var zApex = 0 * millimeter;                 // pitch apex (coned only)
    var zBack = 0 * millimeter;                 // back-cone apex (coned only)
    if (g.coneAngle > 0 * degree)
    {
        const rP = Ro / kBlank;
        mMod = 2 * rP / zFull;
        zApex = rP / tan(g.coneAngle);
        if (zApex <= g.height + ov)
            throw regenError("Pitch apex lies inside the blank - reduce cone angle or height, or raise the tooth count.");
        zBack = -rP * tan(g.coneAngle);
        eqPitch = rP / cos(g.coneAngle);
        eqTeeth = zFull / cos(g.coneAngle);
        eqRoot = eqPitch - 1.25 * mMod;
        eqTipOv = eqPitch + mMod + ov;
    }
    else
    {
        mMod = 2 * Ro / (zFull + 2);
        eqPitch = Ro - mMod;
        eqTeeth = zFull;
        eqRoot = Ro - 2.25 * mMod;
        eqTipOv = Ro + ov;
    }
    const eqBase = eqPitch * cos(g.pressureAngle);
    const tauEq = 2 * PI / eqTeeth;
    var slotHalfAngle = function(r)             // drawing-plane slot half-angle, radians
    {
        var g = tauEq / 4 - invAlpha;
        if (r > eqBase)
        {
            const ar = acos(eqBase / r);
            g = g + tan(ar) - ar / radian;
        }
        return g;
    };
    const eqStart = max(eqRoot, eqBase);
    if (slotHalfAngle(eqStart) <= 0)
        throw regenError("No slot width left at the root - lower the pressure angle or the tooth count.");

    // World root radius at the TOP face, for the bore guard.
    var rRootTop;
    if (g.coneAngle > 0 * degree)
    {
        const z3r = zBack + eqRoot * sin(g.coneAngle);
        rRootTop = eqRoot * cos(g.coneAngle) * (zApex - g.height) / (zApex - z3r);
    }
    else
    {
        rRootTop = eqRoot;
    }
    if (rRootTop <= Ri && Ri > 0 * millimeter)
    {
        var msg = "Tooth slots cut through to the bore: " ~ g.teeth
            ~ " teeth on this arc give module "
            ~ (floor(mMod / millimeter * 100 + 0.5) / 100) ~ " mm. ";
        // Scan upward for the smallest count whose root clears the bore.
        var fits = -1;
        for (var n = g.teeth + 1; n <= 1000; n += 1)
        {
            const zF2 = n * (360 * degree) / g.arcAngle;
            var rrt;
            if (g.coneAngle > 0 * degree)
            {
                const k2 = blankK(g.coneAngle, zF2);
                const rP2 = Ro / k2;
                const m2 = 2 * rP2 / zF2;
                const zA2 = rP2 / tan(g.coneAngle);
                const rt2 = rP2 / cos(g.coneAngle) - 1.25 * m2;
                const z32 = -rP2 * tan(g.coneAngle) + rt2 * sin(g.coneAngle);
                rrt = rt2 * cos(g.coneAngle) * (zA2 - g.height) / (zA2 - z32);
            }
            else
            {
                rrt = Ro - 2.25 * (2 * Ro / (zF2 + 2));
            }
            if (rrt > Ri)
            {
                fits = n;
                break;
            }
        }
        if (fits > 0)
            msg = msg ~ "This blank needs at least " ~ fits
                ~ " teeth on this arc, or a smaller inner radius.";
        else
            msg = msg ~ "No tooth count fits this wall - thicken it or reduce the cone angle or height.";
        throw regenError(msg);
    }

    // Canonical drawing frame: slot centered on the +X axis (mapped out
    // to phi0 at the end, mirrored for the -side). In this frame the
    // root chord is parallel to the Y axis. +side flank, root -> tip.
    var flankPts = [];
    if (eqRoot < eqBase)
        flankPts = append(flankPts, vector(
            eqRoot * cos(slotHalfAngle(eqBase) * radian),
            eqRoot * sin(slotHalfAngle(eqBase) * radian)));
    for (var i = 0; i <= K; i += 1)
    {
        const r = eqStart + (eqTipOv - eqStart) * i / K;
        const g = slotHalfAngle(r);
        flankPts = append(flankPts, vector(r * cos(g * radian), r * sin(g * radian)));
    }

    // Step 5: root fillet, radius 0.38 m (ISO rack tip radius),
    // clamped so the two corner arcs never overlap on the root land.
    // The sharp corner between the root chord and the near-straight
    // flank start becomes a 5-facet tangent arc; the CUTTER loses
    // area at the corner, so the TOOTH root gains the fillet. It is
    // drawn in the equivalent-spur plane, so it maps with the rest.
    var plusPts = flankPts;
    const pf0 = flankPts[0];
    const uDir = vector(0, -1);                 // along the root chord, away from the corner
    var vDir = flankPts[1] - pf0;
    vDir = vDir / norm(vDir);                   // along the flank, away from the corner
    const phiC = acos(dot(uDir, vDir));
    var rho = 0.38 * mMod;
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

    // Closed canonical outline: +side root -> tip, tip chord, mirrored
    // -side tip -> root, root chord closes it.
    var canon = [];
    for (var i = 0; i < size(plusPts); i += 1)
        canon = append(canon, plusPts[i]);
    for (var i = size(plusPts) - 1; i >= 0; i -= 1)
        canon = append(canon, vector(plusPts[i][0], -plusPts[i][1]));

    // Map the canonical profile onto each loft plane.
    var outlines = [[], []];
    for (var j = 0; j < 2; j += 1)
    {
        for (var i = 0; i < size(canon); i += 1)
        {
            const p = canon[i];
            if (g.coneAngle > 0 * degree)
            {
                const rhoP = norm(p);                       // back-cone slant radius
                const thv = atan2(p[1], p[0]);              // development angle
                const phiW = phi0 + thv / cos(g.coneAngle);
                const r3 = rhoP * cos(g.coneAngle);
                const z3 = zBack + rhoP * sin(g.coneAngle);
                const tsc = (zApex - zs[j]) / (zApex - z3); // central projection
                outlines[j] = append(outlines[j],
                    vector(r3 * tsc * cos(phiW), r3 * tsc * sin(phiW)));
            }
            else
            {
                outlines[j] = append(outlines[j], vector(
                    p[0] * cos(phi0) - p[1] * sin(phi0),
                    p[0] * sin(phi0) + p[1] * cos(phi0)));
            }
        }
    }

    const nPts = size(canon);
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
                "start" : outlines[j][e],
                "end"   : outlines[j][(e + 1) % nPts]
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

    // Leave only the solid behind.
    opDeleteBodies(context, id + "deleteSketch", {
        "entities" : qCreatedBy(id + "profile", EntityType.BODY)
    });
}
