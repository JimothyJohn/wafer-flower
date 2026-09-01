FeatureScript 1803;
import(path : "onshape/std/geometry.fs", version : "1803.0");

/*
    Friction Shoe (2026-08-31, Nick: replicate the good bottom-bracket
    friction bearing and make it reusable): an arc-shaped plain-bearing
    pad for a ring riding on a fixed shoe - here the segment's inner
    rail (rev C: running face at r = Ri - rail_w = 316) resting on the
    bottom bracket's rounded edge.

    THE TRICK, made structural: the whole shoe is a surface of
    revolution about the ring axis, so the working surface is conformal
    to the rail arc BY CONSTRUCTION - "a shallow angle identical to the
    inner radius" is guaranteed at any seat angle, not tuned by hand,
    and circumferential sliding never crosses an edge. The working
    surface is a shallow cone (Seat angle, from the ring axis
    direction; 0 = a plain cylindrical running band) blended into the
    plate faces by EXACT tangent fillets (true sketch arcs, not
    chords) - the fillet is the anti-carve edge treatment. A seat
    angle > 0 makes the seat a shallow wedge that self-locates the
    ring axially as it settles; the cone crosses (Seat radius -
    clearance) at the plate mid-plane, which is the mating datum.
    Fillet = thickness/2 degenerates cleanly into a full bullnose at
    ANY seat angle (the tangent takeups sum to exactly the face length
    - verified closed-form: tan(45+a/2) + tan(45-a/2) = 2/cos(a)); the
    two blends merge into one nose, the seat angle stops mattering,
    and the crest sits ~0.2 inside the seat radius. That bullnose IS
    the measured 6.0 round on the 12 plate; the default fillet of 5
    keeps a 2 mm true cone face so the mid-plane datum stays exact.

    DEFAULTS MEASURED off Nick's good part (stl/mine "BottomStaticBracket
    - staticBracket.stl", 2026-08-13 export, 1474 tris): plate 12 thick,
    arc 6 deg (+-3), working-edge round 6.0 (quarter-round, fits the
    vertex cloud to +-0.005), two countersunk holes dia 5.0 with an
    8.5 rim at exactly 45 deg (flat-head M5), 25 mm apart (the grid).
    Seat radius default 316 = the rev C rail_ri. Seat angle 10 is
    ASSUMED (Nick said "shallow"; the mesh predates the rail and does
    not pin it) - set it to what the bench likes.

    RUNNING-SURFACE TREATMENT (asked for; the feature cannot model it,
    the header can): loads here are ~1 N-scale so PV is trivial and
    wear is pure abrasion control - smooth conformal surface, no edges,
    which is what this geometry encodes. Beyond geometry:
    - dissimilar polymers rub better: PETG shoe on PLA rail (or the
      reverse) beats like-on-like;
    - print the shoe FLAT (plate faces on the bed) so extrusion lines
      run circumferentially, i.e. along the sliding direction;
    - 100% infill or >= 4 perimeters at the nose so the crest is solid;
    - dry-film PTFE spray, or a rub of paraffin/candle wax, on the
      working face - dry film over grease on wall art (grease holds
      dust); silicone or PTFE greases are safe on PLA/PETG if used;
    - let it burnish in: the first hours polish the crest; do not chase
      the initial squeak with a redesign.

    Onshape paste rules learned the hard way (do not regress; ledger
    carried from face_gear.fs):
    - annotation strings must be printable ASCII (no em-dashes, no unicode minus)
    - reportFeatureInfo, not reportInfo (and no popup at all - Nick's call)
    - opSphere, not fSphere
    - a parameter group ("Group Name"/"Driving Parameter") must IMMEDIATELY
      follow its driving parameter's declaration - nothing in between, or
      precondition analysis fails on the whole feature
*/

