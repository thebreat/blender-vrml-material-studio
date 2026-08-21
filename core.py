# SPDX-FileCopyrightText: 2026 Brianna O'Leary
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from contextlib import contextmanager
import math
from typing import Any, Iterable

import bpy

from . import vrml_shader
from .constants import (
    DATA_SCHEMA_VERSION,
    EXPORT_KEYS,
    LEGACY_EXPORT_KEYS,
    MATERIAL_POINTER_NAME,
    META_KEYS,
    PREVIEW_NODE_PREFIX,
    PREVIEW_NODE_TAG,
    PREVIEW_ROLE_TAG,
    ROLE_VRML_SHADER,
    VRML_DEFAULTS,
)
from .vrml_text import sanitize_def_name

_SUSPENDED_MATERIALS: set[int] = set()


def _pointer(material: bpy.types.Material) -> int:
    try:
        return material.as_pointer()
    except Exception:
        return id(material)


@contextmanager
def suspend_updates(material: bpy.types.Material):
    pointer = _pointer(material)
    _SUSPENDED_MATERIALS.add(pointer)
    try:
        yield
    finally:
        _SUSPENDED_MATERIALS.discard(pointer)


def updates_suspended(material: bpy.types.Material | None) -> bool:
    return material is not None and _pointer(material) in _SUSPENDED_MATERIALS


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def clamp_color(value: Iterable[float]) -> tuple[float, float, float]:
    components = tuple(float(component) for component in value)
    if len(components) < 3:
        components = components + (0.0,) * (3 - len(components))
    return tuple(clamp01(component) for component in components[:3])


def srgb_channel_to_linear(value: float) -> float:
    value = max(0.0, float(value))
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def linear_channel_to_srgb(value: float) -> float:
    value = max(0.0, float(value))
    if value <= 0.0031308:
        return value * 12.92
    return 1.055 * (value ** (1.0 / 2.4)) - 0.055


def preview_color(value: Iterable[float]) -> tuple[float, float, float]:
    return tuple(srgb_channel_to_linear(component) for component in clamp_color(value))


def stored_color_from_linear(value: Iterable[float]) -> tuple[float, float, float]:
    components = tuple(float(component) for component in value)
    return tuple(clamp01(linear_channel_to_srgb(component)) for component in components[:3])


def roughness_to_shininess(roughness: float) -> float:
    roughness = max(0.02, min(1.0, float(roughness)))
    exponent = max(0.0, (2.0 / (roughness * roughness)) - 2.0)
    return clamp01(exponent / 128.0)


def material_supports_slots(obj: bpy.types.Object | None) -> bool:
    return bool(obj and obj.data and hasattr(obj.data, "materials"))


def active_material(context: bpy.types.Context) -> bpy.types.Material | None:
    obj = getattr(context, "object", None)
    return obj.active_material if obj else None


def property_values(properties: Any) -> dict[str, Any]:
    return {
        "diffuse_color": tuple(float(v) for v in properties.diffuse_color),
        "emissive_color": tuple(float(v) for v in properties.emissive_color),
        "specular_color": tuple(float(v) for v in properties.specular_color),
        "ambient_intensity": float(properties.ambient_intensity),
        "shininess": float(properties.shininess),
        "transparency": float(properties.transparency),
    }


def sync_custom_properties(material: bpy.types.Material) -> None:
    properties = getattr(material, MATERIAL_POINTER_NAME, None)
    if properties is None:
        return

    material[EXPORT_KEYS["schema_version"]] = DATA_SCHEMA_VERSION
    material[EXPORT_KEYS["initialized"]] = bool(properties.initialized)
    material[EXPORT_KEYS["enabled"]] = bool(properties.enabled)
    material[EXPORT_KEYS["def_name"]] = str(properties.def_name)
    material[EXPORT_KEYS["diffuse_color"]] = list(clamp_color(properties.diffuse_color))
    material[EXPORT_KEYS["emissive_color"]] = list(clamp_color(properties.emissive_color))
    material[EXPORT_KEYS["specular_color"]] = list(clamp_color(properties.specular_color))
    material[EXPORT_KEYS["ambient_intensity"]] = float(properties.ambient_intensity)
    material[EXPORT_KEYS["shininess"]] = float(properties.shininess)
    material[EXPORT_KEYS["transparency"]] = float(properties.transparency)
    for key in LEGACY_EXPORT_KEYS:
        if key in material:
            del material[key]


