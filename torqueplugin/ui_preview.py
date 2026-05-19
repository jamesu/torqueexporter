"""Blender 4.x UI preview scaffolding for the Torque exporter.

This module intentionally contains placeholder UI only. It is meant to
show the scale and context of three likely UI placements before the real
controls are ported over:

1. A wide Properties editor panel.
2. A compact 3D View sidebar panel.
3. A popup/dialog operator.
"""

try:
	import bpy
except ImportError:  # pragma: no cover - outside Blender
	bpy = None


PREVIEW_SECTIONS = [
	("Export", [
		"File path / basename",
		"Scale / output settings",
		"Export action button",
	]),
	("Hierarchy", [
		"Scene roots",
		"Detail levels",
		"Collision / LOS meshes",
	]),
	("Sequences", [
		"Common / Action / IFL / Visibility",
		"Frame range / sampling",
		"Sequence list",
	]),
	("Armatures", [
		"Root bone binding",
		"Bone ordering / constraints",
		"Pose preview / validation",
	]),
	("Materials", [
		"Texture slots / images",
		"Material flags",
		"Detail / bump / reflectance",
	]),
	("Advanced", [
		"Legacy compatibility mode",
		"Modern 4.x layout mode",
		"Debug / diagnostics",
	]),
]


def draw_preview(layout, compact=False, mode_label="legacy-style", include_notes=True):
	layout.use_property_split = False
	layout.use_property_decorate = False

	header = layout.box()
	header.label(text=f"Torque Exporter UI Preview ({mode_label})")
	if include_notes:
		header.label(text="Placeholder only. No exporter controls wired yet.")
		header.label(text="Use this to judge scale and context before porting.")

	for title, items in PREVIEW_SECTIONS:
		box = layout.box()
		box.label(text=title)
		col = box.column(align=True)
		if compact:
			for item in items[:2]:
				col.label(text=f"• {item}")
		else:
			for item in items:
				col.label(text=f"• {item}")


if bpy is not None:
	class TORQUEEXPORTER_PT_preview_properties(bpy.types.Panel):
		bl_idname = "TORQUEEXPORTER_PT_preview_properties"
		bl_label = "Torque Exporter Preview"
		bl_space_type = "PROPERTIES"
		bl_region_type = "WINDOW"
		bl_context = "scene"

		def draw(self, context):
			draw_preview(self.layout, compact=False, mode_label="wide Properties editor")


	class TORQUEEXPORTER_PT_preview_sidebar(bpy.types.Panel):
		bl_idname = "TORQUEEXPORTER_PT_preview_sidebar"
		bl_label = "Torque Exporter Preview"
		bl_space_type = "VIEW_3D"
		bl_region_type = "UI"
		bl_category = "Torque"

		def draw(self, context):
			draw_preview(self.layout, compact=True, mode_label="3D View sidebar")


	class TORQUEEXPORTER_OT_preview_dialog(bpy.types.Operator):
		bl_idname = "torqueexporter.preview_dialog"
		bl_label = "Torque Exporter Preview Dialog"
		bl_options = {"REGISTER", "INTERNAL"}

		def invoke(self, context, event):
			return context.window_manager.invoke_props_dialog(self, width=560)

		def draw(self, context):
			draw_preview(self.layout, compact=False, mode_label="popup dialog", include_notes=True)

		def execute(self, context):
			return {"FINISHED"}


	_CLASSES = (
		TORQUEEXPORTER_PT_preview_properties,
		TORQUEEXPORTER_PT_preview_sidebar,
		TORQUEEXPORTER_OT_preview_dialog,
	)


	def register():
		for cls in _CLASSES:
			bpy.utils.register_class(cls)


	def unregister():
		for cls in reversed(_CLASSES):
			bpy.utils.unregister_class(cls)
else:
	def register():
		return None


	def unregister():
		return None
