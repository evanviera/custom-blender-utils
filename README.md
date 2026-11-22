# EV Toolkit (Blender Addon)

Everyday modeling, selection and scene-management tools, with configurable pie menus
(formerly “Custom Utilities”; it also replaces the older “Custom Pie Menus” / ev_pies addon):

- Measure surface point distance from active camera
- Copy/Paste/Clear transformations (with light/camera extras)
- Set origin to bottom center of bounding box
- Remove duplicate materials (node-identical remap & cleanup)
- Collection tools (own menu and pie): edit, duplicate, decompose and merge
  collection instances, replace a collection with an instance, reset a
  collection's anchor point, apply an instance's rotation/scale to its
  collection, and move selected objects to any collection
- Collection Stage: a dedicated scene with every asset collection laid out in its
  own spot for editing, without moving any instance in any scene or file
- Copy the current scene's Render Properties to all other scenes
- Pie menus for axis-constrained Move / Rotate / Scale (G / R / S) and for
  selection (D: select linked in Object Mode, edge loops/rings in Edit Mode)

## Install

This is a Blender extension (4.5+). The addon lives in `ev_toolkit/`
with a `blender_manifest.toml`; the folder name must stay a valid Python
identifier matching the manifest `id`, or Blender skips it.

### Local repository (development)

1. Edit → Preferences → Get Extensions → Repositories (▾) → **+** → Add Local Repository.
2. Set the directory to the root of this git repo (the folder containing `ev_toolkit/`).
3. Enable “EV Toolkit” under Add-ons. Edits to the source load on Blender restart
   or by disabling/enabling the addon.

### From zip

Drag `ev-toolkit.zip` into Blender, or Preferences → Add-ons (▾) → Install from Disk.
Rebuild the zip after changes:

```
blender --command extension build --source-dir ev_toolkit --output-filepath ev-toolkit.zip
```

## Usage

- Utilities menu: 3D View → Header → Utilities
- Utilities pie: press `V` in Object Mode to open “Utilities Pie” (layout and hotkeys: see Preferences)
- Collections menu: 3D View → Header → Collections
- Collections pie: press `C` in Object Mode to open “Collections Pie”
  (circle select stays on `C` in other modes)
- Move / Rotate / Scale pies: `G` / `R` / `S` in Object Mode and mesh Edit Mode
- Select Linked pie: `D` in Object Mode; Select Loops pie: `D` in mesh Edit Mode

### Moving from Custom Utilities / ev_pies
- The extension id changed (`custom_blender_utils` → `ev_toolkit`), so Blender sees
  a new addon: disable the old “Custom Utilities” entry if it still shows, enable
  “EV Toolkit”, and set your pie layouts and tool defaults again.
- Disable or remove the old “Custom Pie Menus” (ev_pies) addon. Its pies are all
  here, and it also replaced Blender's own Select Active Camera operator.

### Preferences
Edit → Preferences → Add-ons → EV Toolkit. Four tabs:

- **Pie Menus**: every pie, grouped by the modes its hotkey works in. Each row
  shows the pie's hotkey and an on/off switch per mode (e.g. turn the G/R/S
  pies off to get Blender's plain transform keys back); expand it for the
  layout, a 3×3 grid matching the pie. Pick any addon action (or Empty) for
  each of the eight directions; the same action can go in several pies. Per
  pie: hotkey (key, modifiers, on/off, restore, using Blender's keymap editor,
  so changes save with your keymap), Icons on/off, Reset (default layout) and
  Clear. A collapsible box shows Blender's own pie
  settings (radius, thresholds, timeouts); those affect every pie in Blender.
- **Interface**: show or hide the Utilities and Collections header menus, the
  Copy Render Settings button in Render Properties, and Send to Stage in the
  Outliner's collection menu.
- **Tools**: the options tools start with: Measure (decimal places, copy to
  clipboard), Geometry Nodes (paste excludes active, import attaches to active,
  export folder), Copy Render Settings (include output).
