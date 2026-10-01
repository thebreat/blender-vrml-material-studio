# Changelog

## 0.5.0 - Unreleased

- Added Favorites: star any built-in or personal preset to collect it in a separate list.
- Added My Presets: save all six active VRML97 fields under a name, then apply, overwrite, rename, or delete the preset.
- Organized Favorites, My Presets, and Built-in Presets inside one collapsible Presets section.
- Added explicit Apply buttons so applying a preset is separate from selecting one for management.
- Stored favorites and personal presets in Blender's add-on preferences so they work across projects without requesting file access permission.

## 0.4.0 - 2026-08-24

- Added 1,200 VRML97 presets, bringing the bundled library to 1,633 entries.
- Organized the new presets into 30 themes and 150 categories.
- Added hierarchical Theme and Category filters so only the selected theme's five categories fill the category menu.
- Expanded search to match preset names, themes, and categories.
- Kept the original 433 entries together under Original Presets.

## 0.3.0 - 2026-08-23

- Added a collapsed-by-default Presets library at the bottom of Material Studio.
- Bundled 433 presets across 13 categories.
- Added name search, category filtering, and direct one-click application to the active material.
- Added shaded circular preview swatches inspired by the Cybertown Mall Material Previewer design.
- Made the swatches reflect diffuse, emissive, specular, shininess, and transparency values.
- Preserved the active Blender material name and VRML DEF name when applying a library entry.
- Retained warnings for the fifteen source entries whose values required VRML97 clamping.

## 0.2.0 - 2026-08-21

- Replaced the Blender diffuse/glossy approximation with a direct VRML97 lighting equation.
- Added the official 3DGrove Item Viewer four-light reference rig.
- Made VRML preview lighting independent of Blender lights, HDRIs, metallic, Fresnel, and roughness.
- Added Blender runtime coverage for the shared VRML97 shader group.
- Made extension registration reload-safe when installing an update over an enabled copy.
- Deferred the initial material scan until Blender releases its restricted registration context.
- Added VRML97 `Set Default` actions for `ambientIntensity`, `emissiveColor`, and `specularColor`.
- Reordered the editor and copied VRML fields to diffuse, emissive, specular, ambient, shininess, transparency.
- Clarified that visible shininess changes depend on surface angle.
- Expanded render regression coverage to include both smooth and faceted geometry.
- Corrected the opposite camera-space Z axis so all CTR reference lights illuminate the intended side of the object.
- Added each official light's VRML ambient contribution, making material `ambientIntensity` visible again.
- Moved display compensation after the completed VRML lighting equation so Blender Standard matches X_ITE channel values without requiring Raw.
- Removed alternate preview-light selectors, material presets, and the manual preview-rebuild control to keep the editor focused on native VRML97 fields.
- Replaced the shared-material warning box with a compact user count and neutral single-user action.
- Stopped deriving VRML specular and emissive colors from Blender's Principled shader.

## 0.1.0 - 2026-07-27

- Initial Blender 5.2 LTS extension release.
- Added all six VRML2 Material fields.
- Added live additive preview shader with original-shader restoration.
- Added clipboard copy and paste.
- Added presets, shared-material safeguards, and selected-object assignment.
- Added exporter-friendly flat Material custom properties.
