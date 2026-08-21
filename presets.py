# SPDX-FileCopyrightText: 2026 Brianna O'Leary
# SPDX-License-Identifier: GPL-3.0-or-later

PRESETS = {
    "VRML_DEFAULT": {
        "label": "VRML97 Default",
        "diffuse_color": (0.8, 0.8, 0.8),
        "emissive_color": (0.0, 0.0, 0.0),
        "specular_color": (0.0, 0.0, 0.0),
        "ambient_intensity": 0.2,
        "shininess": 0.2,
        "transparency": 0.0,
    },
    "MATTE": {
        "label": "Matte",
        "diffuse_color": (0.5, 0.5, 0.5),
        "emissive_color": (0.0, 0.0, 0.0),
        "specular_color": (0.04, 0.04, 0.04),
        "ambient_intensity": 0.25,
        "shininess": 0.05,
        "transparency": 0.0,
    },
    "GLOSSY_PLASTIC": {
        "label": "Glossy Plastic",
        "diffuse_color": (0.25, 0.25, 0.25),
        "emissive_color": (0.0, 0.0, 0.0),
        "specular_color": (0.75, 0.75, 0.75),
        "ambient_intensity": 0.2,
        "shininess": 0.7,
        "transparency": 0.0,
    },
    "POLISHED_METAL": {
        "label": "Polished Metal",
        "diffuse_color": (0.12, 0.12, 0.12),
        "emissive_color": (0.0, 0.0, 0.0),
        "specular_color": (0.9, 0.9, 0.9),
        "ambient_intensity": 0.08,
        "shininess": 0.92,
        "transparency": 0.0,
    },
    "CLEAR_GLASS": {
        "label": "Clear Glass",
        "diffuse_color": (0.82, 0.9, 1.0),
        "emissive_color": (0.0, 0.0, 0.0),
        "specular_color": (0.95, 0.95, 0.95),
        "ambient_intensity": 0.08,
        "shininess": 0.95,
        "transparency": 0.85,
    },
    "EMISSIVE": {
        "label": "Emissive",
        "diffuse_color": (0.0, 0.0, 0.0),
        "emissive_color": (0.8, 0.8, 0.8),
        "specular_color": (0.0, 0.0, 0.0),
        "ambient_intensity": 0.0,
        "shininess": 0.0,
        "transparency": 0.0,
    },
}

PRESET_ITEMS = tuple((key, value["label"], "") for key, value in PRESETS.items())