def _socket_by_names(sockets: Any, names: Iterable[str]):
    for name in names:
        socket = sockets.get(name) if hasattr(sockets, "get") else None
        if socket is not None:
            return socket
    return None


def _first_socket(sockets: Any, index: int = 0):
    try:
        return sockets[index]
    except (IndexError, TypeError):
        return None


def _set_float_input(node: bpy.types.Node, names: Iterable[str], value: float, fallback_index: int | None = None) -> None:
    socket = _socket_by_names(node.inputs, names)
    if socket is None and fallback_index is not None:
        socket = _first_socket(node.inputs, fallback_index)
    if socket is not None and hasattr(socket, "default_value"):
        try:
            socket.default_value = float(value)
        except (TypeError, ValueError):
            pass


def _set_color_input(
    node: bpy.types.Node,
    names: Iterable[str],
    color: Iterable[float],
    fallback_index: int | None = None,
) -> None:
    socket = _socket_by_names(node.inputs, names)
    if socket is None and fallback_index is not None:
        socket = _first_socket(node.inputs, fallback_index)
    if socket is None or not hasattr(socket, "default_value"):
        return

    rgba = tuple(float(component) for component in color)[:3] + (1.0,)
    try:
        socket.default_value = rgba
    except (TypeError, ValueError):
        try:
            socket.default_value = sum(rgba[:3]) / 3.0
        except (TypeError, ValueError):
            pass


def _get_input_value(node: bpy.types.Node, names: Iterable[str], fallback_index: int | None = None):
    socket = _socket_by_names(node.inputs, names)
    if socket is None and fallback_index is not None:
        socket = _first_socket(node.inputs, fallback_index)
    return getattr(socket, "default_value", None) if socket is not None else None


def _node_output(node: bpy.types.Node, names: Iterable[str] = ("BSDF", "Shader")):
    socket = _socket_by_names(node.outputs, names)
    return socket if socket is not None else _first_socket(node.outputs, 0)


def _find_material_output(material: bpy.types.Material):
    node_tree = material.node_tree
    if node_tree is None:
        return None

    outputs = [
        node
        for node in node_tree.nodes
        if node.bl_idname == "ShaderNodeOutputMaterial" or getattr(node, "type", "") == "OUTPUT_MATERIAL"
    ]
    for node in outputs:
        if getattr(node, "is_active_output", False):
            return node
    return outputs[0] if outputs else None


def _material_output(material: bpy.types.Material, tag_created: bool = True) -> bpy.types.Node:
    output = _find_material_output(material)
    if output is not None:
        return output

    node_tree = material.node_tree
    output = node_tree.nodes.new("ShaderNodeOutputMaterial")
    if tag_created:
        output[PREVIEW_NODE_TAG] = True
        output[PREVIEW_ROLE_TAG] = "OUTPUT"
        output.name = f"{PREVIEW_NODE_PREFIX} - Material Output"
        output.label = "VRML2 Material Output"
    else:
        output.name = "Material Output"
    output.location = (720, 40)
    return output


def _preview_node(node_tree: bpy.types.NodeTree, role: str):
    for node in node_tree.nodes:
        if node.get(PREVIEW_NODE_TAG) and node.get(PREVIEW_ROLE_TAG) == role:
            return node
    return None


def _ensure_link(node_tree: bpy.types.NodeTree, from_socket: Any, to_socket: Any) -> None:
    if from_socket is None or to_socket is None:
        return
    for link in list(to_socket.links):
        if link.from_socket == from_socket:
            return
        node_tree.links.remove(link)
    node_tree.links.new(from_socket, to_socket)


