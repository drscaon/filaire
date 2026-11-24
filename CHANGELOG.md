# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.6.0b1] - 2026-11-24 (beta)

### Added

- A Newton layer beside every file with physics, `<file>_newton.usda` (contract section 9,
  a new engine layer): `newton:contactGap` on every collider, and a ±170° limit on each
  rotation between two segments. Newton 1.8 gives a generic joint a degree of freedom only on
  an axis with a limit, so without it a cable is rigid there. The files and their PhysX layers
  are unchanged; `python -m filaire.newton` checks the layers.
- `generate --engines LIST`: the engine layers to write (`physx`, `omniphysics`, `newton`,
  comma-separated, or `none`); by default all of them, as the four Primvaria generators do.

### Changed

- Newton layer: every segment's inertia is raised by the armature Filaire's MuJoCo model gives
  its joints (k (dt / 0.3)², dt = 1 ms); the mass is unchanged. Without it Newton's XPBD solver
  cannot hold the drives against a thin segment's inertia (about 1e-10 kg m²), and a USB-C
  sample held flat at one end drooped 7.9 times more than beam theory; with it, the cable holds
  its shape, its bend depending on XPBD's iteration count.

## [0.5.0b1] - 2026-11-20 (beta)

### Breaking changes

- A cable's materials, and a socket's, are inside it:
  `/World/Cables/<cable>/Looks/…` and `…/PhysicsMaterials/jacket`,
  `connector`, instead of `/World/Looks` and `/World/PhysicsMaterials`
  shared by the file. A cable referenced alone into another stage lost its
  colours and its friction; it now keeps them (PRV-40). The values are
  unchanged.

### Changed values

- `usb_c`: every cable lists the aspect `clearance` and records its USB-C
  extension's drawn opening; the extension's mass follows its opening
  (golden reference updated); the USB-C port of `sockets.usdc` records the
  scene's seed instead of 0.

- Receptacle clearances from published openings (FIL-10), per axis around
  the plug's outline: USB-C 0.05 → 0.045 mm across and 0.05 → 0.08 mm up
  and down (receptacle opening 8.34 × 2.56 mm), USB-A 0.08 → 0.25 and
  0.31 mm (opening 12.50 × 5.12 mm for a 12.00 × 4.50 mm plug). HDMI
  Type A and the 3.5 mm jack keep 0.05 mm, now sourced. The tongue or pins
  inside keep each family's clearance. A USB-C extension's receptacle is
  4 mg lighter: `measured:end_b_mass_kg` 0.0029647 → 0.0029604 kg in the
  `usb_c` golden reference.

- Every physical value of the catalogue now names its source (PRV-33), and
  the values that did not match theirs were corrected. Diameters: `power_c7`
  2 × Ø3.4 → 2 × Ø3.2 mm (H03VVH2-F 2 × 0.75 mm²), `ethernet` Ø6.0 → Ø5.4 mm
  (a Cat.6 patch cable), `hdmi` Ø7.0 → Ø7.3 mm, `speaker_wire` 2 × Ø3.2 →
  2 × Ø3.0 mm, `m12_sensor` Ø5.0 → Ø4.5 mm (PUR 4 × 0.34 mm²), `can_bus`
  Ø5.5 → Ø8.4 mm (a shielded 2 × 2 × 0.25 mm² PUR cable), the ribbon 0.90 →
  0.89 mm thick (3M 3365). Linear densities (g/m): `power_c13` 75–90 → 60–70,
  `power_c7` 30–40 → 32–40, `dc_barrel` 18–28 → 17–22, `usb_c` 30–45 →
  20–30, `usb_micro` 20–35 → 17–23, `usb_a_to_c` 25–40 → 18–26, `ethernet`
  40–55 → 30–36, `hdmi` 60–90 → 60–75, `xlr_mic` 50–70 → 40–56,
  `speaker_wire` 40–55 → 34–40, `m12_sensor` 35–50 → 28–36, `ribbon_idc`
  8–12 → 17–22, `can_bus` 40–55 → 68–80, `servo_lead` 4–7 → 6–7.5,
  `jumper_wire` 2–3 → 2.4–2.9, `battery_lead` 65–80 → 66–80, `balance_lead`
  11–16 → 18–23, `bnc_coax` 36–42 → 36–40, `coiled_handset` 10–15 → 9–12.
  A PVC jacket's friction 0.55 → 0.6 (soft plastic on concrete or wood).
  The moduli are unchanged: they stay estimates.
