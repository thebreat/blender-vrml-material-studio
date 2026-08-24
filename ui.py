# SPDX-FileCopyrightText: 2026 Brianna O'Leary
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import bpy

from . import core, material_library
from .constants import MATERIAL_POINTER_NAME


def _draw_color(
    layout,
    properties,
    property_name: str,
    label: str,
    show_default_button: bool = False,
) -> None:
    box = layout.box()
    row = box.row(align=True)
    row.label(text=label)
    row.prop(properties, property_name, text="")
    if show_default_button:
        operator = row.operator("vrml2.set_field_default", text="Set Default")
        operator.field = property_name

    values = box.row(align=True)
    values.prop(properties, property_name, index=0, text="R")
    values.prop(properties, property_name, index=1, text="G")
    values.prop(properties, property_name, index=2, text="B")


def _draw_material_library(layout, context) -> None:
    header, body = layout.panel("vrml2_contributed_materials", default_closed=True)
    header.label(text="Presets", icon="PRESET")
    if body is None:
        return

    settings = material_library.ensure_items(context.window_manager)
    body.label(text="433 presets by Breetos")
    body.prop(settings, "search", text="", icon="VIEWZOOM")
    body.prop(settings, "category", text="")
    body.template_list(
        "VRML2_UL_contributed_materials",
        "",
        settings,
        "items",
        settings,
        "active_index",
        rows=8,
        maxrows=12,
    )
    body.label(text="Click a preset name to apply it.", icon="INFO")


class VRML2_UL_contributed_materials(bpy.types.UIList):
    bl_idname = "VRML2_UL_contributed_materials"

    def draw_item(
        self,
        _context,
        layout,
        _data,
        item,
        _icon,
        _active_data,
        _active_property,
        _index=0,
        _flt_flag=0,
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.template_icon(
                icon_value=material_library.icon_id(item.preset_index),
                scale=1.5,
            )
            operator = row.operator(
                "vrml2.apply_library_material",
                text=item.name,
            )
            operator.preset_index = item.preset_index
            row.label(text=item.category)
        else:
            layout.label(text="", icon_value=material_library.icon_id(item.preset_index))

    def filter_items(self, _context, data, property_name):
        items = getattr(data, property_name)
        query = data.search.strip().casefold()
        category = data.category
        flags = []
        for item in items:
            visible = (category == "ALL" or item.category == category) and (
                not query or query in item.name.casefold()
            )
            flags.append(self.bitflag_filter_item if visible else 0)
        return flags, []


def draw_material_studio(layout: bpy.types.UILayout, context: bpy.types.Context) -> None:
    obj = getattr(context, "object", None)
    if obj is None:
        layout.label(text="Select an object to edit its active material", icon="INFO")
        return

    if not core.material_supports_slots(obj):
        layout.label(text="This object type does not support material slots", icon="INFO")
        return

    if len(obj.material_slots) > 1:
        layout.prop(obj, "active_material_index", text="Active Material Slot")

    material = obj.active_material
    if material is None:
        layout.label(text="The active object has no material", icon="MATERIAL")
        layout.operator("vrml2.create_material", icon="ADD")
        return

    name_row = layout.row(align=True)
    name_row.label(text=material.name, icon="MATERIAL")
    if material.users > 1:
        name_row.label(text=f"{material.users} users", icon="LINKED")
        name_row.operator("vrml2.make_single_user", text="Single User", icon="DUPLICATE")

    properties = getattr(material, MATERIAL_POINTER_NAME)
    if not properties.initialized:
        intro = layout.box()
        intro.label(text="No VRML2 data is attached to this material.", icon="INFO")
        intro.label(text="Initializing preserves the current surface shader for restoration.")
        column = intro.column(align=True)
        column.operator("vrml2.initialize_material", text="Initialize Existing Material", icon="IMPORT")
        column.operator("vrml2.create_material", text="Create New VRML2 Material", icon="ADD")
        return

    status = layout.row(align=True)
    status.prop(properties, "enabled", text="Use for Export")
    status.prop(properties, "live_preview", text="Live Preview", toggle=True, icon="SHADING_RENDERED")

    layout.prop(properties, "def_name")

    fields = layout.box()
    fields.label(text="VRML2 Material Fields", icon="NODE_MATERIAL")
    _draw_color(fields, properties, "diffuse_color", "Diffuse Color")
    _draw_color(
        fields,
        properties,
        "emissive_color",
        "Emissive Color",
        show_default_button=True,
    )
    _draw_color(
        fields,
        properties,
        "specular_color",
        "Specular Color",
        show_default_button=True,
    )
    ambient_row = fields.row(align=True)
    ambient_row.prop(properties, "ambient_intensity")
    ambient_default = ambient_row.operator("vrml2.set_field_default", text="Set Default")
    ambient_default.field = "ambient_intensity"
    fields.prop(properties, "shininess")
    fields.prop(properties, "transparency")

    tools = layout.row(align=True)
    tools.operator("vrml2.copy_material_block", text="Copy", icon="COPYDOWN")
    tools.operator("vrml2.paste_material_block", text="Paste", icon="PASTEDOWN")

    preview = layout.box()
    preview.label(text="VRML97 Live Preview", icon="SHADING_RENDERED")
    preview.label(text="Ignores Blender lights and HDRIs.")
    preview.label(text="Use Standard View Transform for official viewer color.")
    preview.label(text="Use Material Preview or Rendered viewport shading.")

    selected = getattr(context, "selected_objects", ())
    if len(selected) > 1:
        layout.operator("vrml2.assign_to_selected", icon="MATERIAL")

    layout.separator()
    remove_row = layout.row()
    remove_row.alert = True
    remove_row.operator("vrml2.remove_material_data", icon="TRASH")

    layout.separator()
    _draw_material_library(layout, context)


class VIEW3D_PT_vrml2_material_studio(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_vrml2_material_studio"
    bl_label = "VRML2 Material Studio"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VRML2"

    def draw(self, context):
        draw_material_studio(self.layout, context)


class MATERIAL_PT_vrml2_material_studio(bpy.types.Panel):
    bl_idname = "MATERIAL_PT_vrml2_material_studio"
    bl_label = "VRML2 Material Studio"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"

    @classmethod
    def poll(cls, context):
        return getattr(context, "object", None) is not None

    def draw(self, context):
        draw_material_studio(self.layout, context)


CLASSES = (
    VRML2_UL_contributed_materials,
    VIEW3D_PT_vrml2_material_studio,
    MATERIAL_PT_vrml2_material_studio,
)