def _record_original_state(material: bpy.types.Material) -> None:
    if material.get(META_KEYS["original_recorded"], False):
        return

    material[META_KEYS["original_recorded"]] = True
    material[META_KEYS["use_nodes"]] = bool(material.use_nodes)
    material[META_KEYS["diffuse_color"]] = list(tuple(material.diffuse_color)[:4])
    material[META_KEYS["output_node"]] = ""
    material[META_KEYS["source_node"]] = ""
    material[META_KEYS["source_socket_name"]] = ""
    material[META_KEYS["source_socket_identifier"]] = ""

    if material.use_nodes and material.node_tree is not None:
        output = _find_material_output(material)
        if output is not None:
            material[META_KEYS["output_node"]] = output.name
            surface = _socket_by_names(output.inputs, ("Surface",)) or _first_socket(output.inputs, 0)
            if surface is not None and surface.links:
                link = surface.links[0]
                if not link.from_node.get(PREVIEW_NODE_TAG):
                    material[META_KEYS["source_node"]] = link.from_node.name
                    material[META_KEYS["source_socket_name"]] = link.from_socket.name
                    material[META_KEYS["source_socket_identifier"]] = getattr(
                        link.from_socket, "identifier", ""
                    )

    if hasattr(material, "surface_render_method"):
        material[META_KEYS["surface_render_method"]] = str(material.surface_render_method)
    if hasattr(material, "blend_method"):
        material[META_KEYS["blend_method"]] = str(material.blend_method)


def ensure_preview_graph(material: bpy.types.Material) -> dict[str, bpy.types.Node]:
    """Create the material-level wrapper around the shared VRML97 shader."""
    _record_original_state(material)
    material.use_nodes = True
    node_tree = material.node_tree
    output = _material_output(material)

    # Remove preview nodes from the old Blender-BSDF implementation during the
    # first sync after upgrading, while retaining our output and current group.
    for candidate in list(node_tree.nodes):
        if not candidate.get(PREVIEW_NODE_TAG):
            continue
        role = candidate.get(PREVIEW_ROLE_TAG)
        if role not in {"OUTPUT", ROLE_VRML_SHADER}:
            node_tree.nodes.remove(candidate)

    shader = _preview_node(node_tree, ROLE_VRML_SHADER)
    if shader is not None and shader.bl_idname != "ShaderNodeGroup":
        node_tree.nodes.remove(shader)
        shader = None

    if shader is None:
        shader = node_tree.nodes.new("ShaderNodeGroup")
        shader[PREVIEW_NODE_TAG] = True
        shader[PREVIEW_ROLE_TAG] = ROLE_VRML_SHADER
        shader.name = f"{PREVIEW_NODE_PREFIX} - VRML97 Live Preview"
        shader.label = "VRML97 Live Preview"
        shader.location = (300, 40)

    shader.node_tree = vrml_shader.ensure_shader_group()

    surface = _socket_by_names(output.inputs, ("Surface",)) or _first_socket(output.inputs, 0)
    _ensure_link(node_tree, _node_output(shader, (vrml_shader.SOCKET_SHADER, "Shader")), surface)
    return {ROLE_VRML_SHADER: shader, "OUTPUT": output}


def _restore_render_mode(material: bpy.types.Material) -> None:
    surface_mode = material.get(META_KEYS["surface_render_method"])
    if surface_mode and hasattr(material, "surface_render_method"):
        try:
            material.surface_render_method = surface_mode
        except (TypeError, ValueError):
            pass

    blend_mode = material.get(META_KEYS["blend_method"])
    if blend_mode and hasattr(material, "blend_method"):
        try:
            material.blend_method = blend_mode
        except (TypeError, ValueError):
            pass


def _set_preview_transparency_mode(material: bpy.types.Material, transparency: float) -> None:
    if transparency <= 1e-5:
        _restore_render_mode(material)
        return

    if hasattr(material, "surface_render_method"):
        for mode in ("DITHERED", "BLENDED"):
            try:
                material.surface_render_method = mode
                return
            except (TypeError, ValueError):
                continue

    if hasattr(material, "blend_method"):
        for mode in ("HASHED", "BLEND"):
            try:
                material.blend_method = mode
                return
            except (TypeError, ValueError):
                continue


