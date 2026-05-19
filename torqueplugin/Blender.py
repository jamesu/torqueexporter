"""Legacy Blender API compatibility shim.

This module lets the old exporter code continue to import `Blender` while
routing the supported calls to modern `bpy`/`mathutils` APIs when available.
"""

from __future__ import annotations

import sys as _sys
import time as _time
from types import ModuleType, SimpleNamespace

try:
	import bpy
	import mathutils
except ImportError:  # pragma: no cover - legacy Blender 2.x or no Blender
	bpy = None
	mathutils = None

import blender_compat as bc

__path__ = []  # allow "from Blender.Window import ..." style legacy imports


class _EnumNamespace(SimpleNamespace):
	def __getitem__(self, key):
		return getattr(self, key)

	def get(self, key, default=None):
		return getattr(self, key, default)

	def keys(self):
		return self.__dict__.keys()


class _NoOpNamespace(_EnumNamespace):
	def __getattr__(self, _name):
		return _noop


def _noop(*_args, **_kwargs):
	return None


def _module(name):
	return ModuleType(name)


def _wrap(obj):
	if obj is None:
		return None
	if isinstance(obj, _ObjectProxy):
		return obj
	return _ObjectProxy(obj)


def _flatten_channel_ipos(channel_ipos):
	curves = {}
	for ipo in channel_ipos.values():
		curves.update(ipo._curves)
	return curves


class _ObjectProxy:
	def __init__(self, obj):
		self._obj = obj

	def __getattr__(self, name):
		return getattr(self._obj, name)

	@property
	def name(self):
		return self._obj.name

	@name.setter
	def name(self, value):
		self._obj.name = value

	@property
	def parent(self):
		return _wrap(self._obj.parent)

	@property
	def parentbonename(self):
		return getattr(self._obj, "parent_bone", None)

	@property
	def parentType(self):
		return getattr(self._obj, "parent_type", None)

	@property
	def type(self):
		return self.getType()

	@property
	def constraints(self):
		return self._obj.constraints

	@property
	def modifiers(self):
		return self._obj.modifiers

	def getName(self):
		return self._obj.name

	def getType(self):
		otype = getattr(self._obj, "type", "EMPTY")
		return {
			"ARMATURE": "Armature",
			"MESH": "Mesh",
			"CAMERA": "Camera",
			"EMPTY": "Empty",
			"CURVE": "Curve",
			"LATTICE": "Lattice",
		}.get(otype, otype.title())

	def getData(self, *args):
		return self._obj.data

	def getParent(self):
		return _wrap(self._obj.parent)

	def getPose(self):
		return getattr(self._obj, "pose", None)

	def getIpo(self):
		return _wrap_animation_owner(self._obj)

	def getMatrix(self, space="worldspace"):
		return self._obj.matrix_world.copy()

	def getSize(self, space="worldspace"):
		return self._obj.scale.copy()

	def setLocation(self, x, y, z):
		self._obj.location = (x, y, z)

	def setMatrix(self, matrix):
		self._obj.matrix_world = matrix

	def select(self, state=True):
		self._obj.select_set(state)

	def link(self, data):
		self._obj.data = data

	def makeParent(self, objects, *_args):
		for obj in objects:
			if isinstance(obj, _ObjectProxy):
				obj = obj._obj
			obj.parent = self._obj


class _TextureDataProxy:
	def __init__(self, image=None, type_name="IMAGE", image_flags=0):
		self.image = image
		self.type = type_name
		self.imageFlags = image_flags


class _TextureSlotProxy:
	def __init__(self, tex=None, mapto=0):
		self.tex = tex or _TextureDataProxy()
		self.mapto = mapto


class _MaterialProxy:
	def __init__(self, material):
		self._material = material

	def __getattr__(self, name):
		return getattr(self._material, name)

	@property
	def name(self):
		return self._material.name

	def getIpo(self):
		return _wrap_animation_owner(self._material)

	def getEmit(self):
		return float(getattr(self._material, "emission_strength", 0.0) or 0.0)

	def getAlpha(self):
		try:
			return float(self._material.diffuse_color[3])
		except Exception:
			return 1.0

	def getRef(self):
		return 0.0

	def getTextures(self):
		textures = []
		if getattr(self._material, "use_nodes", False) and getattr(self._material, "node_tree", None) is not None:
			for node in self._material.node_tree.nodes:
				if getattr(node, "type", None) != "TEX_IMAGE":
					continue
				name = (getattr(node, "label", "") or getattr(node, "name", "")).lower()
				mapto = 0
				if "normal" in name:
					mapto = getattr(Texture.MapTo, "NOR", 0)
				elif "ref" in name or "reflect" in name:
					mapto = getattr(Texture.MapTo, "REF", 0)
				elif self.getAlpha() < 1.0:
					mapto = getattr(Texture.MapTo, "ALPHA", 0)
				tex = _TextureDataProxy(image=getattr(node, "image", None), type_name=Texture.Types.IMAGE, image_flags=getattr(Texture.ImageFlags, "MIPMAP", 0))
				textures.append(_TextureSlotProxy(tex=tex, mapto=mapto))
		return textures


