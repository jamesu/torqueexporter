"""Modern Blender 4.x UI port for the Torque exporter.

The panel defaults to a classic layout that mirrors the old exporter, but
the same state is rendered through shared helpers so it can later move to a
different display mode without rewriting every control twice.
"""

from __future__ import annotations

import os
import fnmatch

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


_SYNCING_STATE_IDS = set()
_INTERNAL_UI_UPDATE_IDS = set()


def _begin_internal_ui_update(state):
	state_id = id(state)
	if state_id in _INTERNAL_UI_UPDATE_IDS:
		return False
	_INTERNAL_UI_UPDATE_IDS.add(state_id)
	return True


def _end_internal_ui_update(state):
	_INTERNAL_UI_UPDATE_IDS.discard(id(state))


def _ui_update_active(state):
	return id(state) in _INTERNAL_UI_UPDATE_IDS


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


def _log_ui_error(where, exc):
	print(f"Torque UI warning in {where}: {exc}")


def _ensure_prefs():
	legacy = _legacy_module()
	if legacy is None:
		return None
	prefs = getattr(legacy, "Prefs", None)
	if prefs is None:
		try:
			try:
				legacy.loadPrefs()
			except Exception:
				pass
			prefs = getattr(legacy, "Prefs", None)
			if prefs is None:
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
	prefs = _ensure_prefs() or _legacy_prefs() or {}
	seqs = prefs.get("Sequences", {})
	if not seqs:
		legacy = _legacy_module()
		if legacy is not None:
			try:
				seqs = {name: {} for name in legacy.getCurrentActions().keys()}
			except Exception as exc:
				_log_ui_error("_sequence_items", exc)
	items = [("N/A", "<None>", "")]
	for name in sorted(seqs.keys(), key=lambda x: x.lower()):
		items.append((name, name, "Torque sequence"))
	return items


def _material_items(self, context):
	prefs = _ensure_prefs() or _legacy_prefs() or {}
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


def _normalize_banned_bone(text):
	return str(text or "").strip()


def _parse_banned_bones_text(text):
	return [entry.strip() for entry in str(text or "").split(",") if entry.strip()]


def _banned_bone_matches(name, pattern):
	name_u = str(name or "").upper()
	pattern_u = str(pattern or "").upper()
	if not pattern_u:
		return False
	if "*" in pattern_u or "?" in pattern_u:
		return fnmatch.fnmatchcase(name_u, pattern_u)
	return name_u == pattern_u


def _populate_banned_bone_items(state, banned_bones):
	owned = _begin_internal_ui_update(state)
	try:
		state.banned_bone_items.clear()
		for entry in banned_bones:
			pattern = _normalize_banned_bone(entry)
			if not pattern:
				continue
			item = state.banned_bone_items.add()
			item.name = pattern
		if len(state.banned_bone_items) > 0:
			index = state.banned_bone_list_index
			if index < 0 or index >= len(state.banned_bone_items):
				index = 0
			state.banned_bone_list_index = index
		else:
			state.banned_bone_list_index = -1
		state.banned_bones = ", ".join(item.name for item in state.banned_bone_items if item.name)
	finally:
		if owned:
			_end_internal_ui_update(state)


def _sync_banned_bones_from_state(state):
	raw = getattr(state, "banned_bones", "") or ""
	if isinstance(raw, (list, tuple)):
		banned = [str(entry).strip() for entry in raw if str(entry).strip()]
	else:
		banned = [entry.strip() for entry in str(raw).split(",") if entry.strip()]
	_populate_banned_bone_items(state, banned)


def _on_banned_bone_item_name_changed(self, context):
	if context is None or getattr(context, "scene", None) is None:
		return
	state = getattr(context.scene, "torque_export_ui", None)
	if state is None or _ui_update_active(state):
		return
	self.name = _normalize_banned_bone(self.name)
	_sync_banned_bones_to_prefs(state)


def _sequence_summary(seq):
	parts = []
	if seq.get("Cyclic"):
		parts.append("Cyclic")
	if seq.get("NoExport"):
		parts.append("NoExport")
	if seq.get("Dsq"):
		parts.append("DSQ")
	if seq.get("Duration") is not None:
		parts.append(f"{float(seq.get('Duration', 0.0)):.2f}s")
	action = seq.get("Action", {})
	if action.get("Enabled"):
		parts.append("Action")
	if seq.get("IFL", {}).get("Enabled"):
		parts.append("IFL")
	if seq.get("Vis", {}).get("Enabled"):
		parts.append("Vis")
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
		return [("N/A", "<None>", "No armatures detected")]
	return [(name, name, "Armature in the current scene") for name in sorted(names, key=lambda x: x.lower())]


