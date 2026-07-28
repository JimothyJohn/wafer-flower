# GEARS.md — why these bevel gears work, and how to generate yours

This is the clinic. It explains why the Wafer Halo's gear train — a 108-tooth
45° bevel rack on the sculpture's OD, driven at 10.8:1 by a 10-tooth conical
pinion on a vertical shaft — meshes correctly *as generated*, why classical
bevel-gear theory said it couldn't exist, and exactly which constraints are
load-bearing versus free, so the same method can be re-targeted
algorithmically (different ring size, ratio, motor, cone angle) without
re-deriving anything by hand. Every claim cites the code that enforces it;
all excerpts are from `scripts/segment_stl.py` unless noted.

The one-sentence version: **don't specify tooth flanks — carve them, by
sweeping the actual mating part through the exact relative motion, and let
boolean gates prove the result.**

---

## 1. The problem that theory can't solve

The drive wants four things simultaneously:

1. A **45° straight bevel rack** on the ring's outside diameter — the mixer
   look, working face toward the viewer (aesthetic, non-negotiable).
2. A **10.8:1 ratio**, because the bought motor (Pololu #1596, 1000:1 micro
   metal, 13 rpm no-load at 6 V) runs at 13 × 5/6 ≈ 10.83 rpm on 5 V USB,
   and 10.83 ÷ 10.8 = **1.003 rpm** at the sculpture — the target speed with
   no controller.
3. The pinion shaft **pointing straight down** (radial at 12 o'clock), motor
   directly above it.
4. Packaging: silicon wafers own *all* space in front of the ring (their
   undersides sweep within millimetres of the tooth band), and drywall owns
   the space behind.

Classical bevel gearing cannot deliver this. Two true-rolling bevel gears
must share a pitch-cone **apex** on the line where their shafts intersect,
and the cone angles are then *dictated* by the ratio:
`tan δ₂ = sin Σ / (ratio + cos Σ)`. Consequences, all measured in this repo
before being abandoned:

- A **45°/45° pair only rolls at 1:1**. At 10.8:1 with 90° shafts the ring
  cone must be ~84.7° (nearly a flat face gear) and the pinion ~5.3° (nearly
  a spur) — no mixer look.
- Keeping the ring at 45° and solving for true rolling puts the shared apex
  **~300 mm in front of the wall** on the halo axis; the pinion and motor
  would hang in the wafer field.
- The interim parallel-axis beveloid solved packaging but put the shaft
  along the wall normal — not the drive Nick specified.
- A rolling-sized radial-axis pinion (pitch = ring pitch ÷ ratio = 26.9 mm)
  ballooned to Ø100 at the big end and forced a 108 mm-tall part before the
  size assumption was questioned (§4).

## 2. The move: generation, not specification

The escape is the same one machine tools use. A hobbed or shaped gear is
never *drawn* — the cutter and blank are driven through the meshing motion
and the flanks emerge as the envelope of material that survives. Conjugacy
is then true **by construction**: the running pinion cannot interfere with
flanks its own shape cut while executing the exact motion it will run.

Here that principle is executed volumetrically with CSG (`manifold3d`): the
cutter is a solid model of the pinion, placed at ~500 successive poses of
the relative motion, unioned, and subtracted from the ring blank. The core
of `gear_teeth_bevel45()`:

```python
# segment_stl.py, gear_teeth_bevel45() — the generation sweep.
# One pose per step: the pinion spun ratio*d about its own axis, placed on
# the radial axis, then the whole pose rotated -d so the ring stays still.
cutter_pin, _ = bevel_pinion(cf, backlash=0.0, over=0.5)
n = steps or (48 * int(round(cf.gear_m)) + 1)
span = span_pitches * (2.0 * math.pi / cf.teeth)      # ±2 ring pitches
cut = union_all([(bevel_pinion_at(cf, cutter_pin,
                                  -span / 2.0 + span * i / (n - 1), dr=-0.3)
                  .rotate([0, 0, -math.degrees(-span / 2.0
                                               + span * i / (n - 1))]))
                 for i in range(n)])
gen = blank - cut
```

and the pose function that encodes the crossed-axis kinematics:

```python
# segment_stl.py, bevel_pinion_at() — the imposed motion.
def bevel_pinion_at(cf, pin, d, dr=0.0):
    bg = bevel_geom(cf)
    return (pin.rotate([0.0, 0.0, math.degrees(d * bg['ratio'])])
               .rotate([0.0, 90.0, 0.0])
               .translate([bg['x0'], 0.0, bg['zax'] + dr]))
```

Read it kinematically: while the ring turns `d`, the pinion turns
`ratio · d` about its own (radial) axis. `rotate([0,90,0])` maps the
pinion's local +z (its axis) onto the global radial direction, which also
lands its phase-0 tooth pointing down into the ring. The `.rotate(-d)` in
the sweep transfers the ring's share of the motion onto the cutter, so the
blank can stay fixed. That pair of lines *is* the gear theory in this repo.
The spin sign was derived once by matching surface velocities at the
contact and is *verified*, not trusted — a wrong sign reads as hundreds of
mm³ in the mesh gate (§6).

Because the flanks are an envelope of an imposed motion rather than rolling
involutes, this pair runs with sliding contact, like a cam or a worm. At
this drive's loads (~3 mN·m needed against a 0.54 N·m stall through the
gearbox) sliding is irrelevant; the printed PLA pinion doubles as the
mechanical fuse.

