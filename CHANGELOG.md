# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