class _BezierPointProxy:
	def __init__(self, point):
		self._point = point

	@property
	def vec(self):
		return [self._point.co[0], self._point.co[1]]

	@vec.setter
	def vec(self, value):
		self._point.co = (float(value[0]), float(value[1]))

	@property
	def handleTypes(self):
		return getattr(self._point, "handle_left_type", None), getattr(self._point, "handle_right_type", None)

	@handleTypes.setter
	def handleTypes(self, value):
		try:
			self._point.handle_left_type, self._point.handle_right_type = value
		except Exception:
			pass


class _CurveProxy:
	def __init__(self, owner, name, fcurve):
		self._owner = owner
		self._name = name
		self._fcurve = fcurve

	def getName(self):
		return self._name

	@property
	def bezierPoints(self):
		return [_BezierPointProxy(point) for point in self._fcurve.keyframe_points]

	def append(self, value):
		frame, amount = value
		self._fcurve.keyframe_points.insert(float(frame), float(amount))

	def recalc(self):
		try:
			self._fcurve.update()
		except Exception:
			pass

	def __getitem__(self, frame):
		try:
			return float(self._fcurve.evaluate(float(frame)))
		except Exception:
			return None


class _IpoProxy:
	def __init__(self, owner, action, curves):
		self._owner = owner
		self._action = action
		self._curves = curves
		self.curveConsts = {
			"LocX": "LocX",
			"LocY": "LocY",
			"LocZ": "LocZ",
			"QuatW": "QuatW",
			"QuatX": "QuatX",
			"QuatY": "QuatY",
			"QuatZ": "QuatZ",
			"RotX": "RotX",
			"RotY": "RotY",
			"RotZ": "RotZ",
			"ScaleX": "ScaleX",
			"ScaleY": "ScaleY",
			"ScaleZ": "ScaleZ",
		}

	def getCurves(self):
		return list(self._curves.values())

	def getNcurves(self):
		return len(self._curves)

	def getCurve(self, name):
		return self._curves.get(name)

	def addCurve(self, name):
		if name in self._curves:
			return self._curves[name]
		fcurve = _ensure_fcurve(self._action, self._owner, name)
		curve = _CurveProxy(self, name, fcurve)
		self._curves[name] = curve
		return curve

	def __getitem__(self, key):
		if key in self._curves:
			return self._curves[key]
		if key == 0:
			return self._curves.get("ScaleX")
		if key == 1:
			return self._curves.get("ScaleY")
		if key == 2:
			return self._curves.get("ScaleZ")
		return None

	def __setitem__(self, key, value):
		if value is not None:
			return
		name = {0: "ScaleX", 1: "ScaleY", 2: "ScaleZ"}.get(key, key)
		self._curves.pop(name, None)


class _ActionProxy:
	def __init__(self, action):
		self._action = action

	def getName(self):
		return self._action.name

	def getFrameNumbers(self):
		frames = set()
		for fcurve in getattr(self._action, "fcurves", []):
			for point in fcurve.keyframe_points:
				frames.add(int(round(point.co[0])))
		return sorted(frames)

	def setActive(self, arm):
		arm_obj = arm._obj if isinstance(arm, _ObjectProxy) else arm
		if hasattr(arm_obj, "animation_data_create"):
			anim_data = arm_obj.animation_data_create()
			anim_data.action = self._action
			return
		data = getattr(arm_obj, "data", None)
		if data is not None and hasattr(data, "animation_data_create"):
			anim_data = data.animation_data_create()
			anim_data.action = self._action

	def getAllChannelIpos(self):
		return _action_channel_ipos(self._action)


def _legacy_channel_name(data_path, array_index):
	if data_path == "location":
		return ["LocX", "LocY", "LocZ"][array_index]
	if data_path == "rotation_euler":
		return ["RotX", "RotY", "RotZ"][array_index]
	if data_path == "scale":
		return ["ScaleX", "ScaleY", "ScaleZ"][array_index]
	if data_path == "rotation_quaternion":
		return ["QuatW", "QuatX", "QuatY", "QuatZ"][array_index]
	return f"{data_path}:{array_index}"


def _ensure_fcurve(action, owner, legacy_name):
	data_path, index = _legacy_to_fcurve(owner, legacy_name)
	if data_path is None:
		raise ValueError(legacy_name)
	for fcurve in action.fcurves:
		if fcurve.data_path == data_path and fcurve.array_index == index:
			return fcurve
	return action.fcurves.new(data_path=data_path, index=index)