def _sync_sequence_from_prefs(state, seq_name):
	owned = _begin_internal_ui_update(state)
	prefs = _legacy_prefs() or {}
	try:
		seq = prefs.get("Sequences", {}).get(seq_name)
		if not seq:
			return
		if state.selected_sequence != seq_name:
			state.selected_sequence = seq_name
		state.seq_priority = int(seq.get("Priority", 0))
		state.seq_cyclic = bool(seq.get("Cyclic", False))
		state.seq_no_export = bool(seq.get("NoExport", False))
		state.seq_dsq = bool(seq.get("Dsq", False))
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
	finally:
		if owned:
			_end_internal_ui_update(state)


def _sync_vis_track_detail_from_index(state):
	owned = _begin_internal_ui_update(state)
	try:
		if not state.vis_track_items or state.vis_track_list_index < 0 or state.vis_track_list_index >= len(state.vis_track_items):
			state.vis_track_enabled = False
			state.vis_track_ipo_type = ""
			state.vis_track_ipo_channel = ""
			state.vis_track_ipo_object = ""
			return
		track = state.vis_track_items[state.vis_track_list_index]
		state.vis_track_enabled = bool(track.has_track)
		state.vis_track_ipo_type = str(track.ipo_type or "")
		state.vis_track_ipo_channel = str(track.ipo_channel or "")
		state.vis_track_ipo_object = str(track.ipo_object or "")
	finally:
		if owned:
			_end_internal_ui_update(state)


def _set_sequence_selection(state, seq_name, persist=True):
	owned = _begin_internal_ui_update(state)
	try:
		if seq_name == "N/A":
			state.selected_sequence = "N/A"
			state.sequence_list_index = -1
			state.seq_vis_tracks_summary = "none"
			state.vis_track_list_index = -1
			state.vis_track_items.clear()
			return
		prefs = _legacy_prefs() or {}
		seqs = prefs.get("Sequences", {})
		if seq_name not in seqs:
			return
		state.selected_sequence = seq_name
		names = [item.name for item in state.sequence_items]
		if seq_name in names:
			state.sequence_list_index = names.index(seq_name)
		_sync_sequence_from_prefs(state, seq_name)
		_sync_visibility_from_prefs(state, seq_name)
	finally:
		if owned:
			_end_internal_ui_update(state)
	if persist:
		_sync_state_to_legacy_safe(state)


def _sync_sequence_list_from_prefs(state):
	owned = _begin_internal_ui_update(state)
	prefs = _ensure_prefs() or _legacy_prefs() or {}
	try:
		seqs = prefs.get("Sequences", {})
		if not seqs:
			legacy = _legacy_module()
			if legacy is not None:
				try:
					seqs = {name: {} for name in legacy.getCurrentActions().keys()}
				except Exception as exc:
					_log_ui_error("_sync_sequence_list_from_prefs", exc)
		state.sequence_items.clear()
		names = sorted(seqs.keys(), key=lambda x: x.lower())
		for name in names:
			seq = seqs.get(name, {})
			item = state.sequence_items.add()
			item.name = name
			item.summary = _sequence_summary(seq)
			item.action = "Action" if seq.get("Action", {}).get("Enabled") else ""
			item.flags = ", ".join(
				flag for flag, enabled in (
					("Cyclic", bool(seq.get("Cyclic", False))),
					("NoExport", bool(seq.get("NoExport", False))),
					("DSQ", bool(seq.get("Dsq", False))),
				)
				if enabled
			)

		if not names:
			state.sequence_list_index = -1
			state.selected_sequence = "N/A"
			return

		if state.selected_sequence not in seqs:
			state.selected_sequence = names[0]

		try:
			state.sequence_list_index = names.index(state.selected_sequence)
		except ValueError:
			state.sequence_list_index = 0
			state.selected_sequence = names[0]
		if state.selected_sequence != "N/A":
			_sync_sequence_from_prefs(state, state.selected_sequence)
			_sync_visibility_from_prefs(state, state.selected_sequence)
	finally:
		if owned:
			_end_internal_ui_update(state)


