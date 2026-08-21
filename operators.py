# SPDX-FileCopyrightText: 2026 Brianna O'Leary
# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
from bpy.props import StringProperty

from . import core
from .constants import MATERIAL_POINTER_NAME, VRML_DEFAULTS
from .vrml_text import format_material_block, has_material_block, parse_material_block


def _editable_material(material: bpy.types.Material | None) -> bool:
    if material is None:
        return False
    return not material.library or material.override_library is not None


def _active_initialized_material(context: bpy.types.Context) -> bpy.types.Material | None:
    material = core.active_material(context)
    if material is None:
        return None
    properties = getattr(material, MATERIAL_POINTER_NAME, None)
    return material if properties is not None and properties.initialized else None


class VRML2_OT_create_material(bpy.types.Operator):
    bl_idname = "vrml2.create_material"
    bl_label = "Create VRML2 Material"
    bl_description = "Create and assign a new material controlled by VRML2 Material settings"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return core.material_supports_slots(getattr(context, "object", None))

    def execute(self, context):
        obj = context.object
        material = bpy.data.materials.new(name=f"VRML2_{obj.name}")
        core.prepare_new_material(material)

        try:
            obj.data.materials.append(material)
            obj.active_material_index = len(obj.material_slots) - 1
        except (AttributeError, RuntimeError) as exc:
            bpy.data.materials.remove(material)
            self.report({"ERROR"}, f"Could not assign a material to this object: {exc}")
            return {"CANCELLED"}

        core.initialize_material(material, dict(VRML_DEFAULTS), def_name=material.name, enable_export=True)
        self.report({"INFO"}, f"Created {material.name}")
        return {"FINISHED"}


