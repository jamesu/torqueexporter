# Torque Blender Exporter Migration Plan

This plan governs the Blender API port for the legacy Torque `.dts` exporter.

## Migration Rules

- Preserve the existing UI where it still maps cleanly onto modern Blender.
- Prefer additive changes over rewrites when behavior is already working.
- If a config value is missing, infer a safe default from the current file, scene, or exporter context.
- Keep Torque DTS output behavior stable unless a change is required by Blender API removal.
- Treat the Python 3 compiler pass as a baseline, not as proof of Blender runtime compatibility.

## Defaulting Strategy

When a stored configuration entry is unavailable:

- Use the current `.blend` file path for export basename and output location when possible.
- Fall back to the active scene or selection context for UI defaults.
- Preserve legacy exporter defaults for shape settings such as detail levels, billboard options, and material handling.
- Log when a default was inferred so the user can see what happened without being forced to configure everything up front.

## UI Strategy

- Keep the current exporter layout and behavior where the Blender API still supports it.
- Replace only the parts that rely on removed Blender 2.x UI APIs.
- Prefer thin compatibility shims before introducing a brand-new panel layout.
- Retain existing exporter options unless they are no longer meaningful in modern Blender.

## Phases

### Phase 1: Inventory And Compatibility Boundaries

- Maintain the API usage inventory in [API_USAGE_INVENTORY.md](/Users/jamesu/Desktop/torqueexporter/API_USAGE_INVENTORY.md).
- Confirm which legacy UI pieces can be preserved directly.
- Document the fallback/default rules for missing config values.

### Phase 2: Add-On Skeleton

- Convert the exporter entrypoint to a modern `bpy` add-on.
- Keep old exporter options exposed where possible.
- Implement preference loading with inferred defaults.

### Phase 3: Core Data Access

- Port scene, object, mesh, and armature access to modern Blender APIs.
- Preserve the exporter’s filtering rules, selection behavior, and output structure.

### Phase 4: Animation And Sequences

- Port IPO/action handling to FCurves and current action APIs.
- Keep the existing sequence model and naming conventions if possible.

### Phase 5: Verification And Refinement

- Verify `.dts` output on representative scenes.
- Revisit any UI elements that need compromise after the runtime migration.
- Document behavior changes only where they are unavoidable.

