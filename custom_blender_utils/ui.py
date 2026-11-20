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
    ("pie_show_clear_transformations_clipboard", "object.clear_transformations_clipboard", "Clear Transformations", False),
    ("pie_show_reload_all_images", "image.reload_all_images", "Reload All Images", False),
    ("pie_show_copy_render_settings_to_all_scenes", "scene.copy_render_settings_to_all_scenes", "Copy Render Settings to All Scenes", False),
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
    pie_show_clear_transformations_clipboard: BoolProperty(name="Clear Transformations", default=False)
    pie_show_reload_all_images: BoolProperty(name="Reload All Images", default=False)
    pie_show_copy_render_settings_to_all_scenes: BoolProperty(name="Copy Render Settings to All Scenes", default=False)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Pie Menu Operators")
        for prop_name, _idname, label, _default in PIE_OPERATOR_SPECS:
            layout.prop(self, prop_name, text=label)
        layout.label(text="Only the first 8 enabled operators are shown in the pie menu.")
        layout.separator()
        layout.label(text="Pies (Object Mode): V = Utilities, C = Collections.")

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


def _edit_collection_label(context) -> str:
    """Edit/Close label for the edit-collection toggle, based on the active edit session."""
    scene = context.scene
    is_editing = bool(scene and scene.get("custom_utils_edit_collection_name"))
    return "Close Collection" if is_editing else "Edit Collection"


class CollectionsMenu(bpy.types.Menu):
    bl_label = "Collections"
    bl_idname = "VIEW3D_MT_custom_collections_menu"
    bl_description = "Custom Utilities collection tools"

    def draw(self, context):
        layout = self.layout
        layout.operator("collection.edit_instanced_collection", text=_edit_collection_label(context), icon='OUTLINER_COLLECTION')
        layout.separator()
        layout.operator("object.duplicate_instanced_collection", text="Duplicate Collection", icon='DUPLICATE')
        layout.operator("object.decompose_collection_instance", text="Decompose Collection", icon='MOD_EXPLODE')
        layout.operator("object.merge_collection_instances", text="Merge Collections", icon='AUTOMERGE_ON')
        layout.separator()
        layout.operator("object.move_selected_to_collection", text="Move Selected to Collection", icon='FORWARD')


class VIEW3D_MT_pie_collections(bpy.types.Menu):
    bl_label = "Collections Pie"
    bl_idname = "VIEW3D_MT_pie_collections"
    bl_description = "Custom Utilities collection pie menu"

    def draw(self, context):
        pie = self.layout.menu_pie()
        # Pie order: West, East, South, North, North-West, North-East, South-West, South-East
        pie.operator("object.decompose_collection_instance", text="Decompose Collection", icon='MOD_EXPLODE')
        pie.operator("object.merge_collection_instances", text="Merge Collections", icon='AUTOMERGE_ON')
        pie.operator("object.move_selected_to_collection", text="Move to Collection", icon='FORWARD')
        pie.operator("collection.edit_instanced_collection", text=_edit_collection_label(context), icon='OUTLINER_COLLECTION')
        pie.operator("object.duplicate_instanced_collection", text="Duplicate Collection", icon='DUPLICATE')

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
            pie.operator(idname, text=label)

# This function adds the menu to the toolbar
def draw_func(self, context):
    layout = self.layout
    layout.menu("VIEW3D_MT_custom_menu")
    layout.menu("VIEW3D_MT_custom_collections_menu")

# Adds the copy button to the top of the Render Properties tab
def draw_render_properties_func(self, context):
    self.layout.operator("scene.copy_render_settings_to_all_scenes", icon='SCENE_DATA')

# Keymaps for pie menus: (keymap name, pie menu idname, key, shift, ctrl, alt)
# Both pies live in the Object Mode keymap: every operator in them is an object-mode
# tool. C replaces circle select in Object Mode only; V is unbound in Object Mode.
PIE_KEYMAPS = [
    ("Object Mode", "VIEW3D_MT_pie_collections", 'C', False, False, False),
    ("Object Mode", "VIEW3D_MT_pie_utilities", 'V', False, False, False),
]

addon_keymaps = []

classes = (
    CustomUtilitiesPreferences,
    UtilitiesMenu,
    CollectionsMenu,
    VIEW3D_MT_pie_utilities,
    VIEW3D_MT_pie_collections,
)


def _register_keymaps():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        return
    for km_name, menu_name, key, shift, ctrl, alt in PIE_KEYMAPS:
        km = kc.keymaps.get(km_name)
        if km is None:
            km = kc.keymaps.new(name=km_name, space_type='EMPTY')
        # Avoid creating duplicate keymap items
        existing = next(
            (
                kmi for kmi in km.keymap_items
                if kmi.idname == "wm.call_menu_pie"
                and getattr(kmi.properties, "name", "") == menu_name
            ),
            None,
        )
        if existing is not None:
            addon_keymaps.append((km, existing))
            continue
        kmi = km.keymap_items.new(
            "wm.call_menu_pie", type=key, value='PRESS', shift=shift, ctrl=ctrl, alt=alt
        )
        kmi.properties.name = menu_name
        addon_keymaps.append((km, kmi))


def _unregister_keymaps():
    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except (ReferenceError, RuntimeError):
            pass
    addon_keymaps.clear()


# Registration
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
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
    _register_keymaps()


# Unregistration
def unregister():
    _unregister_keymaps()
    try:
        bpy.types.VIEW3D_MT_editor_menus.remove(draw_func)
    except Exception:
        pass
    try:
        bpy.types.RENDER_PT_context.remove(draw_render_properties_func)
    except Exception:
        pass
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
