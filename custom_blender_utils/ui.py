import bpy
from bpy.props import BoolProperty
"""UI menus and keymaps for the Custom Utilities Blender addon."""

ADDON_PREFERENCES_ID = __package__ if __package__ else __name__.split(".")[0]

PIE_OPERATOR_SPECS = [
    ("pie_show_measure_surface_point", "object.measure_surface_point", "Measure Surface Point", True),
    ("pie_show_copy_transformations", "object.copy_transformations", "Copy Transformations", True),
    ("pie_show_paste_transformations", "object.paste_transformations", "Paste Transformations", True),
    ("pie_show_copy_geometry_nodes_attributes", "object.copy_geometry_nodes_modifier_attributes", "Copy Geometry Nodes Attributes", True),
    ("pie_show_paste_geometry_nodes_attributes", "object.paste_geometry_nodes_modifier_attributes", "Paste Geometry Nodes Attributes", True),
    ("pie_show_select_matching_geometry_nodes", "object.select_objects_with_matching_geometry_nodes", "Select Matching Geometry Nodes Objects", False),
    ("pie_show_export_geometry_nodes_json", "object.export_geometry_nodes_network_to_json", "Export Geometry Nodes Network (JSON)", False),
    ("pie_show_import_geometry_nodes_json", "object.import_geometry_nodes_network_from_json", "Import Geometry Nodes Network (JSON)", False),
    ("pie_show_set_origin_to_bottom_center", "object.set_origin_to_bottom_center", "Set Origin to Bottom", True),
    ("pie_show_remove_duplicate_materials", "object.remove_duplicate_materials", "Remove Duplicate Materials", True),
    ("pie_show_move_selected_to_collection", "object.move_selected_to_collection", "Move to Collection", True),
    ("pie_show_clear_transformations_clipboard", "object.clear_transformations_clipboard", "Clear Transformations", False),
    ("pie_show_reload_all_images", "image.reload_all_images", "Reload All Images", False),
    ("pie_show_copy_render_settings_to_all_scenes", "scene.copy_render_settings_to_all_scenes", "Copy Render Settings to All Scenes", False),
    ("pie_show_edit_instanced_collection", "collection.edit_instanced_collection", "Edit Collection", False),
]


def _get_addon_preferences(context: bpy.types.Context):
    preferences = getattr(context, "preferences", None)
    if preferences is None:
        return None

    addons = preferences.addons
    addon = addons.get(ADDON_PREFERENCES_ID)
    if addon is not None:
        return addon.preferences

    root_name = __name__.split(".")[0]
    addon = addons.get(root_name)
    if addon is not None:
        return addon.preferences

    return None


class CustomUtilitiesPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_PREFERENCES_ID

    pie_show_measure_surface_point: BoolProperty(name="Measure Surface Point", default=True)
    pie_show_copy_transformations: BoolProperty(name="Copy Transformations", default=True)
    pie_show_paste_transformations: BoolProperty(name="Paste Transformations", default=True)
    pie_show_copy_geometry_nodes_attributes: BoolProperty(name="Copy Geometry Nodes Attributes", default=True)
    pie_show_paste_geometry_nodes_attributes: BoolProperty(name="Paste Geometry Nodes Attributes", default=True)
    pie_show_select_matching_geometry_nodes: BoolProperty(name="Select Matching Geometry Nodes Objects", default=False)
    pie_show_export_geometry_nodes_json: BoolProperty(name="Export Geometry Nodes Network (JSON)", default=False)
    pie_show_import_geometry_nodes_json: BoolProperty(name="Import Geometry Nodes Network (JSON)", default=False)
    pie_show_set_origin_to_bottom_center: BoolProperty(name="Set Origin to Bottom", default=True)
    pie_show_remove_duplicate_materials: BoolProperty(name="Remove Duplicate Materials", default=True)
    pie_show_move_selected_to_collection: BoolProperty(name="Move to Collection", default=True)
    pie_show_clear_transformations_clipboard: BoolProperty(name="Clear Transformations", default=False)
    pie_show_reload_all_images: BoolProperty(name="Reload All Images", default=False)
    pie_show_copy_render_settings_to_all_scenes: BoolProperty(name="Copy Render Settings to All Scenes", default=False)
    pie_show_edit_instanced_collection: BoolProperty(name="Edit Collection", default=False)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Pie Menu Operators")
        for prop_name, _idname, label, _default in PIE_OPERATOR_SPECS:
            layout.prop(self, prop_name, text=label)
        layout.label(text="Only the first 8 enabled operators are shown in the pie menu.")

