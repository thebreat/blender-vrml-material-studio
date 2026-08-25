from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "vrml_text.py"
SPEC = importlib.util.spec_from_file_location("vrml_text", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
vrml_text = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vrml_text)


class ParseMaterialBlockTests(unittest.TestCase):
    def test_complete_def_material(self) -> None:
        parsed = vrml_text.parse_material_block(
            """
            # Comments should be ignored.
            DEF Red_Plastic Material {
              ambientIntensity 0.25
              diffuseColor 1 0.1 0
              emissiveColor 0 0 0
              shininess 7.5e-1
              specularColor 0.8 0.8 0.8
              transparency 0.05
            }
            """
        )

        self.assertEqual(parsed["def_name"], "Red_Plastic")
        self.assertEqual(parsed["diffuse_color"], (1.0, 0.1, 0.0))
        self.assertEqual(parsed["shininess"], 0.75)
        self.assertEqual(parsed["transparency"], 0.05)

    def test_partial_fields_and_commas(self) -> None:
        parsed = vrml_text.parse_material_block(
            "diffuseColor 0.2, 0.4, 0.8\ntransparency .5"
        )

        self.assertEqual(
            parsed,
            {"diffuse_color": (0.2, 0.4, 0.8), "transparency": 0.5},
        )

    def test_first_material_block_wins(self) -> None:
        parsed = vrml_text.parse_material_block(
            "Material { diffuseColor 1 0 0 } Material { diffuseColor 0 1 0 }"
        )

        self.assertEqual(parsed["diffuse_color"], (1.0, 0.0, 0.0))

    def test_empty_input(self) -> None:
        self.assertEqual(vrml_text.parse_material_block(""), {})

    def test_distinguishes_material_block_from_partial_fields(self) -> None:
        self.assertTrue(vrml_text.has_material_block("Material { diffuseColor 1 0 0 }"))
        self.assertTrue(vrml_text.has_material_block("DEF Test Material { }"))
        self.assertFalse(vrml_text.has_material_block("diffuseColor 1 0 0"))


class FormatMaterialBlockTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        values = {
            "ambient_intensity": 0.2,
            "diffuse_color": (0.8, 0.7, 0.6),
            "emissive_color": (0.0, 0.1, 0.2),
            "shininess": 0.75,
            "specular_color": (1.0, 0.9, 0.8),
            "transparency": 0.25,
        }

        block = vrml_text.format_material_block(values, "Sample Material")
        parsed = vrml_text.parse_material_block(block)

        self.assertEqual(parsed["def_name"], "Sample_Material")
        for key, expected in values.items():
            self.assertEqual(parsed[key], expected)

    def test_sanitize_def_name(self) -> None:
        self.assertEqual(vrml_text.sanitize_def_name("  123 odd/name  "), "MAT_123_odd_name")
        self.assertEqual(vrml_text.sanitize_def_name("!!!"), "VRML2_Material")

    def test_default_color_fields_are_serialized_in_editor_order(self) -> None:
        values = {
            "ambient_intensity": 0.2,
            "diffuse_color": (0.8, 0.7, 0.6),
            "emissive_color": (0.0, 0.0, 0.0),
            "shininess": 0.0,
            "specular_color": (0.0, 0.0, 0.0),
            "transparency": 0.0,
        }

        block = vrml_text.format_material_block(values)

        field_lines = [line.strip().split()[0] for line in block.splitlines()[1:-1]]
        self.assertEqual(
            field_lines,
            [
                "diffuseColor",
                "emissiveColor",
                "specularColor",
                "ambientIntensity",
                "shininess",
                "transparency",
            ],
        )
        self.assertEqual(vrml_text.parse_material_block(block)["specular_color"], (0.0, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
