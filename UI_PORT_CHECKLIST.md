# Torque UI Port Checklist

Goal: port the old Torque exporter UI into a modern Blender 4.x Scene panel while keeping the controls recognizable and the data source aligned with the current export state.

## Panel Layout

- [x] Properties editor scene panel scaffold exists.
- [x] Single Scene panel layout is the active UI.
- [x] The classic/compact split has been removed from the visible UI.
- [ ] Final decision on whether a separate popup/dialog mode is still needed.

## Export Section

- [x] Export path and basename controls.
- [x] DTS version control.
- [x] Write shape script toggle.
- [x] Export scale control.
- [x] Primitive type control.
- [x] Export action wiring and config sync.
- [x] Reset restores the last saved UI/config state via `LoadedState`.
- [ ] Final file browser behavior.

## Sequence Section

- [x] Sequence selector.
- [x] Sequence list appears as a readable single-line list.
- [x] Sequence list selection syncs the controls.
- [x] DSQ toggle is exposed for sequences.
- [x] Common sequence settings.
- [x] Action sequence settings.
- [x] IFL sequence settings.
- [x] Visibility sequence settings.
- [x] Visibility track list / IPO fields.
- [x] Sequence section includes a short explanatory note.
- [ ] Visibility track editor parity with the legacy GUI.
- [ ] Sequence list add/remove/reorder controls.

## Armature Section

- [x] Armature summary / banned-bone guidance.
- [x] Banned bones list editor with add/remove and selected-pattern editing.
- [x] Wildcard patterns are accepted in the banned-bones list.
- [ ] Bone grid / per-bone toggle parity with the legacy GUI.
- [ ] Armature ordering / traversal tools parity.

## Materials Section

- [x] Material selector.
- [x] Material list appears as a readable single-line list.
- [x] Material list selection syncs the controls.
- [x] Common material flags.
- [x] Texture / map fields.
- [x] Reflectance and detail scale controls.
- [x] Per-material list behavior parity with the legacy GUI.

## General Section

- [x] Max strip size.
- [x] Cluster depth.
- [x] Always write depth.
- [x] Collapse root transform.
- [x] Billboard settings.
- [x] TSE material toggle.

## About Section

- [x] About block / status text.
- [ ] Legacy help text parity.
