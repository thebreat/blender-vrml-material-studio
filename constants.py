# SPDX-FileCopyrightText: 2026 Brianna O'Leary
# SPDX-License-Identifier: GPL-3.0-or-later

EXTENSION_ID = "vrml2_material_studio"
EXTENSION_NAME = "VRML2 Material Studio"
EXTENSION_VERSION = (0, 2, 0)

MATERIAL_POINTER_NAME = "vrml2_material"
DATA_SCHEMA_VERSION = 2

PREVIEW_NODE_TAG = "vrml2_preview_node"
PREVIEW_ROLE_TAG = "vrml2_preview_role"
PREVIEW_NODE_PREFIX = "VRML2 Preview"

ROLE_VRML_SHADER = "VRML_SHADER"

EXPORT_KEYS = {
    "schema_version": "vrml2_schemaVersion",
    "initialized": "vrml2_initialized",
    "enabled": "vrml2_enabled",
    "def_name": "vrml2_defName",
    "ambient_intensity": "vrml2_ambientIntensity",
    "diffuse_color": "vrml2_diffuseColor",
    "include_emissive_color": "vrml2_includeEmissiveColor",
    "emissive_color": "vrml2_emissiveColor",
    "shininess": "vrml2_shininess",
    "include_specular_color": "vrml2_includeSpecularColor",
    "specular_color": "vrml2_specularColor",
    "transparency": "vrml2_transparency",
}

META_KEYS = {
    "original_recorded": "_vrml2_original_recorded",
    "use_nodes": "_vrml2_original_use_nodes",
    "diffuse_color": "_vrml2_original_diffuse_color",
    "output_node": "_vrml2_original_output_node",
    "source_node": "_vrml2_original_source_node",
    "source_socket_name": "_vrml2_original_source_socket_name",
    "source_socket_identifier": "_vrml2_original_source_socket_identifier",
    "surface_render_method": "_vrml2_original_surface_render_method",
    "blend_method": "_vrml2_original_blend_method",
    "owned_material": "_vrml2_owned_material",
}

VRML_DEFAULTS = {
    "ambient_intensity": 0.2,
    "diffuse_color": (0.8, 0.8, 0.8),
    "emissive_color": (0.0, 0.0, 0.0),
    "shininess": 0.2,
    "specular_color": (0.0, 0.0, 0.0),
    "transparency": 0.0,
}

VRML_FIELD_INCLUSION_DEFAULTS = {
    "include_emissive_color": False,
    "include_specular_color": False,
}
