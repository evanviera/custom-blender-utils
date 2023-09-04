import bpy
import json
from mathutils import Vector
from bpy_extras.io_utils import axis_conversion

from . import functions as fn

class CopyTransformationsOperator(bpy.types.Operator):
    bl_idname = "object.copy_transformations"
    bl_label = "Copy Transformations"

    def execute(self, context):
        for obj in bpy.context.selected_objects:
            fn.copy_transformations(obj)
        return {'FINISHED'}

class PasteTransformationsOperator(bpy.types.Operator):
    bl_idname = "object.paste_transformations"
    bl_label = "Paste Transformations"

    def execute(self, context):
        for obj in bpy.context.selected_objects:
            fn.paste_transformations(obj)
        return {'FINISHED'}
    

classes = [
    CopyTransformationsOperator,
    PasteTransformationsOperator,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
