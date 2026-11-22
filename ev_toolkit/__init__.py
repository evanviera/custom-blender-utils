"""Package entry for the EV Toolkit Blender addon.

Handles module reloading during development and delegates to submodules for
registration.
"""

import importlib

bl_info = {
    "name": "EV Toolkit",
    "author": "Evan Viera",
    "version": (0, 5, 0),
    "blender": (4, 5, 0),
    "location": "3D View > Header menus (Utilities, Collections) and pie menus: V Utilities, C Collections, D Select, G/R/S Move/Rotate/Scale",
    "description": "Everyday modeling, selection and scene-management tools with configurable pie menus.",
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
