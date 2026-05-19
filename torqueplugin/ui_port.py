"""Modern Blender 4.x UI port for the Torque exporter.

The panel defaults to a classic layout that mirrors the old exporter, but
the same state is rendered through shared helpers so it can later move to a
different display mode without rewriting every control twice.
"""

from __future__ import annotations

import os

try:
	import bpy
	from bpy.props import (
		BoolProperty,
		CollectionProperty,
		EnumProperty,
		FloatProperty,
		IntProperty,
		PointerProperty,
		StringProperty,
	)
except ImportError:  # pragma: no cover - outside Blender
	bpy = None

try:
	import blender_compat as bc
except Exception:  # pragma: no cover - outside Blender
	bc = None


def _legacy_module():
	try:
		import Dts_Blender as legacy
		return legacy
	except Exception:
		return None


def _legacy_prefs():
	legacy = _legacy_module()
	if legacy is None:
		return None
	return getattr(legacy, "Prefs", None)


def _ensure_prefs():
	legacy = _legacy_module()
	if legacy is None:
		return None
	prefs = getattr(legacy, "Prefs", None)
	if prefs is None:
		try:
			prefs = legacy.initPrefs()
			legacy.Prefs = prefs
		except Exception:
			prefs = None
	return prefs


def _blend_dir():
	if bpy is None:
		return ""
	try:
		filepath = bpy.data.filepath
	except Exception:
		filepath = ""
	if filepath:
		return os.path.dirname(filepath)
	legacy = _legacy_module()
	if legacy is not None:
		try:
			filename = legacy.getCurrentFilename()
		except Exception:
			filename = ""
		if filename:
			return os.path.dirname(filename)
	return ""


def _sequence_items(self, context):
	prefs = _legacy_prefs() or {}
	seqs = prefs.get("Sequences", {})
	items = [("N/A", "<None>", "")]
	for name in sorted(seqs.keys(), key=lambda x: x.lower()):
		items.append((name, name, "Torque sequence"))
	return items


def _material_items(self, context):
	prefs = _legacy_prefs() or {}
	mats = prefs.get("Materials", {})
	items = [("N/A", "<None>", "")]
	for name in sorted(mats.keys(), key=lambda x: x.lower()):
		items.append((name, name, "Torque material"))
	return items


def _material_summary(mat):
	parts = []
	base = mat.get("BaseTex")
	if base:
		parts.append(str(base))
	if mat.get("IFLMaterial"):
		parts.append("IFL")
	if mat.get("DetailMapFlag"):
		parts.append("Detail")
	if mat.get("BumpMapFlag"):
		parts.append("Bump")
	if mat.get("ReflectanceMapFlag"):
		parts.append("Env")
	if mat.get("Translucent"):
		parts.append("Trans")
	if mat.get("Additive"):
		parts.append("Add")
	if mat.get("Subtractive"):
		parts.append("Sub")
	if mat.get("SelfIlluminating"):
		parts.append("Self")
	if not parts:
		return "No summary"
	return ", ".join(parts)


def _armature_items(self, context):
	legacy = _legacy_module()
	names = []
	if legacy is not None:
		try:
			for obj in legacy.getCurrentSceneObjects():
				if bc is not None and bc.is_armature_object(obj):
					names.append(obj.name)
		except Exception:
			pass
	if not names:
		return [("N/A", "<None>", "")]
	return [(name, name, "Armature in the current scene") for name in sorted(names, key=lambda x: x.lower())]


def _sync_sequence_from_prefs(state, seq_name):
	prefs = _legacy_prefs() or {}
	seq = prefs.get("Sequences", {}).get(seq_name)
	if not seq:
		return
	if state.selected_sequence != seq_name:
		state.selected_sequence = seq_name
	state.seq_priority = int(seq.get("Priority", 0))
	state.seq_cyclic = bool(seq.get("Cyclic", False))
	state.seq_no_export = bool(seq.get("NoExport", False))
	state.seq_total_frames = int(seq.get("TotalFrames", 0))
	state.seq_duration = float(seq.get("Duration", 1.0))
	state.seq_fps = float(seq.get("FPS", 25.0))
	state.seq_duration_locked = bool(seq.get("DurationLocked", False))
	state.seq_fps_locked = bool(seq.get("FPSLocked", True))

	action = seq.get("Action", {})
	state.seq_action_enabled = bool(action.get("Enabled", False))
	state.seq_action_start = int(action.get("StartFrame", 1))
	state.seq_action_end = int(action.get("EndFrame", 1))
	state.seq_action_auto_samples = bool(action.get("AutoSamples", False))
	state.seq_action_auto_frames = bool(action.get("AutoFrames", False))
	state.seq_action_frame_samples = int(action.get("FrameSamples", 0))
	state.seq_action_num_ground_frames = int(action.get("NumGroundFrames", 0))
	state.seq_action_blend = bool(action.get("Blend", False))
	state.seq_action_blend_ref_action = str(action.get("BlendRefPoseAction", "") or "")
	state.seq_action_blend_ref_frame = int(action.get("BlendRefPoseFrame", 1))

	ifl = seq.get("IFL", {})
	state.seq_ifl_enabled = bool(ifl.get("Enabled", False))
	state.seq_ifl_material = str(ifl.get("Material", "") or "")
	state.seq_ifl_num_images = int(ifl.get("NumImages", 1))
	state.seq_ifl_total_frames = int(ifl.get("TotalFrames", 1))
	state.seq_ifl_write_file = bool(ifl.get("WriteIFLFile", True))

	vis = seq.get("Vis", {})
	state.seq_vis_enabled = bool(vis.get("Enabled", False))
	state.seq_vis_start = int(vis.get("StartFrame", 1))
	state.seq_vis_end = int(vis.get("EndFrame", 1))