def _sync_visibility_from_prefs(state, seq_name):
	owned = _begin_internal_ui_update(state)
	prefs = _legacy_prefs() or {}
	try:
		seq = prefs.get("Sequences", {}).get(seq_name)
		if not seq:
			state.vis_track_items.clear()
			state.vis_track_list_index = -1
			state.seq_vis_tracks_summary = "none"
			return
		vis = seq.setdefault("Vis", {})
		state.seq_vis_enabled = bool(vis.get("Enabled", False))
		state.seq_vis_start = int(vis.get("StartFrame", 1))
		state.seq_vis_end = int(vis.get("EndFrame", 1))

		track_prefs = vis.get("Tracks", {}) or {}
		state.vis_track_items.clear()
		scene_tracks = []
		legacy = _legacy_module()
		if legacy is not None:
			try:
				scene_tracks = [obj.name for obj in legacy.getCurrentSceneObjects()]
			except Exception as exc:
				_log_ui_error("_sync_visibility_from_prefs.scene_tracks", exc)
		for name in sorted(set(scene_tracks) | set(track_prefs.keys()), key=lambda x: x.lower()):
			track = track_prefs.get(name, {})
			item = state.vis_track_items.add()
			item.name = name
			item.has_track = bool(track.get("hasVisTrack", False))
			item.ipo_type = str(track.get("IPOType", "") or "")
			item.ipo_channel = str(track.get("IPOChannel", "") or "")
			item.ipo_object = str(track.get("IPOObject", "") or "")
		if not state.vis_track_items:
			state.vis_track_list_index = -1
			state.seq_vis_tracks_summary = "none"
			_sync_vis_track_detail_from_index(state)
			return
		if state.vis_track_list_index < 0 or state.vis_track_list_index >= len(state.vis_track_items):
			state.vis_track_list_index = 0
		state.seq_vis_tracks_summary = _sequence_summary(seq)
		_sync_vis_track_detail_from_index(state)
	finally:
		if owned:
			_end_internal_ui_update(state)


def _sync_material_from_prefs(state, mat_name):
	owned = _begin_internal_ui_update(state)
	prefs = _legacy_prefs() or {}
	try:
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
	finally:
		if owned:
			_end_internal_ui_update(state)


def _set_material_selection(state, mat_name, persist=True):
	owned = _begin_internal_ui_update(state)
	try:
		if mat_name == "N/A":
			state.selected_material = "N/A"
			state.material_list_index = -1
			return
		prefs = _legacy_prefs() or {}
		materials = prefs.get("Materials", {})
		if mat_name not in materials:
			return
		state.selected_material = mat_name
		names = [item.name for item in state.material_items]
		if mat_name in names:
			state.material_list_index = names.index(mat_name)
		_sync_material_from_prefs(state, mat_name)
	finally:
		if owned:
			_end_internal_ui_update(state)
	if persist:
		_sync_state_to_legacy_safe(state)


def _sync_material_list_from_prefs(state):
	owned = _begin_internal_ui_update(state)
	prefs = _legacy_prefs() or {}
	try:
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
		if state.selected_material != "N/A":
			_sync_material_from_prefs(state, state.selected_material)
	finally:
		if owned:
			_end_internal_ui_update(state)


def _sync_banned_bones_from_prefs(state):
	prefs = _legacy_prefs() or {}
	state.banned_bones = ", ".join(prefs.get("BannedBones", []))


def _sync_banned_bones_to_prefs(state):
	prefs = _ensure_prefs()
	if prefs is None:
		return
	banned = _parse_banned_bones_text(state.banned_bones)
	prefs["BannedBones"] = banned
	state.banned_bones = ", ".join(banned)


def _on_vis_track_list_index_changed(self, context):
	if _ui_update_active(self):
		return
	items = self.vis_track_items
	if not items:
		owned = _begin_internal_ui_update(self)
		try:
			self.vis_track_list_index = -1
		finally:
			if owned:
				_end_internal_ui_update(self)
		return
	index = max(0, min(self.vis_track_list_index, len(items) - 1))
	owned = _begin_internal_ui_update(self)
	try:
		if index != self.vis_track_list_index:
			self.vis_track_list_index = index
	finally:
		if owned:
			_end_internal_ui_update(self)
	_sync_vis_track_detail_from_index(self)
	_sync_state_to_legacy_safe(self)


def _on_vis_track_changed(self, context):
	if _ui_update_active(self):
		return
	try:
		if self.vis_track_items and 0 <= self.vis_track_list_index < len(self.vis_track_items):
			item = self.vis_track_items[self.vis_track_list_index]
			item.has_track = bool(self.vis_track_enabled)
			item.ipo_type = self.vis_track_ipo_type
			item.ipo_channel = self.vis_track_ipo_channel
			item.ipo_object = self.vis_track_ipo_object
		_sync_state_to_legacy_safe(self)
	except Exception as exc:
		_log_ui_error("_on_vis_track_changed", exc)


