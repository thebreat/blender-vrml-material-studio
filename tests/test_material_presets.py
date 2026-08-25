from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_DATA_PATH = ROOT / "material_presets.json"
THEMED_DATA_PATH = ROOT / "vrml97_material_library.json"


class PresetLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_data = json.loads(ORIGINAL_DATA_PATH.read_text(encoding="utf-8"))
        cls.themed_data = json.loads(THEMED_DATA_PATH.read_text(encoding="utf-8"))
        cls.presets = cls.original_data["materials"] + cls.themed_data

    def test_library_counts_and_hierarchy(self) -> None:
        self.assertEqual(len(self.original_data["materials"]), 433)
        self.assertEqual(len(self.themed_data), 1200)
        self.assertEqual(len(self.presets), 1633)
        self.assertEqual(len({preset["theme"] for preset in self.themed_data}), 30)
        self.assertEqual(len({preset["category"] for preset in self.themed_data}), 150)
        self.assertTrue(all("theme" in preset for preset in self.themed_data))

    def test_every_preset_is_valid_vrml97_material_data(self) -> None:
        names = set()
        for preset in self.presets:
            self.assertTrue(preset["name"])
            self.assertNotIn(preset["name"], names)
            names.add(preset["name"])
            self.assertTrue(preset["category"])

            for field in ("diffuseColor", "emissiveColor", "specularColor"):
                self.assertEqual(len(preset[field]), 3)
                self.assertTrue(all(0.0 <= value <= 1.0 for value in preset[field]))
            for field in ("ambientIntensity", "shininess", "transparency"):
                self.assertGreaterEqual(preset[field], 0.0)
                self.assertLessEqual(preset[field], 1.0)


if __name__ == "__main__":
    unittest.main()