def _sync_material_from_prefs(state, mat_name):
	prefs = _legacy_prefs() or {}
	mat = prefs.get("Materials", {}).get(mat_name)
	if not mat:
		return
	if state.selected_material != mat_name:
		state.selected_material = mat_name
	state.mat_swrap = bool(mat.get("SWrap", False))
	state.mat_twrap = bool(mat.get("TWrap", False))
	state.mat_translucent = bool(mat.get("Translucent", False))
	state.mat_additive = bool(mat.get("Additive", False))
	state.mat_subtractive = bool(mat.get("Subtractive", False))
	state.mat_self_illum = bool(mat.get("SelfIlluminating", False))
	state.mat_never_env_map = bool(mat.get("NeverEnvMap", False))
	state.mat_no_mipmap = bool(mat.get("NoMipMap", False))
	state.mat_mipmap_zero_border = bool(mat.get("MipMapZeroBorder", False))
	state.mat_ifl_material = bool(mat.get("IFLMaterial", False))
	state.mat_detail_map_flag = bool(mat.get("DetailMapFlag", False))
	state.mat_bump_map_flag = bool(mat.get("BumpMapFlag", False))
	state.mat_reflectance_map_flag = bool(mat.get("ReflectanceMapFlag", False))
	state.mat_detail_tex = str(mat.get("DetailTex", "") or "")
	state.mat_bump_tex = str(mat.get("BumpMapTex", "") or "")
	state.mat_ref_tex = str(mat.get("RefMapTex", "") or "")
	state.mat_reflectance = float(mat.get("reflectance", 0.0))
	state.mat_detail_scale = float(mat.get("detailScale", 1.0))


def _sync_material_list_from_prefs(state):
	prefs = _legacy_prefs() or {}
	materials = prefs.get("Materials", {})
	state.material_items.clear()
	names = sorted(materials.keys(), key=lambda x: x.lower())
	for name in names:
		mat = materials.get(name, {})
		item = state.material_items.add()
		item.name = name
		item.summary = _material_summary(mat)
		item.base_tex = str(mat.get("BaseTex", "") or "")
		item.flags = ", ".join(
			flag for flag, enabled in (
				("IFL", bool(mat.get("IFLMaterial", False))),
				("Detail", bool(mat.get("DetailMapFlag", False))),
				("Bump", bool(mat.get("BumpMapFlag", False))),
				("Env", bool(mat.get("ReflectanceMapFlag", False))),
				("Trans", bool(mat.get("Translucent", False))),
			)
			if enabled
		)

	if not names:
		state.material_list_index = -1
		state.selected_material = "N/A"
		return

	if state.selected_material not in materials:
		state.selected_material = names[0]

	try:
		state.material_list_index = names.index(state.selected_material)
	except ValueError:
		state.material_list_index = 0
		state.selected_material = names[0]


def _on_material_list_index_changed(self, context):
	items = self.material_items
	if not items:
		self.selected_material = "N/A"
		return
	index = max(0, min(self.material_list_index, len(items) - 1))
	if index != self.material_list_index:
		self.material_list_index = index
	mat_name = items[index].name
	if self.selected_material != mat_name:
		self.selected_material = mat_name
	_sync_material_from_prefs(self, mat_name)


def _on_selected_sequence_changed(self, context):
	_sync_sequence_from_prefs(self, self.selected_sequence)


def _on_selected_material_changed(self, context):
	_sync_material_from_prefs(self, self.selected_material)
	if self.material_items:
		for idx, item in enumerate(self.material_items):
			if item.name == self.selected_material:
				if self.material_list_index != idx:
					self.material_list_index = idx
				break