class VRML2_OT_initialize_material(bpy.types.Operator):
    bl_idname = "vrml2.initialize_material"
    bl_label = "Initialize Existing Material"
    bl_description = (
        "Read approximate values from the current Blender material, add VRML2 data, "
        "and preserve the current surface connection for restoration"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        material = core.active_material(context)
        return _editable_material(material)

    def execute(self, context):
        material = core.active_material(context)
        if not _editable_material(material):
            self.report({"ERROR"}, "The active material is linked and not editable")
            return {"CANCELLED"}

        values = core.read_existing_blender_values(material)
        core.initialize_material(material, values, def_name=material.name, enable_export=True)
        self.report({"INFO"}, "VRML2 settings initialized; the original shader is preserved")
        return {"FINISHED"}


class VRML2_OT_copy_material_block(bpy.types.Operator):
    bl_idname = "vrml2.copy_material_block"
    bl_label = "Copy Material Block"
    bl_description = "Copy the active material's VRML2 Material block to the system clipboard"

    @classmethod
    def poll(cls, context):
        return _active_initialized_material(context) is not None

    def execute(self, context):
        material = _active_initialized_material(context)
        properties = getattr(material, MATERIAL_POINTER_NAME)
        context.window_manager.clipboard = format_material_block(
            core.property_values(properties),
            def_name=properties.def_name,
        )
        self.report({"INFO"}, "Copied VRML2 Material block")
        return {"FINISHED"}


class VRML2_OT_paste_material_block(bpy.types.Operator):
    bl_idname = "vrml2.paste_material_block"
    bl_label = "Paste Material Block"
    bl_description = "Read VRML2 Material values from the system clipboard"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _editable_material(core.active_material(context))

    def execute(self, context):
        material = core.active_material(context)
        clipboard = context.window_manager.clipboard
        parsed = parse_material_block(clipboard)
        complete_block = has_material_block(clipboard)
        recognized_fields = set(parsed).intersection(
            {
                "ambient_intensity",
                "diffuse_color",
                "emissive_color",
                "shininess",
                "specular_color",
                "transparency",
                "def_name",
            }
        )
        if not recognized_fields and not complete_block:
            self.report({"ERROR"}, "The clipboard does not contain recognizable VRML2 Material values")
            return {"CANCELLED"}

        if complete_block:
            values = dict(VRML_DEFAULTS)
            values.update(parsed)
        else:
            values = dict(parsed)

        properties = getattr(material, MATERIAL_POINTER_NAME)
        if not properties.initialized:
            core.initialize_material(material, dict(VRML_DEFAULTS), def_name=material.name, enable_export=True)

        was_clamped = core.apply_values(material, values)
        message = (
            f"Pasted Material block with {len(recognized_fields)} explicit field(s)"
            if complete_block
            else f"Pasted {len(recognized_fields)} VRML2 field(s)"
        )
        if was_clamped:
            message += "; out-of-range values were clamped to 0–1"
        self.report({"WARNING"} if was_clamped else {"INFO"}, message)
        return {"FINISHED"}


class VRML2_OT_set_field_default(bpy.types.Operator):
    bl_idname = "vrml2.set_field_default"
    bl_label = "Set VRML97 Default"
    bl_description = "Reset this field to its VRML97 default value"
    bl_options = {"REGISTER", "UNDO"}

    field: StringProperty(options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return _editable_material(_active_initialized_material(context))

    def execute(self, context):
        labels = {
            "ambient_intensity": "Ambient Intensity",
            "emissive_color": "Emissive Color",
            "specular_color": "Specular Color",
        }
        if self.field not in labels:
            self.report({"ERROR"}, "This field does not have a supported default action")
            return {"CANCELLED"}

        material = _active_initialized_material(context)
        core.apply_values(material, {self.field: VRML_DEFAULTS[self.field]})
        value = VRML_DEFAULTS[self.field]
        formatted = (
            " ".join(str(component) for component in value)
            if isinstance(value, tuple)
            else str(value)
        )
        self.report({"INFO"}, f"{labels[self.field]} reset to VRML97 default {formatted}")
        return {"FINISHED"}


class VRML2_OT_make_single_user(bpy.types.Operator):
    bl_idname = "vrml2.make_single_user"
    bl_label = "Make Material Single User"
    bl_description = "Duplicate the active material so changes affect only the active object slot"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = getattr(context, "object", None)
        material = core.active_material(context)
        return bool(obj and material and material.users > 1 and len(obj.material_slots) > 0)

    def execute(self, context):
        obj = context.object
        source = obj.active_material
        duplicate = source.copy()
        duplicate.name = f"{source.name}_Single"
        obj.material_slots[obj.active_material_index].material = duplicate
        core.sync_material(duplicate)
        self.report({"INFO"}, f"Created single-user copy {duplicate.name}")
        return {"FINISHED"}


class VRML2_OT_assign_to_selected(bpy.types.Operator):
    bl_idname = "vrml2.assign_to_selected"
    bl_label = "Assign to Selected Objects"
    bl_description = "Assign the active VRML2 material to all other selected objects that support materials"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        material = _active_initialized_material(context)
        return material is not None and len(getattr(context, "selected_objects", ())) > 1

    def execute(self, context):
        material = _active_initialized_material(context)
        active_obj = context.object
        assigned = 0

        for obj in context.selected_objects:
            if obj == active_obj or not core.material_supports_slots(obj):
                continue
            materials = obj.data.materials
            existing_index = next((index for index, item in enumerate(materials) if item == material), -1)
            if existing_index < 0:
                try:
                    materials.append(material)
                    existing_index = len(materials) - 1
                except RuntimeError:
                    continue
            obj.active_material_index = existing_index
            assigned += 1

        self.report({"INFO"}, f"Assigned material to {assigned} selected object(s)")
        return {"FINISHED"}


class VRML2_OT_remove_material_data(bpy.types.Operator):
    bl_idname = "vrml2.remove_material_data"
    bl_label = "Remove VRML2 Data"
    bl_description = "Restore the original shader, remove generated preview nodes, and delete VRML2 custom properties"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _active_initialized_material(context) is not None

    def invoke(self, context, _event):
        return context.window_manager.invoke_confirm(self, _event)

    def execute(self, context):
        material = _active_initialized_material(context)
        core.remove_vrml2_data(material)
        self.report({"INFO"}, "Removed VRML2 data and restored the original shader")
        return {"FINISHED"}


CLASSES = (
    VRML2_OT_create_material,
    VRML2_OT_initialize_material,
    VRML2_OT_copy_material_block,
    VRML2_OT_paste_material_block,
    VRML2_OT_set_field_default,
    VRML2_OT_make_single_user,
    VRML2_OT_assign_to_selected,
    VRML2_OT_remove_material_data,
)
