# SPDX-FileCopyrightText: 2026 Brianna O'Leary
# SPDX-License-Identifier: GPL-3.0-or-later

"""Pure-Python VRML2 Material block parsing and formatting helpers."""

from __future__ import annotations

import re
from typing import Any

_FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_SEPARATOR = r"(?:\s|,)+"
_COLOR_FIELDS = ("diffuseColor", "emissiveColor", "specularColor")
_SCALAR_FIELDS = ("ambientIntensity", "shininess", "transparency")
_FIELD_TO_PYTHON = {
    "ambientIntensity": "ambient_intensity",
    "diffuseColor": "diffuse_color",
    "emissiveColor": "emissive_color",
    "shininess": "shininess",
    "specularColor": "specular_color",
    "transparency": "transparency",
}


def _strip_comments(text: str) -> str:
    return re.sub(r"#.*?$", "", text.replace("\ufeff", ""), flags=re.MULTILINE)


def _first_material_block(text: str) -> tuple[str, str | None]:
    """Return the first balanced Material block and an optional DEF name."""
    cleaned = _strip_comments(text)
    match = re.search(
        r"(?:\bDEF\s+([^\s\[\]\{\},]+)\s+)?\bMaterial\s*\{",
        cleaned,
        flags=re.IGNORECASE,
    )
    if not match:
        return cleaned, None

    opening = cleaned.find("{", match.start())
    depth = 0
    for index in range(opening, len(cleaned)):
        char = cleaned[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return cleaned[match.start() : index + 1], match.group(1)

    return cleaned[match.start() :], match.group(1)


def has_material_block(text: str) -> bool:
    """Return whether text contains a Material node rather than partial fields."""
    if not isinstance(text, str):
        return False
    return bool(re.search(r"\bMaterial\s*\{", _strip_comments(text), flags=re.IGNORECASE))


def parse_material_block(text: str) -> dict[str, Any]:
    """Parse the first VRML2 Material block.

    Partial blocks are accepted. Only fields found in the text are returned.
    Values are not clamped here so callers can decide how to report invalid data.
    """
    if not isinstance(text, str) or not text.strip():
        return {}

    block, def_name = _first_material_block(text)
    parsed: dict[str, Any] = {}

    for field in _COLOR_FIELDS:
        match = re.search(
            rf"\b{field}\b{_SEPARATOR}({_FLOAT}){_SEPARATOR}({_FLOAT}){_SEPARATOR}({_FLOAT})",
            block,
            flags=re.IGNORECASE,
        )
        if match:
            parsed[_FIELD_TO_PYTHON[field]] = tuple(float(match.group(i)) for i in range(1, 4))

    for field in _SCALAR_FIELDS:
        match = re.search(
            rf"\b{field}\b{_SEPARATOR}({_FLOAT})",
            block,
            flags=re.IGNORECASE,
        )
        if match:
            parsed[_FIELD_TO_PYTHON[field]] = float(match.group(1))

    if def_name:
        parsed["def_name"] = def_name

    return parsed


def format_number(value: float) -> str:
    value = 0.0 if abs(float(value)) < 5e-10 else float(value)
    return f"{value:.9g}"


def format_color(value: Any) -> str:
    return " ".join(format_number(component) for component in tuple(value)[:3])


def sanitize_def_name(name: str, fallback: str = "VRML2_Material") -> str:
    """Create a conservative ASCII VRML DEF identifier."""
    candidate = re.sub(r"[^A-Za-z0-9_]", "_", (name or "").strip())
    candidate = re.sub(r"_+", "_", candidate).strip("_")
    if not candidate:
        candidate = fallback
    if candidate[0].isdigit():
        candidate = f"MAT_{candidate}"
    return candidate


def format_material_block(values: dict[str, Any], def_name: str = "") -> str:
    prefix = f"DEF {sanitize_def_name(def_name)} " if def_name.strip() else ""
    lines = [f"{prefix}Material {{"]
    lines.append(f"  ambientIntensity {format_number(values['ambient_intensity'])}")
    lines.append(f"  diffuseColor {format_color(values['diffuse_color'])}")
    if values.get("include_emissive_color", True):
        lines.append(f"  emissiveColor {format_color(values['emissive_color'])}")
    lines.append(f"  shininess {format_number(values['shininess'])}")
    if values.get("include_specular_color", True):
        lines.append(f"  specularColor {format_color(values['specular_color'])}")
    lines.append(f"  transparency {format_number(values['transparency'])}")
    lines.append("}")
    return "\n".join(lines)
