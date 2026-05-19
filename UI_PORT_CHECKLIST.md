# Torque UI Port Checklist

Goal: port the old Torque exporter UI into a modern Blender 4.x panel while keeping the legacy layout as the default display mode for now.

## Display Modes

- [x] Properties editor scene panel scaffold exists.
- [x] Classic mode is the default display.
- [x] Compact mode exists for future rearrangement.
- [ ] Final decision on whether a separate popup/dialog mode is still needed.

## Export Section

- [x] Export path and basename controls.
- [x] DTS version control.
- [x] Write shape script toggle.
- [x] Export scale control.
- [x] Primitive type control.
- [x] Export action wiring and config sync.
- [ ] Final file browser behavior.

## Sequence Section

- [x] Sequence selector.
- [x] Common sequence settings.
- [x] Action sequence settings.
- [x] IFL sequence settings.
- [x] Visibility sequence settings.
- [ ] Visibility track editor parity with the legacy GUI.
- [ ] Sequence list add/remove/reorder controls.

## Armature Section

- [x] Armature selector / summary.
- [x] Banned bones text entry.
- [ ] Bone grid / per-bone toggle parity with the legacy GUI.
- [ ] Armature ordering / traversal tools parity.

## Materials Section

- [x] Material selector.
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
