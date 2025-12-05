import bpy
"""Operators for the Custom Utilities Blender addon.

This module defines all operator classes exposed by the addon. Operators here
focus on discrete actions such as measuring, copying/pasting transformations,
cleaning materials, changing origins, and moving objects between collections.
"""

from bpy.props import StringProperty, EnumProperty, IntProperty

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

EDIT_COLLECTION_NAME_KEY = "custom_utils_edit_collection_name"
EDIT_COLLECTION_LINKED_KEY = "custom_utils_edit_collection_linked_by_operator"
EDIT_COLLECTION_AREA_POINTER_KEY = "custom_utils_edit_collection_area_ptr"
EDIT_COLLECTION_REGION_POINTER_KEY = "custom_utils_edit_collection_region_ptr"


class CUSTOMUTILS_UL_collection_picker(bpy.types.UIList):
    """UI list to display collections with icons."""

    bl_idname = "CUSTOMUTILS_UL_collection_picker"

    def draw_item(
        self,
        context,
        layout,
        data,
        item,
        icon,
        active_data,
        active_propname,
        index=0,
        flt_flag=0,
    ):
        if item is None:
            return
        layout.label(text=item.name, icon='OUTLINER_COLLECTION')


class EditInstancedCollectionOperator(bpy.types.Operator):
    bl_idname = "collection.edit_instanced_collection"
    bl_label = "Edit Collection"
    bl_description = (
        "Toggle editing of an instanced collection: link and isolate it in the active "
        "3D View, or close editing (optionally unlinking it) when run again"
    )
    bl_options = {"REGISTER", "UNDO"}

    def _update_collection_name(self, context):
        name = (self.collection_name or "").strip()
        collections = bpy.data.collections
        if not collections:
            return
        if name:
            coll = collections.get(name)
            if coll is not None:
                idx = list(collections).index(coll)
                if idx != self.collection_index:
                    self.collection_index = idx

    def _update_collection_index(self, context):
        collections = bpy.data.collections
        if not collections:
            return
        idx = self.collection_index
        if idx < 0 or idx >= len(collections):
            return
        name = collections[idx].name
        if name != self.collection_name:
            self.collection_name = name

    collection_name: StringProperty(
        name="Collection",
        description="Collection to edit when none is selected",
        default="",
        update=_update_collection_name,
    )
    collection_index: IntProperty(
        name="Collection Index",
        default=0,
        min=0,
        update=_update_collection_index,
    )

    @staticmethod
    def _get_context_collection(context: bpy.types.Context):
        """Return the active collection from the current context, if any."""
        coll = getattr(context, "collection", None)
        if coll is not None:
            return coll
        view_layer = getattr(context, "view_layer", None)
        if view_layer is not None:
            layer_coll = getattr(view_layer, "active_layer_collection", None)
            if layer_coll is not None:
                return layer_coll.collection
        return None

    def _assign_collection(self, collection: bpy.types.Collection):
        """Sync operator properties to a specific collection."""
        if collection is None:
            return
        self.collection_name = collection.name

    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, "collection_name", bpy.data, "collections", text="Collection")
        layout.template_list(
            "CUSTOMUTILS_UL_collection_picker",
            "",
            bpy.data,
            "collections",
            self,
            "collection_index",
            rows=8,
        )

    def invoke(self, context, event):
        scene = context.scene
        obj = context.active_object
        target_collection = self._get_instanced_collection(obj)
        if target_collection:
            # No need to show a dialog; proceed immediately
            self._assign_collection(target_collection)
            return self.execute(context)

        current_name = scene.get(EDIT_COLLECTION_NAME_KEY)
        if current_name:
            coll = bpy.data.collections.get(current_name)
            self._assign_collection(coll)
            return self.execute(context)

        context_collection = self._get_context_collection(context)
        if context_collection is not None:
            self._assign_collection(context_collection)
            return self.execute(context)

        if bpy.data.collections:
            self.collection_name = bpy.data.collections[0].name
        else:
            self.report({'WARNING'}, "No collections exist in this file")
            return {'CANCELLED'}

        return context.window_manager.invoke_props_dialog(self, width=360)

    @staticmethod
    def _get_instanced_collection(obj: bpy.types.Object):
        """Return the collection instanced by the object, or None."""
        if obj is None:
            return None
        if obj.type == 'EMPTY' and getattr(obj, "instance_type", None) == 'COLLECTION' and obj.instance_collection:
            return obj.instance_collection
        if hasattr(obj, "instance_collection") and obj.instance_collection:
            return obj.instance_collection
        return None

    @staticmethod
    def _gather_objects_from_collection(collection: bpy.types.Collection):
        """Recursively gather all objects from the collection and its children."""
        objs = set()

        def _gather(coll: bpy.types.Collection):
            for o in coll.objects:
                objs.add(o)
            for child in coll.children:
                _gather(child)

        _gather(collection)
        return objs

    @staticmethod
    def _iter_view3d_regions(
        context: bpy.types.Context,
        area_id=None,
        region_id=None,
    ):
        """Yield (area, region) pairs for VIEW_3D WINDOW regions, optionally filtered."""
        screen = getattr(context, "screen", None)
        if screen is None:
            return

        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            if area_id is not None and str(area.as_pointer()) != area_id:
                continue

            window_regions = [reg for reg in area.regions if reg.type == "WINDOW"]
            if region_id is not None:
                window_regions.sort(key=lambda reg: str(reg.as_pointer()) != region_id)

            for region in window_regions:
                yield area, region

            if area_id is not None:
                break

    @staticmethod
    def _find_view3d_space(area: bpy.types.Area):
        """Return the first VIEW_3D space for an area, or None."""
        if not hasattr(area, "spaces"):
            return None
        for space in area.spaces:
            if space.type == "VIEW_3D":
                return space
        return None

    @staticmethod
    def _toggle_local_view_for_region(
        context: bpy.types.Context,
        area: bpy.types.Area,
        region: bpy.types.Region,
    ) -> bool:
        """Toggle local view for the provided area/region if currently active."""
        space = EditInstancedCollectionOperator._find_view3d_space(area)
        if space is None:
            return False

        rv3d = getattr(region, "data", None)
        if rv3d is None:
            rv3d = getattr(space, "region_3d", None)

        # In Blender 4.x the space tracks whether local view is active
        if getattr(space, "local_view", None) is None:
            return False

        try:
            if hasattr(context, "temp_override"):
                override_kwargs = {
                    "area": area,
                    "region": region,
                    "space_data": space,
                }
                window = getattr(context, "window", None)
                screen = getattr(context, "screen", None)
                if window is not None:
                    override_kwargs["window"] = window
                if screen is not None:
                    override_kwargs["screen"] = screen
                if rv3d is not None:
                    override_kwargs["region_data"] = rv3d
                with context.temp_override(**override_kwargs):
                    result = bpy.ops.view3d.localview(frame_selected=False)
            else:
                override = context.copy()
                override["area"] = area
                override["region"] = region
                override["space_data"] = space
                if rv3d is not None:
                    override["region_data"] = rv3d
                window = getattr(context, "window", None)
                screen = getattr(context, "screen", None)
                if window is not None:
                    override["window"] = window
                if screen is not None:
                    override["screen"] = screen
                result = bpy.ops.view3d.localview(override, frame_selected=False)
        except Exception:
            return False

        if not isinstance(result, set) or 'FINISHED' not in result:
            return False

        # Ensure local view has been cleared
        return getattr(space, "local_view", None) is None

    @staticmethod
    def _exit_local_view_if_active(
        context: bpy.types.Context,
        preferred_area_id=None,
        preferred_region_id=None,
    ):
        """Exit local view, prioritizing the VIEW_3D area/region we entered with."""
        # Attempt to toggle using the stored area/region from the active session
        if preferred_area_id is not None or preferred_region_id is not None:
            for area, region in EditInstancedCollectionOperator._iter_view3d_regions(
                context, preferred_area_id, preferred_region_id
            ):
                if EditInstancedCollectionOperator._toggle_local_view_for_region(context, area, region):
                    return

        # Try the current context (e.g., the viewport where the operator was invoked)
        area = getattr(context, "area", None)
        region = getattr(context, "region", None)
        if (
            area is not None
            and area.type == "VIEW_3D"
            and region is not None
            and region.type == "WINDOW"
        ):
            if EditInstancedCollectionOperator._toggle_local_view_for_region(context, area, region):
                return

        # Fallback: scan all VIEW_3D window regions and exit the first local view found
        for area, region in EditInstancedCollectionOperator._iter_view3d_regions(context):
            if EditInstancedCollectionOperator._toggle_local_view_for_region(context, area, region):
                return

    @staticmethod
    def _start_edit_collection(
        context: bpy.types.Context, collection: bpy.types.Collection
    ):
        """Prepare the scene and view for editing this collection.

        Returns a tuple: (linked_now, area_id, region_id).
        """
        scene = context.scene
        scene_collection = scene.collection
        linked_now = False
        area_id = None
        region_id = None

        # Ensure the collection is linked to the scene's master collection
        if collection.name in scene_collection.children:
            if scene_collection.children[collection.name] != collection:
                # Name collision with a different collection; still try to link.
                try:
                    scene_collection.children.link(collection)
                    linked_now = True
                except RuntimeError as e:
                    error_msg = str(e)
                    if "already linked" not in error_msg.lower() and "already in" not in error_msg.lower():
                        raise
        else:
            try:
                scene_collection.children.link(collection)
                linked_now = True
            except RuntimeError as e:
                error_msg = str(e)
                if "already linked" not in error_msg.lower() and "already in" not in error_msg.lower():
                    raise

        # Collect all objects in the collection, including nested child collections
        objs_in_collection = EditInstancedCollectionOperator._gather_objects_from_collection(
            collection
        )

        if not objs_in_collection:
            return linked_now, area_id, region_id

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
        area = getattr(context, "area", None)
        region = getattr(context, "region", None)
        if area is not None and area.type == 'VIEW_3D':
            area_id = str(area.as_pointer())
            if region is not None and region.type == 'WINDOW':
                region_id = str(region.as_pointer())

        if area and area.type == 'VIEW_3D':
            try:
                bpy.ops.view3d.localview(frame_selected=True)
            except Exception:
                # Fallback: at least frame the selected objects
                try:
                    bpy.ops.view3d.view_selected()
                except Exception:
                    pass

        return linked_now, area_id, region_id

    @staticmethod
    def _close_edit_collection(
        context: bpy.types.Context,
        collection: bpy.types.Collection,
        linked_by_operator: bool,
        preferred_area_id=None,
        preferred_region_id=None,
    ) -> None:
        """Close editing for the given collection: exit local view and optionally unlink."""
        scene = context.scene
        scene_collection = scene.collection

        # Exit local view for the active 3D View, but only if it's currently active
        EditInstancedCollectionOperator._exit_local_view_if_active(
            context, preferred_area_id, preferred_region_id
        )

        # Only unlink if this operator originally linked the collection
        if linked_by_operator and collection.name in scene_collection.children:
            try:
                if scene_collection.children[collection.name] == collection:
                    scene_collection.children.unlink(collection)
            except RuntimeError:
                # If unlink fails (e.g., already unlinked), just ignore
                pass

    def execute(self, context):
        scene = context.scene

        # Current selection / target collection (for a potential new edit session)
        obj = context.active_object
        override_name = (self.collection_name or "").strip()
        override_collection = (
            bpy.data.collections.get(override_name) if override_name else None
        )
        instanced_collection = self._get_instanced_collection(obj)
        target_collection = instanced_collection
        if target_collection is None and override_collection is not None:
            target_collection = override_collection
        if target_collection is None:
            context_collection = self._get_context_collection(context)
            if context_collection is not None:
                target_collection = context_collection
        if target_collection is not None:
            self._assign_collection(target_collection)

        # Read current edit-session state from the scene
        current_name = scene.get(EDIT_COLLECTION_NAME_KEY)
        linked_flag = bool(scene.get(EDIT_COLLECTION_LINKED_KEY))
        current_collection = (
            bpy.data.collections.get(current_name) if current_name else None
        )
        stored_area_id = scene.get(EDIT_COLLECTION_AREA_POINTER_KEY)
        stored_region_id = scene.get(EDIT_COLLECTION_REGION_POINTER_KEY)

        # Determine whether we're closing the same collection we would otherwise edit
        closing_same = (
            current_collection is not None
            and target_collection is not None
            and current_collection == target_collection
        )

        # If there's an active edit collection, close it first
        if current_collection is not None:
            self._close_edit_collection(
                context,
                current_collection,
                linked_flag,
                stored_area_id or None,
                stored_region_id or None,
            )
            # Clear state
            for key in (
                EDIT_COLLECTION_NAME_KEY,
                EDIT_COLLECTION_LINKED_KEY,
                EDIT_COLLECTION_AREA_POINTER_KEY,
                EDIT_COLLECTION_REGION_POINTER_KEY,
            ):
                if key in scene:
                    del scene[key]

        # If we just closed the same collection, we're done (pure "Close Collection")
        if closing_same:
            self.report({'INFO'}, f"Closed editing for collection '{current_collection.name}'")
            return {'FINISHED'}

        # If there's no collection to start editing, stop here
        if target_collection is None:
            self.report(
                {'WARNING'},
                "No instanced collection found on the active object to start editing",
            )
            return {'CANCELLED'}

        # Start editing the new target collection
        try:
            linked_now, new_area_id, new_region_id = self._start_edit_collection(
                context, target_collection
            )
        except RuntimeError as e:
            self.report({'ERROR'}, f"Failed to prepare collection for editing: {e}")
            return {'CANCELLED'}

        # Persist edit-session state on the scene
        scene[EDIT_COLLECTION_NAME_KEY] = target_collection.name
        scene[EDIT_COLLECTION_LINKED_KEY] = bool(linked_now)
        if new_area_id:
            scene[EDIT_COLLECTION_AREA_POINTER_KEY] = new_area_id
        else:
            scene.pop(EDIT_COLLECTION_AREA_POINTER_KEY, None)
        if new_region_id:
            scene[EDIT_COLLECTION_REGION_POINTER_KEY] = new_region_id
        else:
            scene.pop(EDIT_COLLECTION_REGION_POINTER_KEY, None)

        if linked_now:
            self.report(
                {'INFO'},
                f"Editing collection '{target_collection.name}' "
                f"(linked to scene and isolated in active view)",
            )
        else:
            self.report(
                {'INFO'},
                f"Editing collection '{target_collection.name}' "
                f"(already in scene, isolated in active view)",
            )

        return {'FINISHED'}

classes = [
    CUSTOMUTILS_UL_collection_picker,
    DistanceMeasureOperator,
    CopyTransformationsOperator,
    PasteTransformationsOperator,
    ClearTransformationsClipboardOperator,
    SetOriginToBottomCenterOperator,
    RemoveDuplicateMaterialsOperator,
    MoveSelectedToCollectionOperator,
    ReloadAllImagesOperator,
    EditInstancedCollectionOperator,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
