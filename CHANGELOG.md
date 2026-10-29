# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