## 3. The two constraints that are actually load-bearing

Everything about this drive is negotiable except two integers.

**Ring tooth count must divide by N.** The ring is assembled from N=9
identical printed segments; if the tooth pattern doesn't tile the 40° joint
exactly, the pitch breaks at every seam. So `teeth = tps × N`, and the
pattern is phased so **every joint lands mid-space** (a space at azimuth 0,
copies at `k·pitch` — see §5d).

**Ratio = ring teeth ÷ pinion teeth, exactly.** Tooth-passing frequency
must match at the mesh, so `108 / pin_T = ratio`. Wanting 10.8:1 forces
`pin_T = 10`. This is the *only* thing the RPM goal fixes:

```python
# segment_stl.py PARAMS
pin_T    = 10,      # pinion tooth count. 108T ring / 10T = 10.8:1 —
                    # pairs the Pololu #1596 at 5 V (13*5/6 = 10.83
                    # no-load rpm) to 1.00 rpm at the ring
```

Note what is *not* on this list: the pinion's size, and even its cone
angle. That's the subject of the next section, and it's the difference
between the Ø100 monster and the Ø41 pinion that shipped.

## 4. The freedom theorem: pinion size is a style knob

Textbook reflex says the pinion's pitch radius must be
`ring_pitch / ratio` (rolling contact at the pitch point). The first
crossed-axis build obeyed that reflex — rho 26.9 mm, tips Ø100, the motor
36 mm off the wall, the whole part 108 mm tall — and got the correct
review: *"way out of scale… it should be right up on its nuts."*

The reflex is wrong **because generation owns conjugacy**. The sweep makes
the ring conjugate to whatever cutter executes the motion; rolling is a
contact-quality optimization, not a meshing requirement. Only the tooth
count is forced. So the pinion's pitch radius and engaged face are free
parameters, sized for packaging:

```python
# segment_stl.py PARAMS
pin_rho  = 12.0,    # pinion mid-face pitch radius. FREE, not the
                    # rolling value ring_pitch/ratio (26.9): conjugacy
                    # is by generation under the imposed motion, so
                    # only the COUNT is forced — the first crossed rev
                    # used the rolling size and read "way out of
                    # scale" (Nick). Small = motor right at the mesh.
pin_face = 10.0,    # pinion face length along its axis: engages the
                    # OUTER pin_face mm of the tooth radial envelope.
```

With rho = 12 the pinion is a Ø17→Ø41 cone, its axis 19.1 mm off the wall
face, and the derived wafer standoff collapses from +78 to +31 mm (§7).
The cost of abandoning rolling is extra sliding — already accepted.

## 5. The recipe

### a. Size the ring teeth: flush module by retune

Tooth count is quantized in steps of N, so the pitch radius can't be tuned
by count. Instead the *module* is retuned so the root circle lands on the
band's outer wall — teeth rise straight off the part, no bare web:

```python
# segment_stl.py, Cfg — FLUSH MODULE
target = self.Ro + 1.25 * self.gear_m + 2.0
self.tps = max(6, int(math.ceil(2 * target / self.gear_m / self.N)))
self.teeth   = self.tps * self.N
if self.g_bev:
    self.gear_m = (self.Ro - 1.0) / (self.teeth / 2.0 - 1.25)
```

At the shipped numbers: nominal module 5.6 → 12 teeth/segment → 108 teeth →
effective module 5.384, root at r284 against the band OD at 285.

### b. The ring blank owns the look