def _sync_state_from_legacy(state):
	prefs = _legacy_prefs() or {}
	if not prefs:
		return
	state.export_basepath = str(prefs.get("exportBasepath", "") or _blend_dir())
	state.export_basename = str(prefs.get("exportBasename", ""))
	state.dts_version = int(prefs.get("DTSVersion", 24))
	state.write_shape_script = bool(prefs.get("WriteShapeScript", False))
	state.export_scale = float(prefs.get("ExportScale", 1.0))
	state.prim_type = str(prefs.get("PrimType", "Tris"))
	state.max_strip_size = int(prefs.get("MaxStripSize", 6))
	state.cluster_depth = int(prefs.get("ClusterDepth", 1))
	state.always_write_depth = bool(prefs.get("AlwaysWriteDepth", False))
	state.collapse_root_transform = bool(prefs.get("CollapseRootTransform", True))
	state.tse_material = bool(prefs.get("TSEMaterial", False))
	state.billboard_enabled = bool(prefs.get("Billboard", {}).get("Enabled", False))
	state.billboard_equator = int(prefs.get("Billboard", {}).get("Equator", 10))
	state.billboard_polar = int(prefs.get("Billboard", {}).get("Polar", 10))
	state.billboard_polar_angle = float(prefs.get("Billboard", {}).get("PolarAngle", 25.0))
	state.billboard_dim = int(prefs.get("Billboard", {}).get("Dim", 64))
	state.billboard_include_poles = bool(prefs.get("Billboard", {}).get("IncludePoles", True))
	state.billboard_size = float(prefs.get("Billboard", {}).get("Size", 20.0))
	state.banned_bones = ", ".join(prefs.get("BannedBones", []))
	state.ui_initialized = True
	if state.selected_sequence != "N/A":
		_sync_sequence_from_prefs(state, state.selected_sequence)
	_sync_material_list_from_prefs(state)


def _on_state_changed(self, context):
	_sync_state_to_legacy_safe(self)


def _sync_state_to_legacy_safe(state):
	try:
		_sync_state_to_legacy(state)
	except Exception as exc:
		print(f"Torque UI sync warning: {exc}")


def _sync_state_to_legacy(state):
	prefs = _ensure_prefs()
	if prefs is None:
		return
	prefs["exportBasepath"] = state.export_basepath
	prefs["exportBasename"] = state.export_basename
	prefs["DTSVersion"] = state.dts_version
	prefs["WriteShapeScript"] = state.write_shape_script
	prefs["ExportScale"] = state.export_scale
	prefs["PrimType"] = state.prim_type
	prefs["MaxStripSize"] = state.max_strip_size
	prefs["ClusterDepth"] = state.cluster_depth
	prefs["AlwaysWriteDepth"] = state.always_write_depth
	prefs["CollapseRootTransform"] = state.collapse_root_transform
	prefs["TSEMaterial"] = state.tse_material
	prefs["Billboard"] = {
		"Enabled": state.billboard_enabled,
		"Equator": state.billboard_equator,
		"Polar": state.billboard_polar,
		"PolarAngle": state.billboard_polar_angle,
		"Dim": state.billboard_dim,
		"IncludePoles": state.billboard_include_poles,
		"Size": state.billboard_size,
	}
	prefs["BannedBones"] = [b.strip() for b in state.banned_bones.split(",") if b.strip()]

	seq_name = state.selected_sequence
	seq = prefs.get("Sequences", {}).get(seq_name)
	if seq:
		seq["Priority"] = state.seq_priority
		seq["Cyclic"] = state.seq_cyclic
		seq["NoExport"] = state.seq_no_export
		seq["TotalFrames"] = state.seq_total_frames
		seq["Duration"] = state.seq_duration
		seq["FPS"] = state.seq_fps
		seq["DurationLocked"] = state.seq_duration_locked
		seq["FPSLocked"] = state.seq_fps_locked
		seq.setdefault("Action", {})
		seq["Action"]["Enabled"] = state.seq_action_enabled
		seq["Action"]["StartFrame"] = state.seq_action_start
		seq["Action"]["EndFrame"] = state.seq_action_end
		seq["Action"]["AutoSamples"] = state.seq_action_auto_samples
		seq["Action"]["AutoFrames"] = state.seq_action_auto_frames
		seq["Action"]["FrameSamples"] = state.seq_action_frame_samples
		seq["Action"]["NumGroundFrames"] = state.seq_action_num_ground_frames
		seq["Action"]["Blend"] = state.seq_action_blend
		seq["Action"]["BlendRefPoseAction"] = state.seq_action_blend_ref_action
		seq["Action"]["BlendRefPoseFrame"] = state.seq_action_blend_ref_frame
		seq.setdefault("IFL", {})
		seq["IFL"]["Enabled"] = state.seq_ifl_enabled
		seq["IFL"]["Material"] = state.seq_ifl_material
		seq["IFL"]["NumImages"] = state.seq_ifl_num_images
		seq["IFL"]["TotalFrames"] = state.seq_ifl_total_frames
		seq["IFL"]["WriteIFLFile"] = state.seq_ifl_write_file
		seq.setdefault("Vis", {})
		seq["Vis"]["Enabled"] = state.seq_vis_enabled
		seq["Vis"]["StartFrame"] = state.seq_vis_start
		seq["Vis"]["EndFrame"] = state.seq_vis_end

	mat_name = state.selected_material
	mat = prefs.get("Materials", {}).get(mat_name)
	if mat:
		translucent = bool(state.mat_translucent)
		additive = bool(state.mat_additive)
		subtractive = bool(state.mat_subtractive)
		if additive:
			translucent = True
			subtractive = False
		elif subtractive:
			translucent = True
			additive = False
		elif not translucent:
			additive = False
			subtractive = False

		never_env_map = bool(state.mat_never_env_map)
		reflectance_map_flag = bool(state.mat_reflectance_map_flag)
		if reflectance_map_flag:
			never_env_map = False
		elif never_env_map:
			reflectance_map_flag = False

		no_mipmap = bool(state.mat_no_mipmap)
		mipmap_zero_border = bool(state.mat_mipmap_zero_border)
		if mipmap_zero_border:
			no_mipmap = False
		elif no_mipmap:
			mipmap_zero_border = False

		mat["SWrap"] = state.mat_swrap
		mat["TWrap"] = state.mat_twrap
		mat["Translucent"] = translucent
		mat["Additive"] = additive
		mat["Subtractive"] = subtractive
		mat["SelfIlluminating"] = state.mat_self_illum
		mat["NeverEnvMap"] = never_env_map
		mat["NoMipMap"] = no_mipmap
		mat["MipMapZeroBorder"] = mipmap_zero_border
		mat["IFLMaterial"] = state.mat_ifl_material
		mat["DetailMapFlag"] = state.mat_detail_map_flag
		mat["BumpMapFlag"] = state.mat_bump_map_flag
		mat["ReflectanceMapFlag"] = reflectance_map_flag
		mat["DetailTex"] = state.mat_detail_tex
		mat["BumpMapTex"] = state.mat_bump_tex
		mat["RefMapTex"] = state.mat_ref_tex
		mat["reflectance"] = state.mat_reflectance
		mat["detailScale"] = state.mat_detail_scale

	try:
		import Dts_Blender as legacy
		legacy.Prefs = prefs
	except Exception:
		pass


