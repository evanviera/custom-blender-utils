"""Package entry for the Custom Utilities Blender addon.

Handles module reloading during development and delegates to submodules for
registration.
"""

import importlib

bl_info = {
    "name": "Custom Utilities",
    "author": "Evan Viera",
    "version": (0, 4, 0),
    "blender": (4, 5, 0),
    "location": "3D View > Header menus (Utilities, Collections), V (Utilities) and C (Collections) pie menus in Object Mode",
    "description": "A curated set of everyday operators for modeling and scene management.",
    "warning": "",
    "wiki_url": "",
    "category": "Interface",
}

from . import functions
from . import catalog
from . import preferences
from . import operators
from . import ui

# If any of these modules were previously imported, reload them (dependencies first)
if "bpy" in locals():
    importlib.reload(functions)
    importlib.reload(catalog)
    importlib.reload(preferences)
    importlib.reload(operators)
    importlib.reload(ui)

import bpy  # noqa: E402  (marks a reload on the next import)


def register():
    preferences.register()
    operators.register()
    ui.register()
    preferences.register_keymaps()


def unregister():
    preferences.unregister_keymaps()
    ui.unregister()
    operators.unregister()
    preferences.unregister()
