# Custom Utilities (Blender Addon)

A curated set of everyday operators for modeling and scene management:

- Measure surface point distance from active camera
- Copy/Paste/Clear transformations (with light/camera extras)
- Set origin to bottom center of bounding box
- Remove duplicate materials (node-identical remap & cleanup)
- Move selected objects to any collection (with name filter)

## Install

This is a Blender extension (4.5+). The addon lives in `custom_blender_utils/`
with a `blender_manifest.toml`; the folder name must stay a valid Python
identifier matching the manifest `id`, or Blender skips it.

### Local repository (development)

1. Edit → Preferences → Get Extensions → Repositories (▾) → **+** → Add Local Repository.
2. Set the directory to the root of this git repo (the folder containing `custom_blender_utils/`).
3. Enable “Custom Utilities” under Add-ons. Edits to the source load on Blender restart
   or by disabling/enabling the addon.

### From zip

Drag `custom-blender-utils.zip` into Blender, or Preferences → Add-ons (▾) → Install from Disk.
Rebuild the zip after changes:

```
blender --command extension build --source-dir custom_blender_utils --output-filepath custom-blender-utils.zip
```

## Usage

- Utilities menu: 3D View → Header → Utilities
- Pie menu: press `C` in the 3D View to open “Utilities Pie”

### Move Selected to Collection
1. Select objects in the 3D View.
2. Utilities → “Move Selected to Collection”.
3. Filter collections by name, pick the target, confirm.

### Transformations Clipboard
- Copy from selected: Utilities → “Copy Transformations”.
- Paste to selected: Utilities → “Paste Transformations”.
- Clear clipboard: Utilities → “Clear Transformations”.

## Notes

- Requires Blender 4.5+.
- Operators are undoable where applicable.
