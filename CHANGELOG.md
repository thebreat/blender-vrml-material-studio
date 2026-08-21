# Changelog

## 0.2.0 - 2026-08-21

- Replaced the Blender diffuse/glossy approximation with a direct VRML97 lighting equation.
- Added Studio, Overhead, and Showroom reference-lighting rigs based on the Worldcheck material previewer.
- Made VRML preview lighting independent of Blender lights, HDRIs, metallic, Fresnel, and roughness.
- Added Blender runtime coverage for the shared VRML97 shader group.
- Made extension registration reload-safe when installing an update over an enabled copy.
- Deferred the initial material scan until Blender releases its restricted registration context.
- Added neutral `Set Default` actions for `emissiveColor` and `specularColor`.
- Reordered the editor and copied VRML fields to diffuse, emissive, specular, ambient, shininess, transparency.
- Added the VRML highlight exponent beside Shininess and clarified that visible highlights depend on surface angle.
- Expanded render regression coverage to include both smooth and faceted geometry.
- Removed the Assumed Ambient Light control and made its stable reference value part of the preview rig.
- Replaced the shared-material warning box with a compact user count and neutral single-user action.
- Stopped deriving VRML specular and emissive colors from Blender's Principled shader.

## 0.1.0 - 2026-07-27

- Initial Blender 5.2 LTS extension release.
- Added all six VRML2 Material fields.
- Added live additive preview shader with original-shader restoration.
- Added clipboard copy and paste.
- Added presets, shared-material safeguards, and selected-object assignment.
- Added exporter-friendly flat Material custom properties.
