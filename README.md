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
- Calculates the VRML97 diffuse, colored specular, ambient, emissive, and transparency terms directly instead of translating them into Blender BSDF properties.
- Includes Studio, Overhead, and Showroom VRML reference-lighting rigs that ignore Blender lights and HDRIs.
- Provides one-click VRML97 default resets for `emissiveColor` and `specularColor`.
- Preserves the material's original node-use state, Surface shader connection, viewport color, and transparency render mode, then restores them when Live Preview is disabled or VRML2 data is removed.
- Copies a complete `Material { ... }` block to the clipboard.
- Pastes complete or partial VRML2 Material blocks from the clipboard.
- Includes starting presets for default VRML, matte, glossy plastic, polished metal, clear glass, and emissive materials.
- Mirrors every export field into simple Material custom properties so a separate exporter can read the values without importing this extension's Python package.
- Supports an optional `DEF Name` for future `DEF`/`USE` exporter integration.

## Installation

1. Keep `vrml2_material_studio-0.2.0.zip` compressed.
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

## VRML2 field notes

`ambientIntensity`, `shininess`, and `transparency` are single values from 0 to 1. The three color fields are RGB triplets from 0 to 1.

`ambientIntensity` is not an RGB color. VRML computes the material ambient color from:

```text
ambient color = diffuseColor × ambientIntensity
```

The `emissiveColor` and `specularColor` controls each have a **Set Default** button that restores the VRML97 value `0 0 0`.

`shininess` changes only the shape of a nonblack `specularColor`. With the default black specular color there is no highlight to reshape. X_ITE follows the VRML97 equation exactly: `shininess 0` with a nonblack specular color spreads that contribution across the lit surface. The editor shows the corresponding VRML highlight exponent (`shininess × 128`) because the upper end of the slider is intentionally subtle. Geometry matters too: a curved surface supplies many normals that can catch a highlight, while a flat face may miss a narrow highlight entirely at its current light and camera angle.

The preview includes a **VRML Preview Lighting** selector with Studio, Overhead, and Showroom reference rigs. These controlled lights are evaluated by the generated VRML97 shader; Blender scene lights and HDRIs are ignored.

The reference rigs include a fixed ambient-light contribution so `ambientIntensity` remains visible and comparable without adding a preview-only ambient control to the material editor.

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

The generated shader evaluates the VRML97 lighting terms directly, including the `shininess × 128` specular exponent. It does not use Blender roughness, metallic, Fresnel, or scene lighting. The reference rigs are based on the Worldcheck material previewer so highlights remain consistent while materials are edited.

A Material node does not have one appearance independent of its scene: the final result still depends on light direction, light colour and intensity, ambient contribution, geometry normals, camera angle, transparency sorting, and display colour management. Historical VRML browsers can also differ from one another in those details.

Use the preview to tune materials interactively, then validate important assets in the final target browser. The preview controls do not alter the six exported values.

## Removal and restoration

- Turning off **Live Preview** restores the original node-use state, viewport color, transparency mode, and Surface shader when one existed.
- **Remove VRML2 Data** restores the original shader, deletes generated preview nodes, and removes the flat VRML2 custom properties.
- For a material created entirely by this extension, removing VRML2 data creates a basic Principled fallback so the material does not become blank.

## Version

### 0.2.0

Replaced the Blender-BSDF approximation with a direct VRML97 live-preview shader and controlled reference-lighting rigs.

### 0.1.0

Initial Blender 5.2 LTS release.