def _on_banned_bone_list_index_changed(self, context):
	if _ui_update_active(self):
		return
	items = self.banned_bone_items
	if not items:
		owned = _begin_internal_ui_update(self)
		try:
			self.banned_bone_list_index = -1
		finally:
			if owned:
				_end_internal_ui_update(self)
		return
	index = max(0, min(self.banned_bone_list_index, len(items) - 1))
	owned = _begin_internal_ui_update(self)
	try:
		if index != self.banned_bone_list_index:
			self.banned_bone_list_index = index
	finally:
		if owned:
			_end_internal_ui_update(self)


def _on_material_list_index_changed(self, context):
	if _ui_update_active(self):
		return
	items = self.material_items
	if not items:
		_set_material_selection(self, "N/A", persist=False)
		return
	index = max(0, min(self.material_list_index, len(items) - 1))
	_set_material_selection(self, items[index].name, persist=True)


def _on_sequence_list_index_changed(self, context):
	if _ui_update_active(self):
		return
	items = self.sequence_items
	if not items:
		_set_sequence_selection(self, "N/A", persist=False)
		return
	index = max(0, min(self.sequence_list_index, len(items) - 1))
	_set_sequence_selection(self, items[index].name, persist=True)


def _sync_state_from_legacy(state):
	owned = _begin_internal_ui_update(state)
	prefs = _legacy_prefs() or {}
	try:
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
		_sync_banned_bones_from_state(state)
		state.ui_initialized = True
		_sync_sequence_list_from_prefs(state)
		if state.selected_sequence != "N/A":
			_set_sequence_selection(state, state.selected_sequence, persist=False)
		_sync_material_list_from_prefs(state)
		if state.selected_material == "N/A" or state.selected_material not in prefs.get("Materials", {}):
			mat_names = sorted(prefs.get("Materials", {}).keys(), key=lambda x: x.lower())
			if mat_names:
				_set_material_selection(state, mat_names[0], persist=False)
	finally:
		if owned:
			_end_internal_ui_update(state)


def _on_state_changed(self, context):
	_sync_state_to_legacy_safe(self)


def _sync_state_to_legacy_safe(state):
	if not _begin_internal_ui_update(state):
		return
	state_id = id(state)
	_SYNCING_STATE_IDS.add(state_id)
	try:
		_sync_state_to_legacy(state)
	except Exception as exc:
		print(f"Torque UI sync warning: {exc}")
	finally:
		_SYNCING_STATE_IDS.discard(state_id)
		_end_internal_ui_update(state)


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
	prefs["BannedBones"] = _parse_banned_bones_text(state.banned_bones)

	seq_name = state.selected_sequence
	seq = prefs.get("Sequences", {}).get(seq_name)
	if seq:
		seq["Priority"] = state.seq_priority
		seq["Cyclic"] = state.seq_cyclic
		seq["NoExport"] = state.seq_no_export
		seq["Dsq"] = state.seq_dsq
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
		seq["Vis"]["Tracks"] = {}
		for item in state.vis_track_items:
			if not item.name:
				continue
			seq["Vis"]["Tracks"][item.name] = {
				"hasVisTrack": bool(item.has_track),
				"IPOType": item.ipo_type,
				"IPOChannel": item.ipo_channel,
				"IPOObject": item.ipo_object,
			}

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
	_sync_sequence_list_from_prefs(state)
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


