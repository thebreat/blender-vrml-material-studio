# SPDX-FileCopyrightText: 2026 Brianna O'Leary
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import bpy
from bpy.app.handlers import persistent
from bpy.props import PointerProperty

from . import core, operators, properties, ui
from .constants import MATERIAL_POINTER_NAME


@persistent
def _vrml2_load_post(_filepath) -> None:
    core.sync_all_materials()


def register() -> None:
    for cls in properties.CLASSES:
        bpy.utils.register_class(cls)

    setattr(
        bpy.types.Material,
        MATERIAL_POINTER_NAME,
        PointerProperty(type=properties.VRML2MaterialProperties),
    )

    for cls in operators.CLASSES:
        bpy.utils.register_class(cls)
    for cls in ui.CLASSES:
        bpy.utils.register_class(cls)

    if _vrml2_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_vrml2_load_post)

    core.sync_all_materials()


def unregister() -> None:
    if _vrml2_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_vrml2_load_post)

    for cls in reversed(ui.CLASSES):
        bpy.utils.unregister_class(cls)
    for cls in reversed(operators.CLASSES):
        bpy.utils.unregister_class(cls)

    if hasattr(bpy.types.Material, MATERIAL_POINTER_NAME):
        delattr(bpy.types.Material, MATERIAL_POINTER_NAME)

    for cls in reversed(properties.CLASSES):
        bpy.utils.unregister_class(cls)
