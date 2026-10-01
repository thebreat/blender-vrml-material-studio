# SPDX-FileCopyrightText: 2026 Brianna O'Leary
# SPDX-License-Identifier: GPL-3.0-or-later

"""Favorites and personal presets stored in Blender's add-on preferences."""

from __future__ import annotations

import json
import math
from typing import Any, Callable, Iterable
import uuid


SCHEMA_VERSION = 1
PRESET_PREFIX = "preset:"
CUSTOM_PREFIX = "custom:"

# Stored entries use the same camelCase field names as the bundled presets so
# both can share the preset helpers and preview swatches.
COLOR_FIELDS = (
    ("diffuse_color", "diffuseColor"),
    ("emissive_color", "emissiveColor"),
    ("specular_color", "specularColor"),
)
SCALAR_FIELDS = (
    ("ambient_intensity", "ambientIntensity"),
    ("shininess", "shininess"),
    ("transparency", "transparency"),
)

_LIBRARY: UserLibrary | None = None
_PREFERENCES_ID: int | None = None
_PREFERENCE_ACCESSORS_OVERRIDE: tuple[Callable[[], str], Callable[[str], None]] | None = None


def preset_key(name: str) -> str:
    return f"{PRESET_PREFIX}{name}"


def custom_key(custom_id: str) -> str:
    return f"{CUSTOM_PREFIX}{custom_id}"


def split_key(key: str) -> tuple[str, str]:
    """Return ("preset" | "custom" | "", identifier) for a favorite key."""
    for kind, prefix in (("preset", PRESET_PREFIX), ("custom", CUSTOM_PREFIX)):
        if key.startswith(prefix) and len(key) > len(prefix):
            return kind, key[len(prefix):]
    return "", key


def _unit(value: Any) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite value")
    return round(max(0.0, min(1.0, number)), 6)


def _color(value: Any) -> list[float]:
    components = [_unit(component) for component in value]
    if len(components) != 3:
        raise ValueError("colors need three components")
    return components


def fields_from_values(values: dict[str, Any]) -> dict[str, Any]:
    """Convert snake_case VRML values into clamped stored fields."""
    fields: dict[str, Any] = {}
    for value_key, field in COLOR_FIELDS:
        fields[field] = _color(values[value_key])
    for value_key, field in SCALAR_FIELDS:
        fields[field] = _unit(values[value_key])
    return fields


def entry_values(entry: dict[str, Any]) -> dict[str, Any]:
    """Convert a stored entry into snake_case values for core.apply_values."""
    values: dict[str, Any] = {}
    for value_key, field in COLOR_FIELDS:
        values[value_key] = tuple(entry[field])
    for value_key, field in SCALAR_FIELDS:
        values[value_key] = entry[field]
    return values


def color_hex(color: Iterable[float]) -> str:
    return "#" + "".join(f"{round(_unit(component) * 255):02X}" for component in color)


def fingerprint(entry: dict[str, Any]) -> str:
    """Identify an entry's current values, so changed swatches are redrawn."""
    parts = [entry["id"]]
    for _value_key, field in COLOR_FIELDS:
        parts.extend(f"{component:.6f}" for component in entry[field])
    for _value_key, field in SCALAR_FIELDS:
        parts.append(f"{entry[field]:.6f}")
    return ":".join(parts)


