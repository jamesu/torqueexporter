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


def get_object_name(obj):
	return getattr(obj, "name", None)


def get_object_type(obj):
	return getattr(obj, "type", None)


def get_object_data(obj, *args):
	if hasattr(obj, "data"):
		return obj.data
	if hasattr(obj, "getData"):
		return obj.getData(*args)
	return None


def get_object_parent(obj):
	if hasattr(obj, "parent"):
		return obj.parent
	if hasattr(obj, "getParent"):
		return obj.getParent()
	return None


def get_object_pose(obj):
	if hasattr(obj, "pose"):
		return obj.pose
	if hasattr(obj, "getPose"):
		return obj.getPose()
	return None


def get_object_matrix(obj):
	if hasattr(obj, "matrix_world"):
		return obj.matrix_world
	if hasattr(obj, "getMatrix"):
		return obj.getMatrix("worldspace")
	return None


def get_object_scale(obj):
	if hasattr(obj, "scale"):
		return obj.scale
	if hasattr(obj, "getSize"):
		return obj.getSize("worldspace")
	return None


def is_armature_object(obj):
	obj_type = get_object_type(obj)
	if obj_type in ("ARMATURE", "Armature"):
		return True
	if hasattr(obj, "getType"):
		return obj.getType() == "Armature"
	return False


def get_scene_objects(scene=None):
	if bpy is not None:
		if scene is None:
			scene = bpy.context.scene
		if scene is None:
			return []
		if hasattr(Blender, "wrap_object"):
			return [Blender.wrap_object(obj) for obj in scene.objects]
		return list(scene.objects)
	if Blender is not None:
		return list(Blender.Object.Get())
	return []


def get_selected_objects():
	if bpy is not None:
		if hasattr(Blender, "wrap_object"):
			return [Blender.wrap_object(obj) for obj in bpy.context.selected_objects]
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
					return Blender.wrap_object(obj) if hasattr(Blender, "wrap_object") else obj
		obj = bpy.data.objects.get(name)
		return Blender.wrap_object(obj) if hasattr(Blender, "wrap_object") else obj
	if Blender is not None:
		try:
			return Blender.Object.Get(name)
		except Exception:
			return None
	return None


def get_material(name):
	if bpy is not None:
		mat = bpy.data.materials.get(name)
		return Blender.wrap_material(mat) if hasattr(Blender, "wrap_material") else mat
	if Blender is not None:
		try:
			return Blender.Material.Get(name)
		except Exception:
			return None
	return None


def get_materials():
	if bpy is not None:
		if hasattr(Blender, "wrap_material"):
			return [Blender.wrap_material(mat) for mat in bpy.data.materials]
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
		if hasattr(Blender, "wrap_action"):
			return {action.name: Blender.wrap_action(action) for action in bpy.data.actions}
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