def update_preview(material: bpy.types.Material) -> None:
    properties = getattr(material, MATERIAL_POINTER_NAME, None)
    if properties is None or not properties.initialized:
        return

    nodes = ensure_preview_graph(material)
    # X_ITE writes VRML RGB values as display-channel values. Blender shader
    # inputs are scene-linear and its display transform encodes them again, so
    # decode the VRML values before evaluating the same lighting equation.
    diffuse_color = preview_color(properties.diffuse_color)
    specular_color = preview_color(properties.specular_color)
    emissive_color = preview_color(properties.emissive_color)
    transparency = clamp01(properties.transparency)

    vrml_shader.configure_preview_node(
        nodes[ROLE_VRML_SHADER],
        diffuse_color=diffuse_color,
        specular_color=specular_color,
        emissive_color=emissive_color,
        ambient_intensity=clamp01(properties.ambient_intensity),
        shininess=clamp01(properties.shininess),
        transparency=transparency,
        lighting=properties.preview_lighting,
    )

    alpha = 1.0 - transparency
    try:
        material.diffuse_color = (*diffuse_color, alpha)
    except (TypeError, ValueError):
        pass
    _set_preview_transparency_mode(material, transparency)


def _find_socket_by_saved_identity(node: bpy.types.Node, identifier: str, name: str):
    if identifier:
        for socket in node.outputs:
            if getattr(socket, "identifier", "") == identifier:
                return socket
    if name:
        socket = node.outputs.get(name)
        if socket is not None:
            return socket
    return _first_socket(node.outputs, 0)


def restore_original_shader(material: bpy.types.Material) -> None:
    node_tree = material.node_tree
    if node_tree is not None:
        # Disconnect the generated shader from every Material Output. This also
        # covers a user changing the active output while Live Preview is on.
        for candidate in node_tree.nodes:
            if not (
                candidate.bl_idname == "ShaderNodeOutputMaterial"
                or getattr(candidate, "type", "") == "OUTPUT_MATERIAL"
            ):
                continue
            candidate_surface = _socket_by_names(candidate.inputs, ("Surface",)) or _first_socket(
                candidate.inputs, 0
            )
            if candidate_surface is None:
                continue
            for link in list(candidate_surface.links):
                if link.from_node.get(PREVIEW_NODE_TAG):
                    node_tree.links.remove(link)

        output_name = material.get(META_KEYS["output_node"], "")
        output = node_tree.nodes.get(output_name) if output_name else None
        if output is None:
            output = _find_material_output(material)

        if output is not None:
            surface = _socket_by_names(output.inputs, ("Surface",)) or _first_socket(output.inputs, 0)
            source_name = material.get(META_KEYS["source_node"], "")
            if surface is not None and source_name and not surface.links:
                source_node = node_tree.nodes.get(source_name)
                if source_node is not None:
                    source_socket = _find_socket_by_saved_identity(
                        source_node,
                        material.get(META_KEYS["source_socket_identifier"], ""),
                        material.get(META_KEYS["source_socket_name"], ""),
                    )
                    if source_socket is not None:
                        node_tree.links.new(source_socket, surface)

    original_color = material.get(META_KEYS["diffuse_color"])
    if original_color is not None:
        try:
            material.diffuse_color = tuple(float(component) for component in original_color)[:4]
        except (TypeError, ValueError):
            pass

    _restore_render_mode(material)

    if material.get(META_KEYS["original_recorded"], False):
        try:
            material.use_nodes = bool(material.get(META_KEYS["use_nodes"], True))
        except (TypeError, ValueError):
            pass


def _fallback_principled(material: bpy.types.Material) -> None:
    if not material.use_nodes or material.node_tree is None:
        return
    output = _material_output(material, tag_created=False)
    surface = _socket_by_names(output.inputs, ("Surface",)) or _first_socket(output.inputs, 0)
    if surface is None or surface.links:
        return

    node = material.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    node.name = "Principled BSDF"
    node.location = (280, 40)
    color = tuple(material.diffuse_color[:3]) if hasattr(material, "diffuse_color") else (0.8, 0.8, 0.8)
    _set_color_input(node, ("Base Color",), color, 0)
    material.node_tree.links.new(_node_output(node), surface)


