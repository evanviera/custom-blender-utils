import bpy
"""Operators for the Custom Utilities Blender addon.

This module defines all operator classes exposed by the addon. Operators here
focus on discrete actions such as measuring, copying/pasting transformations,
cleaning materials, changing origins, and moving objects between collections.
"""

from bpy.props import StringProperty, EnumProperty

from . import functions as fn

class DistanceMeasureOperator(bpy.types.Operator):
    bl_idname = "object.measure_surface_point"
    bl_label = "Distance Measurement Modal Operator"
    bl_description = "Click in the 3D View to measure distance from active camera to the surface point"

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
    bl_description = "Copy location, rotation, and scale (plus type-specific data) to an internal clipboard"

    def execute(self, context):
        for obj in bpy.context.selected_objects:
            fn.copy_transformations(obj)
        return {'FINISHED'}

class PasteTransformationsOperator(bpy.types.Operator):
    bl_idname = "object.paste_transformations"
    bl_label = "Paste Transformations"
    bl_description = "Paste transformations from the internal clipboard to selected objects"

    def execute(self, context):
        for obj in bpy.context.selected_objects:
            fn.paste_transformations(obj)
        return {'FINISHED'}

class ClearTransformationsClipboardOperator(bpy.types.Operator):
    bl_idname = "object.clear_transformations_clipboard"
    bl_label = "Clear Transformations Clipboard"
    bl_description = "Clear the internal transformations clipboard"

    def execute(self, context):
        fn.clear_transformations()
        return {'FINISHED'}

class SetOriginToBottomCenterOperator(bpy.types.Operator):
    bl_idname = "object.set_origin_to_bottom_center"
    bl_label = "Set Origin to Bottom Center"
    bl_description = "Set the object's origin to the center of its bounding box bottom"

    def execute(self, context):
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                fn.set_origin_to_bottom_center(obj)
        return {'FINISHED'}

class RemoveDuplicateMaterialsOperator(bpy.types.Operator):
    bl_idname = "object.remove_duplicate_materials"
    bl_label = "Remove Duplicate Materials"
    bl_description = "Remove materials that are node-identical duplicates, remapping users to the original"

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
    bl_description = "Move selected objects to a chosen collection with optional name filter"

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

class ReloadAllImagesOperator(bpy.types.Operator):
    bl_idname = "image.reload_all_images"
    bl_label = "Reload All Images"
    bl_description = "Reload all image files in the opened Blender file"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        reloaded_count = 0
        skipped_count = 0
        
        for image in bpy.data.images:
            # Only reload images that have a filepath (skip generated/packed images)
            if image.filepath:
                try:
                    image.reload()
                    reloaded_count += 1
                except Exception as e:
                    skipped_count += 1
                    print(f"Failed to reload image '{image.name}': {e}")
        
        if reloaded_count > 0:
            self.report({'INFO'}, f"Reloaded {reloaded_count} image(s)" + (f", skipped {skipped_count}" if skipped_count > 0 else ""))
        else:
            self.report({'WARNING'}, "No images with filepaths found to reload")
        
        return {'FINISHED'}

class LinkInstancedCollectionOperator(bpy.types.Operator):
    bl_idname = "collection.link_instanced_collection"
    bl_label = "Link Instanced Collection to Scene"
    bl_description = (
        "Link the collection from the selected instanced collection object to the "
        "current scene, isolate it in the active 3D View, and frame it on screen"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # Get the active (selected) object
        if not context.selected_objects:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object selected")
            return {'CANCELLED'}

        # Check if the object is a collection instance
        # In Blender, collection instances can be:
        # 1. EMPTY objects with instance_type='COLLECTION' and instance_collection set
        # 2. COLLECTION type objects (in newer Blender versions)
        collection = None
        
        if obj.type == 'EMPTY' and obj.instance_type == 'COLLECTION' and obj.instance_collection:
            collection = obj.instance_collection
        elif hasattr(obj, 'instance_collection') and obj.instance_collection:
            collection = obj.instance_collection
        else:
            self.report({'WARNING'}, f"Selected object '{obj.name}' is not an instanced collection")
            return {'CANCELLED'}

        if not collection:
            self.report({'ERROR'}, "Could not find collection from instance")
            return {'CANCELLED'}

        # Ensure the collection is linked to the scene's master collection
        scene_collection = context.scene.collection
        linked_now = False

        # Check if collection is already a child of the scene collection
        if collection.name in scene_collection.children:
            # Double-check that it's the same collection object
            if scene_collection.children[collection.name] == collection:
                # Already linked to the scene root
                pass
            else:
                # A collection with the same name exists, but it's not the same object.
                # Still try to link; Blender will prevent duplicate parentage as needed.
                try:
                    scene_collection.children.link(collection)
                    linked_now = True
                except RuntimeError as e:
                    error_msg = str(e)
                    if "already linked" not in error_msg.lower() and "already in" not in error_msg.lower():
                        self.report({'ERROR'}, f"Failed to link collection: {error_msg}")
                        return {'CANCELLED'}
        else:
            # Not present as a child; link it
            try:
                scene_collection.children.link(collection)
                linked_now = True
            except RuntimeError as e:
                error_msg = str(e)
                if "already linked" not in error_msg.lower() and "already in" not in error_msg.lower():
                    self.report({'ERROR'}, f"Failed to link collection: {error_msg}")
                    return {'CANCELLED'}

        # At this point, the collection is guaranteed to be part of the scene.
        # Next: isolate and frame this collection in the active 3D View.

        # Collect all objects in the collection, including nested child collections
        objs_in_collection = set()

        def _gather_objects(coll: bpy.types.Collection):
            for o in coll.objects:
                objs_in_collection.add(o)
            for child_coll in coll.children:
                _gather_objects(child_coll)

        _gather_objects(collection)

        if not objs_in_collection:
            msg = (
                f"Collection '{collection.name}' linked to scene but has no objects to display"
                if linked_now
                else f"Collection '{collection.name}' is in the scene but has no objects to display"
            )
            self.report({'INFO'}, msg)
            return {'FINISHED'}

        # Ensure we're in Object mode so view operators work reliably
        if context.mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except Exception:
                pass

        # Deselect everything and select all objects in the collection
        for obj_sel in list(context.selected_objects):
            obj_sel.select_set(False)

        for o in objs_in_collection:
            o.select_set(True)

        # Set an active object from the collection
        active_obj = next(iter(objs_in_collection))
        context.view_layer.objects.active = active_obj

        # Isolate and frame in the active 3D View (if we are in one)
        if getattr(context, "area", None) and context.area.type == 'VIEW_3D':
            try:
                # Local view will both isolate selection in this view and can frame it
                bpy.ops.view3d.localview(frame_selected=True)
            except Exception:
                # Fallback: at least frame the selected objects
                try:
                    bpy.ops.view3d.view_selected()
                except Exception:
                    pass

        if linked_now:
            self.report(
                {'INFO'},
                f"Linked and isolated collection '{collection.name}' in the active view",
            )
        else:
            self.report(
                {'INFO'},
                f"Isolated collection '{collection.name}' in the active view",
            )

        return {'FINISHED'}

classes = [
    DistanceMeasureOperator,
    CopyTransformationsOperator,
    PasteTransformationsOperator,
    ClearTransformationsClipboardOperator,
    SetOriginToBottomCenterOperator,
    RemoveDuplicateMaterialsOperator,
    MoveSelectedToCollectionOperator,
    ReloadAllImagesOperator,
    LinkInstancedCollectionOperator,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
