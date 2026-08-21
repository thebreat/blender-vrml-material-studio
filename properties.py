# SPDX-FileCopyrightText: 2026 Brianna O'Leary
# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, StringProperty

from . import core
from .constants import VRML_DEFAULTS, VRML_FIELD_INCLUSION_DEFAULTS
from .vrml_shader import LIGHTING_ITEMS


def _update_material(properties, _context) -> None:
    material = getattr(properties, "id_data", None)
    if not isinstance(material, bpy.types.Material) or core.updates_suspended(material):
        return
    try:
        core.sync_material(material)
    except Exception as exc:
        print(f"VRML2 Material Studio update failed for {material.name!r}: {exc}")


class VRML2MaterialProperties(bpy.types.PropertyGroup):
    initialized: BoolProperty(
        name="Initialized",
        description="Internal flag indicating that this material has VRML2 data",
        default=False,
        options={"HIDDEN"},
    )
    enabled: BoolProperty(
        name="Use for VRML2 Export",
        description="Mark this material for export by a VRML2 exporter",
        default=True,
        update=_update_material,
    )
    live_preview: BoolProperty(
        name="Live Preview",
        description="Route the Blender material output through the VRML2 approximation shader",
        default=True,
        update=_update_material,
    )
    def_name: StringProperty(
        name="DEF Name",
        description="Optional VRML DEF identifier for later DEF/USE export",
        default="",
        update=_update_material,
    )
    ambient_intensity: FloatProperty(
        name="Ambient Intensity",
        description="VRML2 ambientIntensity; a single scalar multiplied by diffuseColor",
        min=0.0,
        max=1.0,
        default=VRML_DEFAULTS["ambient_intensity"],
        precision=4,
        update=_update_material,
    )
    diffuse_color: FloatVectorProperty(
        name="Diffuse Color",
        description="VRML2 diffuseColor RGB values",
        size=3,
        subtype="COLOR_GAMMA",
        min=0.0,
        max=1.0,
        default=VRML_DEFAULTS["diffuse_color"],
        precision=4,
        update=_update_material,
    )
    include_emissive_color: BoolProperty(
        name="Include Emissive Color",
        description="Write emissiveColor to VRML; when omitted VRML uses 0 0 0",
        default=VRML_FIELD_INCLUSION_DEFAULTS["include_emissive_color"],
        update=_update_material,
    )
    emissive_color: FloatVectorProperty(
        name="Emissive Color",
        description="VRML2 emissiveColor RGB values",
        size=3,
        subtype="COLOR_GAMMA",
        min=0.0,
        max=1.0,
        default=VRML_DEFAULTS["emissive_color"],
        precision=4,
        update=_update_material,
    )
    shininess: FloatProperty(
        name="Shininess",
        description="VRML2 shininess from 0 (broad highlight) to 1 (tight highlight)",
        min=0.0,
        max=1.0,
        default=VRML_DEFAULTS["shininess"],
        precision=4,
        update=_update_material,
    )
    include_specular_color: BoolProperty(
        name="Include Specular Color",
        description="Write specularColor to VRML; when omitted VRML uses 0 0 0",
        default=VRML_FIELD_INCLUSION_DEFAULTS["include_specular_color"],
        update=_update_material,
    )
    specular_color: FloatVectorProperty(
        name="Specular Color",
        description="VRML2 specularColor RGB values",
        size=3,
        subtype="COLOR_GAMMA",
        min=0.0,
        max=1.0,
        default=VRML_DEFAULTS["specular_color"],
        precision=4,
        update=_update_material,
    )
    transparency: FloatProperty(
        name="Transparency",
        description="VRML2 transparency: 0 is opaque and 1 is fully transparent",
        min=0.0,
        max=1.0,
        default=VRML_DEFAULTS["transparency"],
        precision=4,
        update=_update_material,
    )
    preview_lighting: EnumProperty(
        name="VRML Preview Lighting",
        description="Controlled VRML97 reference-lighting rig used by the live preview",
        items=LIGHTING_ITEMS,
        default="STUDIO",
        update=_update_material,
    )
    preview_ambient_light: FloatProperty(
        name="Assumed Ambient Light",
        description=(
            "Preview VRML scene ambient-light level; the displayed ambient term is "
            "diffuseColor x ambientIntensity x this value"
        ),
        min=0.0,
        soft_max=2.0,
        default=0.25,
        precision=3,
        update=_update_material,
    )


CLASSES = (VRML2MaterialProperties,)
