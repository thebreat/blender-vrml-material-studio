# SPDX-FileCopyrightText: 2026 Brianna O'Leary
# SPDX-License-Identifier: GPL-3.0-or-later

"""VRML97 reference-lighting shader graph for Blender previews."""

from __future__ import annotations

from typing import Any, Iterable

import bpy


GROUP_NAME = "VRML97 Live Preview Shader v2"
GROUP_VERSION_KEY = "vrml2_preview_group_version"
GROUP_VERSION = 2
REFERENCE_AMBIENT_INTENSITY = 0.25

SOCKET_DIFFUSE = "Diffuse Color"
SOCKET_SPECULAR = "Specular Color"
SOCKET_EMISSIVE = "Emissive Color"
SOCKET_AMBIENT_INTENSITY = "Ambient Intensity"
SOCKET_SHININESS = "Shininess"
SOCKET_TRANSPARENCY = "Transparency"
SOCKET_SHADER = "Shader"

LIGHTING_ITEMS = (
    ("STUDIO", "Studio", "45-degree key, dim cool fill, and faint warm rim"),
    ("OVERHEAD", "Overhead", "Strong top-down key with a dim cool fill"),
    ("SHOWROOM", "Showroom", "Even catalog lighting with lower contrast"),
)

# These are the three reference rigs used by the Worldcheck material previewer.
# VRML DirectionalLight.direction points along the emitted rays, while the
# lighting equation uses L from the surface toward the light, so every vector is
# negated here. Vectors are interpreted in camera space by the shader, keeping
# the reference rig stable while the user orbits the Blender viewport.
LIGHT_RIGS = {
    "STUDIO": (
        {"vector": (0.55, 0.55, 0.63), "intensity": 1.0, "color": (1.0, 1.0, 1.0)},
        {"vector": (-0.7, -0.25, -0.4), "intensity": 0.28, "color": (0.82, 0.87, 1.0)},
        {"vector": (-0.1, -0.6, 0.9), "intensity": 0.22, "color": (1.0, 0.96, 0.9)},
    ),
    "OVERHEAD": (
        {"vector": (0.1, 0.95, 0.2), "intensity": 1.15, "color": (1.0, 1.0, 1.0)},
        {"vector": (-0.5, -0.3, -0.6), "intensity": 0.16, "color": (0.8, 0.85, 1.0)},
    ),
    "SHOWROOM": (
        {"vector": (0.5, 0.4, 0.6), "intensity": 0.75, "color": (1.0, 1.0, 1.0)},
        {"vector": (-0.6, -0.35, -0.5), "intensity": 0.55, "color": (0.92, 0.94, 1.0)},
        {"vector": (0.0, -0.3, 0.9), "intensity": 0.15, "color": (1.0, 1.0, 1.0)},
    ),
}


def _first_socket(sockets: Any, index: int = 0):
    try:
        return sockets[index]
    except (IndexError, TypeError):
        return None


def _output(node: bpy.types.Node, name: str | None = None):
    if name:
        socket = node.outputs.get(name)
        if socket is not None:
            return socket
    return _first_socket(node.outputs)


def _input(node: bpy.types.Node, name: str | None = None, index: int = 0):
    if name:
        socket = node.inputs.get(name)
        if socket is not None:
            return socket
    return _first_socket(node.inputs, index)


def _link(tree: bpy.types.NodeTree, from_socket: Any, to_socket: Any) -> None:
    if from_socket is None or to_socket is None:
        raise RuntimeError("VRML97 preview shader socket is unavailable")
    tree.links.new(from_socket, to_socket)


def _interface_socket(
    tree: bpy.types.NodeTree,
    name: str,
    in_out: str,
    socket_type: str,
    default: Any = None,
    minimum: float | None = None,
    maximum: float | None = None,
) -> None:
    socket = tree.interface.new_socket(name=name, in_out=in_out, socket_type=socket_type)
    if default is not None and hasattr(socket, "default_value"):
        socket.default_value = default
    if minimum is not None and hasattr(socket, "min_value"):
        socket.min_value = minimum
    if maximum is not None and hasattr(socket, "max_value"):
        socket.max_value = maximum


def _math(
    tree: bpy.types.NodeTree,
    operation: str,
    name: str,
    location: tuple[float, float],
) -> bpy.types.Node:
    node = tree.nodes.new("ShaderNodeMath")
    node.operation = operation
    node.name = name
    node.label = name
    node.location = location
    return node