# This class defines the dropdown menu
class UtilitiesMenu(bpy.types.Menu):
    bl_label = "Utilities"
    bl_idname = "VIEW3D_MT_custom_menu"
    bl_description = "Custom Utilities quick actions"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.measure_surface_point", text="Measure Surface Point")
        layout.operator("object.copy_transformations", text="Copy Transformations")
        layout.operator("object.paste_transformations", text="Paste Transformations")
        layout.operator("object.clear_transformations_clipboard", text="Clear Transformations")
        layout.operator("object.copy_geometry_nodes_modifier_attributes", text="Copy Geometry Nodes Attributes")
        layout.operator("object.paste_geometry_nodes_modifier_attributes", text="Paste Geometry Nodes Attributes")
        layout.operator("object.select_objects_with_matching_geometry_nodes", text="Select Matching Geometry Nodes Objects")
        layout.operator("object.export_geometry_nodes_network_to_json", text="Export Geometry Nodes Network (JSON)")
        layout.operator("object.import_geometry_nodes_network_from_json", text="Import Geometry Nodes Network (JSON)")
        layout.operator("object.set_origin_to_bottom_center", text="Set Origin to Bottom")
        layout.operator("object.remove_duplicate_materials", text="Remove Duplicate Materials")
        layout.operator("image.reload_all_images", text="Reload All Images")
        layout.operator("scene.copy_render_settings_to_all_scenes", text="Copy Render Settings to All Scenes")
        layout.separator()
        layout.operator("object.move_selected_to_collection", text="Move Selected to Collection")

        # Edit/Close Collection toggle, label depends on whether an edit session is active
        scene = context.scene
        is_editing = bool(scene.get("custom_utils_edit_collection_name"))
        label = "Close Collection" if is_editing else "Edit Collection"
        layout.operator("collection.edit_instanced_collection", text=label)

# Pie menu
class VIEW3D_MT_pie_utilities(bpy.types.Menu):
    bl_label = "Utilities Pie"
    bl_idname = "VIEW3D_MT_pie_utilities"
    bl_description = "Custom Utilities pie menu"

    def draw(self, context):
        preferences = _get_addon_preferences(context)
        enabled_specs = []
        for prop_name, idname, label, default in PIE_OPERATOR_SPECS:
            enabled = getattr(preferences, prop_name, default) if preferences else default
            if enabled:
                enabled_specs.append((idname, label))

        pie = self.layout.menu_pie()
        for idx in range(8):
            if idx >= len(enabled_specs):
                pie.separator()
                continue

            idname, label = enabled_specs[idx]
            if idname == "collection.edit_instanced_collection":
                scene = context.scene
                is_editing = bool(scene.get("custom_utils_edit_collection_name"))
                label = "Close Collection" if is_editing else "Edit Collection"
            pie.operator(idname, text=label)

# This function adds the menu to the toolbar
def draw_func(self, context):
    layout = self.layout
    layout.menu("VIEW3D_MT_custom_menu")

# Adds the copy button to the top of the Render Properties tab
def draw_render_properties_func(self, context):
    self.layout.operator("scene.copy_render_settings_to_all_scenes", icon='SCENE_DATA')

# Keymap for pie menu
addon_keymaps = []

# Registration
def register():
    bpy.utils.register_class(CustomUtilitiesPreferences)
    bpy.utils.register_class(UtilitiesMenu)
    bpy.utils.register_class(VIEW3D_MT_pie_utilities)
    # Ensure the draw function is not appended twice
    try:
        bpy.types.VIEW3D_MT_editor_menus.remove(draw_func)
    except Exception:
        pass
    bpy.types.VIEW3D_MT_editor_menus.append(draw_func)
    try:
        bpy.types.RENDER_PT_context.remove(draw_render_properties_func)
    except Exception:
        pass
    bpy.types.RENDER_PT_context.append(draw_render_properties_func)

    # Register the pie menu keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.get('3D View')
        if km is None:
            km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        # Avoid creating duplicate keymap items
        exists = False
        for kmi in km.keymap_items:
            if (
                kmi.idname == "wm.call_menu_pie"
                and getattr(kmi.properties, "name", "") == "VIEW3D_MT_pie_utilities"
                and kmi.type == 'C'
                and kmi.value == 'PRESS'
            ):
                exists = True
                break
        if not exists:
            kmi = km.keymap_items.new("wm.call_menu_pie", type='C', value='PRESS')
            kmi.properties.name = "VIEW3D_MT_pie_utilities"
            addon_keymaps.append(km)

# Unregistration
def unregister():
    bpy.utils.unregister_class(VIEW3D_MT_pie_utilities)
    bpy.utils.unregister_class(UtilitiesMenu)
    bpy.utils.unregister_class(CustomUtilitiesPreferences)
    try:
        bpy.types.VIEW3D_MT_editor_menus.remove(draw_func)
    except Exception:
        pass
    try:
        bpy.types.RENDER_PT_context.remove(draw_render_properties_func)
    except Exception:
        pass
    
    # Unregister the pie menu keymap
    for km in addon_keymaps:
        try:
            keyconfigs = bpy.context.window_manager.keyconfigs.addon
            if keyconfigs is not None:
                keyconfigs.keymaps.remove(km)
        except Exception:
            pass
    del addon_keymaps[:]
