import bpy

# This class defines the dropdown menu
class UtilitiesMenu(bpy.types.Menu):
    bl_label = "Utilities"
    bl_idname = "VIEW3D_MT_custom_menu"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.measure_surface_point", text="Measure Surface Point")
        layout.operator("object.copy_transformations", text="Copy Transformations")
        layout.operator("object.paste_transformations", text="Paste Transformations")
        layout.operator("object.clear_transformations_clipboard", text="Clear Transformations")
        layout.operator("object.set_origin_to_bottom_center", text="Set Origin to Bottom")
        layout.operator("object.remove_duplicate_materials", text="Remove Duplicate Materials")

# Pie menu
class VIEW3D_MT_pie_utilities(bpy.types.Menu):
    bl_label = "Utilities Pie"
    bl_idname = "VIEW3D_MT_pie_utilities"

    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.operator("object.measure_surface_point", text="Measure Surface Point")
        pie.operator("object.copy_transformations", text="Copy Transformations")
        pie.operator("object.paste_transformations", text="Paste Transformations")
        pie.operator("object.clear_transformations_clipboard", text="Clear Transformations")
        pie.operator("object.set_origin_to_bottom_center", text="Set Origin to Bottom")
        pie.operator("object.remove_duplicate_materials", text="Remove Duplicate Materials")

# This function adds the menu to the toolbar
def draw_func(self, context):
    layout = self.layout
    layout.menu("VIEW3D_MT_custom_menu")

# Keymap for pie menu
addon_keymaps = []

# Registration
def register():
    bpy.utils.register_class(UtilitiesMenu)
    bpy.utils.register_class(VIEW3D_MT_pie_utilities)
    bpy.types.VIEW3D_MT_editor_menus.append(draw_func)

    # Register the pie menu keymap
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new("wm.call_menu_pie", type='C', value='PRESS')
    kmi.properties.name = "VIEW3D_MT_pie_utilities"
    addon_keymaps.append(km)

# Unregistration
def unregister():
    bpy.utils.unregister_class(UtilitiesMenu)
    bpy.utils.unregister_class(VIEW3D_MT_pie_utilities)
    bpy.types.VIEW3D_MT_editor_menus.remove(draw_func)
    
    # Unregister the pie menu keymap
    for km in addon_keymaps:
        bpy.context.window_manager.keyconfigs.addon.keymaps.remove(km)
    del addon_keymaps[:]