def _vector_math(
    tree: bpy.types.NodeTree,
    operation: str,
    name: str,
    location: tuple[float, float],
) -> bpy.types.Node:
    node = tree.nodes.new("ShaderNodeVectorMath")
    node.operation = operation
    node.name = name
    node.label = name
    node.location = location
    return node


def _scale_vector(
    tree: bpy.types.NodeTree,
    vector_socket: Any,
    scale_socket: Any,
    name: str,
    location: tuple[float, float],
) -> Any:
    node = _vector_math(tree, "SCALE", name, location)
    _link(tree, vector_socket, _input(node, "Vector", 0))
    _link(tree, scale_socket, _input(node, "Scale", 3))
    return _output(node, "Vector")


def _multiply_vectors(
    tree: bpy.types.NodeTree,
    left_socket: Any,
    right_socket: Any,
    name: str,
    location: tuple[float, float],
) -> Any:
    node = _vector_math(tree, "MULTIPLY", name, location)
    _link(tree, left_socket, _input(node, index=0))
    _link(tree, right_socket, _input(node, index=1))
    return _output(node, "Vector")


def _add_vectors(
    tree: bpy.types.NodeTree,
    left_socket: Any,
    right_socket: Any,
    name: str,
    location: tuple[float, float],
) -> Any:
    node = _vector_math(tree, "ADD", name, location)
    _link(tree, left_socket, _input(node, index=0))
    _link(tree, right_socket, _input(node, index=1))
    return _output(node, "Vector")


def _build_light_term(
    tree: bpy.types.NodeTree,
    group_input: bpy.types.Node,
    normal_socket: Any,
    view_socket: Any,
    exponent_socket: Any,
    light_index: int,
    y: float,
) -> Any:
    direction_name = f"Light {light_index} Vector"
    color_name = f"Light {light_index} Color"
    intensity_name = f"Light {light_index} Intensity"

    transform = tree.nodes.new("ShaderNodeVectorTransform")
    transform.vector_type = "VECTOR"
    transform.convert_from = "CAMERA"
    transform.convert_to = "WORLD"
    transform.name = f"Light {light_index} Camera to World"
    transform.label = transform.name
    transform.location = (-1500, y)
    _link(tree, _output(group_input, direction_name), _input(transform, "Vector"))

    light_normalize = _vector_math(tree, "NORMALIZE", f"Light {light_index} Normalize", (-1300, y))
    _link(tree, _output(transform, "Vector"), _input(light_normalize, index=0))
    light_vector = _output(light_normalize, "Vector")

    ndotl = _vector_math(tree, "DOT_PRODUCT", f"Light {light_index} N dot L", (-1100, y + 80))
    _link(tree, normal_socket, _input(ndotl, index=0))
    _link(tree, light_vector, _input(ndotl, index=1))

    diffuse_factor = _math(tree, "MAXIMUM", f"Light {light_index} Diffuse Clamp", (-900, y + 80))
    _link(tree, _output(ndotl, "Value"), _input(diffuse_factor, index=0))
    _input(diffuse_factor, index=1).default_value = 0.0

    half_add = _vector_math(tree, "ADD", f"Light {light_index} Half Vector", (-1100, y - 80))
    _link(tree, light_vector, _input(half_add, index=0))
    _link(tree, view_socket, _input(half_add, index=1))

    half_normalize = _vector_math(tree, "NORMALIZE", f"Light {light_index} Half Normalize", (-900, y - 80))
    _link(tree, _output(half_add, "Vector"), _input(half_normalize, index=0))

    ndoth = _vector_math(tree, "DOT_PRODUCT", f"Light {light_index} N dot H", (-700, y - 80))
    _link(tree, normal_socket, _input(ndoth, index=0))
    _link(tree, _output(half_normalize, "Vector"), _input(ndoth, index=1))

    specular_clamp = _math(tree, "MAXIMUM", f"Light {light_index} Specular Clamp", (-500, y - 80))
    _link(tree, _output(ndoth, "Value"), _input(specular_clamp, index=0))
    _input(specular_clamp, index=1).default_value = 0.0

    specular_factor = _math(tree, "POWER", f"Light {light_index} Specular Power", (-300, y - 80))
    _link(tree, _output(specular_clamp, "Value"), _input(specular_factor, index=0))
    _link(tree, exponent_socket, _input(specular_factor, index=1))

    diffuse_scaled = _scale_vector(
        tree,
        _output(group_input, SOCKET_DIFFUSE),
        _output(diffuse_factor, "Value"),
        f"Light {light_index} Diffuse",
        (-500, y + 180),
    )
    diffuse_intensity = _scale_vector(
        tree,
        diffuse_scaled,
        _output(group_input, intensity_name),
        f"Light {light_index} Diffuse Intensity",
        (-280, y + 180),
    )
    diffuse_color = _multiply_vectors(
        tree,
        diffuse_intensity,
        _output(group_input, color_name),
        f"Light {light_index} Diffuse Color",
        (-60, y + 180),
    )

    specular_scaled = _scale_vector(
        tree,
        _output(group_input, SOCKET_SPECULAR),
        _output(specular_factor, "Value"),
        f"Light {light_index} Specular",
        (-100, y - 80),
    )
    specular_intensity = _scale_vector(
        tree,
        specular_scaled,
        _output(group_input, intensity_name),
        f"Light {light_index} Specular Intensity",
        (120, y - 80),
    )
    specular_color = _multiply_vectors(
        tree,
        specular_intensity,
        _output(group_input, color_name),
        f"Light {light_index} Specular Color",
        (340, y - 80),
    )

    return _add_vectors(
        tree,
        diffuse_color,
        specular_color,
        f"Light {light_index} Total",
        (560, y + 80),
    )


