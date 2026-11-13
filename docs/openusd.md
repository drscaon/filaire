# OpenUSD layout and contract

How a cable is laid out in the file, the ground and physics scene, and what the Primvaria contract writes on every cable.

Part of the [Filaire](../README.md) documentation.

## OpenUSD layout

Z up, metres, kilograms, `/World` the default prim.

```
/World
  /PhysicsScene                  gravity (shared, see below)
  /Looks, /PhysicsMaterials      UsdPreviewSurface materials; friction and restitution
  /Cables/<cable>                Xform, PhysicsArticulationRootAPI, filaire:* attributes,
                                 variant sets "end_a" and "end_b"
    /Segments/seg_000 …          rigid bodies (RigidBodyAPI, MassAPI), x along the cable
      /Visual                    ONE mesh: the piece of tube this segment carries
      /Collision                 Capsule along x (round, coiled) or Cube (flat, figure-8), purpose guide
    /Joints/joint_000 …          PhysicsJoint: translations locked (coil: transX free between limits),
                                 drives rotX (twist), rotY, rotZ (bending) [, transX (coil)]
    /End_A, /End_B               filled by the selected variant:
      /Body                      rigid body of the connector or stripped end
        /Visual                  ONE mesh, a GeomSubset per material (shell, body, insulators, clear plastic, cores, copper)
        /Collision/hull_00 …     convex parts (MeshCollisionAPI convexHull, purpose guide)
        /MateFrame               origin on the mating plane, +Z = insertion direction
      /Attach                    PhysicsFixedJoint to the end segment
  /Ground                        the shared ground: a collision box, its top face at z = 0
  /GroundMaterial                its physics material
```

## Ground and physics scene (the same in every Primvaria project)

Every file with physics carries the same two prims, so that assets from
different generators can share one scene and every engine gets the same floor:

| Prim | What it is |
|---|---|
| `/World/PhysicsScene` | gravity 9.81 m/s² along −Z |
| `/World/Ground` | a static box (`UsdGeom.Cube`, `CollisionAPI`), its top face at z = 0, 2 cm thick, covering the content with 0.5 m to spare on each side (1 m × 1 m at least), grey and rendered, no PhysX attributes (engines derive their contact offsets) |
| `/World/GroundMaterial` | its physics material: static friction 0.6, dynamic friction 0.5, restitution 0.1, a wooden or concrete floor |

