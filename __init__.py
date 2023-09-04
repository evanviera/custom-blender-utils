import importlib

bl_info = {
    "name": "Custom Utilities -- Packaged",
    "author": "Evan Viera",
    "version": (0, 0, 11),
    "blender": (2, 80, 0),
    "location": "Properties > World",
    "description": "Custom Utilities.",    
    "warning": "",
    "wiki_url": "",
    "category": "Interface",
}

# Import package
from . import ui
from . import operators

# If any of these modules were previously imported, reload them
if "bpy" in locals():
    importlib.reload(ui)
    importlib.reload(operators)

def register():
    operators.register()
    ui.register()

def unregister():
    ui.unregister()
    operators.unregister()