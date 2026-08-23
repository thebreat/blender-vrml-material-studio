from __future__ import annotations

import json
from pathlib import Path
import unittest


DATA_PATH = Path(__file__).resolve().parents[1] / "material_presets.json"


class ContributedMaterialLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    def test_library_identity_and_counts(self) -> None:
        self.assertEqual(self.data["credit"], "Breetos")
        self.assertEqual(self.data["count"], 433)
        self.assertEqual(len(self.data["materials"]), 433)
        self.assertEqual(len(self.data["categories"]), 13)

    def test_every_preset_is_valid_vrml97_material_data(self) -> None:
        names = set()
        categories = set(self.data["categories"])
        for preset in self.data["materials"]:
            self.assertTrue(preset["name"])
            self.assertNotIn(preset["name"], names)
            names.add(preset["name"])
            self.assertIn(preset["category"], categories)

            for field in ("diffuseColor", "emissiveColor", "specularColor"):
                self.assertEqual(len(preset[field]), 3)
                self.assertTrue(all(0.0 <= value <= 1.0 for value in preset[field]))
            for field in ("ambientIntensity", "shininess", "transparency"):
                self.assertGreaterEqual(preset[field], 0.0)
                self.assertLessEqual(preset[field], 1.0)


if __name__ == "__main__":
    unittest.main()
