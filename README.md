# VRML2 Material Studio

VRML2 Material Studio is a Blender 5.2 LTS extension for authoring the six fields in a VRML97/VRML2 `Material` node and seeing them through a live VRML97 lighting preview before export.

## Features

- Stores VRML2 material data per **Blender Material**, so shared Blender materials behave like reusable VRML appearances.
- Edits the native VRML2 fields:
  - `ambientIntensity`
  - `diffuseColor`
  - `emissiveColor`
  - `shininess`
  - `specularColor`
  - `transparency`
- Calculates the VRML97 diffuse, colored specular, emissive, and transparency terms directly instead of translating them into Blender BSDF properties.
- Uses the four-light 3DGrove Item Viewer scene used for official CTR/X_ITE checks.
- Provides one-click VRML97 default resets for `ambientIntensity`, `emissiveColor`, and `specularColor`.
- Includes 433 named materials contributed by Breetos, with searchable categories and gloss-aware preview swatches.
- Preserves the material's original node-use state, Surface shader connection, viewport color, and transparency render mode, then restores them when Live Preview is disabled or VRML2 data is removed.
- Copies a complete `Material { ... }` block to the clipboard.
- Pastes complete or partial VRML2 Material blocks from the clipboard.
- Mirrors every export field into simple Material custom properties so a separate exporter can read the values without importing this extension's Python package.
- Supports an optional `DEF Name` for future `DEF`/`USE` exporter integration.

## Installation

1. Keep `vrml2_material_studio-0.3.0.zip` compressed.
2. Open Blender 5.2 LTS.
3. Go to **Edit > Preferences > Get Extensions**.
4. Open the menu in the upper-right and choose **Install from Disk**.
5. Select the ZIP file and enable **VRML2 Material Studio** if Blender does not enable it automatically.

The installation process is the same on Windows, macOS, and Linux.

## Using the extension

The interface appears in both locations:

- **3D Viewport > Sidebar > VRML2**
- **Material Properties > VRML2 Material Studio**

### Create a new VRML2-controlled material

1. Select an object that supports material slots.
2. Open the VRML2 panel.
3. Click **Create VRML2 Material**.
4. Edit the six VRML fields.
5. Use Material Preview or Rendered viewport shading to see the VRML97 live preview.

### Add VRML2 data to an existing Blender material

1. Make the existing material active.
2. Click **Initialize Existing Material**.
3. The extension reads diffuse, transparency, and shininess starting points from a Principled BSDF. Specular and emissive colors start at their VRML97 defaults.
4. The original node-use state, Surface link, viewport color, and transparency mode are restored when Live Preview is disabled.

Initializing does not delete the original nodes. The extension adds its generated nodes alongside them and temporarily routes the Material Output Surface through the VRML2 preview.

### Shared materials

VRML2 data belongs to the Blender Material, not to the Object. When a material has multiple users, editing it changes every object using that material. Use **Make Material Single User** when one object needs different VRML2 values.

### Contributed material library

