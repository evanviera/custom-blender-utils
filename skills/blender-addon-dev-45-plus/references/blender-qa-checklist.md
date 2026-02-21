# Blender 4.5+ QA Checklist

## Pre-merge Checks

- Confirm `bl_info["blender"] >= (4, 5, 0)`.
- Confirm every new operator has clear `bl_idname`, label, and description.
- Confirm scene-editing operators use `UNDO`.
- Confirm register/unregister is symmetrical for:
  - classes
  - properties on Blender types
  - keymaps
  - handlers/timers
- Confirm no direct dependency on removed/deprecated API symbols.

## Runtime Checks in Blender

- Enable add-on successfully from Preferences.
- Run each operator from intended entry points (menu, panel, hotkey).
- Verify poll failures produce clean UI behavior (disabled button or user report).
- Verify undo/redo for data-editing operators.
- Verify keymaps do not duplicate after reloads.
- Verify disabled add-on unregisters without traceback.

## Geometry Nodes-Specific Checks

- Verify behavior when target object has no GN modifiers.
- Verify behavior with multiple GN modifiers on one object.
- Verify behavior when copied node group is missing.
- Verify pasted values only affect selected scope.

## Release Checks

- Increment `bl_info["version"]` when behavior changes.
- Keep operator names and identifiers stable unless a breaking change is intentional.
- Provide short upgrade notes when renaming operators or properties.
