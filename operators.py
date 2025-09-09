import bpy
import json
from mathutils import Vector
from bpy_extras.io_utils import axis_conversion
from bpy.props import StringProperty, EnumProperty

from . import functions as fn

class DistanceMeasureOperator(bpy.types.Operator):
    bl_idname = "object.measure_surface_point"
    bl_label = "Distance Measurement Modal Operator"

    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            fn.handle_mouse_click(context, event, self)
            return {'FINISHED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

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


class MoveSelectedToCollectionOperator(bpy.types.Operator):
    bl_idname = "object.move_selected_to_collection"
    bl_label = "Move Selected to Collection"
    bl_options = {"REGISTER", "UNDO"}

    filter_text: StringProperty(
        name="Filter",
        description="Filter collections by name",
        default="",
        options={"TEXTEDIT_UPDATE"},
    )

    def _collection_items(self, context):
        items = []
        filter_lower = (self.filter_text or "").lower()
        for col in bpy.data.collections:
            name = col.name
            if filter_lower and filter_lower not in name.lower():
                continue
            items.append((name, name, ""))
        if not items:
            # Provide a disabled placeholder so the enum shows something
            items.append(("", "<no matches>", ""))
        return items

    target_collection: EnumProperty(
        name="Collection",
        description="Target collection to move selected objects to",
        items=_collection_items,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "filter_text")
        layout.prop(self, "target_collection")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=380)

    def execute(self, context):
        if not self.target_collection:
            self.report({'WARNING'}, "No collection selected")
            return {'CANCELLED'}

        target = bpy.data.collections.get(self.target_collection)
        if target is None:
            self.report({'ERROR'}, "Collection not found")
            return {'CANCELLED'}

        selected_objects = list(context.selected_objects)
        if not selected_objects:
            self.report({'WARNING'}, "No selected objects to move")
            return {'CANCELLED'}

        moved_count = 0
        for obj in selected_objects:
            # Link first to ensure the object always remains in at least one collection
            if target not in obj.users_collection:
                try:
                    target.objects.link(obj)
                except RuntimeError:
                    pass

            # Unlink from all other collections
            for col in list(obj.users_collection):
                if col != target:
                    try:
                        col.objects.unlink(obj)
                    except RuntimeError:
                        pass
            moved_count += 1

        self.report({'INFO'}, f"Moved {moved_count} object(s) to '{target.name}'")
        return {'FINISHED'}

classes = [
    DistanceMeasureOperator,
    CopyTransformationsOperator,
    PasteTransformationsOperator,
    ClearTransformationsClipboardOperator,
    SetOriginToBottomCenterOperator,
    RemoveDuplicateMaterialsOperator,
    MoveSelectedToCollectionOperator,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
