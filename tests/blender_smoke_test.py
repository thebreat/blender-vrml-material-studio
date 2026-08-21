from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import sys

import bpy


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "vrml2_material_studio_smoke"
RELOAD_PACKAGE_NAME = f"{PACKAGE_NAME}_reload"


def load_extension(package_name=PACKAGE_NAME):
    spec = importlib.util.spec_from_file_location(
        package_name,
        REPOSITORY_ROOT / "__init__.py",
        submodule_search_locations=[str(REPOSITORY_ROOT)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = module
    spec.loader.exec_module(module)
    return module


def assert_preview_graph(extension, material):
    tagged_nodes = [
        node
        for node in material.node_tree.nodes
        if node.get(extension.constants.PREVIEW_NODE_TAG)
    ]
    shader = next(
        node
        for node in tagged_nodes
        if node.get(extension.constants.PREVIEW_ROLE_TAG) == extension.constants.ROLE_VRML_SHADER
    )
    assert shader.bl_idname == "ShaderNodeGroup"
    assert shader.node_tree.name == extension.vrml_shader.GROUP_NAME
    assert shader.node_tree.get(extension.vrml_shader.GROUP_VERSION_KEY) == extension.vrml_shader.GROUP_VERSION
    assert shader.outputs.get(extension.vrml_shader.SOCKET_SHADER) is not None
    forbidden_bsdfs = {
        "ShaderNodeBsdfAnisotropic",
        "ShaderNodeBsdfDiffuse",
        "ShaderNodeBsdfGlossy",
        "ShaderNodeBsdfPrincipled",
    }
    assert not any(node.bl_idname in forbidden_bsdfs for node in shader.node_tree.nodes)
    return shader


def main() -> None:
    extension = load_extension()
    active_extension = extension
    material = None
    extension.register()

    try:
        assert bpy.app.timers.is_registered(extension._vrml2_deferred_sync)

        # Calling register twice must replace the existing registration cleanly.
        extension.register()
        assert bpy.app.timers.is_registered(extension._vrml2_deferred_sync)

        material = bpy.data.materials.new("VRML2 Smoke Test")
        extension.core.prepare_new_material(material)
        extension.core.initialize_material(
            material,
            dict(extension.constants.VRML_DEFAULTS),
            def_name="Smoke Material",
        )

        settings = getattr(material, extension.constants.MATERIAL_POINTER_NAME)
        assert settings.initialized
        assert settings.def_name == "Smoke_Material"
        assert material[extension.constants.EXPORT_KEYS["initialized"]] is True
        stored_diffuse = material[extension.constants.EXPORT_KEYS["diffuse_color"]]
        assert all(math.isclose(value, 0.8, abs_tol=1e-6) for value in stored_diffuse)
        shader = assert_preview_graph(extension, material)
        assert settings.preview_lighting == "STUDIO"
        assert math.isclose(
            shader.inputs[extension.vrml_shader.SOCKET_SHININESS].default_value,
            settings.shininess,
            abs_tol=1e-6,
        )

        was_clamped = extension.core.apply_values(
            material,
            {
                "diffuse_color": (1.5, 0.25, -0.5),
                "shininess": 0.75,
                "transparency": 0.4,
            },
        )
        assert was_clamped
        assert all(
            math.isclose(actual, expected, abs_tol=1e-6)
            for actual, expected in zip(settings.diffuse_color, (1.0, 0.25, 0.0), strict=True)
        )
        assert math.isclose(
            material[extension.constants.EXPORT_KEYS["transparency"]],
            0.4,
            abs_tol=1e-6,
        )
        assert math.isclose(
            shader.inputs[extension.vrml_shader.SOCKET_SHININESS].default_value,
            0.75,
            abs_tol=1e-6,
        )
        assert math.isclose(
            shader.inputs[extension.vrml_shader.SOCKET_TRANSPARENCY].default_value,
            0.4,
            abs_tol=1e-6,
        )

        settings.preview_lighting = "OVERHEAD"
        extension.core.sync_material(material)
        assert math.isclose(shader.inputs["Light 1 Intensity"].default_value, 1.15, abs_tol=1e-6)
        assert math.isclose(shader.inputs["Light 3 Intensity"].default_value, 0.0, abs_tol=1e-6)

        extension.core.remove_vrml2_data(material)
        assert not settings.initialized
        for key in extension.constants.EXPORT_KEYS.values():
            assert key not in material

        output = extension.core._find_material_output(material)
        surface = output.inputs.get("Surface")
        assert surface is not None and surface.links
        assert surface.links[0].from_node.bl_idname == "ShaderNodeBsdfPrincipled"

        # Simulate Blender loading updated Python modules while the earlier copy
        # is still registered. The replacement must evict the stale RNA classes.
        reloaded_extension = load_extension(RELOAD_PACKAGE_NAME)
        reloaded_extension.register()
        active_extension = reloaded_extension
        assert not bpy.app.timers.is_registered(extension._vrml2_deferred_sync)
        assert bpy.app.timers.is_registered(reloaded_extension._vrml2_deferred_sync)
        assert (
            bpy.types.PropertyGroup.bl_rna_get_subclass_py("VRML2MaterialProperties")
            is reloaded_extension.properties.VRML2MaterialProperties
        )
        tagged_handlers = [
            handler
            for handler in bpy.app.handlers.load_post
            if getattr(handler, reloaded_extension._LOAD_HANDLER_TAG, False)
        ]
        assert tagged_handlers == [reloaded_extension._vrml2_load_post]
    finally:
        if material is not None:
            bpy.data.materials.remove(material)
        active_extension.unregister()
        assert not bpy.app.timers.is_registered(active_extension._vrml2_deferred_sync)
        sys.modules.pop(PACKAGE_NAME, None)
        sys.modules.pop(RELOAD_PACKAGE_NAME, None)

    print("VRML2 Material Studio Blender smoke test passed")


if __name__ == "__main__":
    main()
