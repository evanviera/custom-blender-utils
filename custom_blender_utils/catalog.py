"""The addon's actions as one catalog, shared by the pie menus, header menus and
preferences.

Every operator a pie slot can hold is listed here once, with its label, icon and
group. Pie slots are stored as enum values in the preferences, so each action has
a fixed number: never renumber or reuse one, or saved pie layouts would point at
the wrong action. Add new actions with a new, unused number.
"""

from typing import Callable, Dict, NamedTuple, Optional, Tuple

import bpy

from . import functions as fn


EDIT_COLLECTION_NAME_KEY = "custom_utils_edit_collection_name"


def _edit_collection_label(context: bpy.types.Context) -> str:
    """Edit/Close label for the edit-collection toggle, based on the active edit session."""
    scene = context.scene
    is_editing = bool(scene and scene.get(EDIT_COLLECTION_NAME_KEY))
    return "Close Collection" if is_editing else "Edit Collection"


def _stage_update_label(context: bpy.types.Context) -> str:
    return "Update Collection Stage" if fn.get_stage_scene() is not None else "Build Collection Stage"


def _stage_toggle_label(context: bpy.types.Context) -> str:
    stage = fn.get_stage_scene()
    return "Back from Stage" if stage is not None and context.scene == stage else "Go to Stage"


class Action(NamedTuple):
    key: str
    number: int  # stable enum value; see module docstring
    idname: str
    label: str
    icon: str
    group: str
    label_fn: Optional[Callable[[bpy.types.Context], str]] = None


GROUP_OBJECT = "Object"
GROUP_GEOMETRY_NODES = "Geometry Nodes"
GROUP_SCENE = "Materials & Scene"
GROUP_COLLECTIONS = "Collections"
GROUP_STAGE = "Collection Stage"

GROUPS = (GROUP_OBJECT, GROUP_GEOMETRY_NODES, GROUP_SCENE, GROUP_COLLECTIONS, GROUP_STAGE)

NONE_KEY = "NONE"

ACTIONS: Tuple[Action, ...] = (
    # Object
    Action("MEASURE", 1, "object.measure_surface_point", "Measure Surface Point", 'DRIVER_DISTANCE', GROUP_OBJECT),
    Action("COPY_TRANSFORMS", 2, "object.copy_transformations", "Copy Transformations", 'COPYDOWN', GROUP_OBJECT),
    Action("PASTE_TRANSFORMS", 3, "object.paste_transformations", "Paste Transformations", 'PASTEDOWN', GROUP_OBJECT),
    Action("CLEAR_TRANSFORMS", 4, "object.clear_transformations_clipboard", "Clear Transformations", 'TRASH', GROUP_OBJECT),
    Action("ORIGIN_BOTTOM", 5, "object.set_origin_to_bottom_center", "Set Origin to Bottom", 'OBJECT_ORIGIN', GROUP_OBJECT),
    # Geometry Nodes
    Action("GN_COPY", 10, "object.copy_geometry_nodes_modifier_attributes", "Copy Geometry Nodes Attributes", 'COPYDOWN', GROUP_GEOMETRY_NODES),
    Action("GN_PASTE", 11, "object.paste_geometry_nodes_modifier_attributes", "Paste Geometry Nodes Attributes", 'PASTEDOWN', GROUP_GEOMETRY_NODES),
    Action("GN_SELECT_MATCHING", 12, "object.select_objects_with_matching_geometry_nodes", "Select Matching Geometry Nodes Objects", 'RESTRICT_SELECT_OFF', GROUP_GEOMETRY_NODES),
    Action("GN_EXPORT", 13, "object.export_geometry_nodes_network_to_json", "Export Geometry Nodes Network (JSON)", 'EXPORT', GROUP_GEOMETRY_NODES),
    Action("GN_IMPORT", 14, "object.import_geometry_nodes_network_from_json", "Import Geometry Nodes Network (JSON)", 'IMPORT', GROUP_GEOMETRY_NODES),
    # Materials & Scene
    Action("REMOVE_DUPLICATE_MATERIALS", 20, "object.remove_duplicate_materials", "Remove Duplicate Materials", 'MATERIAL', GROUP_SCENE),
    Action("RELOAD_IMAGES", 21, "image.reload_all_images", "Reload All Images", 'IMAGE_DATA', GROUP_SCENE),
    Action("COPY_RENDER_SETTINGS", 22, "scene.copy_render_settings_to_all_scenes", "Copy Render Settings to All Scenes", 'SCENE_DATA', GROUP_SCENE),
    # Collections
    Action("EDIT_COLLECTION", 30, "collection.edit_instanced_collection", "Edit / Close Collection", 'OUTLINER_COLLECTION', GROUP_COLLECTIONS, _edit_collection_label),
    Action("DUPLICATE_COLLECTION", 31, "object.duplicate_instanced_collection", "Duplicate Collection", 'DUPLICATE', GROUP_COLLECTIONS),
    Action("DECOMPOSE_COLLECTION", 32, "object.decompose_collection_instance", "Decompose Collection", 'MOD_EXPLODE', GROUP_COLLECTIONS),
    Action("MERGE_COLLECTIONS", 33, "object.merge_collection_instances", "Merge Collections", 'AUTOMERGE_ON', GROUP_COLLECTIONS),
    Action("REPLACE_WITH_INSTANCE", 34, "object.replace_collection_with_instance", "Replace with Instance", 'OUTLINER_OB_GROUP_INSTANCE', GROUP_COLLECTIONS),
    Action("RESET_ANCHOR", 35, "object.reset_collection_anchor", "Reset Collection Anchor", 'PIVOT_BOUNDBOX', GROUP_COLLECTIONS),
    Action("APPLY_COLLECTION_TRANSFORM", 36, "object.apply_collection_transform", "Apply Collection Transform", 'CON_TRANSLIKE', GROUP_COLLECTIONS),
    Action("MOVE_TO_COLLECTION", 37, "object.move_selected_to_collection", "Move to Collection", 'FORWARD', GROUP_COLLECTIONS),
    # Collection Stage
    Action("STAGE_UPDATE", 40, "scene.update_collection_stage", "Build / Update Collection Stage", 'SCENE_DATA', GROUP_STAGE, _stage_update_label),
    Action("STAGE_SEND", 41, "object.send_collection_to_stage", "Send to Stage", 'EXPORT', GROUP_STAGE),
    Action("STAGE_TOGGLE", 42, "scene.toggle_collection_stage", "Go to / Back from Stage", 'FILE_REFRESH', GROUP_STAGE, _stage_toggle_label),
)

ACTIONS_BY_KEY: Dict[str, Action] = {action.key: action for action in ACTIONS}

assert len({a.number for a in ACTIONS}) == len(ACTIONS), "Action numbers must be unique"


def action_enum_items():
    """Enum items for a pie slot: 'Empty' plus every action, under group headings."""
    items = [(NONE_KEY, "Empty", "Leave this direction empty", 'BLANK1', 0)]
    for group in GROUPS:
        items.append(("", group, ""))
        for action in ACTIONS:
            if action.group == group:
                items.append((action.key, action.label, f"{action.label} ({action.idname})", action.icon, action.number))
    return items


def draw_action(layout: bpy.types.UILayout, context: bpy.types.Context, key: str, icon: bool = True):
    """Draw the operator button for a catalog action; returns the operator properties or None."""
    action = ACTIONS_BY_KEY.get(key)
    if action is None:
        return None
    text = action.label_fn(context) if action.label_fn else action.label
    return layout.operator(action.idname, text=text, icon=action.icon if icon else 'NONE')