Expand **Contributed Materials** at the bottom of Material Studio to browse the 433-material Breetos collection. Search by name or select one of its 13 categories. Each row includes a shaded circular swatch inspired by the [Cybertown Mall Material Previewer](https://worldcheck.ctrmall.org/materials); the swatch incorporates diffuse, emissive, specular, shininess, and transparency values instead of acting as a flat colour chip.

Click a material name to apply all six VRML97 fields to the active material. Applying an entry does not rename the Blender material or replace its DEF name. Fifteen source entries contained an `ambientIntensity` or `shininess` above VRML97's legal range; the bundled values are clamped to 1.0 and produce a warning when applied.

## VRML2 field notes

`ambientIntensity`, `shininess`, and `transparency` are single values from 0 to 1. The three color fields are RGB triplets from 0 to 1.

These six fields are the complete VRML97 `Material` node. Texture images, animated textures, and texture transforms belong to the surrounding `Appearance` node rather than to `Material`. Per-face and per-vertex colours belong to the geometry's `Color` node and replace the material's diffuse component where used.

`ambientIntensity` is not an RGB color. VRML computes the material ambient color from:

```text
ambient color = diffuseColor × ambientIntensity
```

The `ambientIntensity`, `emissiveColor`, and `specularColor` controls each have a **Set Default** button. They restore the VRML97 values `0.2`, `0 0 0`, and `0 0 0`, respectively.

`shininess` changes only the shape of a nonblack `specularColor`. With the default black specular color there is no highlight to reshape. X_ITE follows the VRML97 equation exactly: `shininess 0` with a nonblack specular color spreads that contribution across the lit surface. Geometry matters too: a curved surface supplies many normals that can catch a highlight, while a flat face may miss a narrow highlight entirely at its current light and camera angle.

The preview reproduces the four unattenuated point lights in 3DGrove's official Item Viewer scene: two white upper lights and two dim blue lower lights. These controlled lights are evaluated by the generated VRML97 shader; Blender scene lights and HDRIs are ignored.

The official Item Viewer lights have nonzero VRML `ambientIntensity` values. The material's `ambientIntensity` therefore changes the live preview through the standard VRML97 equation instead of through an invented Blender ambient term.

For a direct on-screen comparison with the 3DGrove/X_ITE canvas, use Blender's **Standard** View Transform. The shader converts only the completed VRML lighting result into Blender's scene-linear space, so Standard displays the original VRML RGB channels without requiring Raw. The VRML material inputs and lighting equation remain untouched. AgX still applies its own contrast and gamut mapping and is not the exact reference view. The extension does not alter this scene-wide setting automatically.

VRML transparency uses the opposite direction from Blender alpha:

```text
Blender alpha = 1 - VRML transparency
```

## Clipboard workflow

Copy produces a block like this:

```vrml
DEF VRML2_Material Material {
  diffuseColor 0.8 0.8 0.8
  emissiveColor 0 0 0
  specularColor 0 0 0
  ambientIntensity 0.2
  shininess 0.2
  transparency 0
}
```

Paste accepts:

- A complete `Material { ... }` block.
- A `DEF Name Material { ... }` block.
- A larger VRML fragment containing a Material node. Omitted fields take their VRML97 defaults.
- Partial fields such as `diffuseColor 0.2 0.4 0.8`. Only fields found in the clipboard are changed.

Values outside the VRML 0–1 range are clamped and Blender reports a warning.

## Exporter integration

The extension stores flat custom properties directly on each Blender Material. These survive in the `.blend` file and are easy for another add-on to read.

| Custom property | Type | VRML meaning |
| --- | --- | --- |
| `vrml2_initialized` | Boolean | This material contains VRML2 data |
| `vrml2_enabled` | Boolean | Include the material in VRML2 export |
| `vrml2_defName` | String | Optional DEF identifier |
| `vrml2_diffuseColor` | 3-float array | `diffuseColor` |
| `vrml2_emissiveColor` | 3-float array | `emissiveColor` |
| `vrml2_specularColor` | 3-float array | `specularColor` |
| `vrml2_ambientIntensity` | Float | `ambientIntensity` |
| `vrml2_shininess` | Float | `shininess` |
| `vrml2_transparency` | Float | `transparency` |
| `vrml2_schemaVersion` | Integer | Stored-data schema version |

A standalone exporter can read them without depending on this extension:

```python
def get_vrml2_material_values(material):
    if not material.get("vrml2_initialized", False):
        return None
    if not material.get("vrml2_enabled", True):
        return None

    return {
        "def_name": material.get("vrml2_defName", ""),
        "diffuseColor": tuple(material.get("vrml2_diffuseColor", (0.8, 0.8, 0.8))),
        "emissiveColor": tuple(material.get("vrml2_emissiveColor", (0.0, 0.0, 0.0))),
        "specularColor": tuple(material.get("vrml2_specularColor", (0.0, 0.0, 0.0))),
        "ambientIntensity": float(material.get("vrml2_ambientIntensity", 0.2)),
        "shininess": float(material.get("vrml2_shininess", 0.2)),
        "transparency": float(material.get("vrml2_transparency", 0.0)),
    }
```

When this extension is enabled, the same information is also available through Blender RNA:

```python
settings = material.vrml2_material
print(settings.diffuse_color)
print(settings.ambient_intensity)
```

The flat custom properties are the recommended integration point because they keep the exporter independent.

## Preview behavior and limitations

The generated shader evaluates the VRML97 lighting terms directly, including the `shininess × 128` specular exponent. It does not use Blender roughness, metallic, Fresnel, or scene lighting. Its default reference rig is based on the official 3DGrove Item Viewer; the far-away point lights are represented by their normalized surface-to-light directions so the rig remains stable while the Blender viewport orbits an item.

A Material node does not have one appearance independent of its scene: the final result still depends on light direction, light colour and intensity, ambient contribution, geometry normals, camera angle, transparency sorting, and display colour management. Historical VRML browsers can also differ from one another in those details.

Use the preview to tune materials interactively, then validate important assets in the final target browser. The preview controls do not alter the six exported values.

## Removal and restoration

- Turning off **Live Preview** restores the original node-use state, viewport color, transparency mode, and Surface shader when one existed.
- **Remove VRML2 Data** restores the original shader, deletes generated preview nodes, and removes the flat VRML2 custom properties.
- For a material created entirely by this extension, removing VRML2 data creates a basic Principled fallback so the material does not become blank.

## Version

### 0.3.0

Added the collapsible Breetos contributed-material library with 433 searchable, categorized materials and site-inspired preview swatches.

### 0.2.0

Replaced the Blender-BSDF approximation with a direct VRML97 live-preview shader and controlled reference-lighting rigs.

### 0.1.0

Initial Blender 5.2 LTS release.