def _build_group(tree: bpy.types.NodeTree) -> None:
    for name, default in (
        (SOCKET_DIFFUSE, (0.8, 0.8, 0.8, 1.0)),
        (SOCKET_SPECULAR, (0.0, 0.0, 0.0, 1.0)),
        (SOCKET_EMISSIVE, (0.0, 0.0, 0.0, 1.0)),
    ):
        _interface_socket(tree, name, "INPUT", "NodeSocketColor", default)

    for name, default in (
        (SOCKET_AMBIENT_INTENSITY, 0.2),
        (SOCKET_SHININESS, 0.2),
        (SOCKET_TRANSPARENCY, 0.0),
    ):
        _interface_socket(tree, name, "INPUT", "NodeSocketFloat", default, 0.0, 1.0)

    for index in range(1, 4):
        _interface_socket(
            tree,
            f"Light {index} Vector",
            "INPUT",
            "NodeSocketVector",
            (0.0, 0.0, 1.0),
        )
        _interface_socket(
            tree,
            f"Light {index} Color",
            "INPUT",
            "NodeSocketColor",
            (1.0, 1.0, 1.0, 1.0),
        )
        _interface_socket(tree, f"Light {index} Intensity", "INPUT", "NodeSocketFloat", 0.0, 0.0, 2.0)

    _interface_socket(tree, SOCKET_SHADER, "OUTPUT", "NodeSocketShader")

    group_input = tree.nodes.new("NodeGroupInput")
    group_input.name = "VRML97 Inputs"
    group_input.label = "VRML97 Material + Reference Lights"
    group_input.location = (-1900, 200)

    group_output = tree.nodes.new("NodeGroupOutput")
    group_output.name = "VRML97 Output"
    group_output.location = (1600, 100)

    geometry = tree.nodes.new("ShaderNodeNewGeometry")
    geometry.name = "VRML97 Geometry"
    geometry.location = (-1900, -600)

    normal = _vector_math(tree, "NORMALIZE", "VRML97 Normal", (-1680, -500))
    _link(tree, _output(geometry, "Normal"), _input(normal, index=0))

    view_normalize = _vector_math(tree, "NORMALIZE", "VRML97 View Normalize", (-1460, -700))
    _link(tree, _output(geometry, "Incoming"), _input(view_normalize, index=0))

    exponent = _math(tree, "MULTIPLY", "VRML97 Shininess Exponent", (-1460, -900))
    _link(tree, _output(group_input, SOCKET_SHININESS), _input(exponent, index=0))
    _input(exponent, index=1).default_value = 128.0

    light_terms = [
        _build_light_term(
            tree,
            group_input,
            _output(normal, "Vector"),
            _output(view_normalize, "Vector"),
            _output(exponent, "Value"),
            index,
            650.0 - (index - 1) * 550.0,
        )
        for index in range(1, 4)
    ]

    direct_sum = _add_vectors(tree, light_terms[0], light_terms[1], "Lights 1 + 2", (800, 300))
    direct_sum = _add_vectors(tree, direct_sum, light_terms[2], "All Direct Lights", (1020, 250))

    ambient_material = _scale_vector(
        tree,
        _output(group_input, SOCKET_DIFFUSE),
        _output(group_input, SOCKET_AMBIENT_INTENSITY),
        "VRML97 Material Ambient",
        (520, -700),
    )
    ambient_scale = _vector_math(tree, "SCALE", "VRML97 Reference Ambient", (760, -700))
    _link(tree, ambient_material, _input(ambient_scale, "Vector", 0))
    _input(ambient_scale, "Scale", 3).default_value = REFERENCE_AMBIENT_INTENSITY
    ambient = _output(ambient_scale, "Vector")

    with_ambient = _add_vectors(tree, direct_sum, ambient, "Direct + Ambient", (1220, 150))
    final_color = _add_vectors(
        tree,
        with_ambient,
        _output(group_input, SOCKET_EMISSIVE),
        "VRML97 Lit + Emissive",
        (1400, 100),
    )

    emission = tree.nodes.new("ShaderNodeEmission")
    emission.name = "VRML97 Color Output"
    emission.location = (1600, 0)
    _link(tree, final_color, _input(emission, "Color", 0))
    _input(emission, "Strength", 1).default_value = 1.0

    transparent = tree.nodes.new("ShaderNodeBsdfTransparent")
    transparent.name = "VRML97 Transparent"
    transparent.location = (1600, -180)
    _input(transparent, "Color", 0).default_value = (1.0, 1.0, 1.0, 1.0)

    mix = tree.nodes.new("ShaderNodeMixShader")
    mix.name = "VRML97 Transparency"
    mix.location = (1820, 0)
    _link(tree, _output(group_input, SOCKET_TRANSPARENCY), _input(mix, "Fac", 0))
    _link(tree, _output(emission), _input(mix, index=1))
    _link(tree, _output(transparent), _input(mix, index=2))
    _link(tree, _output(mix), _input(group_output, SOCKET_SHADER))

    tree[GROUP_VERSION_KEY] = GROUP_VERSION


