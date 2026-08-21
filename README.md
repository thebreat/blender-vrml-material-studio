# VRML2 Material Studio

VRML2 Material Studio is a Blender 5.2 LTS extension for authoring the six fields in a VRML97/VRML2 `Material` node and seeing a live approximation in Blender before export.

## Features

- Stores VRML2 material data per **Blender Material**, so shared Blender materials behave like reusable VRML appearances.
- Edits the native VRML2 fields:
  - `ambientIntensity`
  - `diffuseColor`
  - `emissiveColor`
  - `shininess`
  - `specularColor`
  - `transparency`
- Creates an additive Blender preview shader with separate diffuse, colored specular, ambient/emissive, and transparency components.
- Preserves the material's original node-use state, Surface shader connection, viewport color, and transparency render mode, then restores them when Live Preview is disabled or VRML2 data is removed.
- Copies a complete `Material { ... }` block to the clipboard.
- Pastes complete or partial VRML2 Material blocks from the clipboard.
- Includes starting presets for default VRML, matte, glossy plastic, polished metal, clear glass, and emissive materials.
- Mirrors every export field into simple Material custom properties so a separate exporter can read the values without importing this extension's Python package.
- Supports an optional `DEF Name` for future `DEF`/`USE` exporter integration.

## Installation

1. Keep `vrml2_material_studio-0.1.0.zip` compressed.
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
5. Use Material Preview or Rendered viewport shading to see the generated preview shader.

### Add VRML2 data to an existing Blender material

1. Make the existing material active.
2. Click **Initialize Existing Material**.
3. The extension reads a best-effort starting point from a Principled BSDF.
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

The preview also includes an **Assumed Ambient Light** value. This is preview-only and is not exported. It represents the ambient-light contribution of the eventual VRML scene, which is not known from a Material node alone.

VRML transparency uses the opposite direction from Blender alpha:

```text
Blender alpha = 1 - VRML transparency
```

## Clipboard workflow

Copy produces a block like this:

```vrml
DEF VRML2_Material Material {
  ambientIntensity 0.2
  diffuseColor 0.8 0.8 0.8
  emissiveColor 0 0 0
  shininess 0.2
  specularColor 0 0 0
  transparency 0
}
```

Paste accepts:

- A complete `Material { ... }` block.
- A `DEF Name Material { ... }` block.
- A larger VRML fragment containing a Material node.
- Partial fields such as `diffuseColor 0.2 0.4 0.8`. Only fields found in the clipboard are changed.

Values outside the VRML 0–1 range are clamped and Blender reports a warning.

## Exporter integration

The extension stores flat custom properties directly on each Blender Material. These survive in the `.blend` file and are easy for another add-on to read.

| Custom property | Type | VRML meaning |
| --- | --- | --- |
| `vrml2_initialized` | Boolean | This material contains VRML2 data |
| `vrml2_enabled` | Boolean | Include the material in VRML2 export |
| `vrml2_defName` | String | Optional DEF identifier |
| `vrml2_ambientIntensity` | Float | `ambientIntensity` |
| `vrml2_diffuseColor` | 3-float array | `diffuseColor` |
| `vrml2_emissiveColor` | 3-float array | `emissiveColor` |
| `vrml2_shininess` | Float | `shininess` |
| `vrml2_specularColor` | 3-float array | `specularColor` |
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
        "ambientIntensity": float(material.get("vrml2_ambientIntensity", 0.2)),
        "diffuseColor": tuple(material.get("vrml2_diffuseColor", (0.8, 0.8, 0.8))),
        "emissiveColor": tuple(material.get("vrml2_emissiveColor", (0.0, 0.0, 0.0))),
        "shininess": float(material.get("vrml2_shininess", 0.2)),
        "specularColor": tuple(material.get("vrml2_specularColor", (0.0, 0.0, 0.0))),
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

## Preview limitations

The preview is intentionally an approximation. VRML97 uses a fixed-function lighting equation, while Blender uses modern shader nodes, color management, environment lighting, and different render engines. The appearance can also vary between VRML browsers because their lights, ambient contribution, transparency sorting, and historical rendering implementations differ.

Use the preview to tune materials interactively, then validate important assets in the final target browser. The preview controls do not alter the six exported values.

## Removal and restoration

- Turning off **Live Preview** restores the original node-use state, viewport color, transparency mode, and Surface shader when one existed.
- **Remove VRML2 Data** restores the original shader, deletes generated preview nodes, and removes the flat VRML2 custom properties.
- For a material created entirely by this extension, removing VRML2 data creates a basic Principled fallback so the material does not become blank.

## Version

### 0.1.0

Initial Blender 5.2 LTS release.