def _legacy_to_fcurve(owner, legacy_name):
	if legacy_name in ("LocX", "LocY", "LocZ"):
		return "location", {"LocX": 0, "LocY": 1, "LocZ": 2}[legacy_name]
	if legacy_name in ("RotX", "RotY", "RotZ"):
		return "rotation_euler", {"RotX": 0, "RotY": 1, "RotZ": 2}[legacy_name]
	if legacy_name in ("ScaleX", "ScaleY", "ScaleZ"):
		return "scale", {"ScaleX": 0, "ScaleY": 1, "ScaleZ": 2}[legacy_name]
	if legacy_name in ("QuatW", "QuatX", "QuatY", "QuatZ"):
		return "rotation_quaternion", {"QuatW": 0, "QuatX": 1, "QuatY": 2, "QuatZ": 3}[legacy_name]
	return None, None


def _action_channel_ipos(action):
	channels = {}
	for fcurve in getattr(action, "fcurves", []):
		name = _legacy_channel_name(fcurve.data_path, fcurve.array_index)
		proxy = channels.get(fcurve.data_path)
		if proxy is None:
			proxy = _IpoProxy(action, action, {})
			proxy._curves = {}
			proxy.curveConsts = {
				"LocX": "LocX",
				"LocY": "LocY",
				"LocZ": "LocZ",
				"QuatW": "QuatW",
				"QuatX": "QuatX",
				"QuatY": "QuatY",
				"QuatZ": "QuatZ",
				"RotX": "RotX",
				"RotY": "RotY",
				"RotZ": "RotZ",
				"ScaleX": "ScaleX",
				"ScaleY": "ScaleY",
				"ScaleZ": "ScaleZ",
			}
			channels[fcurve.data_path] = proxy
		proxy._curves[name] = _CurveProxy(proxy, name, fcurve)
	return channels


def _wrap_animation_owner(obj):
	action = None
	if hasattr(obj, "animation_data") and obj.animation_data is not None:
		action = getattr(obj.animation_data, "action", None)
	if action is None and hasattr(obj, "data") and hasattr(obj.data, "animation_data"):
		anim_data = obj.data.animation_data
		if anim_data is not None:
			action = getattr(anim_data, "action", None)
	if action is None:
		return None
	return _IpoProxy(obj, action, _flatten_channel_ipos(_action_channel_ipos(action)))


class _SceneProxy:
	def __init__(self, scene):
		self._scene = scene
		self.objects = _SceneObjectsProxy(scene)

	def update(self, *args, **kwargs):
		return None

	def getRenderingContext(self):
		return self

	def framesPerSec(self):
		if bpy is None:
			return 25
		return self._scene.render.fps

	def currentFrame(self, frame):
		self._scene.frame_set(frame)

	def makeCurrent(self):
		return None


class _SceneObjectsProxy:
	def __init__(self, scene):
		self._scene = scene

	def link(self, obj):
		if isinstance(obj, _ObjectProxy):
			obj = obj._obj
		if bpy is not None:
			self._scene.collection.objects.link(obj)

	def __iter__(self):
		return iter([_wrap(o) for o in self._scene.objects])


class Object:
	class ParentTypes:
		ARMATURE = "ARMATURE"

	@staticmethod
	def Get(name=None):
		if bpy is None:
			return bc.get_object(name) if name else bc.get_scene_objects()
		if name is None:
			return [_wrap(o) for o in bc.get_scene_objects()]
		obj = bc.get_object(name)
		if obj is None:
			raise ValueError(name)
		return _wrap(obj)

	@staticmethod
	def GetSelected():
		if bpy is None:
			return bc.get_selected_objects()
		return [_wrap(o) for o in bc.get_selected_objects()]

	@staticmethod
	def New(type_name, name):
		if bpy is None:
			return None
		if type_name == "Mesh":
			mesh = bpy.data.meshes.new(name)
			obj = bpy.data.objects.new(name, mesh)
		else:
			obj = bpy.data.objects.new(name, None)
			if type_name == "Empty":
				obj.empty_display_type = "PLAIN_AXES"
		return _wrap(obj)


class Scene:
	@staticmethod
	def GetCurrent():
		return _SceneProxy(bc.get_current_scene()) if bc.get_current_scene() is not None else None


class Material:
	@staticmethod
	def Get(name=None):
		if name is None:
			return [wrap_material(m) for m in bc.get_materials()]
		mat = bc.get_material(name)
		if mat is None:
			raise ValueError(name)
		return wrap_material(mat)


class Text:
	@staticmethod
	def Get(name):
		txt = bc.get_text(name)
		if txt is None:
			raise ValueError(name)
		return txt

	@staticmethod
	def New(name):
		if bpy is None:
			return None
		return bpy.data.texts.new(name)