The visible 45° cone is *not* produced by the cutter — it's the blank: an
annulus intersected with a cone, big end at the wall (radius falls 1 mm per
mm of z toward the viewer):

```python
# segment_stl.py, gear_teeth_bevel45() — the blank
big = cf.g_tip * cf.g_kbig + 1.0
blank = prism(arc(big, -cf.half, cf.half, 200) +
              arc(cf.g_web_i, cf.half, -cf.half, 200), 0.0, F)
tipcone = (Manifold.cylinder(F + 0.2, cf.g_tip * cf.g_kbig + 0.1,
                             cf.g_tip + 0.1, 512)
           .translate([0.0, 0.0, -0.1]))
blank = blank ^ tipcone
```

This separation matters for generality: change the blank and the gear's
silhouette changes; the cutter sweep only decides where the working flanks
are. The face height `gear_F` has a *live-computed* ceiling — the band must
clear the neighbouring wafer's clearance plane, measured by
`gear_F_ceiling()` and enforced by a gate in `main()` that fails the build
if the mandatory clearance cut removes any tooth material.

### c. Build the cutter: a cone of scaled involutes

The cutter (and the printed runner) is the pinion: standard external
involute sections, scaled linearly along the axis so the envelope is a 45°
cone. Linear scaling with `scale_top` gives exactly 1 mm of radius per mm
of length:

```python
# segment_stl.py, bevel_pinion() — sections scaled (station − apex)/rp0
s_lo = (bg['x0'] - over - bg['apex']) / rp0
s_hi = (bg['x1'] + over - bg['apex']) / rp0
p = Manifold.extrude(CrossSection([pts]), bg['face'] + 2 * over,
                     n_divisions=16, twist_degrees=tw,
                     scale_top=(s_hi / s_lo,) * 2)
```

Two details are traps, both encoded: `over=0.5` extends the cutter past
both faces (a cutter ending exactly on a face leaves sliver faces that read
as OPEN after the float32 STL weld), and `twist_degrees` is where a spiral
would go — set `gear_sp`, and the *generated ring inherits the conjugate
spiral automatically*, because the sweep doesn't care what the cutter looks
like.

### d. Sweep, extract, pattern, clip

The sweep spans ±2 ring pitches (`span_pitches=4`) — enough for the cutter
to fully enter and leave a space, which is also what proves tooth handoff.
Then one pitch is extracted and patterned, because the motion is periodic:

```python
# segment_stl.py, gear_teeth_bevel45() — pattern and clip
one = gen ^ wedge                       # one-pitch sample, cut at angle 0
teeth = union_all([one.rotate([0.0, 0.0, -math.degrees(cf.half) + k * pitch])
                   for k in range(cf.tps + 1)])
eps = 1e-5
sector = prism([(0.0, 0.0)] + arc(big + 100.0, -cf.half + eps,
                                  cf.half - eps, 64), -1.0, F + 2.0)
teeth = teeth ^ sector
```

Three phase/pattern rules, each learned the hard way (measured values in
CLAUDE.md): the cutter cuts a **space at angle 0**, so copies tile at
`k·pitch` from the joint (a half-pitch offset reads as ~156 mm³ of joint
interference); **tps+1 copies** are generated then clipped (an unclipped
end wedge lands 232 mm³ inside the neighbour segment); and the sector clip
backs off **1e-5 rad** from the exact joint plane (numerically coincident
faces on assembled neighbours read as phantom interference).

Tip relief is **radial** — the cutter runs with `dr = -0.3`, i.e. its whole
axis 0.3 mm closer to the ring than the runner will sit, so slot floors are
uniformly deeper than running tips. The obvious alternative (shifting the
cutter along z) was shipped once and left a visible uncut 0.3 mm shelf ring
at the wall-face edge of every tooth.

### e. The cosmetic pass: look and function, decoupled

The small pinion only needs the outer 10 mm of the tooth envelope, but the
*visible* pattern should span the whole 45° face. So a second sweep runs a
full-face parallel-axis beveloid cutter over the blank, purely for
appearance. This is safe by a monotonicity argument worth internalizing:
**extra material removal can only add clearance** — it cannot create
interference — so the mesh gate is untouched. Both patterns tile at
`k·pitch`, so they align tooth-for-tooth:

```python
# segment_stl.py, gear_teeth_bevel45() — cosmetic pass (excerpt)
# ... the small crossed pinion only carves the outer pin_face of the
# envelope; the visible deep-bevel tooth pattern is restored by ALSO
# sweeping the old parallel-axis 12T beveloid cutter over the full face.
cut = cut + union_all([
    (cos_pin.rotate([0.0, 0.0, -math.degrees(d * cf.teeth / cf.tps)])
            .translate([C - 0.3, 0.0, 0.0])
            .rotate([0, 0, -math.degrees(d)]))
    for d in (-span / 2.0 + span * i / (nc - 1) for i in range(nc))])
```

### f. Cutter vs runner: backlash by thinning

The generating cutter runs at zero backlash; the printed runner is the same
solid with teeth thinned by `gear_bl = 0.6` mm (`pinion_profile`'s
`psi_p` term). Running clearance therefore exists **by construction**:
flank clearance from the thinning, tip clearance from the radial relief.
0.6 mm is the printed-PLA tune; it is a parameter, not a constant.

## 6. Why meshing is guaranteed — the gates

Generation makes interference impossible *up to discretization* (the sweep
is a union of poses, so the true envelope is scalloped at the step
spacing). The residual is measured, not assumed:

```python
# segment_stl.py, check_mesh() — roll the RUNNER against the generated
# teeth through one full ring pitch and measure boolean overlap
for i in range(steps):
    d = (2 * math.pi / cf.teeth) * i / steps
    r2 = ring.rotate([0, 0, math.degrees(d)])
    p2 = bevel_pinion_at(cf, pin, d)
    worst = max(worst, (r2 ^ p2).volume())
```

CI fails the build if `worst > 0.05 mm³`; the shipped geometry measures
**0.00000 mm³**. The same number is the arbiter for the motion's spin sign
and phase — a wrong sign or a half-pitch phase error reads as hundreds of
mm³, so the convention can never silently rot.

The rest of the gate suite closes the environment: the neighbour-wafer
clearance cut must remove zero tooth material (its ceiling on `gear_F` is
computed live from the wafer geometry, not frozen in a comment); assembled
neighbour segments must measure exactly 0 interference; every body must be
watertight with the expected genus, with sub-0.01 mm³ specks filtered at
the source because a disconnected crumb cancels a handle in the Euler count
and masquerades as correct topology. Downstream, `bracket_stl.py` checks
the *running context*: the pinion against the full ring + wafer field at
nominal, the wall plane including the pinion's swing, and the wheel datum
that preloads the mesh.

## 7. Packaging closes the loop

Two derived quantities tie the gear to the sculpture, both computed in
`Cfg`, neither hand-maintained:

- **`stand`** — the wafers must clear the pinion's front bulge, so the part
  grows exactly as much as the drive needs:
  `pin_bulge = pin_zax + (pin_x1 − pin_apex)·(1 + 2/pin_T)`, and
  `stand = pin_bulge + 3 − gap₀`. At rho 12 that's +31 mm (it was +78 at
  the rolling-sized pinion — shrinking the pinion shrank the sculpture).
- **wall gap** — the pinion's lower teeth swing `(x1−apex)·1.2 − zax`
  behind the ring's wall face (1.2 mm at shipped numbers); the mount holds
  the ring 6 mm off the drywall and the wall-plane check proves it.

The mount side completes the mesh mechanics: the two bore idlers hang the
ring **at the meshing meridian**, so the pinion presses against a hard
radial datum, and the motor shell rides ±8 mm slots to set engagement depth
(preload) before clamping.

## 8. Re-targeting checklist (the algorithm, as an algorithm)

To generate a different bevel drive with this machinery:

1. Pick ring size (`Ri`, `bw`) and nominal module for tooth chunkiness;
   the flush retune (§5a) makes the count/size self-consistent.
2. Pick the ratio from your speed goal; `pin_T = teeth / ratio` must land
   on an integer — that's the only place the RPM constrains the geometry.
3. Pick `pin_rho` and `pin_face` for packaging (motor location, bulge,
   behind-face swing). These are free (§4).
4. Pick the blank's cone (`gear_F`, big end direction) for looks, under
   the live environmental ceiling.
5. Optional spiral: one parameter (`gear_sp`); the ring inherits it.
6. Run the generator. The sweep produces the conjugate flanks; the gates
   (mesh sweep, clearance cut, pair fit, watertightness, context checks)
   either prove the result or point at exactly which assumption broke.

Nothing in the list involves drawing a tooth.

---

*Related: `scripts/onshape/wafer_halo_beveloid.fs` reproduces the ring
band and pinion analytically for OnShape CAD work (parity-tested spec
math); the generated Python parts remain the authority for anything that
prints. History and the full trap ledger live in `CLAUDE.md`.*