def _refresh_sequences(state):
	legacy = _legacy_module()
	if legacy is None:
		return
	prefs = _ensure_prefs()
	if prefs is None:
		return
	try:
		actions = legacy.getCurrentActions()
		for name in actions.keys():
			legacy.getSequenceKey(name)
	except Exception:
		pass
	_sync_state_from_legacy(state)


def _refresh_materials(state):
	legacy = _legacy_module()
	if legacy is None:
		return
	try:
		legacy.importMaterialList()
	except Exception:
		pass
	_sync_state_from_legacy(state)
	_sync_material_list_from_prefs(state)


class TorqueExporterMaterialItem(bpy.types.PropertyGroup):
	name: StringProperty(name="Name", default="")
	summary: StringProperty(name="Summary", default="")
	base_tex: StringProperty(name="Base Texture", default="")
	flags: StringProperty(name="Flags", default="")


class TORQUEEXPORTER_UL_material_items(bpy.types.UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		if self.layout_type in {"DEFAULT", "COMPACT"}:
			col = layout.column(align=True)
			row = col.row(align=True)
			row.label(text=item.name, icon="MATERIAL")
			if item.base_tex:
				row.label(text=item.base_tex)
			if item.summary:
				col.label(text=item.summary)
			elif item.flags:
				col.label(text=item.flags)
		elif self.layout_type == "GRID":
			layout.label(text=item.name)


class TORQUEEXPORTER_OT_refresh_materials(bpy.types.Operator):
	bl_idname = "torqueexporter.refresh_materials"
	bl_label = "Refresh Materials"
	bl_options = {"INTERNAL"}

	def execute(self, context):
		legacy = _legacy_module()
		if legacy is None:
			self.report({"WARNING"}, "Legacy exporter module is not available")
			return {"CANCELLED"}
		try:
			legacy.importMaterialList()
		except Exception:
			pass
		state = context.scene.torque_export_ui
		_sync_state_from_legacy(state)
		_sync_material_list_from_prefs(state)
		return {"FINISHED"}


class TorqueExporterUIState(bpy.types.PropertyGroup):
	display_mode: EnumProperty(
		name="Mode",
		items=[
			("CLASSIC", "Classic", "Legacy-shaped layout"),
			("COMPACT", "Compact", "Condensed 4.x layout"),
		],
		default="CLASSIC",
	)
	ui_initialized: BoolProperty(default=False)

	export_basepath: StringProperty(name="Export Path", default="", update=_on_state_changed)
	export_basename: StringProperty(name="Basename", default="", update=_on_state_changed)
	dts_version: IntProperty(name="DTS Version", default=24, min=0, max=255, update=_on_state_changed)
	write_shape_script: BoolProperty(name="Write Shape Script", default=False, update=_on_state_changed)
	export_scale: FloatProperty(name="Export Scale", default=1.0, min=0.0, update=_on_state_changed)
	prim_type: EnumProperty(
		name="Primitive Type",
		items=[
			("Tris", "Tris", "Standard triangle export"),
			("TriLists", "TriLists", "Triangle lists"),
			("TriStrips", "TriStrips", "Triangle strips"),
		],
		default="Tris",
	)
	max_strip_size: IntProperty(name="Max Strip Size", default=6, min=3, max=256, update=_on_state_changed)
	cluster_depth: IntProperty(name="Cluster Depth", default=1, min=0, max=32, update=_on_state_changed)
	always_write_depth: BoolProperty(name="Always Write Depth", default=False, update=_on_state_changed)
	collapse_root_transform: BoolProperty(name="Collapse Root Transform", default=True, update=_on_state_changed)
	tse_material: BoolProperty(name="TSE Material", default=False, update=_on_state_changed)

	billboard_enabled: BoolProperty(name="Enable Billboard", default=False, update=_on_state_changed)
	billboard_equator: IntProperty(name="Equator", default=10, min=0, max=64, update=_on_state_changed)
	billboard_polar: IntProperty(name="Polar", default=10, min=0, max=64, update=_on_state_changed)
	billboard_polar_angle: FloatProperty(name="Polar Angle", default=25.0, min=0.0, max=45.0, update=_on_state_changed)
	billboard_dim: IntProperty(name="Dimension", default=64, min=16, max=128, update=_on_state_changed)
	billboard_include_poles: BoolProperty(name="Include Poles", default=True, update=_on_state_changed)
	billboard_size: FloatProperty(name="Billboard Size", default=20.0, min=0.0, max=128.0, update=_on_state_changed)

	selected_sequence: EnumProperty(name="Sequence", items=_sequence_items, update=_on_selected_sequence_changed)
	seq_priority: IntProperty(name="Priority", default=0, update=_on_state_changed)
	seq_cyclic: BoolProperty(name="Cyclic", default=False, update=_on_state_changed)
	seq_no_export: BoolProperty(name="No Export", default=False, update=_on_state_changed)
	seq_total_frames: IntProperty(name="Total Frames", default=0, update=_on_state_changed)
	seq_duration: FloatProperty(name="Duration", default=1.0, min=0.0, update=_on_state_changed)
	seq_fps: FloatProperty(name="FPS", default=25.0, min=0.0, update=_on_state_changed)
	seq_duration_locked: BoolProperty(name="Duration Locked", default=False, update=_on_state_changed)
	seq_fps_locked: BoolProperty(name="FPS Locked", default=True, update=_on_state_changed)

	seq_action_enabled: BoolProperty(name="Enable Action", default=False, update=_on_state_changed)
	seq_action_start: IntProperty(name="Start Frame", default=1, update=_on_state_changed)
	seq_action_end: IntProperty(name="End Frame", default=1, update=_on_state_changed)
	seq_action_auto_samples: BoolProperty(name="Auto Samples", default=True, update=_on_state_changed)
	seq_action_auto_frames: BoolProperty(name="Auto Frames", default=True, update=_on_state_changed)
	seq_action_frame_samples: IntProperty(name="Frame Samples", default=1, min=0, update=_on_state_changed)
	seq_action_num_ground_frames: IntProperty(name="Ground Frames", default=0, min=0, update=_on_state_changed)
	seq_action_blend: BoolProperty(name="Blend", default=False, update=_on_state_changed)
	seq_action_blend_ref_action: EnumProperty(name="Blend Ref Action", items=_sequence_items, update=_on_state_changed)
	seq_action_blend_ref_frame: IntProperty(name="Blend Ref Frame", default=1, update=_on_state_changed)

	seq_ifl_enabled: BoolProperty(name="Enable IFL", default=False, update=_on_state_changed)
	seq_ifl_material: EnumProperty(name="IFL Material", items=_material_items, update=_on_state_changed)
	seq_ifl_num_images: IntProperty(name="Num Images", default=1, min=1, update=_on_state_changed)
	seq_ifl_total_frames: IntProperty(name="IFL Total Frames", default=1, min=1, update=_on_state_changed)
	seq_ifl_write_file: BoolProperty(name="Write IFL File", default=True, update=_on_state_changed)

	seq_vis_enabled: BoolProperty(name="Enable Visibility", default=False, update=_on_state_changed)
	seq_vis_start: IntProperty(name="Start Frame", default=1, update=_on_state_changed)
	seq_vis_end: IntProperty(name="End Frame", default=1, update=_on_state_changed)
	seq_vis_tracks_summary: StringProperty(name="Tracks", default="")

	selected_material: EnumProperty(name="Material", items=_material_items, update=_on_selected_material_changed)
	material_list_index: IntProperty(name="Material Index", default=-1, update=_on_material_list_index_changed)
	material_show_advanced: BoolProperty(name="Show Advanced Settings", default=False, update=_on_state_changed)
	mat_swrap: BoolProperty(name="SWrap", default=False, update=_on_state_changed)
	mat_twrap: BoolProperty(name="TWrap", default=False, update=_on_state_changed)
	mat_translucent: BoolProperty(name="Translucent", default=False, update=_on_state_changed)
	mat_additive: BoolProperty(name="Additive", default=False, update=_on_state_changed)
	mat_subtractive: BoolProperty(name="Subtractive", default=False, update=_on_state_changed)
	mat_self_illum: BoolProperty(name="Self Illuminating", default=False, update=_on_state_changed)
	mat_never_env_map: BoolProperty(name="Never Env Map", default=False, update=_on_state_changed)
	mat_no_mipmap: BoolProperty(name="No MipMap", default=False, update=_on_state_changed)
	mat_mipmap_zero_border: BoolProperty(name="MipMap Zero Border", default=False, update=_on_state_changed)
	mat_ifl_material: BoolProperty(name="IFL Material", default=False, update=_on_state_changed)
	mat_detail_map_flag: BoolProperty(name="Detail Map", default=False, update=_on_state_changed)
	mat_bump_map_flag: BoolProperty(name="Bump Map", default=False, update=_on_state_changed)
	mat_reflectance_map_flag: BoolProperty(name="Reflectance Map", default=False, update=_on_state_changed)
	mat_detail_tex: StringProperty(name="Detail Texture", default="", update=_on_state_changed)
	mat_bump_tex: StringProperty(name="Bump Texture", default="", update=_on_state_changed)
	mat_ref_tex: StringProperty(name="Reflectance Texture", default="", update=_on_state_changed)
	mat_reflectance: FloatProperty(name="Reflectance", default=0.0, min=0.0, max=1.0, update=_on_state_changed)
	mat_detail_scale: FloatProperty(name="Detail Scale", default=1.0, min=0.0, update=_on_state_changed)
	material_items: CollectionProperty(type=TorqueExporterMaterialItem)

	banned_bones: StringProperty(
		name="Banned Bones",
		default="",
		description="Comma-separated list of bone names to skip",
		update=_on_state_changed,
	)
	armature_name: EnumProperty(name="Armature", items=_armature_items, update=_on_state_changed)


class TORQUEEXPORTER_OT_refresh_ui(bpy.types.Operator):
	bl_idname = "torqueexporter.refresh_ui"
	bl_label = "Refresh Torque UI"
	bl_options = {"INTERNAL"}

	def execute(self, context):
		state = context.scene.torque_export_ui
		_sync_state_from_legacy(state)
		return {"FINISHED"}


class TORQUEEXPORTER_OT_apply_ui(bpy.types.Operator):
	bl_idname = "torqueexporter.apply_ui"
	bl_label = "Apply Torque UI"
	bl_options = {"INTERNAL"}

	def execute(self, context):
		_sync_state_to_legacy_safe(context.scene.torque_export_ui)
		return {"FINISHED"}


class TORQUEEXPORTER_OT_export_from_ui(bpy.types.Operator):
	bl_idname = "torqueexporter.export_from_ui"
	bl_label = "Export DTS"
	bl_options = {"REGISTER"}

	def execute(self, context):
		_sync_state_to_legacy_safe(context.scene.torque_export_ui)
		legacy = _legacy_module()
		if legacy is None:
			self.report({"ERROR"}, "Legacy exporter module is not available")
			return {"CANCELLED"}
		try:
			legacy.savePrefs()
		except Exception:
			pass
		legacy.entryPoint("normal")
		return {"FINISHED"}


class TORQUEEXPORTER_OT_use_blend_dir(bpy.types.Operator):
	bl_idname = "torqueexporter.use_blend_dir"
	bl_label = "Use Current File Folder"
	bl_options = {"INTERNAL"}

	def execute(self, context):
		state = context.scene.torque_export_ui
		blend_dir = _blend_dir()
		if not blend_dir:
			self.report({"WARNING"}, "Current .blend file has not been saved yet")
			return {"CANCELLED"}
		state.export_basepath = blend_dir
		_sync_state_to_legacy_safe(state)
		return {"FINISHED"}


class TORQUEEXPORTER_PT_scene_panel(bpy.types.Panel):
	bl_idname = "TORQUEEXPORTER_PT_scene_panel"
	bl_label = "Torque Exporter"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "scene"

	def draw(self, context):
		state = context.scene.torque_export_ui
		if not state.ui_initialized:
			_sync_state_from_legacy(state)

		layout = self.layout
		layout.prop(state, "display_mode", expand=True)
		row = layout.row(align=True)
		row.operator("torqueexporter.refresh_ui", text="Refresh")
		row.operator("torqueexporter.apply_ui", text="Sync")
		row.operator("torqueexporter.export_from_ui", text="Export", icon="EXPORT")

		if state.display_mode == "CLASSIC":
			_draw_legacy(layout, state)
		else:
			_draw_modern(layout, state)


def _draw_export_block(layout, state):
	box = layout.box()
	box.label(text="Export")
	col = box.column(align=True)
	path_row = col.row(align=True)
	path_row.prop(state, "export_basepath", text="Export Path")
	path_row.operator("torqueexporter.use_blend_dir", text="", icon="FILE_FOLDER")
	col.prop(state, "export_basename")
	row = col.row(align=True)
	row.prop(state, "dts_version")
	row.prop(state, "export_scale")
	row = col.row(align=True)
	row.prop(state, "write_shape_script")
	row.prop(state, "tse_material")
	col.prop(state, "prim_type")


def _draw_general_block(layout, state):
	box = layout.box()
	box.label(text="General")
	col = box.column(align=True)
	col.prop(state, "max_strip_size")
	col.prop(state, "cluster_depth")
	row = col.row(align=True)
	row.prop(state, "always_write_depth")
	row.prop(state, "collapse_root_transform")

	bb = box.box()
	bb.label(text="Auto Billboard")
	bbcol = bb.column(align=True)
	bbcol.prop(state, "billboard_enabled")
	bbcol.prop(state, "billboard_equator")
	bbcol.prop(state, "billboard_polar")
	bbcol.prop(state, "billboard_polar_angle")
	row = bbcol.row(align=True)
	row.prop(state, "billboard_dim")
	row.prop(state, "billboard_include_poles")
	bbcol.prop(state, "billboard_size")


def _draw_sequence_block(layout, state):
	box = layout.box()
	box.label(text="Sequences")
	box.prop(state, "selected_sequence")
	if state.selected_sequence == "N/A":
		box.label(text="No sequence selected")
		return
	col = box.column(align=True)
	row = col.row(align=True)
	row.prop(state, "seq_priority")
	row.prop(state, "seq_cyclic")
	row = col.row(align=True)
	row.prop(state, "seq_no_export")
	row.prop(state, "seq_total_frames")
	row = col.row(align=True)
	row.prop(state, "seq_duration")
	row.prop(state, "seq_fps")
	row = col.row(align=True)
	row.prop(state, "seq_duration_locked")
	row.prop(state, "seq_fps_locked")

	action = box.box()
	action.label(text="Action")
	acol = action.column(align=True)
	row = acol.row(align=True)
	row.prop(state, "seq_action_enabled")
	row.prop(state, "seq_action_start")
	row.prop(state, "seq_action_end")
	row = acol.row(align=True)
	row.prop(state, "seq_action_auto_samples")
	row.prop(state, "seq_action_auto_frames")
	row = acol.row(align=True)
	row.prop(state, "seq_action_frame_samples")
	row.prop(state, "seq_action_num_ground_frames")
	row = acol.row(align=True)
	row.prop(state, "seq_action_blend")
	row.prop(state, "seq_action_blend_ref_action")
	acol.prop(state, "seq_action_blend_ref_frame")

	ifl = box.box()
	ifl.label(text="IFL")
	iflcol = ifl.column(align=True)
	row = iflcol.row(align=True)
	row.prop(state, "seq_ifl_enabled")
	row.prop(state, "seq_ifl_material")
	row = iflcol.row(align=True)
	row.prop(state, "seq_ifl_num_images")
	row.prop(state, "seq_ifl_total_frames")
	iflcol.prop(state, "seq_ifl_write_file")

	vis = box.box()
	vis.label(text="Visibility")
	viscol = vis.column(align=True)
	row = viscol.row(align=True)
	row.prop(state, "seq_vis_enabled")
	row.prop(state, "seq_vis_start")
	row.prop(state, "seq_vis_end")
	viscol.label(text=f"Tracks: {state.seq_vis_tracks_summary or 'none'}")


def _draw_material_block(layout, state):
	box = layout.box()
	box.label(text="Materials")
	head = box.row(align=True)
	head.label(text="U/V Textures")
	head.operator("torqueexporter.refresh_materials", text="", icon="FILE_REFRESH")
	head.prop(state, "material_show_advanced", text="Advanced", toggle=True)

	if len(state.material_items) == 0:
		box.label(text="No materials imported. Refresh to pull from the current scene.")
		return

	split = box.split(factor=0.42)
	left = split.column()
	left.template_list(
		"TORQUEEXPORTER_UL_material_items",
		"",
		state,
		"material_items",
		state,
		"material_list_index",
		rows=6,
	)

	right = split.column(align=True)
	right.prop(state, "selected_material", text="Selected")

	selected_ok = state.selected_material != "N/A"
	detail = right.column(align=True)
	detail.enabled = selected_ok
	detail.prop(state, "mat_swrap")
	detail.prop(state, "mat_twrap")
	row = detail.row(align=True)
	row.prop(state, "mat_translucent")
	row.prop(state, "mat_additive")
	row.prop(state, "mat_subtractive")
	row = detail.row(align=True)
	row.prop(state, "mat_self_illum")
	row.prop(state, "mat_never_env_map")
	row = detail.row(align=True)
	row.prop(state, "mat_no_mipmap")
	row.prop(state, "mat_mipmap_zero_border")
	row = detail.row(align=True)
	row.prop(state, "mat_ifl_material")
	row.prop(state, "mat_detail_map_flag")

	if state.material_show_advanced:
		adv = right.box()
		adv.label(text="Advanced")
		advcol = adv.column(align=True)
		advcol.enabled = selected_ok
		row = advcol.row(align=True)
		row.prop(state, "mat_bump_map_flag")
		row.prop(state, "mat_reflectance_map_flag")
		advcol.prop(state, "mat_detail_tex")
		advcol.prop(state, "mat_bump_tex")
		advcol.prop(state, "mat_ref_tex")
		row = advcol.row(align=True)
		row.prop(state, "mat_reflectance")
		row.prop(state, "mat_detail_scale")


def _draw_armature_block(layout, state):
	box = layout.box()
	box.label(text="Armatures")
	box.prop(state, "armature_name")
	box.prop(state, "banned_bones")
	pad = box.box()
	pad.label(text="Current scene armatures")
	legacy = _legacy_module()
	if legacy is None:
		pad.label(text="Legacy exporter module not loaded")
		return
	try:
		arm_names = [obj.name for obj in legacy.getCurrentSceneObjects() if bc is not None and bc.is_armature_object(obj)]
	except Exception:
		arm_names = []
	if arm_names:
		for name in sorted(arm_names, key=lambda x: x.lower()):
			pad.label(text=f"• {name}")
	else:
		pad.label(text="No armatures detected")


def _draw_about_block(layout, state):
	box = layout.box()
	box.label(text="About")
	box.label(text="Torque DTS exporter UI port")
	box.label(text="Classic layout mirrors the original exporter")
	box.label(text="Compact layout is reserved for future reorganized UI")


def _draw_legacy(layout, state):
	_draw_export_block(layout, state)
	_draw_sequence_block(layout, state)
	_draw_armature_block(layout, state)
	_draw_material_block(layout, state)
	_draw_general_block(layout, state)
	_draw_about_block(layout, state)


def _draw_modern(layout, state):
	_draw_export_block(layout, state)
	_draw_general_block(layout, state)
	_draw_sequence_block(layout, state)
	_draw_armature_block(layout, state)
	_draw_material_block(layout, state)
	_draw_about_block(layout, state)


_CLASSES = (
	TorqueExporterMaterialItem,
	TorqueExporterUIState,
	TORQUEEXPORTER_UL_material_items,
	TORQUEEXPORTER_OT_refresh_materials,
	TORQUEEXPORTER_OT_refresh_ui,
	TORQUEEXPORTER_OT_apply_ui,
	TORQUEEXPORTER_OT_use_blend_dir,
	TORQUEEXPORTER_OT_export_from_ui,
	TORQUEEXPORTER_PT_scene_panel,
)


def register():
	if bpy is None:
		return
	for cls in _CLASSES:
		bpy.utils.register_class(cls)
	bpy.types.Scene.torque_export_ui = PointerProperty(type=TorqueExporterUIState)


def unregister():
	if bpy is None:
		return
	if hasattr(bpy.types.Scene, "torque_export_ui"):
		del bpy.types.Scene.torque_export_ui
	for cls in reversed(_CLASSES):
		bpy.utils.unregister_class(cls)