def remove_preview_nodes(material: bpy.types.Material, create_fallback: bool = True) -> None:
    # Keep the node-tree reference in case restoring a non-node material makes
    # material.node_tree unavailable through RNA.
    node_tree = material.node_tree
    restore_original_shader(material)
    if node_tree is not None:
        for node in list(node_tree.nodes):
            if node.get(PREVIEW_NODE_TAG):
                node_tree.nodes.remove(node)
    if create_fallback:
        material.use_nodes = True
        _fallback_principled(material)


def sync_material(material: bpy.types.Material) -> None:
    if updates_suspended(material):
        return
    properties = getattr(material, MATERIAL_POINTER_NAME, None)
    if properties is None:
        return

    sync_custom_properties(material)
    if properties.initialized and properties.live_preview:
        update_preview(material)
    else:
        restore_original_shader(material)


def apply_values(material: bpy.types.Material, values: dict[str, Any]) -> bool:
    """Apply parsed or preset values. Returns True when any input was clamped."""
    properties = getattr(material, MATERIAL_POINTER_NAME)
    clamped = False

    with suspend_updates(material):
        for key in ("ambient_intensity", "shininess", "transparency"):
            if key in values:
                raw = float(values[key])
                value = clamp01(raw)
                clamped = clamped or value != raw
                setattr(properties, key, value)

        for key in ("diffuse_color", "emissive_color", "specular_color"):
            if key in values:
                raw = tuple(float(component) for component in values[key])[:3]
                value = clamp_color(raw)
                clamped = clamped or tuple(raw) != tuple(value)
                setattr(properties, key, value)

        if "def_name" in values and values["def_name"]:
            properties.def_name = sanitize_def_name(str(values["def_name"]))

    sync_material(material)
    return clamped


def _principled_from_original(material: bpy.types.Material):
    if not material.use_nodes or material.node_tree is None:
        return None

    output = _find_material_output(material)
    surface = (
        _socket_by_names(output.inputs, ("Surface",)) or _first_socket(output.inputs, 0)
        if output is not None
        else None
    )
    source = surface.links[0].from_node if surface is not None and surface.links else None
    if source is not None and source.bl_idname == "ShaderNodeBsdfPrincipled":
        return source

    for node in material.node_tree.nodes:
        if node.bl_idname == "ShaderNodeBsdfPrincipled" and not node.get(PREVIEW_NODE_TAG):
            return node
    return None


def read_existing_blender_values(material: bpy.types.Material) -> dict[str, Any]:
    values = dict(VRML_DEFAULTS)
    node = _principled_from_original(material)

    if node is None:
        if hasattr(material, "diffuse_color"):
            color = tuple(material.diffuse_color)
            values["diffuse_color"] = stored_color_from_linear(color[:3])
            values["transparency"] = clamp01(1.0 - float(color[3]))
        return values

    base = _get_input_value(node, ("Base Color",), 0)
    if base is not None and hasattr(base, "__len__"):
        values["diffuse_color"] = stored_color_from_linear(base[:3])

    roughness = _get_input_value(node, ("Roughness",), 2)
    if isinstance(roughness, (int, float)):
        values["shininess"] = roughness_to_shininess(float(roughness))

    alpha = _get_input_value(node, ("Alpha",))
    if isinstance(alpha, (int, float)):
        values["transparency"] = clamp01(1.0 - float(alpha))
    elif base is not None and hasattr(base, "__len__") and len(base) > 3:
        values["transparency"] = clamp01(1.0 - float(base[3]))

    return values


def prepare_new_material(material: bpy.types.Material) -> None:
    material[META_KEYS["owned_material"]] = True
    material.use_nodes = True
    material.node_tree.nodes.clear()
    output = material.node_tree.nodes.new("ShaderNodeOutputMaterial")
    output.name = f"{PREVIEW_NODE_PREFIX} - Material Output"
    output.location = (720, 40)


