import bpy

# This class defines the dropdown menu
class UtilitiesMenu(bpy.types.Menu):
    bl_label = "Utilities"
    bl_idname = "VIEW3D_MT_custom_menu"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.copy_transformations", text="Copy Transformations")
        layout.operator("object.paste_transformations", text="Paste Transformations")
        layout.operator("object.set_origin_to_bottom_center", text="Set Origin to Bottom")
        layout.operator("object.remove_duplicate_materials", text="Remove Duplicate Materials")

# This function adds the menu to the toolbar
def draw_func(self, context):
    layout = self.layout
    layout.menu("VIEW3D_MT_custom_menu")

# Registration
def register():
    bpy.utils.register_class(UtilitiesMenu)
    bpy.types.VIEW3D_MT_editor_menus.append(draw_func)

# Unregistration
def unregister():
    bpy.utils.unregister_class(UtilitiesMenu)
    bpy.types.VIEW3D_MT_editor_menus.remove(draw_func)