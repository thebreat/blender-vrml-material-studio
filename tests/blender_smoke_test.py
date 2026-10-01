from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import sys
import tempfile

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


def assert_operator_error(operator, **properties) -> None:
    try:
        operator(**properties)
    except RuntimeError:
        return
    raise AssertionError(f"{operator.idname()} should have reported an error")


def check_favorites_and_custom_colors(extension, settings) -> None:
    user_library = extension.user_library
    material_library = extension.material_library
    window_manager = bpy.context.window_manager

    user_settings = material_library.ensure_user_items(window_manager)
    assert len(user_settings.favorite_items) == 0
    assert len(user_settings.custom_items) == 0

    # Star a preset; it appears in Favorites with its category.
    preset_key = user_library.preset_key("Clear glass")
    assert bpy.ops.vrml2.toggle_favorite(key=preset_key) == {"FINISHED"}
    assert user_library.library().is_favorite(preset_key)
    assert [item.name for item in user_settings.favorite_items] == ["Clear glass"]
    assert user_settings.favorite_items[0].preset_index == 0
    assert user_settings.favorite_items[0].detail == "Glass"
    assert_operator_error(bpy.ops.vrml2.toggle_favorite, key=user_library.preset_key("No Such Preset"))

    # Save the active material's fields as a custom color.
    extension.core.apply_values(
        bpy.context.object.active_material,
        {"diffuse_color": (0.1, 0.2, 0.9), "shininess": 0.6, "transparency": 0.25},
    )
    result = bpy.ops.vrml2.save_custom_material(name="Smoke Blue", add_to_favorites=True)
    assert result == {"FINISHED"}
    library = user_library.library()
    assert len(library.custom) == 1
    entry = library.custom[0]
    assert entry["name"] == "Smoke Blue"
    assert all(
        math.isclose(actual, expected, abs_tol=1e-6)
        for actual, expected in zip(entry["diffuseColor"], (0.1, 0.2, 0.9), strict=True)
    )
    assert [item.name for item in user_settings.custom_items] == ["Smoke Blue"]
    assert user_settings.custom_items[0].detail == "#1A33E6"
    assert [item.name for item in user_settings.favorite_items] == ["Clear glass", "Smoke Blue"]
    assert user_settings.favorite_items[1].preset_index == -1
    assert user_settings.favorite_items[1].custom_id == entry["id"]

    custom_icon = material_library.custom_icon_id(entry)
    assert custom_icon >= 0
    preview_collection = bpy.app.driver_namespace[material_library.PREVIEW_NAMESPACE_KEY]
    assert f"custom:{user_library.fingerprint(entry)}" in preview_collection

    # The file is what other projects read.
    stored = user_library.UserLibrary(library.path)
    assert stored.find_custom(entry["id"])["name"] == "Smoke Blue"
    assert stored.favorites == [preset_key, user_library.custom_key(entry["id"])]

    # Applying a custom color restores all six fields.
    extension.core.apply_values(
        bpy.context.object.active_material,
        dict(extension.constants.VRML_DEFAULTS),
    )
    assert bpy.ops.vrml2.apply_custom_material(custom_id=entry["id"]) == {"FINISHED"}
    assert all(
        math.isclose(actual, expected, abs_tol=1e-6)
        for actual, expected in zip(settings.diffuse_color, (0.1, 0.2, 0.9), strict=True)
    )
    assert math.isclose(settings.transparency, 0.25, abs_tol=1e-6)
    assert_operator_error(bpy.ops.vrml2.apply_custom_material, custom_id="missing")
    assert_operator_error(bpy.ops.vrml2.save_custom_material, name="   ")

    # Overwrite and rename, then delete it from both lists.
    settings.diffuse_color = (0.9, 0.1, 0.1)
    assert bpy.ops.vrml2.update_custom_material(custom_id=entry["id"]) == {"FINISHED"}
    assert user_library.library().find_custom(entry["id"])["diffuseColor"] == [0.9, 0.1, 0.1]
    assert user_settings.custom_items[0].detail == "#E61A1A"
    assert bpy.ops.vrml2.save_custom_material(name="Smoke Other") == {"FINISHED"}
    assert_operator_error(bpy.ops.vrml2.rename_custom_material, custom_id=entry["id"], name="smoke other")
    other_id = user_library.library().find_custom_by_name("Smoke Other")["id"]
    assert bpy.ops.vrml2.delete_custom_material(custom_id=other_id) == {"FINISHED"}
    assert bpy.ops.vrml2.rename_custom_material(custom_id=entry["id"], name="Smoke Red") == {"FINISHED"}
    assert [item.name for item in user_settings.custom_items] == ["Smoke Red"]
    assert user_settings.favorite_items[1].name == "Smoke Red"
    assert bpy.ops.vrml2.delete_custom_material(custom_id=entry["id"]) == {"FINISHED"}
    assert len(user_settings.custom_items) == 0
    assert [item.name for item in user_settings.favorite_items] == ["Clear glass"]

    assert bpy.ops.vrml2.toggle_favorite(key=preset_key) == {"FINISHED"}
    assert len(user_settings.favorite_items) == 0


