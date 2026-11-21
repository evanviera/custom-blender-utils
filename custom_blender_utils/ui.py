"""UI menus for the Custom Utilities Blender addon.

Pie layouts, hotkeys and which menus appear are configured in the addon
preferences (see preferences.py); actions come from catalog.py.
"""

import bpy

from . import catalog
from . import preferences as prefs_mod


# Header menus: action keys in order; None draws a separator.
UTILITIES_MENU = (
    "MEASURE",
    None,
    "COPY_TRANSFORMS",
    "PASTE_TRANSFORMS",
    "CLEAR_TRANSFORMS",
    None,
    "GN_COPY",
    "GN_PASTE",
    "GN_SELECT_MATCHING",
    "GN_EXPORT",
    "GN_IMPORT",
    None,
    "ORIGIN_BOTTOM",
    "REMOVE_DUPLICATE_MATERIALS",
    "RELOAD_IMAGES",
    "COPY_RENDER_SETTINGS",
)

COLLECTIONS_MENU = (
    "EDIT_COLLECTION",
    None,
    "DUPLICATE_COLLECTION",
    "DECOMPOSE_COLLECTION",
    "MERGE_COLLECTIONS",
    "REPLACE_WITH_INSTANCE",
    "RESET_ANCHOR",
    "APPLY_COLLECTION_TRANSFORM",
    None,
    "MOVE_TO_COLLECTION",
    None,
    "STAGE_UPDATE",
    "STAGE_SEND",
    "STAGE_TOGGLE",
)


def _draw_menu(layout, context, keys):
    for key in keys:
        if key is None:
            layout.separator()
        else:
            catalog.draw_action(layout, context, key)


class UtilitiesMenu(bpy.types.Menu):
    bl_label = "Utilities"
    bl_idname = "VIEW3D_MT_custom_menu"
    bl_description = "Custom Utilities quick actions"

    def draw(self, context):
        _draw_menu(self.layout, context, UTILITIES_MENU)


class CollectionsMenu(bpy.types.Menu):
    bl_label = "Collections"
    bl_idname = "VIEW3D_MT_custom_collections_menu"
    bl_description = "Custom Utilities collection tools"

    def draw(self, context):
        _draw_menu(self.layout, context, COLLECTIONS_MENU)


def _draw_pie(layout, context, pie_id):
    pie = layout.menu_pie()
    icons = prefs_mod.pie_shows_icons(context, pie_id)
    for _direction, key in prefs_mod.pie_slot_actions(context, pie_id):
        if catalog.draw_action(pie, context, key, icon=icons) is None:
            pie.separator()


class VIEW3D_MT_pie_utilities(bpy.types.Menu):
    bl_label = "Utilities Pie"
    bl_idname = "VIEW3D_MT_pie_utilities"
    bl_description = "Custom Utilities pie menu"

    def draw(self, context):
        _draw_pie(self.layout, context, "utilities")


class VIEW3D_MT_pie_collections(bpy.types.Menu):
    bl_label = "Collections Pie"
    bl_idname = "VIEW3D_MT_pie_collections"
    bl_description = "Custom Utilities collection pie menu"

    def draw(self, context):
        _draw_pie(self.layout, context, "collections")


# 3D View header menus
def draw_header_menus(self, context):
    prefs = prefs_mod.get_prefs(context)
    layout = self.layout
    if prefs is None or prefs.header_utilities_menu:
        layout.menu(UtilitiesMenu.bl_idname)
    if prefs is None or prefs.header_collections_menu:
        layout.menu(CollectionsMenu.bl_idname)


# Outliner collection right-click menu: send the clicked (active) collection to the stage
def draw_outliner_collection_func(self, context):
    if not prefs_mod.pref(context, "outliner_send_to_stage", True):
        return
    layout = self.layout
    layout.separator()
    op = layout.operator("object.send_collection_to_stage", text="Send to Stage", icon='EXPORT')
    op.use_active_collection = True


# Adds the copy button to the top of the Render Properties tab
def draw_render_properties_func(self, context):
    if not prefs_mod.pref(context, "render_copy_button", True):
        return
    self.layout.operator("scene.copy_render_settings_to_all_scenes", icon='SCENE_DATA')


classes = (
    UtilitiesMenu,
    CollectionsMenu,
    VIEW3D_MT_pie_utilities,
    VIEW3D_MT_pie_collections,
)

_MENU_APPENDS = (
    ("VIEW3D_MT_editor_menus", draw_header_menus),
    ("RENDER_PT_context", draw_render_properties_func),
    ("OUTLINER_MT_collection", draw_outliner_collection_func),
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    for type_name, func in _MENU_APPENDS:
        menu_type = getattr(bpy.types, type_name)
        try:
            menu_type.remove(func)  # never append twice
        except Exception:
            pass
        menu_type.append(func)


def unregister():
    for type_name, func in _MENU_APPENDS:
        try:
            getattr(bpy.types, type_name).remove(func)
        except Exception:
            pass
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
