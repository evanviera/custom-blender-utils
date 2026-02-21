---
name: blender-addon-dev-45-plus
description: Expert workflow for building, refactoring, and debugging Blender add-ons in Python for Blender 4.5 and newer only. Use when tasks involve bpy API usage, operators, panels/menus, property groups, registration, keymaps, geometry nodes integration, context handling, or add-on packaging for Blender 4.5+.
---

# Blender Add-on Engineering (4.5+)

Develop only for Blender 4.5 and later.

## Enforce Version Scope

- Treat Blender 4.5+ as a hard requirement.
- Set `bl_info["blender"]` to at least `(4, 5, 0)` for new or updated add-ons.
- Avoid compatibility branches for Blender 2.8x/3.x/4.0-4.4 unless explicitly requested.
- Prefer current Blender API patterns over deprecated legacy patterns.

## Execute a Change

1. Inspect package layout and registration flow in `__init__.py`, operator modules, and UI modules.
2. Implement the requested behavior with explicit `poll` and clean context assumptions.
3. Keep data edits undo-safe with `bl_options = {"UNDO"}` when an operator changes scene data.
4. Use `self.report(...)` with actionable messages for cancellation and partial success.
5. Register/unregister classes in deterministic order and remove keymaps on unregister.
6. Run local static checks that do not require launching Blender when possible.
7. Return concise manual verification steps for Blender 4.5+ UI/runtime validation.

## Python and bpy Standards

- Use type annotations where they improve readability.
- Keep operators focused on one task.
- Put reusable logic in helper functions/modules, not in UI draw methods.
- Use `context.window_manager.invoke_props_dialog(...)` for confirmable multi-option actions.
- Use `context.temp_override(...)` instead of legacy override dict behavior.
- Prefer `context.selected_objects` and `context.active_object` over `bpy.context` inside operators.

## UI and UX Rules

- Keep labels and descriptions specific and action-oriented.
- Expose destructive or broad operations with confirmations.
- Keep menus predictable; avoid dynamic ordering unless user-configured.
- In preferences and panel UI, make default-safe behavior obvious.

## Geometry Nodes and Modifier Workflows

- Match modifiers by stable identifiers (name + node group identity) when possible.
- Preserve user-authored values unless the user explicitly asks to overwrite all fields.
- Report counts of matched, skipped, and updated objects.
- Fail gracefully when node groups or expected sockets are missing.

## Registration and Keymap Safety

- Maintain a single class registry tuple/list and iterate it for register/unregister.
- Guard duplicate keymap creation.
- Remove addon keymaps and handlers during unregister even after partial failures.

## Load References Only When Needed

- Read `references/blender-api-patterns.md` for concrete API patterns and snippets.
- Read `references/blender-qa-checklist.md` for pre-merge and release validation.
