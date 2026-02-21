# Blender 4.5+ API Patterns

## Operator Template

```python
class MYADDON_OT_example(bpy.types.Operator):
    bl_idname = "myaddon.example"
    bl_label = "Example Action"
    bl_description = "Run example action"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.active_object
        if obj is None:
            self.report({"WARNING"}, "No active object")
            return {"CANCELLED"}
        # mutate data
        self.report({"INFO"}, f"Updated {obj.name}")
        return {"FINISHED"}
```

## PropertyGroup + Collection UIList

- Define persistent add-on state in `bpy.types.PropertyGroup`.
- Store transient UI lists on `WindowManager` for dialogs.
- Register property pointer/collection after class registration, delete on unregister.

## Context Override

```python
with context.temp_override(area=area, region=region):
    bpy.ops.view3d.view_selected("INVOKE_DEFAULT")
```

- Use `temp_override` for operator calls requiring specific area/region context.
- Avoid old override dictionary patterns.

## Registration Pattern

```python
CLASSES = (
    MyPrefs,
    MYADDON_OT_example,
    MYADDON_MT_menu,
)

def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
```

## Add-on Metadata Baseline

```python
bl_info = {
    "name": "My Addon",
    "author": "Your Name",
    "version": (0, 1, 0),
    "blender": (4, 5, 0),
    "location": "View3D",
    "description": "Tools for ...",
    "category": "Object",
}
```

## Reporting and Failure Semantics

- Use `{"CANCELLED"}` when preconditions fail.
- Use `{"FINISHED"}` only after applying intended changes.
- Use `self.report({"INFO"|"WARNING"|"ERROR"}, "...")` for user-visible outcomes.

## Safe Data Updates

- Preserve selection and active object when practical.
- Avoid hidden mode switches; if required, restore prior mode.
- Minimize global state; prefer add-on properties and explicit data flow.
