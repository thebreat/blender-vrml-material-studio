# SPDX-FileCopyrightText: 2026 Brianna O'Leary
# SPDX-License-Identifier: GPL-3.0-or-later

PRESETS = {
    "VRML_DEFAULT": {
        "label": "VRML97 Default",
        "ambient_intensity": 0.2,
        "diffuse_color": (0.8, 0.8, 0.8),
        "emissive_color": (0.0, 0.0, 0.0),
        "shininess": 0.2,
        "specular_color": (0.0, 0.0, 0.0),
        "transparency": 0.0,
    },
    "MATTE": {
        "label": "Matte",
        "ambient_intensity": 0.25,
        "diffuse_color": (0.5, 0.5, 0.5),
        "emissive_color": (0.0, 0.0, 0.0),
        "shininess": 0.05,
        "specular_color": (0.04, 0.04, 0.04),
        "transparency": 0.0,
    },
    "GLOSSY_PLASTIC": {
        "label": "Glossy Plastic",
        "ambient_intensity": 0.2,
        "diffuse_color": (0.25, 0.25, 0.25),
        "emissive_color": (0.0, 0.0, 0.0),
        "shininess": 0.7,
        "specular_color": (0.75, 0.75, 0.75),
        "transparency": 0.0,
    },
    "POLISHED_METAL": {
        "label": "Polished Metal",
        "ambient_intensity": 0.08,
        "diffuse_color": (0.12, 0.12, 0.12),
        "emissive_color": (0.0, 0.0, 0.0),
        "shininess": 0.92,
        "specular_color": (0.9, 0.9, 0.9),
        "transparency": 0.0,
    },
    "CLEAR_GLASS": {
        "label": "Clear Glass",
        "ambient_intensity": 0.08,
        "diffuse_color": (0.82, 0.9, 1.0),
        "emissive_color": (0.0, 0.0, 0.0),
        "shininess": 0.95,
        "specular_color": (0.95, 0.95, 0.95),
        "transparency": 0.85,
    },
    "EMISSIVE": {
        "label": "Emissive",
        "ambient_intensity": 0.0,
        "diffuse_color": (0.0, 0.0, 0.0),
        "emissive_color": (0.8, 0.8, 0.8),
        "shininess": 0.0,
        "specular_color": (0.0, 0.0, 0.0),
        "transparency": 0.0,
    },
}

PRESET_ITEMS = tuple((key, value["label"], "") for key, value in PRESETS.items())
