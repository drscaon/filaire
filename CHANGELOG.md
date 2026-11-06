# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

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