def main() -> None:
    extension = load_extension()
    active_extension = extension
    material = None
    legacy_material = None
    test_object = None
    test_mesh = None
    user_library_directory = tempfile.TemporaryDirectory()
    extension.user_library.set_storage_directory(user_library_directory.name)
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
        assert not hasattr(settings, "preview_lighting")
        assert all(
            math.isclose(actual, expected, abs_tol=1e-6)
            for actual, expected in zip(
                shader.inputs["Light 1 Vector"].default_value,
                (0.615457, -0.492366, -0.615457),
                strict=True,
            )
        )
        assert math.isclose(
            shader.inputs["Light 1 Ambient Intensity"].default_value,
            0.255,
            abs_tol=1e-6,
        )
        assert math.isclose(
            shader.inputs["Light 4 Ambient Intensity"].default_value,
            0.255,
            abs_tol=1e-6,
        )
        assert math.isclose(shader.inputs["Light 4 Intensity"].default_value, 0.6, abs_tol=1e-6)
        assert not hasattr(settings, "preview_ambient_light")
        assert "Ambient Light" not in shader.inputs
        assert "VRML97 Reference Ambient" not in shader.node_tree.nodes
        assert all(
            math.isclose(actual, 0.8, abs_tol=1e-6)
            for actual in shader.inputs[extension.vrml_shader.SOCKET_DIFFUSE].default_value[:3]
        )
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

        extension.core.apply_values(
            material,
            {"shininess": 0.0, "specular_color": (0.8, 0.7, 0.6)},
        )
        assert all(
            math.isclose(component, expected, abs_tol=1e-6)
            for component, expected in zip(
                shader.inputs[extension.vrml_shader.SOCKET_SPECULAR].default_value[:3],
                (0.8, 0.7, 0.6),
                strict=True,
            )
        )
        extension.core.apply_values(
            material,
            {"specular_color": extension.constants.VRML_DEFAULTS["specular_color"]},
        )
        assert all(
            math.isclose(component, 0.0, abs_tol=1e-6)
            for component in shader.inputs[extension.vrml_shader.SOCKET_SPECULAR].default_value[:3]
        )
        copied = extension.vrml_text.format_material_block(extension.core.property_values(settings))
        assert "specularColor 0 0 0" in copied
        assert "emissiveColor 0 0 0" in copied

        test_mesh = bpy.data.meshes.new("VRML2 Default Button Test Mesh")
        test_object = bpy.data.objects.new("VRML2 Default Button Test Object", test_mesh)
        bpy.context.scene.collection.objects.link(test_object)
        test_mesh.materials.append(material)
        bpy.context.view_layer.objects.active = test_object
        test_object.select_set(True)
        settings.ambient_intensity = 0.91
        result = bpy.ops.vrml2.set_field_default(field="ambient_intensity")
        assert result == {"FINISHED"}
        assert math.isclose(
            settings.ambient_intensity,
            extension.constants.VRML_DEFAULTS["ambient_intensity"],
            abs_tol=1e-6,
        )

        library_settings = extension.material_library.ensure_items(bpy.context.window_manager)
        assert len(library_settings.items) == 1633
        assert library_settings.items[0].name == "Clear glass"
        assert library_settings.items[0].theme == "Original Presets"
        assert library_settings.items[0].category == "Glass"
        assert library_settings.items[433].name == "Titanium White - Traditional Oil Pigments"
        assert library_settings.items[433].theme == "Fine-Art Paints"
        assert library_settings.items[433].category == "Traditional Oil Pigments"
        assert len(extension.material_library.themes()) == 31
        library_settings.theme = "Fine-Art Paints"
        assert library_settings.category == "ALL"
        category_items = extension.material_library.category_items(library_settings)
        assert len(category_items) == 6
        assert category_items[1][0] == "Traditional Oil Pigments"

        icon_id = extension.material_library.icon_id(433)
        assert icon_id >= 0
        preview_collection = bpy.app.driver_namespace[
            extension.material_library.PREVIEW_NAMESPACE_KEY
        ]
        assert preview_collection["433"].image_size[:] == (40, 40)
        assert len(preview_collection["433"].image_pixels_float) == 40 * 40 * 4

        result = bpy.ops.vrml2.apply_library_material(preset_index=433)
        assert result == {"FINISHED"}
        first_themed_preset = extension.material_library.materials()[433]
        assert all(
            math.isclose(actual, expected, abs_tol=1e-6)
            for actual, expected in zip(
                settings.diffuse_color,
                first_themed_preset["diffuseColor"],
                strict=True,
            )
        )
        assert math.isclose(
            settings.transparency,
            first_themed_preset["transparency"],
            abs_tol=1e-6,
        )

        check_favorites_and_custom_colors(extension, settings)

        extension.core.remove_vrml2_data(material)
        assert not settings.initialized
        for key in extension.constants.EXPORT_KEYS.values():
            assert key not in material

        output = extension.core._find_material_output(material)
        surface = output.inputs.get("Surface")
        assert surface is not None and surface.links
        assert surface.links[0].from_node.bl_idname == "ShaderNodeBsdfPrincipled"

        legacy_material = bpy.data.materials.new("VRML2 Legacy Field Test")
        legacy_material[extension.constants.EXPORT_KEYS["initialized"]] = True
        legacy_material[extension.constants.EXPORT_KEYS["emissive_color"]] = (0.0, 0.0, 0.0)
        legacy_material[extension.constants.EXPORT_KEYS["specular_color"]] = (0.0, 0.0, 0.0)
        for legacy_key in extension.constants.LEGACY_EXPORT_KEYS:
            legacy_material[legacy_key] = False
        extension.core.migrate_material(legacy_material)
        for legacy_key in extension.constants.LEGACY_EXPORT_KEYS:
            assert legacy_key not in legacy_material

        # Simulate Blender loading updated Python modules while the earlier copy
        # is still registered. The replacement must evict the stale RNA classes.
        reloaded_extension = load_extension(RELOAD_PACKAGE_NAME)
        reloaded_extension.user_library.set_storage_directory(user_library_directory.name)
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
        if test_object is not None:
            bpy.data.objects.remove(test_object, do_unlink=True)
        if test_mesh is not None:
            bpy.data.meshes.remove(test_mesh)
        if material is not None:
            bpy.data.materials.remove(material)
        if legacy_material is not None:
            bpy.data.materials.remove(legacy_material)
        active_extension.unregister()
        assert not bpy.app.timers.is_registered(active_extension._vrml2_deferred_sync)
        sys.modules.pop(PACKAGE_NAME, None)
        sys.modules.pop(RELOAD_PACKAGE_NAME, None)
        user_library_directory.cleanup()

    print("VRML2 Material Studio Blender smoke test passed")


if __name__ == "__main__":
    main()
