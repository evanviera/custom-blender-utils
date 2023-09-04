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

class ClearTransformationsClipboardOperator(bpy.types.Operator):
    bl_idname = "object.clear_transformations_clipboard"
    bl_label = "Clear Transformations Clipboard"

    def execute(self, context):
        fn.clear_transformations()
        return {'FINISHED'}

class SetOriginToBottomCenterOperator(bpy.types.Operator):
    bl_idname = "object.set_origin_to_bottom_center"
    bl_label = "Set Origin to Bottom Center"

    def execute(self, context):
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                fn.set_origin_to_bottom_center(obj)
        return {'FINISHED'}

class RemoveDuplicateMaterialsOperator(bpy.types.Operator):
    bl_idname = "object.remove_duplicate_materials"
    bl_label = "Remove Duplicate Materials"

    def execute(self, context):
        def get_base_name(material_name):
            split_name = material_name.split('.')
            if len(split_name) > 1 and split_name[-1].isdigit():
                return '.'.join(split_name[:-1])
            return material_name

        def compare_materials(mat1, mat2):
            if mat1.node_tree is None or mat2.node_tree is None:
                return False  # or handle this case as per your requirements

            nodes1 = mat1.node_tree.nodes
            nodes2 = mat2.node_tree.nodes

            # Compare the number of nodes in each material
            if len(nodes1) != len(nodes2):
                return False

            # For each node, create a tuple containing its type, location, properties, and connections
            node_data1 = [(node.type, node.location, str(node.inputs), str(node.outputs)) for node in nodes1]
            node_data2 = [(node.type, node.location, str(node.inputs), str(node.outputs)) for node in nodes2]

            return sorted(node_data1) == sorted(node_data2)

        materials = bpy.data.materials
        unique_materials = {}
        removed_shaders = []  # List to store the names of removed shaders

        for mat in materials:
            base_name = get_base_name(mat.name)
            if base_name not in unique_materials:
                unique_materials[base_name] = mat
            else:
                if compare_materials(mat, unique_materials[base_name]):
                    mat.user_remap(unique_materials[base_name])
                    removed_shaders.append(mat.name)  # Add the name of the removed shader to the list
                    bpy.data.materials.remove(mat)

        # Check if any shaders were removed
        if removed_shaders:
            report_message = f"{len(removed_shaders)} duplicate shaders remapped and removed: {', '.join(removed_shaders)}"
        else:
            report_message = "No duplicate shaders were found."

        self.report({'INFO'}, report_message)
        return {'FINISHED'}


classes = [
    CopyTransformationsOperator,
    PasteTransformationsOperator,
    ClearTransformationsClipboardOperator,
    SetOriginToBottomCenterOperator,
    RemoveDuplicateMaterialsOperator,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
