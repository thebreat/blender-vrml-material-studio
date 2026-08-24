# SPDX-FileCopyrightText: 2026 Brianna O'Leary
# SPDX-License-Identifier: GPL-3.0-or-later

"""Breetos preset library and native Blender preview icons."""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import bpy


DATA_PATH = Path(__file__).with_name("material_presets.json")
PREVIEW_SIZE = 40
PREVIEW_NAMESPACE_KEY = "vrml2_material_studio.material_previews"
_PREVIEW_COLLECTION = None


@lru_cache(maxsize=1)
def library_data() -> dict:
    with DATA_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)


def materials() -> list[dict]:
    return library_data()["materials"]


def category_items(_owner=None, _context=None):
    return [("ALL", "All Categories", "Show every preset")] + [
        (category, category, f"Show {category} materials")
        for category in library_data()["categories"]
    ]


def ensure_items(window_manager: bpy.types.WindowManager):
    settings = window_manager.vrml2_material_library
    source = materials()
    if len(settings.items) != len(source):
        settings.items.clear()
        for index, preset in enumerate(source):
            item = settings.items.add()
            item.preset_index = index
            item.name = preset["name"]
            item.category = preset["category"]
        settings.active_index = min(settings.active_index, len(settings.items) - 1)
    return settings


def preset_values(preset: dict) -> dict:
    return {
        "diffuse_color": tuple(preset["diffuseColor"]),
        "emissive_color": tuple(preset["emissiveColor"]),
        "specular_color": tuple(preset["specularColor"]),
        "ambient_intensity": preset["ambientIntensity"],
        "shininess": preset["shininess"],
        "transparency": preset["transparency"],
    }


def register_previews() -> None:
    global _PREVIEW_COLLECTION
    import bpy.utils.previews

    previous = bpy.app.driver_namespace.pop(PREVIEW_NAMESPACE_KEY, None)
    if previous is not None:
        bpy.utils.previews.remove(previous)
    _PREVIEW_COLLECTION = bpy.utils.previews.new()
    bpy.app.driver_namespace[PREVIEW_NAMESPACE_KEY] = _PREVIEW_COLLECTION


def unregister_previews() -> None:
    global _PREVIEW_COLLECTION
    import bpy.utils.previews

    preview_collection = bpy.app.driver_namespace.pop(PREVIEW_NAMESPACE_KEY, None)
    if preview_collection is not None:
        bpy.utils.previews.remove(preview_collection)
    _PREVIEW_COLLECTION = None


def icon_id(preset_index: int) -> int:
    """Create a site-inspired shaded material ball only when Blender displays it."""
    if _PREVIEW_COLLECTION is None:
        return 0

    key = str(preset_index)
    preview = _PREVIEW_COLLECTION.get(key)
    if preview is None:
        preview = _PREVIEW_COLLECTION.new(key)
        preview.image_size = (PREVIEW_SIZE, PREVIEW_SIZE)
        preview.image_pixels_float = _preview_pixels(materials()[preset_index], PREVIEW_SIZE)
    return preview.icon_id


def _luminance(color) -> float:
    return 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]


def _mix(first, second, amount: float):
    return tuple(a + (b - a) * amount for a, b in zip(first, second))


def _clamp_color(color):
    return tuple(max(0.0, min(1.0, component)) for component in color)


def _preview_colors(preset: dict):
    base = tuple(
        diffuse + emissive
        for diffuse, emissive in zip(preset["diffuseColor"], preset["emissiveColor"])
    )
    specular = tuple(preset["specularColor"])
    energy = _luminance(specular)
    mid = _mix(base, specular, 0.35 * energy)
    if energy > 0.05 and _luminance(specular) > _luminance(base):
        hot = specular
    else:
        clamped_base = _clamp_color(base)
        hot = _mix(clamped_base, (1.0, 1.0, 1.0), 0.35)
    shade = tuple(component * 0.55 for component in mid)
    return _clamp_color(hot), _clamp_color(mid), _clamp_color(shade)


def _preview_pixels(preset: dict, size: int) -> list[float]:
    """Approximate the previewer's gloss-aware circular CSS swatch."""
    hot, mid, shade = _preview_colors(preset)
    material_alpha = max(0.3, 1.0 - preset["transparency"])
    highlight_stop = 0.10 + 0.30 * (1.0 - preset["shininess"])
    center_x = (size - 1) * 0.30
    center_y = (size - 1) * 0.74  # Pixel rows begin at the bottom in Blender.
    radius = (size - 2) * 0.5
    max_distance = math.hypot(radius * 1.4, radius * 1.4)
    pixels: list[float] = []

    for y in range(size):
        for x in range(size):
            dx = x - (size - 1) * 0.5
            dy = y - (size - 1) * 0.5
            distance_from_ball_center = math.hypot(dx, dy)
            if distance_from_ball_center > radius:
                pixels.extend((0.0, 0.0, 0.0, 0.0))
                continue

            radial = min(1.0, math.hypot(x - center_x, y - center_y) / max_distance)
            if radial <= highlight_stop:
                color = _mix(hot, mid, radial / max(highlight_stop, 0.001))
            else:
                color = _mix(mid, shade, (radial - highlight_stop) / (1.0 - highlight_stop))

            checker = 0.64 if ((x // 5) + (y // 5)) % 2 == 0 else 0.46
            color = _mix((checker, checker, checker), color, material_alpha)

            # Add the site's diagonal sheen and lower-right contact shading.
            diagonal = (x / max(size - 1, 1)) + ((size - 1 - y) / max(size - 1, 1))
            if diagonal < 0.75:
                color = _mix(color, (1.0, 1.0, 1.0), (0.75 - diagonal) * 0.10)
            edge = max(0.0, (distance_from_ball_center / radius - 0.72) / 0.28)
            lower_right = max(0.0, dx / radius) * max(0.0, -dy / radius)
            color = tuple(component * (1.0 - 0.18 * edge - 0.16 * lower_right) for component in color)

            pixels.extend((*_clamp_color(color), 1.0))

    return pixels
