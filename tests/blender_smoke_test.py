from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import sys

import bpy


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "vrml2_material_studio_smoke"


def load_extension():
    spec = importlib.util.spec_from_file_location(
        PACKAGE_NAME,
        REPOSITORY_ROOT / "__init__.py",
        submodule_search_locations=[str(REPOSITORY_ROOT)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_NAME] = module
    spec.loader.exec_module(module)
    return module


def assert_preview_graph(extension, material) -> None:
    tagged_nodes = [
        node
        for node in material.node_tree.nodes
        if node.get(extension.constants.PREVIEW_NODE_TAG)
    ]
    roles = {node.get(extension.constants.PREVIEW_ROLE_TAG) for node in tagged_nodes}
    expected_roles = {
        extension.constants.ROLE_DIFFUSE,
        extension.constants.ROLE_SPECULAR,
        extension.constants.ROLE_EMISSION,
        extension.constants.ROLE_ADD_LIT,
        extension.constants.ROLE_ADD_EMISSION,
        extension.constants.ROLE_TRANSPARENT,
        extension.constants.ROLE_MIX_TRANSPARENCY,
    }
    assert expected_roles.issubset(roles), (expected_roles, roles)


def main() -> None:
    extension = load_extension()
    material = None
    extension.register()

    try:
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
        assert_preview_graph(extension, material)

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

        extension.core.remove_vrml2_data(material)
        assert not settings.initialized
        for key in extension.constants.EXPORT_KEYS.values():
            assert key not in material

        output = extension.core._find_material_output(material)
        surface = output.inputs.get("Surface")
        assert surface is not None and surface.links
        assert surface.links[0].from_node.bl_idname == "ShaderNodeBsdfPrincipled"
    finally:
        if material is not None:
            bpy.data.materials.remove(material)
        extension.unregister()
        sys.modules.pop(PACKAGE_NAME, None)

    print("VRML2 Material Studio Blender smoke test passed")


if __name__ == "__main__":
    main()
