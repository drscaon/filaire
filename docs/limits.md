# Limits and roadmap

Everything Filaire does not do or has not verified, stated plainly, and what comes next.

Part of the [Filaire](../README.md) documentation.

## Limits

- **Not calibrated.** Moduli and densities are orders of magnitude; no
  cable's `E·I` was measured. The sag check proves the export is consistent
  with the model, not that the model matches a real cable. See
  [Checking a preset against a real cable](physics.md#checking-a-preset-against-a-real-cable).
- **Approximate connectors.** See [Connectors](connectors.md#connectors): simplified
  outlines, no moving latches, threads or contacts; several dimensions not
  from a source.
- **Elastic, straight rest shape.** No plastic set (a real cable keeps its
  coils), no initial tension in coiled cords, no knots.
- **Isaac Sim not tested here.** The files follow the standard `UsdPhysics`
  schemas (rigid bodies, D6 joints with drives, articulation root, convex
  hulls), with the PhysX settings in a layer over each file; they are checked in MuJoCo and Blender
  but have not been loaded in Isaac Sim / PhysX (no NVIDIA GPU), where
  drive units and articulation behaviour may need adjusting. Each cable is
  one articulation of up to 400 links (213 bodies for a 1 m servo lead), far
  longer than a robot's. Isaac Sim once failed on articulations of more
  than 128 bodies, a bug
  [fixed in late 2023](https://forums.developer.nvidia.com/t/articulation-for-robot-with-large-number-of-meshes/272815);
  if a long cable is slow or unstable there, `--max-segments` lowers the
  count.
- **Rest shape differs in Blender.** See [Blender](physics.md#blender): Bullet's
  springs rest in the first frame's pose, the generated one.
- **Visual per segment.** Each segment carries its piece of tube, so a
  simulated cable shows small creases at the joints when it bends.

## Roadmap

1. Calibration against measured bending stiffness (three-point bending or
   cantilever tests) for a few real cables per preset.
2. Plastic set and pre-coiled rest shapes; tied bundles and hanks.
3. A PhysX test in Isaac Sim, and MJCF export with MuJoCo's cable plugin.
4. More connectors (Schuko and French sockets with their earth contacts,
   D-sub with its screws, DisplayPort, M8) and snap-fit latches.
5. Insertion tasks: forces, misalignment tolerances, success labels.
