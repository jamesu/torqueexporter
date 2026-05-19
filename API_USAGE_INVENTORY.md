# Current API Usage Inventory

Initial audit of legacy APIs used by the Torque Blender exporter. This file is the working reference for the Blender API migration and should be updated as each subsystem is modernized.

## Status

- Python 3 syntax compatibility: complete enough for `python3 -m compileall torqueplugin`
- Blender API migration: not started
- This inventory: first-pass audit only, focused on high-impact legacy calls and patterns
- UI migration policy: preserve the legacy UI where possible
- Config policy: infer safe defaults when stored values are missing
- Current implementation phase: legacy GUI is temporarily bypassed so export code can be worked on in isolation
- Export-path lookup state: scene, object, action, and material access now flow through helper wrappers in `Dts_Blender.py`, `DtsPoseUtil.py`, `DtsShape_Blender.py`, and `Torque_Util.py`; most remaining direct legacy calls are in dormant GUI code or compatibility branches

## High-Impact Legacy APIs

### Blender module bootstrap

- `import Blender`
- `from Blender import ...`
- `#!BPY`

Used throughout the add-on entrypoints and helper modules.

### Preferences and persistence

- `Registry.GetKey`
- `Registry.SetKey`
- `Text.Get`
- `Text.New`
- `Text.clear()`
- `Text.asLines()`

These are concentrated in `torqueplugin/Dts_Blender.py` and are part of the exporter configuration path.

### Scene, object, and selection access

- `Blender.Get("filename")`
- `Blender.Get("version")`
- `Blender.Object.Get()`
- `Blender.Object.GetSelected()`
- `Blender.Object.Get(name)`
- `Blender.Scene.GetCurrent()`
- `Scene.GetCurrent().getRenderingContext()`
- `Object.getData()`
- `Object.getType()`
- `Object.getParent()`
- `Object.getPose()`

These are the main APIs that need `bpy.context`, `bpy.types.Object`, evaluated depsgraph access, and modern scene handling.

### Mesh and geometry APIs

- `from Blender import NMesh`
- `NMesh.Modes.TWOSIDED`
- `NMesh.FaceModes.TWOSIDE`
- `mesh_data.update()`
- `face.image`
- `face.materialIndex`
- `face.mode`
- `msh.materials`
- `msh.faces`

These are especially important in `torqueplugin/DtsMesh_Blender.py` and `torqueplugin/DtsShape_Blender.py`.

### Armature and animation APIs

- `from Blender import Armature`
- `Blender.Armature.NLA.GetActions()`
- `arm.getData()`
- `arm.getPose()`
- `pose.bones[...]`
- IPO curve access such as `getIpo()`, `getCurves()`, `getFrameNumbers()`
- `Blender.Ipo.PO_SCALEX`, `Blender.Ipo.PO_SCALEY`, `Blender.Ipo.PO_SCALEZ`
- `bIpo.curveConsts[...]`
- `bIpo[...]`

These are the core animation and bone-related migration points.

### UI APIs

- `from Blender import Draw`
- `from Blender import BGL`
- `from Blender import Window`
- `from Blender import Image`
- `from Blender.Window import Theme`

These are used heavily in `torqueplugin/Common_Gui.py` and will likely be replaced or removed depending on how much legacy UI is preserved.

## File-By-File Notes

### `torqueplugin/Dts_Blender.py`

Highest-density legacy file.

- Uses `import Blender`, `Registry`, `Text`, `Object.Get`, `Object.GetSelected`, `Scene.GetCurrent`, `Blender.Get`.
- Uses `getData()`, `getPose()`, `getType()`, `getParent()` throughout export and GUI paths.
- Uses `Armature.NLA.GetActions()` and IPO-based animation helpers.
- Contains many old-style sequence/material list operations that now work under Python 3 but still depend on Blender 2.x concepts.

### `torqueplugin/DtsShape_Blender.py`

