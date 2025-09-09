# Custom Utilities (Blender Addon)

A curated set of everyday operators for modeling and scene management:

- Measure surface point distance from active camera
- Copy/Paste/Clear transformations (with light/camera extras)
- Set origin to bottom center of bounding box
- Remove duplicate materials (node-identical remap & cleanup)
- Move selected objects to any collection (with name filter)

## Install

1. Download or zip the `Custom-Utilities` folder.
2. In Blender: Edit → Preferences → Add-ons → Install…
3. Select the zip/folder, enable “Custom Utilities”.

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

- Designed for Blender 2.80+.
- Operators are undoable where applicable.
