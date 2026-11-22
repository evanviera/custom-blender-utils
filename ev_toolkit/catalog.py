"""The addon's actions as one catalog, shared by the pie menus, header menus and
preferences.

Every operator a pie slot can hold is listed here once, with its label, icon and
group. Pie slots are stored as enum values in the preferences, so each action has
a fixed number: never renumber or reuse one, or saved pie layouts would point at
the wrong action. Add new actions with a new, unused number.
"""

from typing import Any, Callable, Dict, NamedTuple, Optional, Tuple

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


def _active_object(context: bpy.types.Context):
    return getattr(context, "active_object", None)


def _has_materials(context: bpy.types.Context) -> bool:
    obj = _active_object(context)
    return bool(obj and obj.material_slots)


def _has_data(context: bpy.types.Context) -> bool:
    obj = _active_object(context)
    return bool(obj and obj.data is not None)


def _is_light(context: bpy.types.Context) -> bool:
    obj = _active_object(context)
    return bool(obj and obj.type == 'LIGHT')


def _is_collection_instance(context: bpy.types.Context) -> bool:
    obj = _active_object(context)
    return bool(obj and obj.instance_type == 'COLLECTION' and obj.instance_collection)


class Action(NamedTuple):
    key: str
    number: int  # stable enum value; see module docstring
    idname: str
    label: str  # name in menus and the preferences
    icon: str
    group: str
    label_fn: Optional[Callable[[bpy.types.Context], str]] = None  # dynamic button text
    text: Optional[str] = None  # shorter button text, when the pie gives the context (e.g. "X")
    props: Tuple[Tuple[str, Any], ...] = ()  # operator options the button sets
    show_fn: Optional[Callable[[bpy.types.Context], bool]] = None  # hide (keep the slot) when False


GROUP_OBJECT = "Object"
GROUP_GEOMETRY_NODES = "Geometry Nodes"
GROUP_SCENE = "Materials & Scene"
GROUP_COLLECTIONS = "Collections"
GROUP_STAGE = "Collection Stage"
GROUP_TRANSFORM = "Transform"
GROUP_SELECT_OBJECT = "Select (Object Mode)"
GROUP_SELECT_MESH = "Select (Edit Mesh)"

GROUPS = (
    GROUP_OBJECT, GROUP_GEOMETRY_NODES, GROUP_SCENE, GROUP_COLLECTIONS, GROUP_STAGE,
    GROUP_TRANSFORM, GROUP_SELECT_OBJECT, GROUP_SELECT_MESH,
)

_AXES = (("X", (True, False, False)), ("Y", (False, True, False)), ("Z", (False, False, True)))


def _transform_actions(prefix: str, number: int, idname: str, label: str, free_icon: str):
    """Free and X/Y/Z-constrained versions of a transform operator."""
    actions = []
    for offset, (axis, constraint) in enumerate(_AXES):
        actions.append(Action(
            f"{prefix}_{axis}", number + offset, idname, f"{label} {axis}", f"EVENT_{axis}", GROUP_TRANSFORM,
            text=axis, props=(("constraint_axis", constraint),),
        ))
    actions.append(Action(prefix, number + 3, idname, label, free_icon, GROUP_TRANSFORM))
    return tuple(actions)


# Blender 5 split mesh.loop_multi_select(ring=...) into separate loop and ring operators.
if "select_edge_loop_multi" in dir(bpy.ops.mesh):
    _EDGE_LOOPS = ("mesh.select_edge_loop_multi", ())
    _EDGE_RINGS = ("mesh.select_edge_ring_multi", ())
else:
    _EDGE_LOOPS = ("mesh.loop_multi_select", (("ring", False),))
    _EDGE_RINGS = ("mesh.loop_multi_select", (("ring", True),))

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
    # Transform (axis-constrained move / rotate / scale)
    *_transform_actions("MOVE", 50, "transform.translate", "Move", 'VIEW_PAN'),
    *_transform_actions("ROTATE", 55, "transform.rotate", "Rotate", 'DRIVER_ROTATIONAL_DIFFERENCE'),
    *_transform_actions("SCALE", 60, "transform.resize", "Scale", 'FULLSCREEN_ENTER'),
    # Select (Object Mode): shown only when they apply to the active object
    Action("SELECT_LINKED_MATERIAL", 70, "object.select_linked", "Select Linked Material", 'MATERIAL', GROUP_SELECT_OBJECT,
           text="Material", props=(("type", 'MATERIAL'),), show_fn=_has_materials),
    Action("SELECT_LINKED_DATA", 71, "object.select_linked", "Select Linked Object Data", 'MESH_DATA', GROUP_SELECT_OBJECT,
           text="Object Data", props=(("type", 'OBDATA'),), show_fn=_has_data),
    Action("SELECT_CHILDREN", 72, "object.select_grouped", "Select Children", 'CON_CHILDOF', GROUP_SELECT_OBJECT,
           text="Children", props=(("type", 'CHILDREN_RECURSIVE'),)),
    Action("SELECT_SAME_TYPE", 73, "object.select_grouped", "Select Same Type", 'OBJECT_DATAMODE', GROUP_SELECT_OBJECT,
           text="Type", props=(("type", 'TYPE'),)),
    Action("SELECT_SAME_COLOR", 74, "object.select_grouped", "Select Same Color", 'COLOR', GROUP_SELECT_OBJECT,
           text="Color", props=(("type", 'COLOR'),)),
    Action("SELECT_ACTIVE_CAMERA", 75, "object.select_camera", "Select Active Camera", 'CAMERA_DATA', GROUP_SELECT_OBJECT),
    Action("SELECT_SAME_LIGHT_TYPE", 76, "object.select_grouped", "Select Same Light Type", 'LIGHT', GROUP_SELECT_OBJECT,
           text="Light Type", props=(("type", 'LIGHT_TYPE'),), show_fn=_is_light),
    Action("SELECT_LINKED_INSTANCE", 77, "object.select_linked", "Select Linked Instanced Collection", 'OUTLINER_OB_GROUP_INSTANCE', GROUP_SELECT_OBJECT,
           text="Instanced Collection", props=(("type", 'DUPGROUP'),), show_fn=_is_collection_instance),
    # Select (Edit Mesh)
    Action("SELECT_EDGE_LOOPS", 80, _EDGE_LOOPS[0], "Select Edge Loops", 'EDGESEL', GROUP_SELECT_MESH,
           text="Edge Loops", props=_EDGE_LOOPS[1]),
    Action("SELECT_EDGE_RINGS", 81, _EDGE_RINGS[0], "Select Edge Rings", 'MOD_EDGESPLIT', GROUP_SELECT_MESH,
           text="Edge Rings", props=_EDGE_RINGS[1]),
    Action("SELECT_LESS", 82, "mesh.select_less", "Select Less", 'SELECT_SUBTRACT', GROUP_SELECT_MESH),
    Action("SELECT_MORE", 83, "mesh.select_more", "Select More", 'SELECT_EXTEND', GROUP_SELECT_MESH),
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
    """Draw the operator button for a catalog action.

    Returns the operator properties, or None when nothing was drawn (unknown key, or an
    action that doesn't apply right now); pies then draw a separator to keep the slot.
    """
    action = ACTIONS_BY_KEY.get(key)
    if action is None or (action.show_fn is not None and not action.show_fn(context)):
        return None
    if action.label_fn is not None:
        text = action.label_fn(context)
    else:
        text = action.text or action.label
    op = layout.operator(action.idname, text=text, icon=action.icon if icon else 'NONE')
    for name, value in action.props:
        setattr(op, name, value)
    return op