def initialize_material(
    material: bpy.types.Material,
    values: dict[str, Any] | None = None,
    def_name: str = "",
    enable_export: bool = True,
) -> None:
    properties = getattr(material, MATERIAL_POINTER_NAME)
    values = values or dict(VRML_DEFAULTS)

    with suspend_updates(material):
        properties.initialized = True
        properties.enabled = bool(enable_export)
        properties.live_preview = True
        properties.def_name = sanitize_def_name(def_name or material.name)
        properties.diffuse_color = clamp_color(values.get("diffuse_color", VRML_DEFAULTS["diffuse_color"]))
        properties.emissive_color = clamp_color(values.get("emissive_color", VRML_DEFAULTS["emissive_color"]))
        properties.specular_color = clamp_color(values.get("specular_color", VRML_DEFAULTS["specular_color"]))
        properties.ambient_intensity = clamp01(values.get("ambient_intensity", VRML_DEFAULTS["ambient_intensity"]))
        properties.shininess = clamp01(values.get("shininess", VRML_DEFAULTS["shininess"]))
        properties.transparency = clamp01(values.get("transparency", VRML_DEFAULTS["transparency"]))

    sync_material(material)


def remove_vrml2_data(material: bpy.types.Material) -> None:
    properties = getattr(material, MATERIAL_POINTER_NAME)
    create_fallback = bool(material.get(META_KEYS["owned_material"], False))
    remove_preview_nodes(material, create_fallback=create_fallback)

    with suspend_updates(material):
        properties.initialized = False
        properties.enabled = False
        properties.live_preview = True
        properties.def_name = ""
        properties.diffuse_color = VRML_DEFAULTS["diffuse_color"]
        properties.emissive_color = VRML_DEFAULTS["emissive_color"]
        properties.specular_color = VRML_DEFAULTS["specular_color"]
        properties.ambient_intensity = VRML_DEFAULTS["ambient_intensity"]
        properties.shininess = VRML_DEFAULTS["shininess"]
        properties.transparency = VRML_DEFAULTS["transparency"]

    for key in tuple(EXPORT_KEYS.values()) + LEGACY_EXPORT_KEYS + tuple(META_KEYS.values()):
        if key in material:
            del material[key]


def migrate_material(material: bpy.types.Material) -> None:
    properties = getattr(material, MATERIAL_POINTER_NAME, None)
    if properties is None:
        return

    stored_initialized = bool(material.get(EXPORT_KEYS["initialized"], False))
    if stored_initialized and not properties.initialized:
        values = {
            "diffuse_color": material.get(EXPORT_KEYS["diffuse_color"], VRML_DEFAULTS["diffuse_color"]),
            "emissive_color": material.get(EXPORT_KEYS["emissive_color"], VRML_DEFAULTS["emissive_color"]),
            "specular_color": material.get(EXPORT_KEYS["specular_color"], VRML_DEFAULTS["specular_color"]),
            "ambient_intensity": material.get(
                EXPORT_KEYS["ambient_intensity"], VRML_DEFAULTS["ambient_intensity"]
            ),
            "shininess": material.get(EXPORT_KEYS["shininess"], VRML_DEFAULTS["shininess"]),
            "transparency": material.get(EXPORT_KEYS["transparency"], VRML_DEFAULTS["transparency"]),
        }
        with suspend_updates(material):
            properties.initialized = True
            properties.enabled = bool(material.get(EXPORT_KEYS["enabled"], True))
            properties.def_name = str(material.get(EXPORT_KEYS["def_name"], ""))
            properties.diffuse_color = clamp_color(values["diffuse_color"])
            properties.emissive_color = clamp_color(values["emissive_color"])
            properties.specular_color = clamp_color(values["specular_color"])
            properties.ambient_intensity = clamp01(values["ambient_intensity"])
            properties.shininess = clamp01(values["shininess"])
            properties.transparency = clamp01(values["transparency"])

    if properties.initialized:
        sync_material(material)


def sync_all_materials() -> None:
    for material in bpy.data.materials:
        try:
            migrate_material(material)
        except Exception as exc:
            print(f"VRML2 Material Studio: could not sync {material.name!r}: {exc}")