def _snapshot_state(state):
	return {
		"export_basepath": state.export_basepath,
		"export_basename": state.export_basename,
		"dts_version": state.dts_version,
		"write_shape_script": state.write_shape_script,
		"export_scale": state.export_scale,
		"prim_type": state.prim_type,
		"max_strip_size": state.max_strip_size,
		"cluster_depth": state.cluster_depth,
		"always_write_depth": state.always_write_depth,
		"collapse_root_transform": state.collapse_root_transform,
		"tse_material": state.tse_material,
		"billboard_enabled": state.billboard_enabled,
		"billboard_equator": state.billboard_equator,
		"billboard_polar": state.billboard_polar,
		"billboard_polar_angle": state.billboard_polar_angle,
		"billboard_dim": state.billboard_dim,
		"billboard_include_poles": state.billboard_include_poles,
		"billboard_size": state.billboard_size,
		"selected_sequence": state.selected_sequence,
		"seq_priority": state.seq_priority,
		"seq_cyclic": state.seq_cyclic,
		"seq_no_export": state.seq_no_export,
		"seq_total_frames": state.seq_total_frames,
		"seq_duration": state.seq_duration,
		"seq_fps": state.seq_fps,
		"seq_duration_locked": state.seq_duration_locked,
		"seq_fps_locked": state.seq_fps_locked,
		"seq_action_enabled": state.seq_action_enabled,
		"seq_action_start": state.seq_action_start,
		"seq_action_end": state.seq_action_end,
		"seq_action_auto_samples": state.seq_action_auto_samples,
		"seq_action_auto_frames": state.seq_action_auto_frames,
		"seq_action_frame_samples": state.seq_action_frame_samples,
		"seq_action_num_ground_frames": state.seq_action_num_ground_frames,
		"seq_action_blend": state.seq_action_blend,
		"seq_action_blend_ref_action": state.seq_action_blend_ref_action,
		"seq_action_blend_ref_frame": state.seq_action_blend_ref_frame,
		"seq_dsq": state.seq_dsq,
		"seq_ifl_enabled": state.seq_ifl_enabled,
		"seq_ifl_material": state.seq_ifl_material,
		"seq_ifl_num_images": state.seq_ifl_num_images,
		"seq_ifl_total_frames": state.seq_ifl_total_frames,
		"seq_ifl_write_file": state.seq_ifl_write_file,
		"seq_vis_enabled": state.seq_vis_enabled,
		"seq_vis_start": state.seq_vis_start,
		"seq_vis_end": state.seq_vis_end,
		"seq_vis_tracks_summary": state.seq_vis_tracks_summary,
		"vis_track_list_index": state.vis_track_list_index,
		"vis_track_enabled": state.vis_track_enabled,
		"vis_track_ipo_type": state.vis_track_ipo_type,
		"vis_track_ipo_channel": state.vis_track_ipo_channel,
		"vis_track_ipo_object": state.vis_track_ipo_object,
		"selected_material": state.selected_material,
		"material_show_advanced": state.material_show_advanced,
		"mat_swrap": state.mat_swrap,
		"mat_twrap": state.mat_twrap,
		"mat_translucent": state.mat_translucent,
		"mat_additive": state.mat_additive,
		"mat_subtractive": state.mat_subtractive,
		"mat_self_illum": state.mat_self_illum,
		"mat_never_env_map": state.mat_never_env_map,
		"mat_no_mipmap": state.mat_no_mipmap,
		"mat_mipmap_zero_border": state.mat_mipmap_zero_border,
		"mat_ifl_material": state.mat_ifl_material,
		"mat_detail_map_flag": state.mat_detail_map_flag,
		"mat_bump_map_flag": state.mat_bump_map_flag,
		"mat_reflectance_map_flag": state.mat_reflectance_map_flag,
		"mat_detail_tex": state.mat_detail_tex,
		"mat_bump_tex": state.mat_bump_tex,
		"mat_ref_tex": state.mat_ref_tex,
		"mat_reflectance": state.mat_reflectance,
		"mat_detail_scale": state.mat_detail_scale,
		"banned_bone_list_index": state.banned_bone_list_index,
		"banned_bones": state.banned_bones,
	}


def _restore_snapshot(state, snapshot):
	owned = _begin_internal_ui_update(state)
	try:
		for key, value in snapshot.items():
			try:
				setattr(state, key, value)
			except Exception as exc:
				_log_ui_error("_restore_snapshot.%s" % key, exc)
	finally:
		if owned:
			_end_internal_ui_update(state)


def _ensure_loaded_state(prefs):
	loaded = prefs.get("LoadedState")
	if loaded is None:
		loaded = {}
		prefs["LoadedState"] = loaded
	return loaded


def _load_saved_snapshot(state):
	prefs = _ensure_prefs()
	if prefs is None:
		return
	loaded = _ensure_loaded_state(prefs)
	if not loaded:
		_sync_state_from_legacy(state)
		_store_saved_snapshot(state)
		return
	_restore_snapshot(state, loaded)
	_sync_banned_bones_from_state(state)
	if state.selected_sequence != "N/A":
		_set_sequence_selection(state, state.selected_sequence, persist=False)
	if state.selected_material != "N/A":
		_set_material_selection(state, state.selected_material, persist=False)


def _store_saved_snapshot(state):
	prefs = _ensure_prefs()
	if prefs is None:
		return
	prefs["LoadedState"] = _snapshot_state(state)


def _bootstrap_ui_state():
	if bpy is None:
		return
	scene = getattr(getattr(bpy, "context", None), "scene", None)
	if scene is None:
		return
	try:
		state = scene.torque_export_ui
	except Exception:
		return
	try:
		_sync_state_from_legacy(state)
	except Exception as exc:
		_log_ui_error("_bootstrap_ui_state", exc)
	try:
		prefs = _ensure_prefs()
		if prefs is not None and not prefs.get("LoadedState"):
			_store_saved_snapshot(state)
	except Exception as exc:
		_log_ui_error("_bootstrap_ui_state.loaded_state", exc)


