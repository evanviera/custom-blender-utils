import importlib
"""Package entry for the Custom Utilities Blender addon.

Handles module reloading during development and delegates to submodules for
registration.
"""

bl_info = {
    "name": "Custom Utilities",
    "author": "Evan Viera",
    "version": (0, 1, 11),
    "blender": (4, 5, 0),
    "location": "3D View > Header menu (Utilities) and C pie menu",
    "description": "A curated set of everyday operators for modeling and scene management.",
    "warning": "",
    "wiki_url": "",
    "category": "Interface",
}

# Import package
from . import ui
from . import operators
from . import functions

# If any of these modules were previously imported, reload them
if "bpy" in locals():
    importlib.reload(ui)
    importlib.reload(operators)
    importlib.reload(functions)

def register():
    operators.register()
    ui.register()

def unregister():
    ui.unregister()
    operators.unregister()
