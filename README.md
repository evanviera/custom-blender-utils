# Custom Utilities (Blender Addon)

A curated set of everyday operators for modeling and scene management:

- Measure surface point distance from active camera
- Copy/Paste/Clear transformations (with light/camera extras)
- Set origin to bottom center of bounding box
- Remove duplicate materials (node-identical remap & cleanup)
- Collection tools (own menu and pie): edit, duplicate, decompose and merge
  collection instances, replace a collection with an instance, reset a
  collection's anchor point, and move selected objects to any collection
- Copy the current scene's Render Properties to all other scenes

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
- Utilities pie: press `V` in Object Mode to open “Utilities Pie”
- Collections menu: 3D View → Header → Collections
- Collections pie: press `C` in Object Mode to open “Collections Pie”
  (circle select stays on `C` in other modes)

### Collection Tools
All of these work on collection instances (empties instancing a collection).
Source collections are never modified; copies get their own object data
(materials stay shared).

- **Edit / Close Collection**: link and isolate the active instance's collection
  for editing; run again to close. Works on collections excluded from the view
  layer (e.g. after Replace with Instance): they are shown while editing and
  excluded again on close.
- **Duplicate Collection**: copy the active instance's collection (child
  collections, objects, data) under a new name, e.g. `ladder` → `ladder-metal`,
  and switch the selected instances of it to the copy. Other instances keep the
  original. Internal references (parenting, modifier/GN object inputs,
  constraints, drivers) point at the copies.
- **Decompose Collection**: replace the selected instances with editable copies
  of their contents at exactly the same world transforms (including instance
  offset, nested instances, and non-uniform instance scale). Parts land in the
  instance's collections and keep the instance's parent. “Nested Instances”
  (redo panel) controls whether nested collection instances are decomposed too.
- **Merge Collections**: merge the collections of 2+ selected instances into one
  new collection instanced by the active instance; the other instances are
  removed and nothing moves visually.
- **Replace with Instance**: select any object in a collection (e.g. one block of
  a wall). The collection is excluded from the view layer (unloaded, but kept in
  the outliner) and replaced by an instance in exactly the same place, created
  in the collection's parent. Redo panel: Pivot (bottom center, bounds center,
  active object, 3D cursor, or current instance offset) and Top-Level
  Collection (replace the outermost collection instead of the direct one). If
  the collection is already instanced elsewhere, its instance offset is kept so
  those instances don't move.
- **Reset Collection Anchor**: select an instance; its collection's anchor point
  (instance offset) moves to the bottom center of the collection's contents.
  Every instance of the collection in the file (any scene, nested or parented) is
  shifted to compensate, so nothing moves. Redo panel: Anchor (bottom center,
  bounds center, 3D cursor, or the collection origin). Instances with animated
  transforms or linked from a library are reported, since they can't be
  compensated.
- **Move Selected to Collection**: filter collections by name, pick the target,
  confirm.

### Transformations Clipboard
- Copy from selected: Utilities → “Copy Transformations”.
- Paste to selected: Utilities → “Paste Transformations”.
- Clear clipboard: Utilities → “Clear Transformations”.

### Copy Render Settings to All Scenes
Render Properties → button under the render engine (also in the Utilities menu).
Copies everything in the Render tab — engine, EEVEE/Cycles/Workbench settings,
light paths, film, motion blur, simplify, performance, bake, Freestyle, Grease
Pencil and color management — to every other scene. Level Link settings are not
copied. Enable “Include Output Properties” to also copy resolution, frame rate,
output path, file format and metadata.

## Notes

- Requires Blender 4.5+.
- Operators are undoable where applicable.
