"""Compatibility helpers for legacy Blender exporter code.

The helpers prefer modern bpy APIs when available, but fall back to the
legacy Blender module so the code still compiles outside Blender.
"""

try:
	import bpy
except ImportError:  # pragma: no cover - unavailable outside Blender
	bpy = None

try:
	import Blender
except ImportError:  # pragma: no cover - unavailable outside old Blender
	Blender = None


def is_modern():
	return bpy is not None


def get_current_scene():
	if bpy is not None:
		return bpy.context.scene
	if Blender is not None:
		return Blender.Scene.GetCurrent()
	return None


def get_scene_objects(scene=None):
	if bpy is not None:
		if scene is None:
			scene = bpy.context.scene
		return list(scene.objects) if scene is not None else []
	if Blender is not None:
		return list(Blender.Object.Get())
	return []


def get_selected_objects():
	if bpy is not None:
		return list(bpy.context.selected_objects)
	if Blender is not None:
		selected = Blender.Object.GetSelected()
		if selected is None:
			return []
		try:
			return list(selected)
		except TypeError:
			return [selected]
	return []


def get_object(name, scene=None):
	if bpy is not None:
		if scene is not None:
			for obj in get_scene_objects(scene):
				if obj.name == name:
					return obj
		return bpy.data.objects.get(name)
	if Blender is not None:
		try:
			return Blender.Object.Get(name)
		except Exception:
			return None
	return None


def get_material(name):
	if bpy is not None:
		return bpy.data.materials.get(name)
	if Blender is not None:
		try:
			return Blender.Material.Get(name)
		except Exception:
			return None
	return None


def get_materials():
	if bpy is not None:
		return list(bpy.data.materials)
	if Blender is not None:
		return list(Blender.Material.Get())
	return []


def get_text(name):
	if bpy is not None:
		return bpy.data.texts.get(name)
	if Blender is not None:
		try:
			return Blender.Text.Get(name)
		except Exception:
			return None
	return None


def get_actions():
	if bpy is not None:
		return {action.name: action for action in bpy.data.actions}
	if Blender is not None:
		return Blender.Armature.NLA.GetActions()
	return {}


def set_frame(scene, frame):
	if bpy is not None and scene is not None:
		scene.frame_set(frame)
		return
	if Blender is not None:
		Blender.Scene.GetCurrent().getRenderingContext().currentFrame(frame)


def redraw_all():
	if bpy is not None:
		try:
			for window in bpy.context.window_manager.windows:
				for area in window.screen.areas:
					area.tag_redraw()
		except Exception:
			pass
		return
	if Blender is not None:
		try:
			Blender.Window.RedrawAll()
		except Exception:
			pass


def get_fps(scene=None):
	if bpy is not None:
		if scene is None:
			scene = bpy.context.scene
		if scene is None:
			return 25.0
		rate = getattr(scene.render.fps_base, "__float__", None)
		try:
			return float(scene.render.fps) / float(scene.render.fps_base)
		except Exception:
			return float(scene.render.fps)
	if Blender is not None:
		if scene is None:
			scene = Blender.Scene.GetCurrent()
		return float(scene.getRenderingContext().framesPerSec())
	return 25.0