- A coiled cord records what was drawn for it: `variation:length_m` is the
  coil's length and `variation:linear_density_kg_per_m` the wire's density,
  instead of the axis length with its two leads and the density per metre of
  axis. Those two are now measured: `measured:axis_length_m` and
  `measured:axis_linear_density_kg_per_m`. The cable itself is unchanged; no
  other preset changes (PRV-34).

### Added

- Aspect `clearance` (FIL-10): a receptacle whose opening is published with
  a tolerance draws its own width and height, uniformly over it, and its
  cavity and colliders follow. Today the USB-C extension at the end of a
  `usb_c` cable (`variation:end_b_opening_m`) and the USB-C and USB-A ports
  of `sockets.usdc` (`variation:opening_m`, seed: the scene's).
  `--no-vary clearance` keeps the nominal opening.

- `filaire:clearanceWidth` and `filaire:clearanceHeight` on every mate
  frame: the clearance around the plug's outline, across its width and its
  height (FIL-10).

- `docs/sources.md` and `filaire/sources.py`: the source of every physical
  value (cable datasheets, a friction table, or an estimate with what it
  rests on), the range each source gives, and each connector family's
  published figures and approximate dimensions. `tests/test_sources.py` fails
  on a value with no source, on a value or a drawn cable outside its source's
  range, and when the page is not the module's tables (PRV-33).
- `CONNECTOR_RESTITUTION` in `filaire.catalog`: the connectors' restitution,
  0.2, was a number written in the export code.
- The conformance check (shared by the four generators) checks that an asset
  is whole on its own (contract, section 4): every relationship or connection
  inside an asset root (a material binding, a physics material, a joint's
  bodies) points inside it, in every variant (PRV-40).
- `tests/test_mate_frames.py`: on every connector of every preset, the plug's
  colliders reach its declared insertion depth along +Z of its MateFrame, and
  a receptacle's, on a panel or on a cable, start on the frame's plane
  (contract, section 8).
- The conformance check (`contract.conformance`, `python -m filaire.conformance`,
  shared by the four generators) checks sections 7 and 8 of the contract: a
  variant set and its variants are named in `snake_case`, have a default
  selection, and the set is one section 7 lists, with its meaning, for the
  asset's generator (`contract.VARIANT_SETS`); no variant changes what identifies the asset (its `assetInfo`,
  `primvaria:*` identity and semantic labels), each variant being selected in
  turn on a copy of the stage; a mate frame is an `Xform` named `MateFrame` or
  `MateFrame_<feature>`, inside an asset, in every variant; nothing is written
  under `primvaria:mate:*`, which is not in the contract yet (PRV-35).
- `generate --no-vary ASPECTS` and `--nominal`, as in the other generators of
  the suite: `--no-vary layout,color` keeps those aspects nominal, and an
  unknown aspect is refused. `--no-vary-layout`… still work, and are
  deprecated (PRV-35).
- `docs/variation.md`: how every drawn value follows its preset, and every
  preset's numbers, written from `filaire/declared.py` and the presets;
  `tests/test_distributions.py` draws 1500 cables of every preset and checks
  that each value stays in its range and follows its rule, and builds one
  cable of each preset to check that it records what was drawn (PRV-34).

- Reproducibility references (`tests/test_golden.py`, shared by the four
  generators): four cases of fixed preset, seed and options whose pack tables
  must give the same drawn and measured values on every Python and platform
  of the CI. Contract, section 6, rule 1 (PRV-32).

### Changed

- README and docs images rendered again with the sourced values of PRV-33
  (diameters, densities): the hero, the presets and plugs sheets, the social
  preview, and the coiled-cord and drop GIFs, simulated again.
- The README's hero image shows every preset as a 15 cm cable, in rows of
  three, framed close enough to see the connectors' details, on a plain
  blue-grey floor that dark and white jackets both stand out from
  (`scripts/readme_images.py`).
- `sim-test` places plug and receptacle by their MateFrames for the insertion
  and locking checks, instead of by their bodies' origins, where the frames
  are today: a frame moved in a file is now what the check tests.

## [0.4.0b1] - 2026-11-13 (beta)

### Breaking changes

