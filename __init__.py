# SPDX-FileCopyrightText: 2026 Brianna O'Leary
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import bpy
from bpy.app.handlers import persistent
from bpy.props import PointerProperty

from . import core, operators, properties, ui
from .constants import MATERIAL_POINTER_NAME


_LOAD_HANDLER_TAG = "_vrml2_material_studio_load_post"
_SYNC_TIMER_NAMESPACE_KEY = "vrml2_material_studio.sync_timer"
_REMOVED_CLASS_NAMES = (
    (bpy.types.Operator, "VRML2_OT_apply_preset"),
    (bpy.types.Operator, "VRML2_OT_refresh_preview"),
    (bpy.types.Menu, "VRML2_MT_presets"),
)


@persistent
def _vrml2_load_post(_filepath) -> None:
    core.sync_all_materials()


setattr(_vrml2_load_post, _LOAD_HANDLER_TAG, True)


def _vrml2_deferred_sync() -> float | None:
    """Sync after Blender releases the restricted registration context."""
    try:
        core.sync_all_materials()
    except AttributeError as exc:
        if "_RestrictData" in str(exc) and "materials" in str(exc):
            return 0.1
        raise

    namespace = bpy.app.driver_namespace
    if namespace.get(_SYNC_TIMER_NAMESPACE_KEY) is _vrml2_deferred_sync:
        namespace.pop(_SYNC_TIMER_NAMESPACE_KEY, None)
    return None


def _cancel_deferred_sync() -> None:
    callback = bpy.app.driver_namespace.pop(_SYNC_TIMER_NAMESPACE_KEY, None)
    if callback is not None and bpy.app.timers.is_registered(callback):
        bpy.app.timers.unregister(callback)


def _schedule_material_sync() -> None:
    _cancel_deferred_sync()
    bpy.app.driver_namespace[_SYNC_TIMER_NAMESPACE_KEY] = _vrml2_deferred_sync
    bpy.app.timers.register(_vrml2_deferred_sync, first_interval=0.0)


def _unregister_classes(classes) -> None:
    """Unregister this extension's current or stale classes by RNA name."""
    for cls in reversed(classes):
        registered_cls = getattr(bpy.types, cls.__name__, None)
        if registered_cls is None:
            for base_type in (
                bpy.types.PropertyGroup,
                bpy.types.Operator,
                bpy.types.Menu,
                bpy.types.Panel,
            ):
                if issubclass(cls, base_type):
                    registered_cls = base_type.bl_rna_get_subclass_py(cls.__name__)
                    break
        if registered_cls is None and getattr(cls, "is_registered", False):
            registered_cls = cls
        if registered_cls is not None:
            bpy.utils.unregister_class(registered_cls)


def _clear_existing_registration() -> None:
    """Remove an earlier enabled copy before registering the current module."""
    _cancel_deferred_sync()

    for handler in tuple(bpy.app.handlers.load_post):
        if getattr(handler, _LOAD_HANDLER_TAG, False):
            bpy.app.handlers.load_post.remove(handler)

    _unregister_classes(ui.CLASSES)
    _unregister_classes(operators.CLASSES)
    for base_type, class_name in _REMOVED_CLASS_NAMES:
        registered_cls = base_type.bl_rna_get_subclass_py(class_name)
        if registered_cls is not None:
            bpy.utils.unregister_class(registered_cls)

    if hasattr(bpy.types.Material, MATERIAL_POINTER_NAME):
        delattr(bpy.types.Material, MATERIAL_POINTER_NAME)

    _unregister_classes(properties.CLASSES)


def register() -> None:
    _clear_existing_registration()

    try:
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

        bpy.app.handlers.load_post.append(_vrml2_load_post)
        _schedule_material_sync()
    except Exception:
        _clear_existing_registration()
        raise


def unregister() -> None:
    _clear_existing_registration()