Shape export core with legacy armature and IPO handling.

- Uses `import Blender` and `from Blender import NMesh, Armature, Scene, Object, Material, Texture`.
- Uses `BuildCurveMap`, `getCurves()`, `getFrameNumbers()`.
- Uses `Blender.Object.Get()`, `Blender.Scene.GetCurrent()`, `arm.getPose()`, `o.getData()`.
- Uses `NMesh`-style face and mesh access.

### `torqueplugin/DtsMesh_Blender.py`

Mesh conversion path.

- Uses `import Blender` and `from Blender import NMesh`.
- Uses `msh.mode`, `NMesh.Modes.TWOSIDED`, `NMesh.FaceModes.TWOSIDE`.
- Uses face/image/material access patterns that need a modern mesh/UV/material rewrite.
Status: the active export path now snapshots modern evaluated `bpy.types.Mesh` data into a legacy-style proxy, including faces, UVs, materials, and vertex-group weights, so the mesh exporter can operate without the removed `getFromObject()` path.

### `torqueplugin/DtsPoseUtil.py`

Pose and bone math helpers.

- Uses `import Blender` and `from Blender import Mathutils as bMath`.
- Uses `Blender.Object.Get()`, `Blender.Scene.GetCurrent()`, `arm.getData()`, `arm.getPose()`.
- Contains helper code that expects the old pose data model.

### `torqueplugin/Common_Gui.py`

Legacy UI layer.

- Uses `import Blender`, `Draw`, `BGL`, `Window`, `Image`, and `Theme`.
- Contains many print/debug traces, but the more important issue is the old custom UI framework itself.

### `torqueplugin/DTSPython/Torque_Util.py`

Mixed utility layer with remaining Blender integration.

- Uses `import Blender`.
- Uses `Blender.Armature.NLA.GetActions()`.
- Uses `Blender.Object.Get(track['IPOObject'])`.
- Uses `getIpo()`, IPO curve constants, and curve accessors.
Status: this module now resolves through the Blender compatibility wrapper in the modern export path, so its legacy calls remain available while the shim absorbs the API translation.

### `torqueplugin/DTSPython/Dts_Stream.py`

- No Blender API dependency in the current audit slice.
- Python 3 indentation issues were fixed during compilation work.

### `torqueplugin/DTSPython/Torque_Math.py`, `Dts_Mesh.py`, `Dts_Shape.py`

- These are mostly Torque-side math and data structures.
- They no longer block Python 3 syntax compilation.
- They still contain debug prints and some legacy style, but they are not the primary Blender API migration surface.

## Audit Summary

The migration is dominated by three areas:

1. Replacing the legacy `Blender` module and `Registry`/`Text` persistence model.
2. Rebuilding object, mesh, and armature access around `bpy` and evaluated data.
3. Replacing IPO/NLA-era animation assumptions with modern actions and FCurves.

The codebase already compiles under Python 3, so the next meaningful step is the Blender API port rather than further syntax cleanup.

The migration should keep legacy UI structure intact wherever feasible and use inferred defaults to avoid forcing users through a full reconfiguration when a value is absent.
Status: the package import chain now resolves under Python 3, including the legacy DTSPython modules and the top-level Blender shim, so the exporter modules load cleanly in the current workspace.
Status: preference bootstrap now falls back to inferred defaults instead of hard-failing when Registry/text configuration is unavailable.
Status: the active export path now uses modern object, parent, and data access helpers for mesh, armature, and sequence import flows, reducing direct `getType()`/`getData()` usage in the main code path.
Status: animation and visibility code now route through explicit helper accessors for action channels and IPO lookup. Legacy curve names are still preserved in the compatibility layer so old scenes continue to evaluate the same way after import into modern Blender.
Status: mesh export now snapshots evaluated Blender meshes into a read-only compatibility proxy, replacing the removed temporary-mesh and `getFromObject()` workflow for modifier-aware exports.