class TorqueExporterMaterialItem(bpy.types.PropertyGroup):
	name: StringProperty(name="Name", default="")
	summary: StringProperty(name="Summary", default="")
	base_tex: StringProperty(name="Base Texture", default="")
	flags: StringProperty(name="Flags", default="")


class TorqueExporterSequenceItem(bpy.types.PropertyGroup):
	name: StringProperty(name="Name", default="")
	summary: StringProperty(name="Summary", default="")
	action: StringProperty(name="Action", default="")
	flags: StringProperty(name="Flags", default="")


class TorqueExporterVisTrackItem(bpy.types.PropertyGroup):
	name: StringProperty(name="Name", default="")
	has_track: BoolProperty(name="Enabled", default=False)
	ipo_type: StringProperty(name="IPO Type", default="")
	ipo_channel: StringProperty(name="IPO Channel", default="")
	ipo_object: StringProperty(name="IPO Object", default="")


class TorqueExporterBannedBoneItem(bpy.types.PropertyGroup):
	name: StringProperty(name="Pattern", default="", update=_on_banned_bone_item_name_changed)


class TORQUEEXPORTER_UL_banned_bone_items(bpy.types.UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		if self.layout_type in {"DEFAULT", "COMPACT"}:
			row = layout.row(align=True)
			row.prop(item, "name", text="", emboss=True, icon="BONE_DATA")
		elif self.layout_type == "GRID":
			layout.label(text=item.name or "<empty>")


class TORQUEEXPORTER_UL_material_items(bpy.types.UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		if self.layout_type in {"DEFAULT", "COMPACT"}:
			row = layout.row(align=True)
			row.label(text=item.name, icon="MATERIAL")
			if item.base_tex:
				row.label(text=item.base_tex)
			elif item.summary:
				row.label(text=item.summary)
			elif item.flags:
				row.label(text=item.flags)
		elif self.layout_type == "GRID":
			layout.label(text=item.name)


class TORQUEEXPORTER_UL_sequence_items(bpy.types.UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		if self.layout_type in {"DEFAULT", "COMPACT"}:
			row = layout.row(align=True)
			row.label(text=item.name, icon="ACTION")
			if item.summary:
				row.label(text=item.summary)
			elif item.flags:
				row.label(text=item.flags)
		elif self.layout_type == "GRID":
			layout.label(text=item.name)


class TORQUEEXPORTER_UL_vis_track_items(bpy.types.UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		if self.layout_type in {"DEFAULT", "COMPACT"}:
			row = layout.row(align=True)
			row.label(text=item.name, icon="VISIBLE_IPO_ON" if item.has_track else "HIDE_OFF")
			summary = []
			if item.ipo_type:
				summary.append(item.ipo_type)
			if item.ipo_channel:
				summary.append(item.ipo_channel)
			if item.ipo_object:
				summary.append(item.ipo_object)
			if summary:
				row.label(text=" / ".join(summary))
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


class TORQUEEXPORTER_OT_refresh_sequences(bpy.types.Operator):
	bl_idname = "torqueexporter.refresh_sequences"
	bl_label = "Refresh Sequences"
	bl_options = {"INTERNAL"}

	def execute(self, context):
		legacy = _legacy_module()
		if legacy is None:
			self.report({"WARNING"}, "Legacy exporter module is not available")
			return {"CANCELLED"}
		state = context.scene.torque_export_ui
		_sync_sequence_list_from_prefs(state)
		_sync_state_from_legacy(state)
		return {"FINISHED"}


class TORQUEEXPORTER_OT_add_banned_bone(bpy.types.Operator):
	bl_idname = "torqueexporter.add_banned_bone"
	bl_label = "Add Banned Bone"
	bl_options = {"INTERNAL"}

	def execute(self, context):
		state = context.scene.torque_export_ui
		item = state.banned_bone_items.add()
		owned = _begin_internal_ui_update(state)
		try:
			state.banned_bone_list_index = len(state.banned_bone_items) - 1
			item.name = ""
			state.banned_bones = ", ".join(entry.name for entry in state.banned_bone_items if entry.name)
		finally:
			if owned:
				_end_internal_ui_update(state)
		_sync_banned_bones_to_prefs(state)
		return {"FINISHED"}


class TORQUEEXPORTER_OT_remove_banned_bone(bpy.types.Operator):
	bl_idname = "torqueexporter.remove_banned_bone"
	bl_label = "Remove Banned Bone"
	bl_options = {"INTERNAL"}

	def execute(self, context):
		state = context.scene.torque_export_ui
		if not state.banned_bone_items:
			return {"CANCELLED"}
		index = max(0, min(state.banned_bone_list_index, len(state.banned_bone_items) - 1))
		try:
			state.banned_bone_items.remove(index)
		except Exception as exc:
			self.report({"ERROR"}, str(exc))
			return {"CANCELLED"}
		owned = _begin_internal_ui_update(state)
		try:
			state.banned_bone_list_index = min(index, len(state.banned_bone_items) - 1)
			state.banned_bones = ", ".join(item.name for item in state.banned_bone_items if item.name)
		finally:
			if owned:
				_end_internal_ui_update(state)
		_sync_banned_bones_to_prefs(state)
		return {"FINISHED"}


class TorqueExporterUIState(bpy.types.PropertyGroup):
	ui_initialized: BoolProperty(default=False)

	export_basepath: StringProperty(name="Export Path", default="", update=_on_state_changed)
	export_basename: StringProperty(name="Basename", default="", update=_on_state_changed)
	dts_version: IntProperty(name="DTS Version", default=24, min=23, max=24, update=_on_state_changed)
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
		update=_on_state_changed,
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

	selected_sequence: StringProperty(name="Sequence", default="N/A")
	seq_priority: IntProperty(name="Priority", default=0, update=_on_state_changed)
	seq_cyclic: BoolProperty(name="Cyclic", default=False, update=_on_state_changed)
	seq_no_export: BoolProperty(name="No Export", default=False, update=_on_state_changed)
	seq_dsq: BoolProperty(name="DSQ", default=False, update=_on_state_changed)
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
	vis_track_enabled: BoolProperty(name="Track Enabled", default=False, update=_on_vis_track_changed)
	vis_track_ipo_type: StringProperty(name="IPO Type", default="", update=_on_vis_track_changed)
	vis_track_ipo_channel: StringProperty(name="IPO Channel", default="", update=_on_vis_track_changed)
	vis_track_ipo_object: StringProperty(name="IPO Object", default="", update=_on_vis_track_changed)

	sequence_list_index: IntProperty(name="Sequence Index", default=-1, update=_on_sequence_list_index_changed)
	sequence_items: CollectionProperty(type=TorqueExporterSequenceItem)
	vis_track_list_index: IntProperty(name="Visibility Track Index", default=-1, update=_on_vis_track_list_index_changed)
	vis_track_items: CollectionProperty(type=TorqueExporterVisTrackItem)

	selected_material: StringProperty(name="Material", default="N/A")
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
	banned_bone_list_index: IntProperty(
		name="Banned Bone Index",
		default=-1,
		update=_on_banned_bone_list_index_changed,
	)
	banned_bone_items: CollectionProperty(type=TorqueExporterBannedBoneItem)


class TORQUEEXPORTER_OT_refresh_ui(bpy.types.Operator):
	bl_idname = "torqueexporter.reset_ui"
	bl_label = "Reset Torque UI"
	bl_options = {"INTERNAL"}

	def execute(self, context):
		state = context.scene.torque_export_ui
		_load_saved_snapshot(state)
		_sync_state_to_legacy_safe(state)
		return {"FINISHED"}


class TORQUEEXPORTER_OT_export_from_ui(bpy.types.Operator):
	bl_idname = "torqueexporter.export_from_ui"
	bl_label = "Export DTS"
	bl_options = {"REGISTER"}

	def execute(self, context):
		_sync_state_to_legacy_safe(context.scene.torque_export_ui)
		_store_saved_snapshot(context.scene.torque_export_ui)
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
		layout = self.layout
		try:
			state = context.scene.torque_export_ui
			row = layout.row(align=True)
			row.operator("torqueexporter.reset_ui", text="Reset")
			row.operator("torqueexporter.export_from_ui", text="Export", icon="EXPORT")

			if not state.ui_initialized:
				box = layout.box()
				box.label(text="Torque UI not initialized")
				box.label(text="Use Reset to load current saved state.")
				return

			_draw_main(layout, state)
		except Exception as exc:
			_log_ui_error("TORQUEEXPORTER_PT_scene_panel.draw", exc)
			box = layout.box()
			box.label(text="Torque Exporter UI error")
			box.label(text=str(exc))
			box.label(text="See console for details.")


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
	head = box.row(align=True)
	head.label(text="Sequences come from the scene's actions and are configured here.")
	head.operator("torqueexporter.refresh_sequences", text="", icon="FILE_REFRESH")
	if len(state.sequence_items) == 0:
		box.label(text="No sequences imported. Refresh to pull from prefs or actions.")
		return
	list_box = box.box()
	list_box.template_list(
		"TORQUEEXPORTER_UL_sequence_items",
		"",
		state,
		"sequence_items",
		state,
		"sequence_list_index",
		rows=7,
	)
	if state.sequence_list_index < 0 or len(state.sequence_items) == 0:
		box.label(text="No sequence selected")
		return

	gen = box.box()
	gen.label(text="General")
	gencol = gen.column(align=True)
	row = gencol.row(align=True)
	row.prop(state, "seq_priority")
	row.prop(state, "seq_cyclic")
	row = gencol.row(align=True)
	row.prop(state, "seq_no_export")
	row.prop(state, "seq_dsq")
	row.prop(state, "seq_total_frames")
	row = gencol.row(align=True)
	row.prop(state, "seq_duration")
	row.prop(state, "seq_fps")
	row = gencol.row(align=True)
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
	viscol.label(text="Visibility tracks come from scene objects and map to IPO-based material/alpha tracks.")
	track_box = vis.box()
	track_box.template_list(
		"TORQUEEXPORTER_UL_vis_track_items",
		"",
		state,
		"vis_track_items",
		state,
		"vis_track_list_index",
		rows=6,
	)
	track_detail = vis.box()
	track_detail.label(text="General")
	tdcol = track_detail.column(align=True)
	tdcol.enabled = state.seq_vis_enabled and state.vis_track_list_index >= 0 and len(state.vis_track_items) > 0
	tdcol.prop(state, "vis_track_enabled")
	tdcol.prop(state, "vis_track_ipo_type")
	tdcol.prop(state, "vis_track_ipo_channel")
	tdcol.prop(state, "vis_track_ipo_object")
	viscol.label(text=f"Tracks: {state.seq_vis_tracks_summary or 'none'}")


def _draw_material_block(layout, state):
	box = layout.box()
	box.label(text="Materials")
	head = box.row(align=True)
	head.label(text="Material list")
	head.operator("torqueexporter.refresh_materials", text="", icon="FILE_REFRESH")
	head.prop(state, "material_show_advanced", text="Advanced", toggle=True)

	if len(state.material_items) == 0:
		box.label(text="No materials imported. Refresh to pull from the current scene.")
		return

	list_box = box.box()
	list_box.template_list(
		"TORQUEEXPORTER_UL_material_items",
		"",
		state,
		"material_items",
		state,
		"material_list_index",
		rows=7,
	)

	selected_ok = state.material_list_index >= 0 and len(state.material_items) > 0
	gen = box.box()
	gen.label(text="General")
	detail = gen.column(align=True)
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
		adv = box.box()
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
	box.label(text="Banned Bones")
	col = box.column(align=True)
	col.prop(state, "banned_bones", text="")
	box.label(text="Enter a comma-separated list of bone names or wildcards like Head*, Toe?, Spine*.")


def _draw_about_block(layout, state):
	box = layout.box()
	box.label(text="About")
	box.label(text="Torque DTS exporter UI port")
	box.label(text="This panel mirrors the old exporter state while using Blender 4.x UI.")


def _draw_main(layout, state):
	_draw_export_block(layout, state)
	_draw_sequence_block(layout, state)
	_draw_armature_block(layout, state)
	_draw_material_block(layout, state)
	_draw_general_block(layout, state)
	_draw_about_block(layout, state)


_CLASSES = (
	TorqueExporterMaterialItem,
	TorqueExporterSequenceItem,
	TorqueExporterVisTrackItem,
	TorqueExporterBannedBoneItem,
	TORQUEEXPORTER_UL_banned_bone_items,
	TORQUEEXPORTER_UL_material_items,
	TORQUEEXPORTER_UL_sequence_items,
	TORQUEEXPORTER_UL_vis_track_items,
	TorqueExporterUIState,
	TORQUEEXPORTER_OT_refresh_materials,
	TORQUEEXPORTER_OT_refresh_sequences,
	TORQUEEXPORTER_OT_refresh_ui,
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
	_bootstrap_ui_state()


def unregister():
	if bpy is None:
		return
	if hasattr(bpy.types.Scene, "torque_export_ui"):
		del bpy.types.Scene.torque_export_ui
	for cls in reversed(_CLASSES):
		bpy.utils.unregister_class(cls)