- **Collections**: the options collection tools start with (Decompose nested
  instances, Replace with Instance pivot and top-level, Reset Anchor anchor) and
  the Collection Stage: scene name, Update/Send options, and the layout a new
  stage starts with (each stage then keeps its own layout).

Tool options set here are where each run starts; the redo panel still changes
them for that run. (Before 0.4.0 these options remembered the last run instead.)

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
- **Apply Collection Transform**: select a rotated and/or scaled instance; its
  rotation and scale are applied to the collection itself, about the
  collection's anchor, so the instance ends up with no rotation and a scale of
  1. Every instance of the collection (and of its child collections) in the
  file is counter-rotated/scaled, so none of them moves in any scene. Redo
  panel: Rotation, Scale. It refuses (and says why) rather than move
  something: objects shared with or parented to objects outside the
  collection, animated or constrained top-level objects, or an instance whose
  scale differs non-uniformly from the selected one while rotated
  differently (it would need shear; parented instances absorb it in their
  parent inverse). Objects needing shear get it baked into their own data
  when it isn't shared. Only collection-instance empties are compensated:
  Geometry Nodes Collection Info, particles, and other files linking the
  collection are not.
- **Move Selected to Collection**: filter collections by name, pick the target,
  confirm.

### Collection Stage
A scene (“Collection Stage”) where every asset collection sits in its own spot,
side by side on the ground, with a name label in front. Go there to tweak
collections in place; every instance of them updates.

How collections are placed: a collection's objects are shared by every scene
that uses it, so a collection is put in its spot by moving its contents **and**
its instance offset by the same amount. Instances draw relative to the instance
offset, so instances in every scene, and in other files that link the
collection, do not move.

- **Build / Update Collection Stage** (Collections menu): creates the stage on
  first run, then adds every asset collection not on it yet (collections that
  are instanced anywhere or marked as assets). Collections already on the stage
  stay where they are; new ones are added in rows below. Dialog options:
  - Relayout All: repack every collection (e.g. after edits made them overlap;
    overlaps are reported).
  - Instance Direct Uses: where a collection is shown directly (not instanced)
    in another scene, it is replaced there by an instance in the same place, as
    with Replace with Instance, so it doesn't move. Off: such collections are
    skipped.
  - Layout: spacing, grid snap (collections only move by whole grid steps, so
    modular parts stay grid-aligned), row width, order (name or size), labels.
    These are saved with the stage and used by Send to Stage.
- **Send to Stage** (Collections menu and pie, Outliner collection right-click):
  puts the selection's collections (the collection of a selected instance, or
  the collection holding a selected object) in a free spot. Run it on a
  collection you just built: it moves to the stage and is replaced by an
  instance where you built it. Collections already on the stage are moved to a
  free spot. Redo panel: Top-Level Collection, Anchor (instance offset for
  collections nothing instances yet; instanced ones always keep theirs), Open
  Stage.
- **Go to Stage / Back from Stage**: switch between the stage and the scene you
  came from.

Collections nested in a stage collection ride along with it. A collection is
skipped (and reported) when its contents can't be moved as one block: an object
also in a collection outside it, an object parented to one outside it, an
animated location on a top-level object, a child collection shown on its own
in another scene, or a library-linked collection. Edit Collection on an instance
now shows the collection at its stage spot.

### Select & Transform Pies
- **Move / Rotate / Scale** (`G` / `R` / `S`, Object Mode and mesh Edit Mode):
  X, Y and Z constrain to that axis; the top slot transforms freely. These
  replace Blender's G/R/S keys while their hotkeys are on.
- **Select Linked** (`D`, Object Mode): Material, Object Data, Children
  (recursive), Same Type, Same Color, Active Camera, Same Light Type and
  Instanced Collection. Options that don't apply to the active object (no
  materials, not a light, not a collection instance) are hidden, keeping
  their slot.
- **Select Loops** (`D`, mesh Edit Mode): Edge Loops and Edge Rings from the
  selected edges, Select Less, Select More.

All of these are ordinary actions too: put any of them in any pie slot.

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
