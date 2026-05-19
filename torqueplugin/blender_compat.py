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
	raw_obj = getattr(obj, "_obj", obj)
	if hasattr(raw_obj, "data"):
		data = raw_obj.data
		if bpy is not None and get_object_type(raw_obj) == "MESH":
			apply_modifiers = any(bool(arg) for arg in args)
			return get_mesh_data(raw_obj, apply_modifiers=apply_modifiers)
		return data
	if hasattr(obj, "getData"):
		return obj.getData(*args)
	return None


def get_material_for_mesh(obj, face):
	raw_obj = getattr(obj, "_obj", obj)
	mesh = getattr(raw_obj, "data", None)
	if mesh is None:
		return None
	index = getattr(face, "mat", getattr(face, "material_index", -1))
	if index < 0:
		return None
	materials = getattr(mesh, "materials", [])
	if index >= len(materials):
		return None
	return materials[index]


def get_mesh_data(obj, apply_modifiers=False):
	raw_obj = getattr(obj, "_obj", obj)
	if bpy is None or raw_obj is None:
		return get_object_data(obj)
	if get_object_type(raw_obj) != "MESH":
		return get_object_data(obj)
	mesh = getattr(raw_obj, "data", None)
	if mesh is None:
		return None
	temp_mesh = None
	if apply_modifiers and hasattr(raw_obj, "evaluated_get"):
		try:
			depsgraph = bpy.context.evaluated_depsgraph_get()
			evaluated = raw_obj.evaluated_get(depsgraph)
			temp_mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=depsgraph)
			mesh = temp_mesh
		except Exception:
			mesh = getattr(raw_obj, "data", None)
	try:
		if hasattr(Blender, "wrap_mesh"):
			return Blender.wrap_mesh(mesh, owner_object=raw_obj)
		return mesh
	finally:
		if temp_mesh is not None:
			try:
				bpy.data.meshes.remove(temp_mesh)
			except Exception:
				pass


def get_object_parent(obj):
	if hasattr(obj, "parent"):
		return obj.parent
	if hasattr(obj, "getParent"):
		return obj.getParent()
	return None


def get_armature_data(obj):
	raw_obj = getattr(obj, "_obj", obj)
	if hasattr(raw_obj, "data"):
		return raw_obj.data
	if hasattr(obj, "getData"):
		return obj.getData()
	return None


def get_bone_rest_matrix(bone):
	if hasattr(bone, "matrix_local"):
		return bone.matrix_local
	if hasattr(bone, "matrix") and isinstance(getattr(bone, "matrix"), dict):
		return bone.matrix.get("ARMATURESPACE")
	return None


def get_bone_parent_name(bone):
	parent = getattr(bone, "parent", None)
	if parent is not None:
		return getattr(parent, "name", None)
	if hasattr(bone, "hasParent") and bone.hasParent():
		return bone.parent.name
	return None


def get_bone_children(bone):
	children = getattr(bone, "children", None)
	if children is not None:
		return list(children)
	return []


def is_armature_in_rest_pose(obj):
	raw_obj = getattr(obj, "_obj", obj)
	if raw_obj is None:
		return False
	if hasattr(raw_obj, "pose_position"):
		return getattr(raw_obj, "pose_position") == "REST"
	data = getattr(raw_obj, "data", None)
	if data is not None and hasattr(data, "pose_position"):
		return getattr(data, "pose_position") == "REST"
	if hasattr(raw_obj, "mode"):
		return getattr(raw_obj, "mode") == "EDIT"
	return False


def reset_pose_bone_transform(pose_bone):
	if hasattr(pose_bone, "rotation_mode"):
		try:
			pose_bone.rotation_mode = "QUATERNION"
		except Exception:
			pass
	if hasattr(pose_bone, "rotation_quaternion"):
		try:
			pose_bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
		except Exception:
			pass
	elif hasattr(pose_bone, "quat"):
		try:
			pose_bone.quat = (0.0, 0.0, 0.0, 1.0)
		except Exception:
			pass
	if hasattr(pose_bone, "location"):
		try:
			pose_bone.location = (0.0, 0.0, 0.0)
		except Exception:
			pass
	elif hasattr(pose_bone, "loc"):
		try:
			pose_bone.loc = (0.0, 0.0, 0.0)
		except Exception:
			pass
	if hasattr(pose_bone, "scale"):
		try:
			pose_bone.scale = (1.0, 1.0, 1.0)
		except Exception:
			pass
	elif hasattr(pose_bone, "size"):
		try:
			pose_bone.size = (1.0, 1.0, 1.0)
		except Exception:
			pass


def update_pose(obj):
	raw_obj = getattr(obj, "_obj", obj)
	if raw_obj is None:
		return
	if hasattr(raw_obj, "update_tag"):
		try:
			raw_obj.update_tag()
		except Exception:
			pass
	scene = get_current_scene()
	if bpy is not None and scene is not None:
		try:
			depsgraph = bpy.context.evaluated_depsgraph_get()
			depsgraph.update()
		except Exception:
			pass
		try:
			scene.frame_set(scene.frame_current)
		except Exception:
			pass
	elif hasattr(obj, "update"):
		try:
			obj.update()
		except Exception:
			pass


def get_pose_bone_matrix(pose_bone):
	if hasattr(pose_bone, "matrix"):
		return pose_bone.matrix
	if hasattr(pose_bone, "poseMatrix"):
		return pose_bone.poseMatrix
	return None


def get_object_pose(obj):
	if hasattr(obj, "pose"):
		return obj.pose
	if hasattr(obj, "getPose"):
		return obj.getPose()
	return None


def get_object_ipo(obj):
	if hasattr(obj, "getIpo"):
		return obj.getIpo()
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


def get_image_name(image):
	if image is None:
		return None
	if hasattr(image, "getName"):
		try:
			return image.getName()
		except Exception:
			pass
	return getattr(image, "name", None)


def get_material_images(material):
	raw_material = getattr(material, "_material", material)
	images = []
	if raw_material is None:
		return images
	if getattr(raw_material, "use_nodes", False) and getattr(raw_material, "node_tree", None) is not None:
		for node in raw_material.node_tree.nodes:
			if getattr(node, "type", None) != "TEX_IMAGE":
				continue
			image = getattr(node, "image", None)
			if image is not None:
				images.append(image)
		return images
	for slot in getattr(raw_material, "texture_slots", []) or []:
		if slot is None:
			continue
		texture = getattr(slot, "texture", None)
		image = getattr(texture, "image", None)
		if image is not None:
			images.append(image)
	return images


def get_material_primary_image(material):
	images = get_material_images(material)
	return images[0] if images else None


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


def get_action_channel_ipos(action):
	if hasattr(action, "getAllChannelIpos"):
		return action.getAllChannelIpos()
	if bpy is not None and hasattr(action, "fcurves"):
		return {fc.data_path: fc for fc in action.fcurves}
	return {}


def get_ipo_scale_index(name):
	return {"ScaleX": 0, "ScaleY": 1, "ScaleZ": 2, "SizeX": 0, "SizeY": 1, "SizeZ": 2}.get(name, None)


def get_ipo_curve_names():
	return ("LocX", "LocY", "LocZ", "QuatX", "QuatY", "QuatZ", "QuatW", "ScaleX", "ScaleY", "ScaleZ")


def get_ipo_curve_key(ipo, name):
	if hasattr(ipo, "curveConsts"):
		try:
			return ipo.curveConsts[name]
		except Exception:
			return name
	return name


def set_frame(scene, frame):
	raw_scene = getattr(scene, "_scene", scene)
	if bpy is not None and scene is not None:
		raw_scene.frame_set(frame)
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
