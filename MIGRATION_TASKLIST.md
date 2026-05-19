# Torque Blender Exporter Modernization Task List

Canonical backlog for updating the legacy Torque `.dts` Blender exporter to modern Blender APIs.
Migration rules and sequencing are documented in [MIGRATION_PLAN.md](/Users/jamesu/Desktop/torqueexporter/MIGRATION_PLAN.md).

## 0. Scope And Baseline

- [ ] Confirm the target Blender version range to support, then document it at the top of the exporter.
- [ ] Run a quick behavioral audit of the legacy add-on so we preserve current `.dts` output expectations.
- [ ] Identify any Torque-side format assumptions that must remain unchanged during the Blender API migration.
- [ ] Preserve the old UI where possible instead of replacing it with a brand-new layout.
- [ ] Define best-guess defaults for missing config values so export can proceed without forcing complete setup.

## 1. Legacy API Inventory

Current working inventory: [API_USAGE_INVENTORY.md](/Users/jamesu/Desktop/torqueexporter/API_USAGE_INVENTORY.md)

- [ ] Catalog every old Blender API usage in `torqueplugin/Dts_Blender.py`.
- [ ] Catalog every old Blender API usage in `torqueplugin/DtsShape_Blender.py`.
- [ ] Catalog every old Blender API usage in `torqueplugin/DtsMesh_Blender.py`.
- [ ] Catalog every old Blender API usage in `torqueplugin/DtsPoseUtil.py`.
- [ ] Catalog every old Blender API usage in `torqueplugin/Common_Gui.py`.
- [ ] Replace `#!BPY`, `import Blender`, and `from Blender import ...` entry points with modern add-on structure.
- [ ] Remove reliance on `Registry`, `Text`, `Scene.GetCurrent()`, `Object.Get()`, `Object.GetSelected()`, `NMesh`, `Ipo`, and other removed APIs.

## 2. Add-On Structure

- [ ] Convert the exporter into a standard `bpy` add-on with `bl_info`.
- [ ] Define operators for export actions instead of legacy script menu hooks.
- [ ] Register panels, properties, and menus in a modern Blender-compatible way.
- [ ] Add clean `register()` and `unregister()` entry points.
- [ ] Ensure the exporter can be enabled/disabled without requiring manual script execution.

## 3. Preferences And Configuration

- [ ] Replace registry-based preferences in `torqueplugin/Dts_Blender.py` with `bpy.props` and add-on preferences.
- [ ] Replace text-buffer persistence for config with a modern storage approach.
- [ ] Preserve export defaults such as basename, output path, detail settings, and billboard options.
- [ ] Infer sensible defaults from the `.blend` file, scene, and selection when stored config values are missing.
- [ ] Rework any UI state that currently depends on global mutable module variables.

## 4. Scene, Object, And Mesh Access

- [x] Centralize export scene/object lookup behind helper functions.
- [x] Update object iteration to use `bpy.context.scene.objects` or evaluated depsgraph access where needed.
- [x] Update selection handling to use `bpy.context.selected_objects`.
- [x] Replace `getData()` calls with modern `obj.data` access.
- [x] Replace parent and bone-parent handling with the current object/armature relationship APIs.
- [ ] Update mesh access to use `bpy.types.Mesh`, evaluated meshes, and `bmesh` where required.
- [ ] Preserve collision mesh, bounds mesh, and export filtering behavior.

Status: export-path scene, object, action, and material lookups are now routed through helper wrappers in `Dts_Blender.py`, `DtsPoseUtil.py`, `DtsShape_Blender.py`, and `Torque_Util.py`. The active export path now also uses modern object, parent, and data access helpers instead of direct `getType()` / `getData()` calls.

## 5. Materials, UVs, And Shading

- [ ] Replace legacy material and texture access with modern Blender material slots and image nodes.
- [ ] Rebuild face/image/material grouping logic in `torqueplugin/DtsMesh_Blender.py`.
- [ ] Update UV extraction paths for current mesh UV APIs.
- [ ] Verify double-sided handling and material assignment still match the DTS exporter’s expectations.

## 6. Armatures, Bones, And Animation

- [ ] Replace legacy pose access in `torqueplugin/DtsShape_Blender.py` and `torqueplugin/DtsPoseUtil.py` with current pose-bone APIs.
- [ ] Update bone lookup, rest pose, and pose evaluation logic for modern armatures.
- [x] Replace IPO/action-based animation handling with current action and FCurve APIs.
- [ ] Rebuild curve discovery logic that currently depends on IPO curve names like `LocX`, `QuatX`, and `SizeX`.
- [ ] Validate frame sampling, sequence generation, and node animation export against known good files.

Status: the active sequence export and visibility-validation paths now use helper-based action-channel and IPO access. The exporter preserves legacy curve semantics for imported old scenes, but the core action handling is now routed through the modern helper layer.

## 7. Geometry And Modifier Evaluation

- [ ] Update modifier handling for evaluated meshes in modern Blender.
- [ ] Replace multiresolution and mesh update code paths that depend on removed APIs.
- [ ] Confirm triangulation, strip generation, and primitive batching still behave correctly.
- [ ] Recheck vertex weights, skinning, and root bone assignment against modern armature deformation behavior.

## 8. UI And Export Workflow

- [ ] Modernize only the UI portions that cannot survive the Blender API migration.
- [ ] Keep existing exporter options available where they still make sense.
- [ ] Simplify or remove obsolete options that were specific to the old Blender API.
- [ ] Make error reporting and warnings visible in Blender’s UI and console.
- [x] Temporarily disable the legacy GUI layer so export code can be migrated in isolation.

## 9. Code Cleanup And Compatibility

- [x] Replace Python 2 syntax with Python 3 syntax throughout the add-on.
- [ ] Remove deprecated language patterns such as old-style `print`, `filter` assumptions, and legacy exception handling.
- [ ] Standardize imports and reduce reliance on globals where practical.
- [ ] Add type-safe helper functions for path handling, object filtering, and bone lookup if useful.

Status: a compatibility helper module now handles scene/object/material/action access for the export-focused code paths, reducing direct legacy API usage without widening the UI scope.
Status: the legacy `DTSPython` import chain now loads under Python 3 via package-relative imports and the `Blender` shim, so the main exporter modules import cleanly in the current workspace.
Status: preference loading now falls back to inferred defaults when registry/text configuration is absent, which matches the bounded "best guess" export behavior.

## 10. Verification

- [ ] Export a simple static mesh and verify the generated `.dts` loads in the target Torque toolchain.
- [ ] Export a skinned mesh and verify bone weights, animation, and rest pose behavior.
- [ ] Export collision and LOS meshes and confirm detail levels are preserved.
- [ ] Export a shape with materials, UVs, and double-sided faces and compare output against the legacy exporter.
- [ ] Test on at least one modern Blender release in the chosen support range.

## 11. Packaging And Documentation

- [ ] Update installation instructions for modern Blender add-on installation.
- [ ] Document supported Blender versions and any behavioral differences from the legacy exporter.
- [ ] Document the fallback/default behavior for missing configuration values.
- [ ] Document the decision to preserve the legacy UI where feasible.
- [ ] Document known limitations, especially where Torque DTS behavior is preserved over Blender-native conventions.
- [ ] Add a short migration note explaining that this file is the active task tracker for the rewrite.

## Suggested Execution Order

1. Establish target Blender version and baseline behavior.
2. Replace add-on scaffolding and preferences.
3. Port object, mesh, material, and armature access.
4. Port animation and curve handling.
5. Clean up Python 3 compatibility and modern Blender registration.
6. Verify exports against known scenes.
7. Update docs and remove dead legacy paths.