The code is one file, `ground.py`, identical in Granulaire, Maillage, Filaire
and Quincaillerie; a test checks every generated file against it. The MuJoCo
checks and the Blender rigid-body checks take the ground's friction from the
file (Blender's cloth, in Maillage, has its own collision settings).

Each rigid body has exactly one visual mesh, as in Quincaillerie: Blender
and other DCCs import one object per body, so a rigid body set on it moves
the whole part. Each segment spans the chord between its two joints, so
neighbouring segments meet exactly at their joint even on a tight curve.

## PhysX layer

The files hold plain OpenUSD (`UsdGeom`, `UsdShade`, `UsdPhysics`) and
nothing specific to an engine. What only PhysX reads is written beside each
file as a layer over it, `filaire_<preset>_physx.usda` and
`sockets_physx.usda`:

| On | Schema | Values |
|---|---|---|
| every rigid body | `PhysxRigidBodyAPI` | 32 position and 4 velocity solver iterations (light links on stiff joints need many), depenetration velocity capped at 1 m/s, no CCD |
| every collider but the ground | `PhysxCollisionAPI` | contact offset 0.5 mm, rest offset 0 |

The layer has the file as its only sublayer and holds `over`s only, so
opening it (Isaac Sim: File > Open) gives the file with these settings, and
the file alone is still complete for every other engine. The settings of a
connector are written inside the variant that brings it, so they follow the
end you select. `python -m filaire.physx <folder>` checks the layers of a
pack; the OpenUSD validators run on them in CI. Not simulated: see
[Limits](limits.md#limits).

**Without physics** (`--no-physics`, `write_outputs(…, physics=False)`):
each cable is one mesh, `/World/Cables/<cable>/Visual`, each end a `Body`
with its `Visual` and `MateFrame`; no rigid bodies, colliders, joints,
physics materials, physics scene or ground. The `filaire:*` attributes stay.

**OpenUSD compliance.**

```bash
python -m filaire.validate output/usb_c      # files or folders; exit 1 on any issue
```

This runs every validator of OpenUSD's `UsdValidation` registry, the checks
`usdchecker` runs (composition, stage metadata, geometry and subsets,
material bindings, shaders, UsdPhysics bodies, colliders, joints and
articulations), on each file as authored and once per end variant of each
cable, since a variant that is not selected is not composed. From Python:
`filaire.validate.validate(file)` returns the messages. The tests and CI
require no error and no warning, with and without physics.

Selecting a variant (`end_b = "usb_c_inline"`, `"cut"`…) swaps the end, its
collision parts and its joint. Angular drives use UsdPhysics units
(stiffness per degree); the same values per radian and the rod's stiffness
are kept as engine-neutral attributes:

| Attribute (on the cable) | Content |
|---|---|
| `filaire:bendingStiffness` | E·I about the width axis and about the height axis (N·m²) |
| `filaire:torsionalStiffness` | G·J (N·m²) |
| `filaire:jointStiffness` | per joint: twist, bend y, bend z (N·m/rad) |
| `filaire:youngsModulus`, `filaire:shearModulus`, `filaire:linearDensity` | material (Pa, kg/m) |
| `filaire:segmentLength`, `filaire:segmentCount`, `filaire:restShape` | discretisation; rest shape is straight |
| `filaire:dampingTime` | joint damping = stiffness × 0.01 s |
| `filaire:coil:*`, `filaire:axialStiffness` | coiled cords: coil diameter, pitch, turns, wire length, coiled length, straight leads (m, end A and B); spring k (N/m) |
| `filaire:length`, `filaire:layout`, `filaire:profile`, `filaire:jacket`, … | what the cable is |

| Attribute (on a `MateFrame`) | Content |
|---|---|
| `filaire:connector`, `filaire:name`, `filaire:standard` | family and name (`usb_c`, "USB-C plug") |
| `filaire:role`, `filaire:mount`, `filaire:contactGender` | plug / receptacle, cable / panel, male / female |
| `filaire:insertionDepth`, `filaire:clearance`, `filaire:keying` | for insertion tasks (m) |
| `filaire:lockTwist` | bayonets only: the turn that locks the plug once fully in (degrees, about +Z) |

## Primvaria contract

```bash
python -m filaire.conformance output/usb_c
```

Filaire is part of [Primvaria](https://primvaria.com) and follows its
[mission](https://github.com/drscaon/primvaria/blob/main/MISSION.md) and its
[OpenUSD contract](https://github.com/drscaon/primvaria/blob/main/docs/contract.md),
version 0, which the four generators share. Every cable and every socket is an asset any tool can find without knowing Filaire: a model of kind
`component` with `assetInfo` (name, identifier, version) and the attributes
`primvaria:contract`, `primvaria:generator`, `primvaria:version`,
`primvaria:preset` and `primvaria:seed`; `/World` is an `assembly`, `/World/Cables` and `/World/Sockets` are groups; a socket is not drawn, so its preset is its connector family and its seed 0. The command above checks
the stage units, the model hierarchy and this identity; the tests and CI
require it on every preset.

What was drawn for each cable is in the file too, its ground truth:
`primvaria:variation:aspects` lists the aspects that were switched on
(`length`, `layout`, `ends`, `color`, `stiffness`, `density`) and `primvaria:variation:<name>` holds each drawn value
(`length_m`, `nominal_length_m`, `layout`, `end_a`, `end_b`, `color`, `youngs_modulus_pa`, `linear_density_kg_per_m`). A socket draws nothing: its list of aspects is empty. An aspect that is switched off is still recorded, at its
nominal value, and the other aspects keep their draws.

What was measured on each cable once generated is there as well, as
`primvaria:measured:<name>` (`cable_mass_kg`, `end_a_mass_kg`, `bending_stiffness_y_nm2`, `torsional_stiffness_nm2`, `segments`…).
The pack's `instances.csv` is read back from the OpenUSD files, one row per
asset with the same names (`variation:<name>`, `measured:<name>`), and
`manifest.json` says what the pack is; both have the same shape in the four
generators, and the command above fails when the table and the files disagree.

Each cable also says what it is with OpenUSD's own semantic labels
(`UsdSemantics.LabelsAPI`), which renderers such as Isaac Sim turn into
segmentation masks: `semantics:labels:class` holds `cable` and the preset (`usb_c`); for a socket, `socket` and its connector family (`rj45`), and
`semantics:labels:instance` the asset's name. The classes are a
column of `instances.csv` and are listed in `manifest.json`.
