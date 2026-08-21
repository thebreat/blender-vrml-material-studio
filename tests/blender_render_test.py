from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "vrml2_material_studio_render_test"


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


def configure_scene():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 192
    scene.render.resolution_y = 192
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    camera_data = bpy.data.cameras.new("VRML97 Preview Test Camera")
    camera = bpy.data.objects.new("VRML97 Preview Test Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = (0.0, -5.2, 0.35)
    camera.rotation_euler = (Vector((0.0, 0.0, 0.0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.lens = 52.0

    return scene


def create_test_shape(kind: str, material):
    for obj in tuple(bpy.context.scene.objects):
        if obj.type == "MESH":
            bpy.data.objects.remove(obj, do_unlink=True)

    if kind == "smooth":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=64, radius=1.0)
        obj = bpy.context.object
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    elif kind == "faceted":
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0)
        obj = bpy.context.object
    else:
        raise ValueError(f"Unknown test shape: {kind}")

    obj.name = f"VRML97 Preview Test {kind.title()} Shape"
    obj.data.materials.append(material)
    return obj


def render_metrics(scene, output_path: Path) -> dict[str, float]:
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(str(output_path), check_existing=False)
    pixels = list(image.pixels)
    luminances = []
    for index in range(0, len(pixels), 4):
        red, green, blue, alpha = pixels[index : index + 4]
        if alpha <= 0.5:
            continue
        luminances.append(0.2126 * red + 0.7152 * green + 0.0722 * blue)

    try:
        assert luminances
        return {
            "mean": sum(luminances) / len(luminances),
            "peak": max(luminances),
            "highlight_area": sum(value >= 0.5 for value in luminances) / len(luminances),
        }
    finally:
        bpy.data.images.remove(image)


def main() -> None:
    extension = load_extension()
    extension.register()

    try:
        scene = configure_scene()
        material = bpy.data.materials.new("VRML97 Preview Render Test")
        extension.core.prepare_new_material(material)
        extension.core.initialize_material(
            material,
            {
                "ambient_intensity": 0.0,
                "diffuse_color": (0.1, 0.1, 0.1),
                "emissive_color": (0.0, 0.0, 0.0),
                "shininess": 0.05,
                "specular_color": (0.8, 0.8, 0.8),
                "transparency": 0.0,
            },
            def_name="VRML97 Render Test",
        )
        create_test_shape("smooth", material)

        settings = getattr(material, extension.constants.MATERIAL_POINTER_NAME)
        settings.preview_lighting = "STUDIO"
        extension.core.sync_material(material)

        low_path = Path("/tmp/vrml97-shininess-005.png")
        low = render_metrics(scene, low_path)

        settings.shininess = 1.0
        extension.core.sync_material(material)
        high_path = Path("/tmp/vrml97-shininess-100.png")
        high = render_metrics(scene, high_path)

        assert low["mean"] > high["mean"], (low, high)
        assert low["highlight_area"] > high["highlight_area"], (low, high)
        assert high["peak"] > 0.1, high
        assert not math.isclose(low["mean"], high["mean"], rel_tol=0.05), (low, high)

        create_test_shape("faceted", material)
        settings.shininess = 0.05
        extension.core.sync_material(material)
        faceted_low = render_metrics(scene, Path("/tmp/vrml97-faceted-shininess-005.png"))

        settings.shininess = 1.0
        extension.core.sync_material(material)
        faceted_high = render_metrics(scene, Path("/tmp/vrml97-faceted-shininess-100.png"))

        assert faceted_low["mean"] > faceted_high["mean"], (faceted_low, faceted_high)
        assert faceted_low["highlight_area"] > faceted_high["highlight_area"], (
            faceted_low,
            faceted_high,
        )
        assert not math.isclose(
            faceted_low["mean"], faceted_high["mean"], rel_tol=0.05
        ), (faceted_low, faceted_high)

        create_test_shape("smooth", material)

        extension.core.apply_values(
            material,
            {
                "ambient_intensity": 0.0,
                "diffuse_color": (0.35, 0.35, 0.35),
                "emissive_color": (0.0, 0.0, 0.0),
                "shininess": 0.2,
                "specular_color": (0.0, 0.0, 0.0),
                "transparency": 0.0,
            },
        )
        extension.core.sync_material(material)
        ambient_zero = render_metrics(scene, Path("/tmp/vrml97-ambient-000.png"))

        settings.ambient_intensity = 1.0
        extension.core.sync_material(material)
        ambient_full = render_metrics(scene, Path("/tmp/vrml97-ambient-100.png"))
        assert ambient_full["mean"] > ambient_zero["mean"], (ambient_zero, ambient_full)
        assert ambient_full["peak"] > ambient_zero["peak"], (ambient_zero, ambient_full)

        extension.core.apply_values(
            material,
            {
                "ambient_intensity": 0.25,
                "diffuse_color": (0.4305, 0.4362, 0.4407),
                "emissive_color": (0.0, 0.0, 0.0),
                "shininess": 0.6848,
                "specular_color": (0.252, 0.252, 0.252),
                "transparency": 0.0,
            },
        )
        graphite = render_metrics(scene, Path("/tmp/vrml97-graphite-reference.png"))
        assert graphite["mean"] > 0.01, graphite
        assert graphite["peak"] > graphite["mean"], graphite
        print(
            "VRML97 render test passed: "
            f"smooth_low={low}, smooth_high={high}, "
            f"faceted_low={faceted_low}, faceted_high={faceted_high}, "
            f"ambient0={ambient_zero}, "
            f"ambient1={ambient_full}, graphite={graphite}"
        )
    finally:
        extension.unregister()
        sys.modules.pop(PACKAGE_NAME, None)


if __name__ == "__main__":
    main()