class Armature:
	class NLA:
		@staticmethod
		def GetActions():
			return bc.get_actions()

	@staticmethod
	def Get(name):
		if bpy is None:
			raise ValueError(name)
		return bpy.data.armatures.get(name)


class Constraint:
	class Settings:
		BONE = "bone"


class Modifier:
	class Types:
		ARMATURE = "ARMATURE"


class Mesh:
	@staticmethod
	def Get(name):
		if bpy is None:
			raise ValueError(name)
		return bpy.data.meshes.get(name)

	@staticmethod
	def New(name):
		if bpy is None:
			return None
		return bpy.data.meshes.new(name)


class Image:
	@staticmethod
	def Get():
		if bpy is None:
			return []
		return list(bpy.data.images)


class Ipo:
	PO_SCALEX = 0
	PO_SCALEY = 1
	PO_SCALEZ = 2


class Window:
	class MButs:
		L = 1

	class Types:
		SCRIPT = "SCRIPT"

	@staticmethod
	def EditMode(state):
		return None

	@staticmethod
	def RedrawAll():
		bc.redraw_all()

	@staticmethod
	def WaitCursor(state):
		return None

	@staticmethod
	def DrawProgressBar(value, text):
		return None

	@staticmethod
	def GetMouseCoords():
		return (0, 0)

	@staticmethod
	def GetMouseButtons():
		return 0

	@staticmethod
	def GetAreaSize():
		return (0, 0)

	@staticmethod
	def GetScreenInfo(_type):
		return [{"vertices": [0, 0, 0, 0]}]

	@staticmethod
	def FileSelector(callback, title, default):
		return None


class Draw:
	LEFTMOUSE = 0
	MIDDLEMOUSE = 1
	RIGHTMOUSE = 2
	MOUSEX = 3
	MOUSEY = 4
	WHEELDOWNMOUSE = 5
	WHEELUPMOUSE = 6
	ESCKEY = 7

	@staticmethod
	def PupMenu(message):
		return 1

	@staticmethod
	def Register(*args, **kwargs):
		return None

	@staticmethod
	def Exit():
		return None


class BGL:
	GL_LINES = 0
	GL_QUADS = 1
	GL_TRIANGLES = 2
	GL_BLEND = 3
	GL_COLOR_BUFFER_BIT = 0
	GL_DEPTH_BUFFER_BIT = 0
	GL_SMOOTH = 0
	GL_SRC_ALPHA = 0
	GL_ONE_MINUS_SRC_ALPHA = 0

	@staticmethod
	def __getattr__(name):
		def _noop(*args, **kwargs):
			return None
		return _noop


class sys:
	@staticmethod
	def time():
		return _time.time()


def Get(key):
	if bpy is None:
		if key == "filename":
			return ""
		if key == "version":
			return "legacy"
		return ""
	if key == "filename":
		return bpy.data.filepath
	if key == "version":
		return bpy.app.version_string
	return ""


def Set(key, value):
	if bpy is not None and key == "curframe":
		bpy.context.scene.frame_set(int(value))


def wrap_object(obj):
	return _wrap(obj)


def wrap_material(material):
	if material is None:
		return None
	if bpy is None:
		return material
	if isinstance(material, _MaterialProxy):
		return material
	return _MaterialProxy(material)


def wrap_action(action):
	if action is None:
		return None
	if bpy is None:
		return action
	if isinstance(action, _ActionProxy):
		return action
	return _ActionProxy(action)


Mathutils = mathutils
BGL = _NoOpNamespace(
	GL_LINES=0,
	GL_QUADS=1,
	GL_TRIANGLES=2,
	GL_BLEND=3,
	GL_COLOR_BUFFER_BIT=0,
	GL_DEPTH_BUFFER_BIT=0,
	GL_SMOOTH=0,
	GL_SRC_ALPHA=0,
	GL_ONE_MINUS_SRC_ALPHA=0,
)
NMesh = _EnumNamespace(
	Modes=_EnumNamespace(TWOSIDED=1),
	FaceModes=_EnumNamespace(TWOSIDE=1),
)
Texture = _EnumNamespace(
	Types=_EnumNamespace(IMAGE="IMAGE"),
	MapTo=_EnumNamespace(ALPHA=1, REF=2, NOR=4),
	ImageFlags=_EnumNamespace(MIPMAP=1),
)
Window.Types = _EnumNamespace(SCRIPT="SCRIPT")
Window.MButs = _EnumNamespace(L=1)
Object.ParentTypes = _EnumNamespace(ARMATURE="ARMATURE")
_window_submodule = ModuleType("Blender.Window")
_window_submodule.Theme = _EnumNamespace()
_sys.modules.setdefault(__name__ + ".Window", _window_submodule)
