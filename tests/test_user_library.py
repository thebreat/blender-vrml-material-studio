from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "user_library.py"
SPEC = importlib.util.spec_from_file_location("user_library", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
user_library = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(user_library)


BLUE = {
    "diffuse_color": (0.1, 0.2, 0.9),
    "emissive_color": (0.0, 0.0, 0.0),
    "specular_color": (0.5, 0.5, 0.5),
    "ambient_intensity": 0.2,
    "shininess": 0.6,
    "transparency": 0.0,
}
RED = dict(BLUE, diffuse_color=(0.9, 0.1, 0.1))


class UserLibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = ""
        self.write_count = 0

    def write_text(self, text: str) -> None:
        self.text = text
        self.write_count += 1

    def open_library(self):
        return user_library.UserLibrary(lambda: self.text, self.write_text)

    def test_empty_preference_is_an_empty_library(self) -> None:
        library = self.open_library()
        self.assertEqual(library.favorites, [])
        self.assertEqual(library.custom, [])
        self.assertEqual(self.text, "")

    def test_saved_presets_survive_a_new_library_instance(self) -> None:
        entry, replaced = self.open_library().save_custom("  Deep Blue ", BLUE)
        self.assertFalse(replaced)
        self.assertEqual(entry["name"], "Deep Blue")

        reopened = self.open_library()
        self.assertEqual(len(reopened.custom), 1)
        stored = reopened.find_custom(entry["id"])
        self.assertEqual(stored["diffuseColor"], [0.1, 0.2, 0.9])
        self.assertEqual(user_library.entry_values(stored), dict(BLUE))
        self.assertEqual(json.loads(self.text)["version"], user_library.SCHEMA_VERSION)

    def test_values_are_clamped_to_vrml_range(self) -> None:
        entry, _replaced = self.open_library().save_custom(
            "Hot",
            dict(BLUE, diffuse_color=(1.5, -0.2, 0.5), shininess=4.0),
        )
        self.assertEqual(entry["diffuseColor"], [1.0, 0.0, 0.5])
        self.assertEqual(entry["shininess"], 1.0)

    def test_saving_an_existing_name_replaces_it_and_keeps_favorite(self) -> None:
        library = self.open_library()
        first, _replaced = library.save_custom("Signal", BLUE)
        library.set_favorite(user_library.custom_key(first["id"]), True)

        second, replaced = library.save_custom("signal", RED)
        self.assertTrue(replaced)
        self.assertEqual(second["id"], first["id"])
        self.assertEqual(second["name"], "signal")
        self.assertEqual(second["diffuseColor"], [0.9, 0.1, 0.1])
        self.assertEqual(len(library.custom), 1)
        self.assertTrue(library.is_favorite(user_library.custom_key(first["id"])))

    def test_update_rename_and_delete(self) -> None:
        library = self.open_library()
        blue, _replaced = library.save_custom("Blue", BLUE)
        red, _replaced = library.save_custom("Red", RED)

        updated = library.update_custom(blue["id"], RED)
        self.assertEqual(updated["diffuseColor"], [0.9, 0.1, 0.1])

        with self.assertRaises(ValueError):
            library.rename_custom(blue["id"], "RED")
        with self.assertRaises(ValueError):
            library.rename_custom(blue["id"], "   ")
        self.assertEqual(library.rename_custom(blue["id"], "Crimson")["name"], "Crimson")

        key = user_library.custom_key(red["id"])
        library.set_favorite(key, True)
        library.delete_custom(red["id"])
        self.assertIsNone(library.find_custom(red["id"]))
        self.assertFalse(library.is_favorite(key))
        self.assertEqual([entry["name"] for entry in self.open_library().custom], ["Crimson"])

        with self.assertRaises(ValueError):
            library.delete_custom(red["id"])

    def test_favorites_keep_their_order(self) -> None:
        library = self.open_library()
        custom, _replaced = library.save_custom("Blue", BLUE)
        keys = [
            user_library.preset_key("Clear glass"),
            user_library.custom_key(custom["id"]),
            user_library.preset_key("Titanium White - Traditional Oil Pigments"),
        ]
        for key in keys:
            self.assertTrue(library.toggle_favorite(key))
        self.assertEqual(self.open_library().favorites, keys)

        self.assertFalse(library.toggle_favorite(keys[0]))
        self.assertEqual(self.open_library().favorites, keys[1:])

        with self.assertRaises(ValueError):
            library.set_favorite(user_library.custom_key("missing"), True)
        with self.assertRaises(ValueError):
            library.set_favorite("not-a-key", True)

    def test_changes_from_another_instance_are_reloaded(self) -> None:
        first = self.open_library()
        second = self.open_library()
        first.save_custom("Blue", BLUE)
        second.save_custom("Red", RED)

        self.assertEqual([entry["name"] for entry in second.custom], ["Blue", "Red"])
        revision = first.revision
        self.assertTrue(first.refresh())
        self.assertNotEqual(first.revision, revision)
        self.assertEqual([entry["name"] for entry in first.custom], ["Blue", "Red"])
        self.assertFalse(first.refresh())

    def test_unreadable_preference_does_not_prevent_recovery(self) -> None:
        self.text = "{ not json"
        library = self.open_library()
        self.assertEqual(library.custom, [])
        library.save_custom("Recovered", BLUE)
        self.assertEqual(json.loads(self.text)["custom"][0]["name"], "Recovered")

    def test_invalid_entries_are_skipped_and_unknown_data_is_kept(self) -> None:
        valid = {
            "id": "abc",
            "name": "Kept",
            "diffuseColor": [0.1, 0.2, 0.3],
            "emissiveColor": [0, 0, 0],
            "specularColor": [0, 0, 0],
            "ambientIntensity": 0.2,
            "shininess": 0.2,
            "transparency": 0,
            "note": "from a newer version",
        }
        self.text = json.dumps(
            {
                "version": 99,
                "future": {"setting": True},
                "favorites": ["custom:abc", "custom:gone", "preset:Clear glass", 4, "bogus"],
                "custom": [
                    valid,
                    dict(valid),  # Duplicate id.
                    {"id": "bad", "name": "Missing fields"},
                    {"id": "nan", **{key: value for key, value in valid.items() if key != "id"}, "shininess": "x"},
                ],
            }
        )
        library = self.open_library()
        self.assertEqual([entry["id"] for entry in library.custom], ["abc"])
        self.assertEqual(library.favorites, ["custom:abc", "preset:Clear glass"])

        library.save_custom("Another", BLUE)
        saved = json.loads(self.text)
        self.assertEqual(saved["future"], {"setting": True})
        self.assertEqual(saved["custom"][0]["note"], "from a newer version")

    def test_save_and_favorite_are_one_preference_update(self) -> None:
        library = self.open_library()
        entry, _replaced = library.save_custom("Blue", BLUE, add_to_favorites=True)
        self.assertEqual(self.write_count, 1)
        self.assertEqual(library.favorites, [user_library.custom_key(entry["id"])])

    def test_helpers(self) -> None:
        self.assertEqual(user_library.split_key("preset:Clear glass"), ("preset", "Clear glass"))
        self.assertEqual(user_library.split_key("custom:abc"), ("custom", "abc"))
        self.assertEqual(user_library.split_key("custom:"), ("", "custom:"))
        self.assertEqual(user_library.color_hex((1.0, 0.5, 0.0)), "#FF8000")


if __name__ == "__main__":
    unittest.main()
