import bpy

# This class defines a simple operator
class SimpleOperator(bpy.types.Operator):
    bl_idname = "object.simple_operator"
    bl_label = "Simple Operator"

    def execute(self, context):
        print("Hello from Simple Operator!")
        return {'FINISHED'}

# This class defines the dropdown menu
class SimpleMenu(bpy.types.Menu):
    bl_label = "Utilities"
    bl_idname = "VIEW3D_MT_custom_menu"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.simple_operator", text="Say Hello")
        layout.operator("object.copy_transformations", text="Copy Transformations")
        layout.operator("object.paste_transformations", text="Paste Transformations")

# This function adds the menu to the toolbar
def draw_func(self, context):
    layout = self.layout
    layout.menu("VIEW3D_MT_custom_menu")

# Registration
def register():
    bpy.utils.register_class(SimpleOperator)
    bpy.utils.register_class(SimpleMenu)
    bpy.types.VIEW3D_MT_editor_menus.append(draw_func)

# Unregistration
def unregister():
    bpy.utils.unregister_class(SimpleOperator)
    bpy.utils.unregister_class(SimpleMenu)
    bpy.types.VIEW3D_MT_editor_menus.remove(draw_func)