def ensure_shader_group() -> bpy.types.NodeTree:
    group = bpy.data.node_groups.get(GROUP_NAME)
    if group is not None and group.get(GROUP_VERSION_KEY) == GROUP_VERSION:
        return group

    if group is not None:
        group.name = f"{GROUP_NAME} (Outdated)"

    group = bpy.data.node_groups.new(GROUP_NAME, "ShaderNodeTree")
    _build_group(group)
    return group


def _set_color(node: bpy.types.Node, name: str, value: Iterable[float]) -> None:
    color = tuple(float(component) for component in value)[:3]
    node.inputs[name].default_value = (*color, 1.0)


def configure_preview_node(
    node: bpy.types.Node,
    *,
    diffuse_color: Iterable[float],
    specular_color: Iterable[float],
    emissive_color: Iterable[float],
    ambient_intensity: float,
    shininess: float,
    transparency: float,
    lighting: str,
) -> None:
    node.node_tree = ensure_shader_group()
    _set_color(node, SOCKET_DIFFUSE, diffuse_color)
    _set_color(node, SOCKET_SPECULAR, specular_color)
    _set_color(node, SOCKET_EMISSIVE, emissive_color)
    node.inputs[SOCKET_AMBIENT_INTENSITY].default_value = float(ambient_intensity)
    node.inputs[SOCKET_SHININESS].default_value = float(shininess)
    node.inputs[SOCKET_TRANSPARENCY].default_value = float(transparency)

    rig = LIGHT_RIGS.get(lighting, LIGHT_RIGS["STUDIO"])
    for index in range(1, 4):
        light = rig[index - 1] if index <= len(rig) else None
        vector = light["vector"] if light else (0.0, 0.0, 1.0)
        color = light["color"] if light else (1.0, 1.0, 1.0)
        intensity = light["intensity"] if light else 0.0
        node.inputs[f"Light {index} Vector"].default_value = vector
        node.inputs[f"Light {index} Color"].default_value = (*color, 1.0)
        node.inputs[f"Light {index} Intensity"].default_value = intensity