annotation {
    "Feature Type Name" : "Friction Shoe",
    "Feature Type Description" : "Arc friction-bearing shoe, revolved about the ring axis so the working surface is conformal to the mating rail arc by construction: shallow cone seat (0 = cylindrical band) with exact tangent edge fillets (fillet = thickness/2 at angle 0 gives a full bullnose), plus optional countersunk mount holes on the mid-arc meridian."
}
export const frictionShoe = defineFeature(function(context is Context, id is Id, def is map)
    precondition
    {
        annotation { "Name" : "Seat radius", "Description" : "Plan radius of the mating rail's running face, about the ring axis (rev C rail: Ri 320 - rail_w 4 = 316). The working cone crosses (seat radius - clearance) at the plate mid-plane." }
        isLength(def.seatRadius, { (millimeter) : [1, 316, 10000] } as LengthBoundSpec);

        annotation { "Name" : "Clearance", "Description" : "Radial backoff of the working face from the seat radius. At seat angle 0 this is a true running gap; on an angled seat it only shifts where the ring settles axially (by clearance / tan(angle)). 0.1-0.15 suits FDM." }
        isLength(def.clearance, { (millimeter) : [0, 0.1, 2] } as LengthBoundSpec);

        annotation { "Name" : "Arc angle", "Description" : "Circumferential span of the shoe, centered on the +X meridian. The measured bracket spans 6 deg (+-3)." }
        isAngle(def.arcAngle, { (degree) : [0.5, 6, 360] } as AngleBoundSpec);

        annotation { "Name" : "Seat angle", "Description" : "Lean of the working face from the ring-axis direction: 0 = cylindrical running band fully conformal to the rail face; larger = shallower wedge the ring settles into (self-locating). Default 10 is an assumption - Nick's 'shallow', not a measured value." }
        isAngle(def.seatAngle, { (degree) : [0, 10, 60] } as AngleBoundSpec);

        annotation { "Name" : "Plate thickness", "Description" : "Axial thickness of the shoe plate, centered on the sketch plane (mid-plane z = 0 is the mating datum). Measured bracket: 12." }
        isLength(def.plateThickness, { (millimeter) : [0.5, 12, 100] } as LengthBoundSpec);

        annotation { "Name" : "Edge fillet", "Description" : "Tangent blend radius at both edges of the working face - the anti-carve round. Fillet = thickness/2 merges the two blends into a full bullnose at ANY seat angle (that reproduces the measured 6.0 round on the 12 plate; the crest then sits ~0.2 inside the seat radius and the angle stops mattering). Default 5 keeps a 2 mm true cone face. The guard reports the exact maximum." }
        isLength(def.edgeFillet, { (millimeter) : [0, 5, 50] } as LengthBoundSpec);

        annotation { "Name" : "Body depth", "Description" : "Radial depth of the plate behind the working face (the mounting land lives here). Measured bracket: 53." }
        isLength(def.bodyDepth, { (millimeter) : [2, 53, 500] } as LengthBoundSpec);

        annotation { "Name" : "Face inward", "Default" : false, "Description" : "Unchecked: the working face looks radially OUTWARD (shoe inside the ring bore, rail rides over it - the wall-art case). Checked: mirrored about the seat radius to rub a surface that looks outward (e.g. riding an OD)." }
        def.faceInward is boolean;

        annotation { "Name" : "Flip lean", "Default" : false, "Description" : "Mirrors the seat lean in z. Unchecked: the face leans back going toward +z (the ring settles toward -z)." }
        def.flipLean is boolean;

        annotation { "Name" : "Mount holes", "Default" : true, "Description" : "Countersunk through-holes on the mid-arc meridian, axes along the ring axis, countersinks opening toward +z. Measured: dia 5.0, countersink rim 8.5 at 45 deg (flat-head M5), spaced 25 (the grid)." }
        def.mountHoles is boolean;
        if (def.mountHoles)
        {
            annotation { "Group Name" : "Mount Holes", "Driving Parameter" : "mountHoles", "Collapsed By Default" : false }
            {
                annotation { "Name" : "Hole count", "Description" : "Holes march radially inward-to-outward from the first hole radius at the hole spacing." }
                isInteger(def.holeCount, { (unitless) : [1, 2, 12] } as IntegerBoundSpec);

                annotation { "Name" : "First hole radius", "Description" : "Plan radius of the first (innermost) hole center. The guard reports the span the plate can host." }
                isLength(def.firstHoleRadius, { (millimeter) : [1, 270.5, 10000] } as LengthBoundSpec);

                annotation { "Name" : "Hole spacing", "Description" : "Radial center-to-center spacing. 25 keeps the wall layout on the grid." }
                isLength(def.holeSpacing, { (millimeter) : [1, 25, 500] } as LengthBoundSpec);

                annotation { "Name" : "Hole diameter", "Description" : "Through bore. Measured 5.0 on the bracket; FDM print-fit for a loose M5 may want 5.4." }
                isLength(def.holeDia, { (millimeter) : [0.5, 5.0, 30] } as LengthBoundSpec);

                annotation { "Name" : "Countersink diameter", "Description" : "Rim diameter at the +z face; the cone is 45 deg so depth = (countersink - hole) / 2. Measured 8.5 (snug for a nominal 9.5 flat M5 head)." }
                isLength(def.csDia, { (millimeter) : [0.5, 8.5, 60] } as LengthBoundSpec);
            }
        }
    }
    {
        const ov = 1 * millimeter;
        const T = def.plateThickness;
        const a = def.seatAngle;
        const f = def.edgeFillet;
        var Rf = def.seatRadius - def.clearance;
        if (def.faceInward)
            Rf = def.seatRadius + def.clearance;

        const zT = T / 2;
        const zB = -T / 2;
        const tanA = tan(a);
        const rTopC = Rf - zT * tanA;       // face line meets z = +T/2
        const rBotC = Rf + zT * tanA;       // face line meets z = -T/2
        const rBack = Rf - def.bodyDepth;
        if (!def.faceInward && rBack < 0.1 * millimeter)
            throw regenError("Body depth reaches the ring axis - maximum here is "
                ~ mm2(Rf - 0.1 * millimeter) ~ " mm.");

        // Tangent-fillet feasibility: material wedge is (90 - angle) at
        // the bottom corner, (90 + angle) at the top; the two takeups
        // along the face must fit inside its length T / cos(angle).
        const phiB = acos(sin(a));
        const phiT = acos(-sin(a));
        var tOffB = 0 * millimeter;
        var tOffT = 0 * millimeter;
        if (f > 0.005 * millimeter)
        {
            tOffB = f / tan(phiB / 2);
            tOffT = f / tan(phiT / 2);
        }
        const lFace = T / cos(a);
        if (tOffB + tOffT > lFace + 1e-6 * millimeter)
        {
            const fMax = lFace / (1 / tan(phiB / 2) + 1 / tan(phiT / 2));
            throw regenError("Edge fillet too large for this thickness / seat angle - maximum here is "
                ~ mm2(fMax) ~ " mm. (Fillet = thickness/2 at seat angle 0 is the full bullnose.)");
        }
        if (tOffB > rBotC - rBack - 0.5 * millimeter || tOffT > rTopC - rBack - 0.5 * millimeter)
            throw regenError("Body depth too small - the edge fillet consumes the plate. Grow body depth past "
                ~ mm2(max(tOffB - rBotC + Rf, tOffT - rTopC + Rf) + 0.5 * millimeter) ~ " mm.");

        // Profile walk in (r, z), counterclockwise from the back-bottom
        // corner: bottom face, tangent arc, cone face, tangent arc, top
        // face, back face. Arcs are exact skArc entities - the running
        // surface must not be a chord approximation.
        const u = vector(-sin(a), cos(a));  // up the face
        const cBot = vector(rBotC, zB);
        const cTop = vector(rTopC, zT);
        var segs = [];
        var pA = vector(rBack, zB);
        var pD = vector(rBack, zT);
        if (f > 0.005 * millimeter)
        {
            const uB = vector(-1, 0);
            var bisB = uB + u;
            bisB = bisB / norm(bisB);
            const ctrB = cBot + bisB * (f / sin(phiB / 2));
            const pB0 = cBot + uB * tOffB;
            var pB1 = cBot + u * tOffB;

            const uT = vector(sin(a), -cos(a));
            const vT = vector(-1, 0);
            var bisT = uT + vT;
            bisT = bisT / norm(bisT);
            const ctrT = cTop + bisT * (f / sin(phiT / 2));
            var pT0 = cTop + uT * tOffT;
            const pT1 = cTop + vT * tOffT;

            const rem = lFace - tOffB - tOffT;
            if (rem < 1e-4 * millimeter)
            {
                // Fillets meet: full bullnose. Share one exact point so
                // the loop closes watertight.
                pB1 = (pB1 + pT0) / 2;
                pT0 = pB1;
            }
            segs = append(segs, { "kind" : "line", "s" : pA, "e" : pB0 });
            segs = append(segs, { "kind" : "arc", "s" : pB0,
                "m" : arcMid(ctrB, pB0, pB1, f), "e" : pB1 });
            if (rem >= 1e-4 * millimeter)
                segs = append(segs, { "kind" : "line", "s" : pB1, "e" : pT0 });
            segs = append(segs, { "kind" : "arc", "s" : pT0,
                "m" : arcMid(ctrT, pT0, pT1, f), "e" : pT1 });
            segs = append(segs, { "kind" : "line", "s" : pT1, "e" : pD });
        }
        else
        {
            segs = append(segs, { "kind" : "line", "s" : pA, "e" : cBot });
            segs = append(segs, { "kind" : "line", "s" : cBot, "e" : cTop });
            segs = append(segs, { "kind" : "line", "s" : cTop, "e" : pD });
        }
        segs = append(segs, { "kind" : "line", "s" : pD, "e" : pA });

        // Orientation options: mirror in z (lean flip) and/or about the
        // face radius (rub the other side of a rail). Arcs mirror to
        // arcs; the region does not care about winding.
        for (var k = 0; k < size(segs); k += 1)
        {
            var s = segs[k];
            if (def.flipLean)
            {
                s.s = vector(s.s[0], -s.s[1]);
                s.e = vector(s.e[0], -s.e[1]);
                if (s.kind == "arc")
                    s.m = vector(s.m[0], -s.m[1]);
            }
            if (def.faceInward)
            {
                s.s = vector(2 * Rf - s.s[0], s.s[1]);
                s.e = vector(2 * Rf - s.e[0], s.e[1]);
                if (s.kind == "arc")
                    s.m = vector(2 * Rf - s.m[0], s.m[1]);
            }
            segs[k] = s;
        }

        var sk = newSketch(context, id + "profile", {
            "sketchPlane" : qCreatedBy(makeId("Front"), EntityType.FACE)
        });
        for (var k = 0; k < size(segs); k += 1)
        {
            if (segs[k].kind == "arc")
                skArc(sk, "e" ~ k, {
                    "start" : segs[k].s,
                    "mid"   : segs[k].m,
                    "end"   : segs[k].e
                });
            else
                skLineSegment(sk, "e" ~ k, {
                    "start" : segs[k].s,
                    "end"   : segs[k].e
                });
        }
        skSolve(sk);

        const zAxis = line(vector(0, 0, 0) * millimeter, vector(0, 0, 1));
        opRevolve(context, id + "shoe", {
            "entities" : qSketchRegion(id + "profile"),
            "axis" : zAxis,
            "angleForward" : def.arcAngle
        });
        opTransform(context, id + "center", {
            "bodies" : qCreatedBy(id + "shoe", EntityType.BODY),
            "transform" : rotationAround(zAxis, -def.arcAngle / 2)
        });
        opDeleteBodies(context, id + "delProfile", {
            "entities" : qCreatedBy(id + "profile", EntityType.BODY)
        });

        if (def.mountHoles)
        {
            const hr = def.holeDia / 2;
            const cr = def.csDia / 2;
            if (cr <= hr)
                throw regenError("Countersink diameter must exceed the hole diameter.");
            const csDep = cr - hr;          // 45 deg cone
            if (csDep >= T)
                throw regenError("45 deg countersink is deeper than the plate - shrink the countersink diameter.");

            // Holes live on the flat mounting land: off the back face and
            // off the fillet/face zone by 1 mm, in post-mirror plan radii.
            const flatOut = min(rTopC - tOffT, rBotC - tOffB);
            var lo = rBack + 1 * millimeter;
            var hi = flatOut - 1 * millimeter;
            if (def.faceInward)
            {
                lo = 2 * Rf - flatOut + 1 * millimeter;
                hi = 2 * Rf - rBack - 1 * millimeter;
            }

            var tools = [];
            for (var i = 0; i < def.holeCount; i += 1)
            {
                const rH = def.firstHoleRadius + i * def.holeSpacing;
                if (rH - cr < lo || rH + cr > hi)
                    throw regenError("Mount hole " ~ (i + 1) ~ " (center at " ~ mm2(rH)
                        ~ " mm) leaves the flat land - centers must sit between "
                        ~ mm2(lo + cr) ~ " and " ~ mm2(hi - cr) ~ " mm plan radius.");

                var hs = newSketchOnPlane(context, id + ("boreSk" ~ i), {
                    "sketchPlane" : plane(
                        vector(0 * millimeter, 0 * millimeter, zB - ov),
                        vector(0, 0, 1),
                        vector(1, 0, 0))
                });
                skCircle(hs, "bore", {
                    "center" : vector(rH, 0 * millimeter),
                    "radius" : hr
                });
                skSolve(hs);
                opExtrude(context, id + ("bore" ~ i), {
                    "entities" : qSketchRegion(id + ("boreSk" ~ i)),
                    "direction" : vector(0, 0, 1),
                    "endBound" : BoundingType.BLIND,
                    "endDepth" : T + 2 * ov
                });
                tools = append(tools, qCreatedBy(id + ("bore" ~ i), EntityType.BODY));
                opDeleteBodies(context, id + ("delBoreSk" ~ i), {
                    "entities" : qCreatedBy(id + ("boreSk" ~ i), EntityType.BODY)
                });

                // Countersink: right profile revolved about the hole's own
                // axis; the 45 deg flank overshoots the rim by ov along
                // its own slope so the cut breaks out clean.
                var cs = newSketch(context, id + ("csSk" ~ i), {
                    "sketchPlane" : qCreatedBy(makeId("Front"), EntityType.FACE)
                });
                skLineSegment(cs, "axisEdge", {
                    "start" : vector(rH, zT - csDep),
                    "end"   : vector(rH, zT + ov)
                });
                skLineSegment(cs, "top", {
                    "start" : vector(rH, zT + ov),
                    "end"   : vector(rH + cr + ov, zT + ov)
                });
                skLineSegment(cs, "flank", {
                    "start" : vector(rH + cr + ov, zT + ov),
                    "end"   : vector(rH + hr, zT - csDep)
                });
                skLineSegment(cs, "bottom", {
                    "start" : vector(rH + hr, zT - csDep),
                    "end"   : vector(rH, zT - csDep)
                });
                skSolve(cs);
                opRevolve(context, id + ("cs" ~ i), {
                    "entities" : qSketchRegion(id + ("csSk" ~ i)),
                    "axis" : line(vector(rH, 0 * millimeter, 0 * millimeter), vector(0, 0, 1)),
                    "angleForward" : 360 * degree
                });
                tools = append(tools, qCreatedBy(id + ("cs" ~ i), EntityType.BODY));
                opDeleteBodies(context, id + ("delCsSk" ~ i), {
                    "entities" : qCreatedBy(id + ("csSk" ~ i), EntityType.BODY)
                });
            }
            opBoolean(context, id + "drill", {
                "tools" : qUnion(tools),
                "targets" : qCreatedBy(id + "shoe", EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
            });
        }
    });

// Midpoint of the minor arc from p0 to p1 about ctr (radius rho) - skArc
// wants an on-arc mid, and the running surface must be an exact arc,
// not a chord fan.
function arcMid(ctr is Vector, p0 is Vector, p1 is Vector, rho)
{
    const a0 = atan2(p0[1] - ctr[1], p0[0] - ctr[0]);
    const a1 = atan2(p1[1] - ctr[1], p1[0] - ctr[0]);
    var sweep = a1 - a0;
    if (sweep > 180 * degree)
        sweep = sweep - 360 * degree;
    if (sweep < -180 * degree)
        sweep = sweep + 360 * degree;
    const am = a0 + sweep / 2;
    return ctr + vector(cos(am), sin(am)) * rho;
}

// Two-decimal millimeter formatting for guard messages.
function mm2(x)
{
    return floor(x / millimeter * 100 + 0.5) / 100;
}