- The PhysX schemas and attributes (`PhysxRigidBodyAPI`, `PhysxCollisionAPI`)
  are no longer in the files: they are a layer over each file,
  `filaire_<preset>_physx.usda` and `sockets_physx.usda`, to open instead of
  the file in Isaac Sim (`physx.py`, `python -m filaire.physx` to check a
  pack). The files hold plain OpenUSD and `UsdPhysics` only. The Blender
  add-on no longer reads its collision margin from a PhysX attribute (the
  margin is the same, 0.05 mm).

- Pack files (Primvaria contract): `cables.csv` and `summary.json` are replaced by
  `instances.csv` and `manifest.json`, the same in the four generators. The
  table is read back from the OpenUSD files, one row per asset: identity,
  aspects, `variation:<name>` and `measured:<name>` columns, then the
  generator's own; the former summary is the manifest's `summary`.
- The `filaire:preset` attribute of a cable and the custom data
  `filaire:preset`, `filaire:version` and `filaire:seed` on `/World` are gone:
  each cable has them as `primvaria:preset`, `primvaria:version` and
  `primvaria:seed` (Primvaria contract). `filaire:physics` stays.

### Added

- Semantic labels on every asset, with OpenUSD's `UsdSemantics.LabelsAPI`:
  `semantics:labels:class` (`cable` and the preset (`usb_c`)) and
  `semantics:labels:instance` (the asset's name). `instances.csv` gains a
  `classes` column and `manifest.json` lists the classes of the pack; the
  conformance check requires the labels (`contract.write_labels`,
  `contract.labels`).
- `python -m filaire.conformance` refuses engine data in a file (schemas and
  attributes of PhysX or OmniPhysics belong in an engine layer, contract
  section 9) and checks that an engine layer lies over the file it is named
  after and over nothing else. `contract.py` and `tests/test_contract.py`
  stay the same in the four generators.
- `examples/`: four short scripts, each explained by its own comments (a first
  pack and its ground truth, one aspect switched off, reading the file with
  OpenUSD alone, the sag and drop checks in MuJoCo); a test runs each one.
- Checking a preset against a real cable (`docs/physics.md`): the few
  published bending stiffness values, none of them by cable type, and a ruler
  test (Peirce's cantilever test) with the overhang each preset predicts.
- What was measured on each cable is written in the file as
  `primvaria:measured:<name>` (`cable_mass_kg`, `end_a_mass_kg`, `bending_stiffness_y_nm2`, `torsional_stiffness_nm2`, `segments`…).
- `python -m filaire.conformance` also checks every pack it finds: the table must
  say what the files say. `pack.py` and `tests/test_pack.py` are shared by the
  four generators.
- Ground truth of the variation, in the file (Primvaria contract, variation
  model): `primvaria:variation:aspects`, the aspects that were switched on, and
  one `primvaria:variation:<name>` per drawn value (`length_m`, `nominal_length_m`, `layout`, `end_a`, `end_b`, `color`, `youngs_modulus_pa`, `linear_density_kg_per_m`).
  `python -m filaire.conformance` requires the aspects on every asset.
- `CONTRIBUTING.md`, issue templates (bug report, cable or connector request),
  `SECURITY.md` and `CITATION.cff`.
- Primvaria OpenUSD contract, version 0
  ([docs/contract.md](https://github.com/drscaon/primvaria/blob/main/docs/contract.md)):
  every cable and every socket is an asset any tool can find without knowing Filaire: a model of kind `component` with `assetInfo` (name,
  identifier, version) and the attributes `primvaria:contract`,
  `primvaria:generator`, `primvaria:version`, `primvaria:preset` and
  `primvaria:seed`; `/World` is an `assembly`, `/World/Cables` and `/World/Sockets` are groups; a socket is not drawn, so its preset is its connector family and its seed 0.
- `python -m filaire.conformance`: checks files against the contract (stage
  units, model hierarchy, identity). Run in the tests and, in CI, on every
  preset.

### Changed

- The README's table of outputs says that `instances.csv` holds each asset's classes, with a link to the
  semantic labels.
- The README is a third of its former length; the detail moved, unchanged, to
  `docs/`: `usage.md`, `connectors.md`, `openusd.md`, `physics.md`,
  `limits.md`, `development.md`.
  [primvaria.com/filaire](https://primvaria.com/filaire/) is built from these
  files.
- Continuous integration runs the checks shared by the four generators
  (Primvaria's reusable workflow).

### Fixed

- `filaire list` no longer fails on a console that is not UTF-8 (cp1252:
  Windows with redirected output, Git Bash): a sign the console lacks is
  printed as `?`.

## [0.3.0b1] - 2026-11-11 (beta)

### Breaking changes

- Python 3.11 or later (was 3.10): MuJoCo 4 requires it, and Python 3.10 reached
  its end of life in October 2026.
- `usd-core` 26.5 or later (was 24.0): the OpenUSD validators do not load from
  earlier wheels (25.5 lacks the validator libraries, 25.8 and 25.11 the
  UsdPreviewSurface definitions), and 24.x has no `UsdValidation` at all. A CI
  job runs the tests on exactly 26.5.
- MuJoCo 4 (`mujoco>=4.0`, was 3.2) for the `sim` and `dev` extras; MuJoCo 3 is no
  longer supported.
- The ground and physics scene are the same in every Primvaria project (`ground.py`, the
  same file in each): `/World/PhysicsScene`, gravity 9.81 m/s² along −Z; `/World/Ground`,
  a 2 cm box (`UsdGeom.Cube`) whose top is z = 0, covering the content with 0.5 m to
  spare, rendered, no PhysX attributes; `/World/GroundMaterial`, static friction 0.6,
  dynamic 0.5, restitution 0.1. A test checks every generated file against it.
  Filaire's ground had PhysX contact offsets, a 1 m margin and no physics material,
  and the MuJoCo floor copied each cable's friction; it now takes the file's ground.

### Added

- `python -m filaire.validate FILE_OR_FOLDER...`, as in the other Primvaria projects:
  every OpenUSD validator on each file, exit 1 on any error or warning; CI uses it.
  Each file is now also checked as authored (its default variant selections), not
  only once per end variant.
- `bnc_coax` (new Lab category): a stiff 50 Ω coaxial lead (RG-58, Ø4.95 mm) with BNC
  plugs, a BNC jack on an extension, or a stripped end. The `bnc` family is the first
  **bayonet**: the plug goes on with its slots over the jack's two studs, then turns a
  quarter turn to lock.
  - Receptacles of a bayonet keep clear of everything the plug sweeps, pushed in then
    turned (`twist` on a connector spec); the studs are what is left.
  - `locked()` checks it geometrically, and `filaire sim-test` in MuJoCo: pushed in,
    turned 90°, pulled with 5 N, the plug stays in; not turned, it comes out.
  - The locking turn is authored on the mate frames (`filaire:lockTwist`).
- Robotics and drones: four presets and six connector families.
  - `servo_lead`: a 3-wire flat lead (brown, red, orange or black, red, white), with a
    3-way 2.54 mm servo plug keyed by a rib; at the other end a servo extension
    (3 pins), cut or stripped. Fixed receptacle: a servo port, 3 pins in a slot.
  - `jumper_wire`: 2.54 mm jumper pins (`pin_m`) and sockets (`pin_f`), in any
    combination; receptacles: a breadboard contact and a header pin. The new
    `square` keying: square pins go in at every quarter turn.
  - `battery_lead`: a red and black silicone figure-8 lead with a high-current DC plug
    (3.5 mm bullets, 7.2 mm apart, 60 A class), female on the battery side, male on
    an extension or on a board.
  - `balance_lead`: a 5-wire 2.5 mm balance lead (4S), black and four red, into a
    charger or BMS header.
  - `can_bus` (Industrial): a CAN bus cable with D-sub 9 (DE-9, shell size E) female
    plugs, a male one on an extension, or a stripped end.
- Wire colours: flat and figure-8 presets can give each wire its own jacket colour
  (`stripes`): the servo, battery and balance leads, and the ribbon's red wire 1.
- A silicone jacket (friction 0.9), for the battery and balance leads.
- CI job: the OpenUSD validators on every preset, with and without physics
  (was three sample files).

### Changed

- README: Isaac Sim note on the length of the cable articulations (up to 400 links)
  and `--max-segments`.
- README hero image: the cables 30 to 50 cm long, in two columns stacked by their
  own width, seen from closer (about twice the scale), so the connectors show.
- MuJoCo drop check: the same stiff contacts as the multi-cable scene (time constant
  max(4 dt, 2 ms) instead of MuJoCo's 20 ms). The light plugs of thin leads (a few
  grams per metre) rested up to 2 mm into the floor with the default.
- Coiled handset cord: a straight lead of bare wire (4–8 cm, drawn per end) between
  each RJ9 plug and the coil, as on real cords, instead of coil right up to the plug.
  The coil opens out of the lead over about one coil diameter. The leads are physical
  too: their joints bend and twist like the wire and do not stretch, their segments
  weigh and collide as the wire. New `filaire:coil:coiledLength` and
  `filaire:coil:leads`; `filaire:length` is the whole axis (coil and leads).
- Coiled cords: the axial joints are limited (`PhysicsLimitAPI` on `transX`, read by the
  MuJoCo and Blender importers): from 0, as a close-coiled cord does not compress (its
  turns touch), to the stretch at which the wire is straight. Without it a released
  coil sprang back shorter than its rest length.
- `coarsen` (fewer, longer links for fast simulation) puts springs in series joint by
  joint, so a cord whose joints differ (a coil and its leads) keeps its stiffness.
- `scripts/drop_gif.py`: six 1.5 m cables, the coiled cord among them, dropped in very
  different orientations (yaw, pitch and roll) onto a steel swing-set frame instead of
  a bar; obstacles take an optional friction, colour and metalness. New
  `scripts/coil_gif.py`: a coiled cord pulled down and let go. README animations
  re-rendered.
- README images: a factory floor (grey concrete; saw-cut joints and a lane line in the
  animations) instead of the plain sand-coloured floor.
- Connector looks, closer to the real parts (visual only: the colliders, masses and
  insertion results do not change):
  - panel receptacles: a metal shell around the opening of USB-C, USB-A, micro-USB,
    HDMI, RJ45, XLR and M12 ports, in a dark device face instead of a white block;
    power inlets (C14, C8) in black with metal pins; DC jacks black with a metal
    centre pin; the IDC header black with gold pins; wall sockets stay white;
  - the tongue or insert inside a receptacle has its own colour;
  - the 3.5 mm plug gets its two black insulator rings (tip, ring, sleeve);
  - RJ45 and RJ9 plugs are clear plastic (`opacity` and `ior` in UsdPreviewSurface);
  - bare metal pins on the CEE 7/7 and Europlug plugs, the Europlug's with their
    insulated sleeves; metal pins in the male XLR and M12 receptacles; XLR and M12
    plugs show a black insert inside their metal rim or coupling nut.
- Blender import: faces whose authored normals are all their own face normal are
  marked flat (`filaire.blender.physics.flat_where_flat`, run by the add-on hook and
  `scripts/render_blender.py`). Blender imported them smooth, and Cycles shaded the large
  flat faces next to curved ones with dark streaks (white wall sockets looked dirty).
- README images re-rendered with these looks (hero, presets, every connector
  family, social preview), and a paragraph on the looks in the Connectors
  section. `scripts/render_blender.py` renders clear plastic as transmission
  (Blender reads UsdPreviewSurface opacity as alpha).
- README: the same header as the other Primvaria projects (PyPI and suite
  badges), an Engines table matching the suite's engine matrix, and links to
  primvaria.com.

## [0.2.0b1] - 2026-10-29 (beta)

First release on PyPI; USB Micro-B and DC barrel connectors, a Blender add-on.

### Added
- Connector families: USB Micro-B (`usb_micro`, keyed by its trapezoid) and
  coaxial DC barrels 5.5 × 2.1, 5.5 × 2.5 and 4.0 × 1.7 mm (`dc5521`,
  `dc5525`, `dc4017`), each with a jack on a cable and a fixed jack: 17
  families, 28 end variants.
- Presets `dc_barrel` (DC power cord, figure-8) and `usb_micro` (USB-A to
  Micro-B): 14 presets.
- `fits(plug, angle, socket=other)` tests a plug against another family's
  receptacle: a 5.5 × 2.5 mm plug goes loosely onto a 5.5 × 2.1 mm jack, the
  reverse is stopped by the thicker pin.
- A Blender add-on (`filaire blender-addon`, a Blender 4.4+ extension, also
  attached to releases), adapted from Quincaillerie's: on File > Import >
  USD, every segment and connector becomes a rigid body (origin at its
  centre of mass, compound of the USD capsules, boxes and convex hulls,
  mass, friction, margins), the cable joints Generic Spring constraints with
  the drives' stiffness and damping, the connectors' fixed joints Fixed
  constraints; 4000 substeps per second.
- `filaire blender-test`: the drop check in Blender through the add-on, and
  `--mode naive` (rigid bodies set by hand) for comparison. CI runs it on
  every preset.
- `--no-physics` (`write_outputs(…, physics=False)`): visual assets only, one
  mesh per cable, no rigid bodies, colliders, joints, physics scene or ground.
- `filaire.validate.validate()`: every OpenUSD `UsdValidation` validator on
  each end variant; the tests and the CI smoke test require no issue.
- README: hero with every preset, a labelled sheet of the 14 presets and of
  the 17 connector families (each plug on its cable in front of its
  receptacle), on a warm wood surface where grey cables stand out.

### Changed
- Released on PyPI (`pip install filaire`) by the release workflow, through Trusted Publishing.
- README images and links use absolute URLs, so that they show on PyPI; the README links to
  Primvaria, the suite the project belongs to.
- One visual mesh per rigid body: a connector's shell, body, cores and
  copper are one mesh with a GeomSubset per material (displayColor per
  face), so every DCC imports one object per body. Crease normals on every
  visual mesh (smooth tubes, sharp connector edges).
- Every body carries `PhysxRigidBodyAPI` (solver iterations) and every
  collider `PhysxCollisionAPI` (contact and rest offsets), for Isaac Sim.
- The ground is a collision box whose top face is at z = 0, instead of a
  plane mesh.

### Fixed
- On tight curves the rigid segments were as long as the arc they stand
  for, so neighbouring segments overlapped by up to 0.4 mm at their joint;
  each segment now spans the chord between its two joints (its mass is
  still that of the arc).

## [0.1.0b1] - 2026-10-24 (beta)

First beta.

### Added
- 12 cable presets in 5 categories: Power (`power_c13`, figure-8
  `power_c7`), Data (`usb_c`, `usb_a_to_c`, `ethernet`, `hdmi`), Audio
  (`audio_jack`, `xlr_mic`, `speaker_wire`), Industrial (`m12_sensor`,
  `ribbon_idc`), Telephone (`coiled_handset`).
- 13 connector families (USB-C, USB-A, HDMI A, RJ45, RJ9, 3.5 mm jack, IEC
  C13/C14, IEC C7/C8, CEE 7/7, Europlug, XLR3, M12 A-coded, IDC 2 × 5) with
  male and female contacts kept apart from the geometric role. Receptacles
  (fixed, and on a cable for extensions and couplers) are derived from the
  plugs layer by layer with a clearance; the keying is found from the
  geometry. Published dimensions where found, the others marked approximate.
- End variants: any connector plug or receptacle on a cable, a clean cut or
  a stripped end with the cores out, on each end independently
  (`--end-a`, `--end-b`; 21 variants), all authored as OpenUSD variant sets.
- Cables 1 m long by default (`--length`, or `--length preset` for retail
  lengths), lying straight, slack or coiled on the floor (`--layout`);
  `--color`, `--modulus`, `--max-segments`; one random stream per aspect
  (`--no-vary-…`).
- Rod model: rigid segments with twist and bending springs from the
  cross-section (round, figure-8, flat ribbon) and an effective modulus;
  coiled cords as helical springs with an axial spring. Exported with
  UsdPhysics: rigid bodies, D6 joints with drives, articulation root,
  convex collision parts, mate frames; fixed receptacles in `sockets.usdc`.
  `cables.csv` and `summary.json`.
- MuJoCo checks (`filaire sim-test`), read from the OpenUSD files: drop,
  cantilever sag against beam theory, coil extension against spring theory,
  insertion and keying at 0°, 90° and 180°.
- `filaire preview` (top view) and `filaire connectors` (plug faces and
  receptacles), with matplotlib; `filaire list`, `filaire ends`.
- Several cables in one MuJoCo scene, colliding with each other and with
  static obstacles (`filaire.sim.mujoco_model.scene_model`).
- README with results, Blender renders, an animated drop of five cables onto
  a bar (simulated in MuJoCo), logo and GitHub social preview
  (`docs/images/social_preview.png`); scripts to rebuild the images.
- Test suite (pytest), lint and format (ruff), continuous integration with
  the MuJoCo checks of every preset, release workflow, Dependabot, GitHub
  Flow `pre-push` hook.
