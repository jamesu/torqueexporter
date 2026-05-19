# Torque Blender Exporter Installation

This repository is still in migration. There are two practical ways to use it today:

1. Temporary developer setup for working on the exporter in-place.
2. Legacy-script installation for Blender builds that still support the old `#!BPY` exporter model.

The modern `bpy` add-on packaging work is still tracked in `MIGRATION_TASKLIST.md`.

## 1. Temporary Developer Setup

Use this when you want to edit the exporter and test changes without copying files around.

This is the easiest way to work on the exporter right now. You keep the repo checked out in one place, point Blender at the `torqueplugin` directory, and run the script from inside Blender while you edit files on disk.

### 1. Keep the repository in a fixed location

Keep the repository checked out somewhere stable, for example:

```text
/home/user/torqueexporter
```

Do not move it around while Blender is running. The exporter imports modules by filename, so a stable path makes debugging much easier.

### 2. Add `torqueplugin` to Blender's Python path

The exporter modules expect the `torqueplugin` directory itself to be importable. The simplest way to do that is to add the directory to `PYTHONPATH` before Blender starts.

Example:

```bash
export PYTHONPATH="/home/user/torqueexporter/torqueplugin:$PYTHONPATH"
blender
```

If you start Blender from a desktop icon instead of a terminal, use one of these options instead:

1. Launch Blender from a terminal after setting `PYTHONPATH`.
2. Start Blender with a small wrapper script that exports `PYTHONPATH` first.
3. Use a Blender startup script that inserts `/home/user/torqueexporter/torqueplugin` into `sys.path`.

### 3. Verify the path inside Blender

Open Blender, switch to the Scripting workspace, and run this in the Python console or a text block:

```python
import sys
sys.path.insert(0, "/home/user/torqueexporter/torqueplugin")

import Dts_Blender
print(Dts_Blender.Version)
```

If that prints a version string, the exporter code is visible to Blender and you can edit files in the checkout while re-running the script.

### 4. Run the exporter from the checked-out script

Open `torqueplugin/Dts_Blender.py` in Blender's text editor and run it from there if you want the legacy entrypoint behavior.

That gives you the closest thing to the old workflow while still letting you modify the files on disk in your editor.

### Notes

- This is the best option for active development.
- It lets you test the current compatibility shim without copying files into Blender's installation directory.
- If Blender cannot import `Dts_Blender`, check that `torqueplugin` itself is on `sys.path`, not just the repository root.
- If you move the repository, update any local path you added to Blender's Python search path.
- The script still uses the legacy entrypoint layout, so this is a development workflow, not the final add-on install path.

## 2. Legacy Script Installation

Use this if you want to install the exporter into a Blender build that still supports the old exporter script entrypoint.

### Install steps

1. Copy the `torqueplugin` directory into Blender’s legacy scripts location.
2. Ensure the directory keeps the same relative layout so `Dts_Blender.py` can import its sibling modules.
3. Restart Blender.
4. Look for the Torque `.dts` exporter entry in the legacy export menu.

### Notes

- This matches the current script-based exporter layout.
- It is only suitable for Blender versions that still understand the old script registration model.
- Modern Blender add-on installation is not yet the final delivery path for this repository.

## 3. What To Expect Right Now

- The exporter can be developed in-place from this repository.
- The current codebase still uses compatibility helpers and legacy-script packaging.
- The proper `bl_info` / `register()` / `unregister()` add-on path remains a tracked migration task.