def _normalize_custom(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    custom_id = raw.get("id")
    name = raw.get("name")
    if not isinstance(custom_id, str) or not custom_id:
        return None
    if not isinstance(name, str) or not name.strip():
        return None
    try:
        fields = {field: _color(raw[field]) for _value_key, field in COLOR_FIELDS}
        fields.update({field: _unit(raw[field]) for _value_key, field in SCALAR_FIELDS})
    except (KeyError, TypeError, ValueError):
        return None
    # Keep unknown keys so a newer version's extra data survives a save.
    entry = dict(raw)
    entry.update(fields, id=custom_id, name=name.strip())
    return entry


class UserLibrary:
    """Favorites and personal presets backed by a JSON text property.

    Blender owns persistence of the property in its preferences. Keeping the
    serializer independent from ``bpy`` makes the data rules easy to test.
    """

    def __init__(
        self,
        read_text: Callable[[], str],
        write_text: Callable[[str], None],
    ):
        self._read_text = read_text
        self._write_text = write_text
        self.favorites: list[str] = []
        self.custom: list[dict[str, Any]] = []
        self.revision = ""
        self._extra: dict[str, Any] = {}
        self._source_text = ""
        self._favorite_set: frozenset[str] = frozenset()
        self._custom_by_id: dict[str, dict[str, Any]] = {}
        self.refresh(force=True)

    # Reading ---------------------------------------------------------------

    def refresh(self, force: bool = False) -> bool:
        """Reload when the preference text changed. Returns True after reload."""
        text = self._read_text() or ""
        if not force and text == self._source_text:
            return False
        favorites, custom, extra = self._decode(text)
        self._source_text = text
        self._commit(favorites, custom, extra)
        return True

    @staticmethod
    def _decode(text: str) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
        if not text.strip():
            return [], [], {}
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("the top level is not an object")
        except (TypeError, ValueError):
            # A malformed preference should not prevent the extension loading.
            return [], [], {}

        custom = []
        seen_ids = set()
        for raw in data.get("custom", ()) if isinstance(data.get("custom"), list) else ():
            entry = _normalize_custom(raw)
            if entry is not None and entry["id"] not in seen_ids:
                seen_ids.add(entry["id"])
                custom.append(entry)

        favorites = []
        raw_favorites = data.get("favorites")
        for key in raw_favorites if isinstance(raw_favorites, list) else ():
            if not isinstance(key, str) or key in favorites:
                continue
            kind, identifier = split_key(key)
            if kind == "preset" or (kind == "custom" and identifier in seen_ids):
                favorites.append(key)

        extra = {
            key: value
            for key, value in data.items()
            if key not in {"version", "favorites", "custom"}
        }
        return favorites, custom, extra

    def _commit(
        self,
        favorites: list[str],
        custom: list[dict[str, Any]],
        extra: dict[str, Any],
    ) -> None:
        self.favorites = favorites
        self.custom = custom
        self._extra = extra
        self._favorite_set = frozenset(favorites)
        self._custom_by_id = {entry["id"]: entry for entry in custom}
        self.revision = uuid.uuid4().hex

    # Writing ---------------------------------------------------------------

    def _write(self, favorites: list[str], custom: list[dict[str, Any]]) -> None:
        payload = dict(self._extra)
        payload.update(version=SCHEMA_VERSION, favorites=favorites, custom=custom)
        text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        self._write_text(text)
        self._source_text = text
        self._commit(favorites, custom, self._extra)

    def _working_copy(self) -> tuple[list[str], list[dict[str, Any]]]:
        self.refresh()
        return list(self.favorites), [dict(entry) for entry in self.custom]

    # Queries ---------------------------------------------------------------

    def is_favorite(self, key: str) -> bool:
        return key in self._favorite_set

    def find_custom(self, custom_id: str) -> dict[str, Any] | None:
        return self._custom_by_id.get(custom_id)

    def find_custom_by_name(self, name: str) -> dict[str, Any] | None:
        wanted = name.strip().casefold()
        return next((entry for entry in self.custom if entry["name"].casefold() == wanted), None)

    # Changes ---------------------------------------------------------------

    def set_favorite(self, key: str, favorite: bool) -> None:
        favorites, custom = self._working_copy()
        kind, identifier = split_key(key)
        if kind == "custom" and not any(entry["id"] == identifier for entry in custom):
            raise ValueError("That saved preset no longer exists")
        if not kind:
            raise ValueError(f"Unrecognized favorite {key!r}")
        if favorite and key not in favorites:
            favorites.append(key)
        elif not favorite and key in favorites:
            favorites.remove(key)
        else:
            return
        self._write(favorites, custom)

    def toggle_favorite(self, key: str) -> bool:
        """Toggle a favorite and return True when it is now a favorite."""
        self.refresh()
        favorite = not self.is_favorite(key)
        self.set_favorite(key, favorite)
        return favorite

    def save_custom(
        self,
        name: str,
        values: dict[str, Any],
        add_to_favorites: bool = False,
    ) -> tuple[dict[str, Any], bool]:
        """Add a personal preset, or replace the one with the same name."""
        name = name.strip()
        if not name:
            raise ValueError("Saved presets need a name")
        fields = fields_from_values(values)
        favorites, custom = self._working_copy()
        wanted = name.casefold()
        existing = next((entry for entry in custom if entry["name"].casefold() == wanted), None)
        if existing is None:
            existing = {"id": uuid.uuid4().hex, "name": name}
            custom.append(existing)
            replaced = False
        else:
            replaced = True
        existing.update(fields, name=name)
        if add_to_favorites:
            key = custom_key(existing["id"])
            if key not in favorites:
                favorites.append(key)
        self._write(favorites, custom)
        return self._custom_by_id[existing["id"]], replaced

    def update_custom(self, custom_id: str, values: dict[str, Any]) -> dict[str, Any]:
        fields = fields_from_values(values)
        favorites, custom = self._working_copy()
        entry = next((entry for entry in custom if entry["id"] == custom_id), None)
        if entry is None:
            raise ValueError("That saved preset no longer exists")
        entry.update(fields)
        self._write(favorites, custom)
        return self._custom_by_id[custom_id]

    def rename_custom(self, custom_id: str, name: str) -> dict[str, Any]:
        name = name.strip()
        if not name:
            raise ValueError("Saved presets need a name")
        favorites, custom = self._working_copy()
        entry = next((entry for entry in custom if entry["id"] == custom_id), None)
        if entry is None:
            raise ValueError("That saved preset no longer exists")
        if any(
            other["id"] != custom_id and other["name"].casefold() == name.casefold()
            for other in custom
        ):
            raise ValueError(f"A saved preset named {name!r} already exists")
        entry["name"] = name
        self._write(favorites, custom)
        return self._custom_by_id[custom_id]

    def delete_custom(self, custom_id: str) -> dict[str, Any]:
        favorites, custom = self._working_copy()
        entry = next((entry for entry in custom if entry["id"] == custom_id), None)
        if entry is None:
            raise ValueError("That saved preset no longer exists")
        custom.remove(entry)
        key = custom_key(custom_id)
        if key in favorites:
            favorites.remove(key)
        self._write(favorites, custom)
        return entry


def reset() -> None:
    """Forget the runtime cache after registration or test setup changes."""
    global _LIBRARY, _PREFERENCES_ID
    _LIBRARY = None
    _PREFERENCES_ID = None


def set_preference_accessors(
    read_text: Callable[[], str] | None,
    write_text: Callable[[str], None] | None,
) -> None:
    """Override Blender preference access for an isolated test harness."""
    global _PREFERENCE_ACCESSORS_OVERRIDE
    if (read_text is None) != (write_text is None):
        raise ValueError("Both preference accessors are required")
    _PREFERENCE_ACCESSORS_OVERRIDE = (
        (read_text, write_text) if read_text is not None and write_text is not None else None
    )
    reset()


def _preference_accessors() -> tuple[Callable[[], str], Callable[[str], None], int]:
    if _PREFERENCE_ACCESSORS_OVERRIDE is not None:
        read_text, write_text = _PREFERENCE_ACCESSORS_OVERRIDE
        return read_text, write_text, id(_PREFERENCE_ACCESSORS_OVERRIDE)

    import bpy

    addon = bpy.context.preferences.addons.get(__package__)
    if addon is None:
        raise RuntimeError("VRML2 Material Studio preferences are unavailable")
    preferences = addon.preferences

    def write_text(text: str) -> None:
        preferences.user_library_data = text
        # Programmatic RNA changes do not set this flag automatically. Marking
        # the preferences dirty lets Blender's normal auto-save setting decide
        # when to persist the update, without forcing unrelated preferences to
        # disk when the user has disabled auto-save.
        bpy.context.preferences.is_dirty = True

    return (
        lambda: preferences.user_library_data,
        write_text,
        id(preferences),
    )


def library(refresh: bool = True) -> UserLibrary:
    """Return the shared library stored in Blender's add-on preferences."""
    global _LIBRARY, _PREFERENCES_ID
    read_text, write_text, preferences_id = _preference_accessors()
    if _LIBRARY is None or _PREFERENCES_ID != preferences_id:
        _LIBRARY = UserLibrary(read_text, write_text)
        _PREFERENCES_ID = preferences_id
    elif refresh:
        _LIBRARY.refresh()
    return _LIBRARY
