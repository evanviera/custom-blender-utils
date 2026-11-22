import bpy
"""Utility functions for the EV Toolkit Blender addon.

This module encapsulates shared functionality used by operators, such as
measuring distances, handling mouse clicks/raycast, transformation clipboard
operations, and origin adjustments.
"""

import json
import math
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from mathutils import Matrix, Vector, Color, Euler, Quaternion
from bpy_extras import view3d_utils

def measure_distance_from_camera_to_location(location: Vector) -> Optional[float]:
    """Return the distance from the active camera to a world-space location.

    Returns None if there is no active camera.
    """
    cam = bpy.context.scene.camera
    if not cam:
        print("No active camera")
        return None
    
    cam_loc = cam.matrix_world.to_translation()
    return (cam_loc - location).length

def handle_mouse_click(
    context: bpy.types.Context,
    event: bpy.types.Event,
    operator: bpy.types.Operator,
    precision: int = 2,
    copy_to_clipboard: bool = True,
) -> None:
    """Handle a 3D view click by raycasting and reporting camera-to-hit distance."""
    x, y = event.mouse_region_x, event.mouse_region_y
    region = context.region
    rv3d = context.space_data.region_3d if context.space_data.type == 'VIEW_3D' else None

    if not rv3d:
        print("Not in 3D view context")
        return

    coord = x, y
    view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    view_loc = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
    depsgraph = context.evaluated_depsgraph_get()
    result, location, _, _, _, _ = context.scene.ray_cast(depsgraph, view_loc, view_vector)

    if result:
        distance = measure_distance_from_camera_to_location(location)
        if distance:
            text = f"{distance:.{precision}f}"
            print(f"Distance: {text}")
            operator.report({'INFO'}, f"Distance: {text}" + (" (copied)" if copy_to_clipboard else ""))
            if copy_to_clipboard:
                context.window_manager.clipboard = text
    else:
        print("No surface point clicked")

transformations_clipboard = {}
geometry_nodes_modifiers_clipboard: Dict[str, Any] = {}

def clear_transformations() -> None:
    """Clear the internal transformations clipboard."""
    global transformations_clipboard
    transformations_clipboard = {}


def clear_geometry_nodes_modifiers() -> None:
    """Clear the internal Geometry Nodes modifier clipboard."""
    global geometry_nodes_modifiers_clipboard
    geometry_nodes_modifiers_clipboard = {}


def has_geometry_nodes_modifiers_data() -> bool:
    """Return True when Geometry Nodes modifier data exists in the clipboard."""
    return bool(geometry_nodes_modifiers_clipboard.get('by_group'))


def get_geometry_nodes_clipboard_network_items() -> List[Tuple[str, str, str]]:
    """Return enum items for stored Geometry Nodes modifier entries."""
    items: List[Tuple[str, str, str]] = []
    entries = geometry_nodes_modifiers_clipboard.get('entries', [])
    for entry in entries:
        entry_id = entry.get('entry_id')
        if not entry_id:
            continue
        group_identity = entry.get('group_identity', {})
        group_name = group_identity.get('name', '<Unknown Group>')
        modifier_name = entry.get('modifier_name', '<Unnamed Modifier>')
        stack_index = entry.get('stack_index', -1)
        label = f"{group_name} ({modifier_name})"
        description = f"Source stack index {stack_index}"
        items.append((entry_id, label, description))
    return items


def get_geometry_nodes_clipboard_parameter_items() -> List[Tuple[str, str, str]]:
    """Return enum items for all stored modifier settings and GN exposed inputs."""
    items, _lookup = _build_geometry_nodes_parameter_catalog()
    return items


def get_geometry_nodes_clipboard_parameter_lookup() -> Dict[str, Tuple[str, str]]:
    """Return enum identifier lookup to (kind, key) tuples."""
    _items, lookup = _build_geometry_nodes_parameter_catalog()
    return lookup


def get_geometry_nodes_clipboard_entry_parameter_items() -> Dict[str, List[Dict[str, str]]]:
    """Return parameter metadata grouped by copied Geometry Nodes modifier entry id."""
    by_entry: Dict[str, List[Dict[str, str]]] = {}
    entries = geometry_nodes_modifiers_clipboard.get('entries', [])
    for entry in entries:
        entry_id = entry.get('entry_id')
        if not entry_id:
            continue

        param_items: List[Dict[str, str]] = []
        for key in entry.get('settings', {}).keys():
            param_items.append(
                {
                    'kind': 'setting',
                    'key': key,
                    'label': key.replace('_', ' ').title(),
                }
            )

        input_labels = entry.get('input_labels', {})
        for key in entry.get('inputs', {}).keys():
            param_items.append(
                {
                    'kind': 'input',
                    'key': key,
                    'label': input_labels.get(key, key),
                }
            )

        by_entry[entry_id] = param_items
    return by_entry


def _build_geometry_nodes_parameter_catalog() -> Tuple[List[Tuple[str, str, str]], Dict[str, Tuple[str, str]]]:
    catalog_by_selector: Dict[Tuple[str, str], str] = {}
    items: List[Tuple[str, str, str]] = []
    lookup: Dict[str, Tuple[str, str]] = {}
    entries = geometry_nodes_modifiers_clipboard.get('entries', [])
    for entry in entries:
        for key in entry.get('settings', {}).keys():
            selector = ('setting', key)
            if selector not in catalog_by_selector:
                param_id = f"param_{len(items)}"
                catalog_by_selector[selector] = param_id
                display_name = key.replace("_", " ").title()
                item = (
                    param_id,
                    display_name,
                    f"Modifier setting '{key}'",
                )
                items.append(item)
                lookup[param_id] = selector
        input_labels = entry.get('input_labels', {})
        for key in entry.get('inputs', {}).keys():
            selector = ('input', key)
            if selector not in catalog_by_selector:
                param_id = f"param_{len(items)}"
                catalog_by_selector[selector] = param_id
                display_name = input_labels.get(key, key)
                item = (
                    param_id,
                    display_name,
                    f"Geometry Nodes input '{display_name}' ({key})",
                )
                items.append(item)
                lookup[param_id] = selector
    return items, lookup

def copy_transformations(obj: bpy.types.Object) -> None:
    """Copy basic transforms (and type-specific data) from an object to the clipboard."""
    global transformations_clipboard
    transformations = {
        'location': tuple(obj.location),
        'rotation': tuple(obj.rotation_euler),
        'scale': tuple(obj.scale)
    }
    if obj.type == 'LIGHT':
        transformations['light_intensity'] = obj.data.energy
        transformations['light_color'] = tuple(obj.data.color)
    elif obj.type == 'CAMERA':
        transformations['focal_length'] = obj.data.lens
        transformations['dof'] = {
            'use_dof': obj.data.dof.use_dof,
            'focus_distance': obj.data.dof.focus_distance,
            'aperture_fstop': obj.data.dof.aperture_fstop,
        }
        transformations['clip'] = {
            'start': obj.data.clip_start,
            'end': obj.data.clip_end
        }
    if obj.type not in transformations_clipboard:
        transformations_clipboard[obj.type] = []
    transformations_clipboard[obj.type].append(transformations)

def paste_transformations(obj: bpy.types.Object) -> None:
    """Paste the earliest copied transformations for the object's type back onto it."""
    global transformations_clipboard
    obj_type = obj.type
    if obj_type in transformations_clipboard and transformations_clipboard[obj_type]:
        transformations = transformations_clipboard[obj_type].pop(0)
        obj.location = Vector(transformations['location'])
        obj.rotation_euler = Vector(transformations['rotation'])
        obj.scale = Vector(transformations['scale'])
        if obj_type == 'LIGHT':
            obj.data.energy = transformations['light_intensity']
            obj.data.color = Vector(transformations['light_color'])
        elif obj_type == 'CAMERA':
            obj.data.lens = transformations['focal_length']
            obj.data.dof.use_dof = transformations['dof']['use_dof']
            obj.data.dof.focus_distance = transformations['dof']['focus_distance']
            obj.data.dof.aperture_fstop = transformations['dof']['aperture_fstop']
            obj.data.clip_start = transformations['clip']['start']
            obj.data.clip_end = transformations['clip']['end']


_UNSUPPORTED = object()

_GN_MODIFIER_SETTINGS_SKIP = {
    'rna_type',
    'type',
    'name',
    'node_group',
}

_GN_MODIFIER_SETTINGS_ALLOW = {
    # Intentionally empty: copy/paste is limited to the same parameters visible
    # in the Geometry Nodes modifier input panel.
}

_ID_COLLECTION_BY_TYPE = {
    'ACTION': 'actions',
    'ARMATURE': 'armatures',
    'BRUSH': 'brushes',
    'CAMERA': 'cameras',
    'COLLECTION': 'collections',
    'CURVE': 'curves',
    'FONT': 'fonts',
    'GREASEPENCIL': 'grease_pencils',
    'IMAGE': 'images',
    'LATTICE': 'lattices',
    'LIGHT': 'lights',
    'LIGHT_PROBE': 'lightprobes',
    'MASK': 'masks',
    'MATERIAL': 'materials',
    'MESH': 'meshes',
    'META': 'metaballs',
    'MOVIECLIP': 'movieclips',
    'NODETREE': 'node_groups',
    'OBJECT': 'objects',
    'PARTICLE': 'particles',
    'POINTCLOUD': 'pointclouds',
    'SCENE': 'scenes',
    'SOUND': 'sounds',
    'SPEAKER': 'speakers',
    'TEXT': 'texts',
    'TEXTURE': 'textures',
    'VOLUME': 'volumes',
    'WORLD': 'worlds',
}


def _serialize_datablock_reference(data_block: bpy.types.ID) -> Dict[str, Any]:
    return {
        '__id_ref__': True,
        'id_type': getattr(data_block, 'id_type', None),
        'name': data_block.name,
        'library': data_block.library.filepath if data_block.library else '',
        'value': data_block,
    }


def _serialize_value(value: Any) -> Any:
    if isinstance(value, bpy.types.ID):
        return _serialize_datablock_reference(value)

    if isinstance(value, (bool, int, float, str)) or value is None:
        return value

    if isinstance(value, (Vector, Color, Euler, Quaternion)):
        return tuple(value)

    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            serialized = _serialize_value(item)
            if serialized is _UNSUPPORTED:
                continue
            out[str(key)] = serialized
        return out

    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            serialized = _serialize_value(item)
            if serialized is _UNSUPPORTED:
                return _UNSUPPORTED
            out.append(serialized)
        return out

    if hasattr(value, 'to_list'):
        try:
            return value.to_list()
        except Exception:
            return _UNSUPPORTED

    try:
        as_tuple = tuple(value)
    except TypeError:
        return _UNSUPPORTED

    out = []
    for item in as_tuple:
        serialized = _serialize_value(item)
        if serialized is _UNSUPPORTED:
            return _UNSUPPORTED
        out.append(serialized)
    return tuple(out)


def _resolve_datablock_reference(data: Dict[str, Any]) -> Optional[bpy.types.ID]:
    direct = data.get('value')
    if isinstance(direct, bpy.types.ID):
        try:
            _ = direct.name
            return direct
        except ReferenceError:
            pass

    id_type = data.get('id_type')
    name = data.get('name')
    if not id_type or not name:
        return None

    collection_name = _ID_COLLECTION_BY_TYPE.get(id_type)
    if not collection_name:
        return None

    collection = getattr(bpy.data, collection_name, None)
    if collection is None:
        return None

    library_path = data.get('library') or ''
    candidate = collection.get(name)
    if candidate is None:
        return None
    if not library_path:
        return candidate

    candidate_library = candidate.library.filepath if candidate.library else ''
    if candidate_library == library_path:
        return candidate

    for item in collection:
        if item.name != name:
            continue
        item_library = item.library.filepath if item.library else ''
        if item_library == library_path:
            return item
    return None


def _deserialize_value(value: Any) -> Any:
    if isinstance(value, dict):
        if value.get('__id_ref__'):
            return _resolve_datablock_reference(value)
        return {k: _deserialize_value(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_deserialize_value(item) for item in value]

    if isinstance(value, tuple):
        return tuple(_deserialize_value(item) for item in value)

    return value


def _node_group_identity(node_group: bpy.types.NodeTree) -> Dict[str, Any]:
    session_uid = getattr(node_group, 'session_uid', None)
    library_path = node_group.library.filepath if node_group.library else ''
    key = f"{node_group.name}|{session_uid if session_uid is not None else 'no_session_uid'}|{library_path}"
    return {
        'key': key,
        'name': node_group.name,
        'session_uid': session_uid,
        'library': library_path,
    }


def _node_tree_identity(node_tree: bpy.types.NodeTree) -> Dict[str, Any]:
    session_uid = getattr(node_tree, 'session_uid', None)
    library_path = node_tree.library.filepath if node_tree.library else ''
    key = f"{node_tree.name}|{session_uid if session_uid is not None else 'no_session_uid'}|{library_path}|{node_tree.bl_idname}"
    return {
        'key': key,
        'name': node_tree.name,
        'session_uid': session_uid,
        'library': library_path,
        'bl_idname': node_tree.bl_idname,
    }


def get_geometry_nodes_modifier_group_keys(obj: bpy.types.Object) -> List[str]:
    """Return Geometry Nodes node-group identity keys used by an object's modifiers."""
    keys: List[str] = []
    for modifier in obj.modifiers:
        if modifier.type != 'NODES' or modifier.node_group is None:
            continue
        keys.append(_node_group_identity(modifier.node_group)['key'])
    return keys


def get_geometry_nodes_modifier_signature(obj: bpy.types.Object) -> Tuple[str, ...]:
    """Return a stable signature for Geometry Nodes networks on an object."""
    return tuple(sorted(get_geometry_nodes_modifier_group_keys(obj)))


def get_object_geometry_nodes_network_choices(obj: bpy.types.Object) -> List[Dict[str, Any]]:
    """Return unique Geometry Nodes networks on an object with labels for UI selection."""
    ordered_keys: List[str] = []
    key_counts: Dict[str, int] = {}
    key_names: Dict[str, str] = {}

    for modifier in obj.modifiers:
        if modifier.type != 'NODES' or modifier.node_group is None:
            continue
        identity = _node_group_identity(modifier.node_group)
        key = identity['key']
        if key not in key_counts:
            ordered_keys.append(key)
            key_names[key] = identity.get('name', modifier.node_group.name)
            key_counts[key] = 0
        key_counts[key] += 1

    choices: List[Dict[str, Any]] = []
    for key in ordered_keys:
        count = key_counts[key]
        name = key_names[key]
        label = name if count == 1 else f"{name} (x{count})"
        choices.append(
            {
                'group_key': key,
                'name': name,
                'count': count,
                'label': label,
            }
        )
    return choices


def get_object_geometry_nodes_network_enum_items(obj: bpy.types.Object) -> List[Tuple[str, str, str]]:
    """Return EnumProperty-compatible network choices for an object's GN modifiers."""
    items: List[Tuple[str, str, str]] = []
    for choice in get_object_geometry_nodes_network_choices(obj):
        group_key = choice.get('group_key', '')
        label = choice.get('label', choice.get('name', group_key))
        name = choice.get('name', label)
        count = int(choice.get('count', 0) or 0)
        description = f"Geometry Nodes network '{name}'"
        if count > 1:
            description += f" used by {count} modifiers"
        items.append((group_key, label, description))
    return items


def _to_json_safe_value(value: Any) -> Any:
    """Convert bpy values to JSON-safe primitives."""
    if isinstance(value, bpy.types.ID):
        return {
            '__id_ref__': True,
            'id_type': getattr(value, 'id_type', None),
            'name': value.name,
            'library': value.library.filepath if value.library else '',
        }

    if isinstance(value, (bool, int, float, str)) or value is None:
        return value

    if isinstance(value, (Vector, Color, Euler, Quaternion)):
        return list(value)

    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            serialized = _to_json_safe_value(item)
            if serialized is _UNSUPPORTED:
                continue
            out[str(key)] = serialized
        return out

    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            serialized = _to_json_safe_value(item)
            if serialized is _UNSUPPORTED:
                return _UNSUPPORTED
            out.append(serialized)
        return out

    if hasattr(value, 'to_list'):
        try:
            return value.to_list()
        except Exception:
            return _UNSUPPORTED

    try:
        as_tuple = tuple(value)
    except TypeError:
        return _UNSUPPORTED

    out = []
    for item in as_tuple:
        serialized = _to_json_safe_value(item)
        if serialized is _UNSUPPORTED:
            return _UNSUPPORTED
        out.append(serialized)
    return out


def _serialize_node_socket(socket: bpy.types.NodeSocket) -> Dict[str, Any]:
    socket_data = {
        'name': socket.name,
        'identifier': getattr(socket, 'identifier', ''),
        'type': getattr(socket, 'type', ''),
        'bl_idname': getattr(socket, 'bl_idname', ''),
    }

    if hasattr(socket, 'default_value'):
        try:
            default_value = _to_json_safe_value(socket.default_value)
            if default_value is not _UNSUPPORTED:
                socket_data['default_value'] = default_value
        except Exception:
            pass

    return socket_data


def _capture_node_runtime_properties(node: bpy.types.Node) -> Dict[str, Any]:
    props: Dict[str, Any] = {}
    if not hasattr(node, "bl_rna") or not hasattr(node.bl_rna, "properties"):
        return props

    for prop in node.bl_rna.properties:
        prop_name = getattr(prop, "identifier", "")
        if not prop_name or prop_name in {"rna_type", "name", "location"}:
            continue
        if getattr(prop, "is_readonly", False):
            continue
        if getattr(prop, "is_hidden", False):
            continue
        try:
            value = getattr(node, prop_name)
        except Exception:
            continue
        serialized = _to_json_safe_value(value)
        if serialized is _UNSUPPORTED:
            continue
        props[prop_name] = serialized

    for key in node.keys():
        if key == "_RNA_UI":
            continue
        try:
            value = node[key]
        except Exception:
            continue
        serialized = _to_json_safe_value(value)
        if serialized is _UNSUPPORTED:
            continue
        props[f"idprop:{key}"] = serialized

    return props


def _capture_tree_interface(node_tree: bpy.types.NodeTree) -> Dict[str, List[Dict[str, Any]]]:
    interface_data = {
        'inputs': [],
        'outputs': [],
    }
    interface = getattr(node_tree, "interface", None)
    items_tree = getattr(interface, "items_tree", None) if interface is not None else None
    if items_tree is None:
        return interface_data

    for item in items_tree:
        if getattr(item, "item_type", "") != "SOCKET":
            continue
        socket_info = {
            'name': getattr(item, "name", ""),
            'identifier': getattr(item, "identifier", ""),
            'socket_type': getattr(item, "socket_type", ""),
            'in_out': getattr(item, "in_out", ""),
        }
        default_attribute_name = getattr(item, "default_attribute_name", None)
        if default_attribute_name not in (None, ""):
            socket_info['default_attribute_name'] = default_attribute_name

        if socket_info['in_out'] == "INPUT":
            interface_data['inputs'].append(socket_info)
        elif socket_info['in_out'] == "OUTPUT":
            interface_data['outputs'].append(socket_info)

    return interface_data


def _serialize_node_tree_recursive(
    node_tree: bpy.types.NodeTree,
    groups: Dict[str, Dict[str, Any]],
) -> str:
    identity = _node_tree_identity(node_tree)
    group_key = identity['key']

    if group_key in groups:
        return group_key

    nodes_data: List[Dict[str, Any]] = []
    links_data: List[Dict[str, Any]] = []
    nested_group_keys: List[str] = []
    nested_seen: Set[str] = set()

    for node in node_tree.nodes:
        node_data = {
            'name': node.name,
            'label': node.label,
            'bl_idname': node.bl_idname,
            'type': node.type,
            'mute': bool(getattr(node, "mute", False)),
            'hide': bool(getattr(node, "hide", False)),
            'location': [float(node.location[0]), float(node.location[1])],
            'width': float(getattr(node, "width", 0.0)),
            'height': float(getattr(node, "height", 0.0)),
            'parent': node.parent.name if getattr(node, "parent", None) else None,
            'inputs': [_serialize_node_socket(sock) for sock in node.inputs],
            'outputs': [_serialize_node_socket(sock) for sock in node.outputs],
            'properties': _capture_node_runtime_properties(node),
        }

        child_tree = getattr(node, "node_tree", None)
        if isinstance(child_tree, bpy.types.NodeTree):
            child_key = _serialize_node_tree_recursive(child_tree, groups)
            node_data['node_tree_key'] = child_key
            if child_key not in nested_seen:
                nested_seen.add(child_key)
                nested_group_keys.append(child_key)

        nodes_data.append(node_data)

    for link in node_tree.links:
        links_data.append(
            {
                'from_node': link.from_node.name if link.from_node else "",
                'from_socket': link.from_socket.name if link.from_socket else "",
                'from_socket_identifier': getattr(link.from_socket, "identifier", "") if link.from_socket else "",
                'to_node': link.to_node.name if link.to_node else "",
                'to_socket': link.to_socket.name if link.to_socket else "",
                'to_socket_identifier': getattr(link.to_socket, "identifier", "") if link.to_socket else "",
            }
        )

    groups[group_key] = {
        'identity': identity,
        'tree_flags': {
            'is_modifier': bool(getattr(node_tree, "is_modifier", False)),
            'is_tool': bool(getattr(node_tree, "is_tool", False)),
        },
        'interface': _capture_tree_interface(node_tree),
        'nodes': nodes_data,
        'links': links_data,
        'nested_group_keys': nested_group_keys,
    }
    return group_key


def _sanitize_filename(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in name)
    cleaned = cleaned.strip("_")
    return cleaned or "geometry_nodes_network"


def get_default_geometry_nodes_export_filepath(node_group_name: str, directory: str = "") -> str:
    """Return a default JSON path for GN export: in `directory` if given ('//' = relative
    to the .blend), else next to the .blend file, else in the home folder."""
    blend_path = bpy.data.filepath
    directory = (directory or "").strip()
    if directory and (blend_path or not directory.startswith("//")):
        base_dir = bpy.path.abspath(directory)
    elif blend_path:
        base_dir = os.path.dirname(blend_path)
    else:
        base_dir = os.path.expanduser("~")
    filename = f"{_sanitize_filename(node_group_name)}.json"
    return os.path.join(base_dir, filename)


def export_geometry_nodes_network_to_json(
    obj: bpy.types.Object,
    group_key: str,
    filepath: str,
) -> Dict[str, Any]:
    """Export one GN network from an object to JSON, recursively including nested groups."""
    if obj is None:
        raise ValueError("No source object provided")

    target_group = None
    for modifier in obj.modifiers:
        if modifier.type != 'NODES' or modifier.node_group is None:
            continue
        identity_key = _node_group_identity(modifier.node_group)['key']
        if identity_key == group_key:
            target_group = modifier.node_group
            break

    if target_group is None:
        raise ValueError("Selected Geometry Nodes network was not found on the active object")

    groups: Dict[str, Dict[str, Any]] = {}
    root_key = _serialize_node_tree_recursive(target_group, groups)

    export_data: Dict[str, Any] = {
        'schema_version': 1,
        'exported_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_object': {
            'name': obj.name,
            'type': obj.type,
        },
        'root_group_key': root_key,
        'groups': groups,
    }

    resolved_path = bpy.path.abspath(filepath)
    if not resolved_path.lower().endswith(".json"):
        resolved_path = f"{resolved_path}.json"
    out_dir = os.path.dirname(resolved_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(resolved_path, "w", encoding="utf-8") as handle:
        json.dump(export_data, handle, indent=2)

    node_count = sum(len(group_data.get('nodes', [])) for group_data in groups.values())
    link_count = sum(len(group_data.get('links', [])) for group_data in groups.values())
    return {
        'filepath': resolved_path,
        'root_group_name': target_group.name,
        'group_count': len(groups),
        'node_count': node_count,
        'link_count': link_count,
    }


def _clear_node_tree_contents(node_tree: bpy.types.NodeTree) -> None:
    for link in list(node_tree.links):
        try:
            node_tree.links.remove(link)
        except Exception:
            pass

    for node in list(node_tree.nodes):
        try:
            node_tree.nodes.remove(node)
        except Exception:
            pass

    interface = getattr(node_tree, "interface", None)
    items_tree = getattr(interface, "items_tree", None) if interface is not None else None
    if interface is None or items_tree is None:
        return

    for item in list(items_tree):
        try:
            interface.remove(item)
        except Exception:
            pass


def _import_tree_interface(
    node_tree: bpy.types.NodeTree,
    interface_data: Dict[str, Any],
) -> None:
    interface = getattr(node_tree, "interface", None)
    if interface is None:
        return

    for socket_info in interface_data.get('inputs', []):
        socket_type = socket_info.get('socket_type') or 'NodeSocketFloat'
        name = socket_info.get('name') or "Input"
        try:
            socket_item = interface.new_socket(name=name, in_out='INPUT', socket_type=socket_type)
        except Exception:
            continue
        default_attribute_name = socket_info.get('default_attribute_name')
        if default_attribute_name not in (None, "") and hasattr(socket_item, "default_attribute_name"):
            try:
                socket_item.default_attribute_name = default_attribute_name
            except Exception:
                pass

    for socket_info in interface_data.get('outputs', []):
        socket_type = socket_info.get('socket_type') or 'NodeSocketFloat'
        name = socket_info.get('name') or "Output"
        try:
            interface.new_socket(name=name, in_out='OUTPUT', socket_type=socket_type)
        except Exception:
            continue


def _find_socket_by_identity(
    sockets: Any,
    identifier: str,
    name: str,
) -> Optional[bpy.types.NodeSocket]:
    if identifier:
        for socket in sockets:
            if getattr(socket, "identifier", "") == identifier:
                return socket

    if name:
        for socket in sockets:
            if socket.name == name:
                return socket
    return None


def _assign_socket_default(socket: bpy.types.NodeSocket, value: Any) -> bool:
    try:
        socket.default_value = value
        return True
    except Exception:
        if isinstance(value, list):
            try:
                socket.default_value = tuple(value)
                return True
            except Exception:
                return False
        return False


def _assign_node_property(node: bpy.types.Node, prop_name: str, value: Any) -> bool:
    try:
        setattr(node, prop_name, value)
        return True
    except Exception:
        if isinstance(value, list):
            try:
                setattr(node, prop_name, tuple(value))
                return True
            except Exception:
                return False
        return False


def _assign_node_idprop(node: bpy.types.Node, key: str, value: Any) -> bool:
    try:
        node[key] = value
        return True
    except Exception:
        if isinstance(value, list):
            try:
                node[key] = tuple(value)
                return True
            except Exception:
                return False
        return False


def _restore_node_runtime_properties(
    node: bpy.types.Node,
    properties: Dict[str, Any],
    stats: Dict[str, int],
) -> None:
    for prop_name, stored_value in properties.items():
        value = _deserialize_value(stored_value)
        if value is None and isinstance(stored_value, dict) and stored_value.get('__id_ref__'):
            stats['skipped_values'] += 1
            continue

        if prop_name.startswith("idprop:"):
            idprop_key = prop_name.split(":", 1)[1]
            if _assign_node_idprop(node, idprop_key, value):
                stats['applied_values'] += 1
            else:
                stats['skipped_values'] += 1
            continue

        if _assign_node_property(node, prop_name, value):
            stats['applied_values'] += 1
        else:
            stats['skipped_values'] += 1


def _restore_node_socket_defaults(
    node: bpy.types.Node,
    sockets_data: List[Dict[str, Any]],
    is_input: bool,
    stats: Dict[str, int],
) -> None:
    sockets = node.inputs if is_input else node.outputs
    for socket_data in sockets_data:
        if 'default_value' not in socket_data:
            continue

        socket = _find_socket_by_identity(
            sockets,
            socket_data.get('identifier', ''),
            socket_data.get('name', ''),
        )
        if socket is None or not hasattr(socket, 'default_value'):
            stats['skipped_values'] += 1
            continue

        stored_value = socket_data.get('default_value')
        value = _deserialize_value(stored_value)
        if value is None and isinstance(stored_value, dict) and stored_value.get('__id_ref__'):
            stats['skipped_values'] += 1
            continue

        if _assign_socket_default(socket, value):
            stats['applied_values'] += 1
        else:
            stats['skipped_values'] += 1


def _import_node_tree_recursive(
    group_key: str,
    groups_data: Dict[str, Dict[str, Any]],
    cache: Dict[str, bpy.types.NodeTree],
    in_progress: Set[str],
    stats: Dict[str, int],
) -> bpy.types.NodeTree:
    if group_key in cache:
        return cache[group_key]

    group_data = groups_data.get(group_key)
    if not isinstance(group_data, dict):
        raise ValueError(f"Missing group data for key '{group_key}'")

    identity = group_data.get('identity', {})
    group_name = identity.get('name') or "Imported_GeometryNodes"
    tree_type = identity.get('bl_idname') or "GeometryNodeTree"

    try:
        node_tree = bpy.data.node_groups.new(name=group_name, type=tree_type)
    except Exception:
        node_tree = bpy.data.node_groups.new(name=group_name, type="GeometryNodeTree")

    cache[group_key] = node_tree
    in_progress.add(group_key)
    stats['group_count'] += 1

    _clear_node_tree_contents(node_tree)
    _import_tree_interface(node_tree, group_data.get('interface', {}))

    created_nodes: Dict[str, bpy.types.Node] = {}
    node_payload: Dict[str, Dict[str, Any]] = {}
    for node_data in group_data.get('nodes', []):
        bl_idname = node_data.get('bl_idname', '')
        if not bl_idname:
            stats['skipped_nodes'] += 1
            continue

        try:
            node = node_tree.nodes.new(type=bl_idname)
        except Exception:
            stats['skipped_nodes'] += 1
            continue

        source_name = node_data.get('name', node.name)
        try:
            if source_name:
                node.name = source_name
        except Exception:
            pass
        try:
            node.label = node_data.get('label', "")
        except Exception:
            pass
        try:
            node.mute = bool(node_data.get('mute', False))
        except Exception:
            pass
        try:
            node.hide = bool(node_data.get('hide', False))
        except Exception:
            pass
        try:
            location = node_data.get('location', [0.0, 0.0])
            if isinstance(location, list) and len(location) >= 2:
                node.location = (float(location[0]), float(location[1]))
        except Exception:
            pass
        try:
            node.width = float(node_data.get('width', node.width))
        except Exception:
            pass

        child_key = node_data.get('node_tree_key')
        if child_key and child_key in groups_data and hasattr(node, "node_tree"):
            try:
                child_tree = _import_node_tree_recursive(
                    child_key,
                    groups_data,
                    cache,
                    in_progress,
                    stats,
                )
                node.node_tree = child_tree
            except Exception:
                stats['skipped_values'] += 1

        _restore_node_runtime_properties(node, node_data.get('properties', {}), stats)
        _restore_node_socket_defaults(node, node_data.get('inputs', []), True, stats)

        created_nodes[source_name] = node
        node_payload[source_name] = node_data
        stats['node_count'] += 1

    for source_name, node in created_nodes.items():
        parent_name = node_payload.get(source_name, {}).get('parent')
        if not parent_name:
            continue
        parent = created_nodes.get(parent_name)
        if parent is None:
            continue
        try:
            node.parent = parent
        except Exception:
            stats['skipped_values'] += 1

    for link_data in group_data.get('links', []):
        from_node = created_nodes.get(link_data.get('from_node', ''))
        to_node = created_nodes.get(link_data.get('to_node', ''))
        if from_node is None or to_node is None:
            stats['skipped_links'] += 1
            continue

        from_socket = _find_socket_by_identity(
            from_node.outputs,
            link_data.get('from_socket_identifier', ''),
            link_data.get('from_socket', ''),
        )
        to_socket = _find_socket_by_identity(
            to_node.inputs,
            link_data.get('to_socket_identifier', ''),
            link_data.get('to_socket', ''),
        )
        if from_socket is None or to_socket is None:
            stats['skipped_links'] += 1
            continue

        try:
            node_tree.links.new(from_socket, to_socket)
            stats['link_count'] += 1
        except Exception:
            stats['skipped_links'] += 1

    in_progress.discard(group_key)
    try:
        node_tree.update_tag()
    except Exception:
        pass
    return node_tree


def import_geometry_nodes_network_from_json(
    filepath: str,
    target_object: Optional[bpy.types.Object] = None,
    attach_to_active_object: bool = True,
) -> Dict[str, Any]:
    """Import a Geometry Nodes network JSON export into node groups and optionally attach it."""
    resolved_path = bpy.path.abspath(filepath)
    if not os.path.exists(resolved_path):
        raise ValueError(f"JSON file not found: {resolved_path}")

    try:
        with open(resolved_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Invalid JSON root; expected an object")

    schema_version = data.get('schema_version')
    if schema_version != 1:
        raise ValueError(f"Unsupported schema_version '{schema_version}'; expected 1")

    groups_data = data.get('groups')
    if not isinstance(groups_data, dict) or not groups_data:
        raise ValueError("JSON does not contain any exported node groups")

    root_group_key = data.get('root_group_key')
    if not isinstance(root_group_key, str) or not root_group_key:
        raise ValueError("JSON missing root_group_key")
    if root_group_key not in groups_data:
        raise ValueError("root_group_key does not reference an exported group")

    stats: Dict[str, int] = {
        'group_count': 0,
        'node_count': 0,
        'link_count': 0,
        'applied_values': 0,
        'skipped_values': 0,
        'skipped_nodes': 0,
        'skipped_links': 0,
    }
    cache: Dict[str, bpy.types.NodeTree] = {}
    in_progress: Set[str] = set()

    root_tree = _import_node_tree_recursive(
        root_group_key,
        groups_data,
        cache,
        in_progress,
        stats,
    )

    root_group_data = groups_data.get(root_group_key, {})
    root_flags = root_group_data.get('tree_flags', {}) if isinstance(root_group_data, dict) else {}
    # Exported files before this importer patch won't have tree_flags.
    # In that case, force modifier-compat on the imported root group.
    if hasattr(root_tree, "is_modifier"):
        try:
            root_tree.is_modifier = bool(root_flags.get('is_modifier', True))
        except Exception:
            pass
    if hasattr(root_tree, "is_tool"):
        try:
            root_tree.is_tool = bool(root_flags.get('is_tool', False))
        except Exception:
            pass
    if hasattr(root_tree, "interface_update"):
        try:
            root_tree.interface_update(bpy.context)
        except Exception:
            pass
    try:
        root_tree.update_tag()
    except Exception:
        pass

    attached_modifier = False
    modifier_name = ""
    if attach_to_active_object:
        if target_object is None:
            raise ValueError("No active object available to attach imported network")
        if not hasattr(target_object, "modifiers"):
            raise ValueError(f"Object '{target_object.name}' does not support modifiers")

        modifier_name = root_tree.name
        try:
            modifier = target_object.modifiers.new(name=modifier_name, type='NODES')
            modifier.node_group = root_tree
            attached_modifier = True
        except Exception as exc:
            raise ValueError(f"Failed to attach imported network to '{target_object.name}': {exc}") from exc

        try:
            target_object.update_tag(refresh={'DATA', 'OBJECT'})
        except Exception:
            pass
        obj_data = getattr(target_object, "data", None)
        if obj_data is not None and hasattr(obj_data, "update_tag"):
            try:
                obj_data.update_tag()
            except Exception:
                pass

    return {
        'filepath': resolved_path,
        'root_group_key': root_group_key,
        'root_group_name': root_tree.name,
        'group_count': stats['group_count'],
        'node_count': stats['node_count'],
        'link_count': stats['link_count'],
        'applied_values': stats['applied_values'],
        'skipped_values': stats['skipped_values'],
        'skipped_nodes': stats['skipped_nodes'],
        'skipped_links': stats['skipped_links'],
        'attached_modifier': attached_modifier,
        'modifier_name': modifier_name,
    }


def _capture_modifier_settings(modifier: bpy.types.Modifier) -> Dict[str, Any]:
    settings: Dict[str, Any] = {}
    properties = modifier.bl_rna.properties
    for prop_name in _GN_MODIFIER_SETTINGS_ALLOW:
        prop = properties.get(prop_name) if hasattr(properties, "get") else None
        if prop is None:
            continue
        if prop_name in _GN_MODIFIER_SETTINGS_SKIP or prop.is_readonly:
            continue
        try:
            value = getattr(modifier, prop_name)
        except Exception:
            continue
        serialized = _serialize_value(value)
        if serialized is _UNSUPPORTED:
            continue
        settings[prop_name] = serialized
    return settings


def _modifier_visible_input_labels(modifier: bpy.types.Modifier) -> Dict[str, str]:
    labels: Dict[str, str] = {}
    node_group = getattr(modifier, "node_group", None)
    if node_group is None:
        return labels

    interface = getattr(node_group, "interface", None)
    items_tree = getattr(interface, "items_tree", None) if interface is not None else None
    if items_tree is not None:
        for item in items_tree:
            if getattr(item, "item_type", "") != "SOCKET":
                continue
            if getattr(item, "in_out", "") != "INPUT":
                continue
            if getattr(item, "hide_in_modifier", False):
                continue
            identifier = getattr(item, "identifier", "")
            if not identifier:
                continue
            labels[identifier] = getattr(item, "name", identifier)

    if labels:
        return labels

    # Backward-compatible fallback for older Blender versions.
    group_inputs = getattr(node_group, "inputs", None)
    if group_inputs is None:
        return labels

    for socket in group_inputs:
        if getattr(socket, "hide_in_modifier", False):
            continue
        identifier = getattr(socket, "identifier", "")
        if not identifier:
            continue
        labels[identifier] = getattr(socket, "name", identifier)
    return labels


def _modifier_input_container(modifier: bpy.types.Modifier) -> Optional[Any]:
    """Return the Blender 5.2+ `modifier.properties.inputs` struct, or None on older versions.

    Before 5.2, modifier inputs are IDProperties keyed by socket identifier
    (`modifier["Socket_1"]`, `modifier["Socket_1_use_attribute"]`, ...).
    """
    properties = getattr(modifier, "properties", None)
    if properties is None:
        return None
    return getattr(properties, "inputs", None)


def _modifier_input_item(modifier: bpy.types.Modifier, identifier: str) -> Optional[Any]:
    container = _modifier_input_container(modifier)
    if container is None:
        return None
    item = getattr(container, identifier, None)
    if item is None or not hasattr(item, "value"):
        return None
    return item


def _has_modifier_input(modifier: bpy.types.Modifier, identifier: str) -> bool:
    if _modifier_input_container(modifier) is not None:
        return _modifier_input_item(modifier, identifier) is not None
    return identifier in modifier.keys()


def _get_modifier_input_value(modifier: bpy.types.Modifier, identifier: str) -> Any:
    """Return the stored value of a GN modifier input; raises KeyError when missing."""
    if _modifier_input_container(modifier) is not None:
        item = _modifier_input_item(modifier, identifier)
        if item is None:
            raise KeyError(identifier)
        return item.value
    return modifier[identifier]


def _set_modifier_input_value(modifier: bpy.types.Modifier, identifier: str, value: Any) -> None:
    if _modifier_input_container(modifier) is not None:
        item = _modifier_input_item(modifier, identifier)
        if item is None:
            raise KeyError(identifier)
        item.value = value
        return
    modifier[identifier] = value


def _get_modifier_input_attribute_state(
    modifier: bpy.types.Modifier,
    identifier: str,
) -> Optional[Dict[str, Any]]:
    """Return the field source of an input as {'type', 'attribute_name', 'layer_name'}.

    'type' is 'VALUE', 'ATTRIBUTE' or 'LAYER'. Returns None for inputs that can't
    read attributes.
    """
    if _modifier_input_container(modifier) is not None:
        item = _modifier_input_item(modifier, identifier)
        if item is None or not hasattr(item, "attribute_name"):
            return None
        return {
            'type': getattr(item, "type", 'VALUE'),
            'attribute_name': item.attribute_name,
            'layer_name': getattr(item, "layer_name", ""),
        }

    use_key = f"{identifier}_use_attribute"
    if use_key not in modifier.keys():
        return None
    return {
        'type': 'ATTRIBUTE' if modifier[use_key] else 'VALUE',
        'attribute_name': modifier.get(f"{identifier}_attribute_name", ""),
        'layer_name': "",
    }


def _set_modifier_input_attribute_state(
    modifier: bpy.types.Modifier,
    identifier: str,
    state: Dict[str, Any],
) -> bool:
    source_type = state.get('type', 'VALUE')
    attribute_name = state.get('attribute_name', "")

    if _modifier_input_container(modifier) is not None:
        item = _modifier_input_item(modifier, identifier)
        if item is None or not hasattr(item, "attribute_name"):
            return False
        item.attribute_name = attribute_name
        if hasattr(item, "layer_name"):
            item.layer_name = state.get('layer_name', "")
        try:
            item.type = source_type
        except TypeError:
            # Target socket doesn't support this source (e.g. LAYER on a non-boolean input).
            item.type = 'ATTRIBUTE' if source_type != 'VALUE' else 'VALUE'
        return True

    use_key = f"{identifier}_use_attribute"
    if use_key not in modifier.keys():
        return False
    modifier[use_key] = source_type != 'VALUE'
    modifier[f"{identifier}_attribute_name"] = attribute_name
    return True


def _capture_modifier_inputs(
    modifier: bpy.types.Modifier,
) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, Dict[str, Any]]]:
    inputs: Dict[str, Any] = {}
    input_labels: Dict[str, str] = {}
    input_attributes: Dict[str, Dict[str, Any]] = {}

    base_labels = _modifier_visible_input_labels(modifier)
    if not base_labels:
        return inputs, input_labels, input_attributes

    for key, label in base_labels.items():
        if not _has_modifier_input(modifier, key):
            continue
        try:
            value = _get_modifier_input_value(modifier, key)
        except Exception:
            continue

        serialized = _serialize_value(value)
        if serialized is _UNSUPPORTED:
            continue
        inputs[key] = serialized
        input_labels[key] = label

        attribute_state = _get_modifier_input_attribute_state(modifier, key)
        if attribute_state is not None:
            input_attributes[key] = attribute_state

    return inputs, input_labels, input_attributes


def copy_geometry_nodes_modifiers(obj: bpy.types.Object) -> Dict[str, int]:
    """Copy all Geometry Nodes modifiers from an object into the addon clipboard."""
    global geometry_nodes_modifiers_clipboard

    by_group: Dict[str, List[Dict[str, Any]]] = {}
    entries: List[Dict[str, Any]] = []
    copied_modifiers = 0
    group_ordinals: Dict[str, int] = {}

    for stack_index, modifier in enumerate(obj.modifiers):
        if modifier.type != 'NODES' or modifier.node_group is None:
            continue

        identity = _node_group_identity(modifier.node_group)
        group_key = identity['key']
        group_ordinal = group_ordinals.get(group_key, 0)
        group_ordinals[group_key] = group_ordinal + 1

        entry_id = f"entry_{len(entries)}"
        entry = {
            'entry_id': entry_id,
            'modifier_name': modifier.name,
            'stack_index': stack_index,
            'group_ordinal': group_ordinal,
            'group_identity': identity,
            'settings': _capture_modifier_settings(modifier),
            'inputs': {},
            'input_labels': {},
            'input_attributes': {},
        }
        entry_inputs, entry_input_labels, entry_input_attributes = _capture_modifier_inputs(modifier)
        entry['inputs'] = entry_inputs
        entry['input_labels'] = entry_input_labels
        entry['input_attributes'] = entry_input_attributes
        by_group.setdefault(group_key, []).append(entry)
        entries.append(entry)
        copied_modifiers += 1

    geometry_nodes_modifiers_clipboard = {
        'source_object_name': obj.name,
        'source_object_type': obj.type,
        'by_group': by_group,
        'entries': entries,
        'copied_modifiers': copied_modifiers,
    }
    return {
        'copied_modifiers': copied_modifiers,
        'copied_groups': len(by_group),
    }


def _select_matching_modifier(
    target_candidates: List[Dict[str, Any]],
    stored_entry: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    unused = [item for item in target_candidates if not item['used']]
    if not unused:
        return None

    stored_name = stored_entry.get('modifier_name')
    if stored_name:
        for candidate in unused:
            if candidate['modifier'].name == stored_name:
                return candidate

    stored_stack_index = stored_entry.get('stack_index')
    if isinstance(stored_stack_index, int):
        for candidate in unused:
            if candidate['stack_index'] == stored_stack_index:
                return candidate

    ordered_unused = sorted(unused, key=lambda item: item['stack_index'])
    stored_group_ordinal = stored_entry.get('group_ordinal')
    if isinstance(stored_group_ordinal, int):
        if 0 <= stored_group_ordinal < len(ordered_unused):
            return ordered_unused[stored_group_ordinal]

    return ordered_unused[0]


def _apply_modifier_settings(
    modifier: bpy.types.Modifier,
    stored_settings: Dict[str, Any],
) -> Dict[str, int]:
    applied = 0
    skipped_missing = 0
    skipped_type = 0
    properties = modifier.bl_rna.properties

    for prop_name, stored_value in stored_settings.items():
        prop = properties.get(prop_name) if hasattr(properties, 'get') else None
        if prop is None:
            skipped_missing += 1
            continue
        if prop.is_readonly:
            skipped_type += 1
            continue

        value = _deserialize_value(stored_value)
        if value is None and isinstance(stored_value, dict) and stored_value.get('__id_ref__'):
            skipped_type += 1
            continue

        try:
            setattr(modifier, prop_name, value)
            applied += 1
        except Exception:
            skipped_type += 1

    return {
        'applied': applied,
        'skipped_missing': skipped_missing,
        'skipped_type': skipped_type,
    }


def _apply_modifier_inputs(
    modifier: bpy.types.Modifier,
    stored_inputs: Dict[str, Any],
    stored_attributes: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, int]:
    applied = 0
    skipped_missing = 0
    skipped_type = 0
    stored_attributes = stored_attributes or {}

    for key, stored_value in stored_inputs.items():
        if not _has_modifier_input(modifier, key):
            skipped_missing += 1
            continue

        # The field source travels with its input: pasting "Radius" also pastes
        # whether it reads a named attribute.
        attribute_state = stored_attributes.get(key)
        if attribute_state is not None:
            try:
                _set_modifier_input_attribute_state(modifier, key, attribute_state)
            except Exception:
                pass

        value = _deserialize_value(stored_value)
        if value is None and isinstance(stored_value, dict) and stored_value.get('__id_ref__'):
            skipped_type += 1
            continue

        try:
            _set_modifier_input_value(modifier, key, value)
            applied += 1
        except Exception:
            skipped_type += 1

    return {
        'applied': applied,
        'skipped_missing': skipped_missing,
        'skipped_type': skipped_type,
    }


def _filter_parameter_map(
    values_map: Dict[str, Any],
    prefix: str,
    selected_parameters: Optional[Set[Tuple[str, str]]],
) -> Dict[str, Any]:
    if selected_parameters is None:
        return values_map
    filtered: Dict[str, Any] = {}
    for key, value in values_map.items():
        if (prefix, key) in selected_parameters:
            filtered[key] = value
    return filtered


def paste_geometry_nodes_modifiers(
    obj: bpy.types.Object,
    selected_entry_ids: Optional[Set[str]] = None,
    selected_parameters_by_entry: Optional[Dict[str, Set[Tuple[str, str]]]] = None,
    context: Optional[bpy.types.Context] = None,
) -> Dict[str, int]:
    """Paste Geometry Nodes modifier clipboard data onto matching modifiers on an object."""
    clipboard_groups = geometry_nodes_modifiers_clipboard.get('by_group', {})
    if not clipboard_groups:
        return {
            'matched_modifiers': 0,
            'applied_values': 0,
            'skipped_missing': 0,
            'skipped_type': 0,
        }

    target_by_group: Dict[str, List[Dict[str, Any]]] = {}
    for stack_index, modifier in enumerate(obj.modifiers):
        if modifier.type != 'NODES' or modifier.node_group is None:
            continue
        key = _node_group_identity(modifier.node_group)['key']
        target_by_group.setdefault(key, []).append(
            {
                'modifier': modifier,
                'stack_index': stack_index,
                'used': False,
            }
        )

    matched_modifiers = 0
    applied_values = 0
    skipped_missing = 0
    skipped_type = 0
    touched_modifiers: List[bpy.types.Modifier] = []
    touched_node_groups: Set[bpy.types.NodeTree] = set()

    for group_key, stored_entries in clipboard_groups.items():
        target_candidates = target_by_group.get(group_key, [])
        if not target_candidates:
            continue

        for stored_entry in stored_entries:
            entry_id = stored_entry.get('entry_id')
            if selected_entry_ids is not None and entry_id not in selected_entry_ids:
                continue

            match = _select_matching_modifier(target_candidates, stored_entry)
            if match is None:
                continue
            match['used'] = True
            matched_modifiers += 1
            touched_modifiers.append(match['modifier'])
            if match['modifier'].node_group is not None:
                touched_node_groups.add(match['modifier'].node_group)

            selected_parameters = None
            if selected_parameters_by_entry is not None:
                selected_parameters = selected_parameters_by_entry.get(entry_id, set())

            filtered_settings = _filter_parameter_map(
                stored_entry.get('settings', {}),
                'setting',
                selected_parameters,
            )
            filtered_inputs = _filter_parameter_map(
                stored_entry.get('inputs', {}),
                'input',
                selected_parameters,
            )

            settings_stats = _apply_modifier_settings(
                match['modifier'],
                filtered_settings,
            )
            inputs_stats = _apply_modifier_inputs(
                match['modifier'],
                filtered_inputs,
                stored_entry.get('input_attributes', {}),
            )

            applied_values += settings_stats['applied'] + inputs_stats['applied']
            skipped_missing += settings_stats['skipped_missing'] + inputs_stats['skipped_missing']
            skipped_type += settings_stats['skipped_type'] + inputs_stats['skipped_type']

    if touched_modifiers:
        try:
            obj.modifiers.update()
        except Exception:
            pass

        ctx = context if context is not None else bpy.context
        for node_group in touched_node_groups:
            if hasattr(node_group, "interface_update"):
                try:
                    node_group.interface_update(ctx)
                except Exception:
                    pass
            if hasattr(node_group, "update_tag"):
                try:
                    node_group.update_tag()
                except Exception:
                    pass

        try:
            obj.update_tag(refresh={'OBJECT', 'DATA'})
        except TypeError:
            try:
                obj.update_tag()
            except Exception:
                pass
        except Exception:
            pass

    return {
        'matched_modifiers': matched_modifiers,
        'applied_values': applied_values,
        'skipped_missing': skipped_missing,
        'skipped_type': skipped_type,
    }

def set_origin_to_bottom_center(obj: bpy.types.Object) -> None:
    """Set the origin to the center of the object's bounding box bottom face."""
    # Calculate the center bottom position of the bounding box
    bbox_center_x = (obj.bound_box[0][0] + obj.bound_box[6][0]) / 2
    bbox_center_y = (obj.bound_box[0][1] + obj.bound_box[6][1]) / 2
    bbox_bottom_z = min([v[2] for v in obj.bound_box])

    # Get the world coordinates of the new origin
    world_origin = obj.matrix_world @ Vector((bbox_center_x, bbox_center_y, bbox_bottom_z))

    # Set the origin to the calculated position
    prev_cursor_loc = bpy.context.scene.cursor.location.copy()
    bpy.context.scene.cursor.location = world_origin
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.context.scene.cursor.location = prev_cursor_loc


# Scene-level structs drawn by Blender's own Render Properties panels. Display settings
# come before view settings because valid view transforms depend on the display device.
_RENDER_TAB_SCENE_STRUCTS = (
    "render",
    "eevee",
    "display",
    "display_settings",
    "view_settings",
    "sequencer_colorspace_settings",
    "grease_pencil_settings",
    "hydra",
)

# RenderSettings properties drawn in the Output Properties tab rather than Render.
_OUTPUT_TAB_RENDER_PROPS = {
    "resolution_x", "resolution_y", "resolution_percentage",
    "pixel_aspect_x", "pixel_aspect_y", "ppm_base", "ppm_factor",
    "use_border", "use_crop_to_border",
    "border_min_x", "border_min_y", "border_max_x", "border_max_y",
    "fps", "fps_base", "frame_map_old", "frame_map_new",
    "use_compositing", "use_sequencer", "dither_intensity",
    "metadata_input",
    "filepath", "save_output", "use_file_extension", "use_overwrite",
    "use_placeholder", "use_render_cache",
    "image_settings", "ffmpeg",
    "use_multiview", "views_format", "views",
}
_OUTPUT_TAB_RENDER_PREFIXES = ("use_stamp", "stamp_")

# Add-ons whose Render Properties panels are left alone when copying render settings.
_RENDER_COPY_EXCLUDED_ADDONS = {"level_link"}

_RENDER_COPY_MAX_DEPTH = 8


def _addon_package_root(module_name: str) -> str:
    parts = module_name.split(".")
    if parts[0] == "bl_ext" and len(parts) >= 3:
        return ".".join(parts[:3])
    return parts[0]


def _render_tab_addon_scene_props(scene: bpy.types.Scene) -> List[str]:
    """Return Scene PropertyGroup pointers owned by add-ons that draw Render Properties panels.

    This picks up render engines such as Cycles (`scene.cycles`, `scene.cycles_curves`)
    without listing them by hand, and skips add-ons in `_RENDER_COPY_EXCLUDED_ADDONS`.
    """
    def all_subclasses(cls):
        for sub in cls.__subclasses__():
            yield sub
            yield from all_subclasses(sub)

    render_tab_packages: Set[str] = set()
    for panel in all_subclasses(bpy.types.Panel):
        if getattr(panel, "bl_space_type", "") != 'PROPERTIES' or getattr(panel, "bl_context", "") != "render":
            continue
        root = _addon_package_root(panel.__module__)
        if root.startswith("bl_") and not root.startswith("bl_ext."):
            continue  # Built-in UI, covered by _RENDER_TAB_SCENE_STRUCTS.
        if root.rsplit(".", 1)[-1] in _RENDER_COPY_EXCLUDED_ADDONS:
            continue
        render_tab_packages.add(root)

    prop_names: List[str] = []
    for prop in scene.bl_rna.properties:
        if prop.type != 'POINTER' or not prop.is_runtime:
            continue
        group = getattr(scene, prop.identifier, None)
        module_name = type(group).__module__ if group is not None else ""
        if module_name and _addon_package_root(module_name) in render_tab_packages:
            prop_names.append(prop.identifier)
    return prop_names


def _copy_curve_mapping(src: bpy.types.CurveMapping, dst: bpy.types.CurveMapping) -> None:
    for src_curve, dst_curve in zip(src.curves, dst.curves):
        dst_points = dst_curve.points
        while len(dst_points) < len(src_curve.points):
            dst_points.new(0.0, 0.0)
        while len(dst_points) > len(src_curve.points):
            dst_points.remove(dst_points[-1])
        for src_point, dst_point in zip(src_curve.points, dst_points):
            dst_point.location = src_point.location
            dst_point.handle_type = src_point.handle_type
            dst_point.select = src_point.select
    dst.update()


def _copy_rna_struct(
    src: Any,
    dst: Any,
    path: str,
    failures: List[str],
    skip: Optional[Callable[[str], bool]] = None,
    depth: int = 0,
) -> int:
    """Copy every writable RNA property from `src` to `dst`, recursing into nested structs.

    ID datablock references are assigned, never recursed into. Returns the number of
    values written; paths that couldn't be written are appended to `failures`.
    """
    if depth > _RENDER_COPY_MAX_DEPTH:
        return 0

    copied = 0
    for prop in src.bl_rna.properties:
        prop_id = prop.identifier
        if prop_id == "rna_type" or (skip is not None and skip(prop_id)):
            continue
        prop_path = f"{path}.{prop_id}"

        try:
            src_value = getattr(src, prop_id)
        except Exception:
            continue

        if prop.type == 'POINTER':
            if isinstance(src_value, bpy.types.ID) or (src_value is None and not prop.is_readonly):
                if prop.is_readonly:
                    continue
                try:
                    setattr(dst, prop_id, src_value)
                    copied += 1
                except Exception:
                    failures.append(prop_path)
                continue
            dst_value = getattr(dst, prop_id, None)
            if src_value is None or dst_value is None:
                continue
            if isinstance(src_value, bpy.types.CurveMapping):
                copied += _copy_rna_struct(
                    src_value, dst_value, prop_path, failures,
                    skip=lambda name: name == "curves", depth=depth + 1,
                )
                try:
                    _copy_curve_mapping(src_value, dst_value)
                except Exception:
                    failures.append(f"{prop_path}.curves")
                continue
            copied += _copy_rna_struct(src_value, dst_value, prop_path, failures, depth=depth + 1)
            continue

        if prop.type == 'COLLECTION':
            dst_value = getattr(dst, prop_id, None)
            if dst_value is None or len(src_value) != len(dst_value):
                if len(src_value) or (dst_value is not None and len(dst_value)):
                    failures.append(prop_path)
                continue
            for index, (src_item, dst_item) in enumerate(zip(src_value, dst_value)):
                copied += _copy_rna_struct(
                    src_item, dst_item, f"{prop_path}[{index}]", failures, depth=depth + 1,
                )
            continue

        if prop.is_readonly:
            continue
        if prop.type == 'ENUM' and src_value == "":
            continue  # Unset in the source (no valid item), nothing to copy.
        try:
            dst_value = getattr(dst, prop_id)
            if getattr(prop, "is_array", False):
                unchanged = tuple(dst_value) == tuple(src_value)
            else:
                unchanged = dst_value == src_value
        except Exception:
            unchanged = False
        if unchanged:
            continue  # Avoid firing update callbacks for values that already match.
        try:
            setattr(dst, prop_id, src_value)
            copied += 1
        except Exception:
            failures.append(prop_path)

    return copied


def copy_render_settings_to_scenes(
    source: bpy.types.Scene,
    targets: List[bpy.types.Scene],
    include_output: bool = False,
) -> Dict[str, Any]:
    """Copy the Render Properties tab of `source` onto each scene in `targets`.

    Covers the render engine and everything Blender and render-engine add-ons draw in
    the Render tab (EEVEE, Cycles, Workbench, Grease Pencil, Hydra, Freestyle, motion
    blur, simplify, performance, bake, color management). Add-ons in
    `_RENDER_COPY_EXCLUDED_ADDONS` (Level Link) are skipped. With `include_output`,
    the Output tab settings stored on `scene.render` (resolution, frame rate, output
    path, file format, metadata, stereoscopy) are copied too.
    """
    def skip_render_prop(prop_id: str) -> bool:
        if include_output:
            return False
        return prop_id in _OUTPUT_TAB_RENDER_PROPS or prop_id.startswith(_OUTPUT_TAB_RENDER_PREFIXES)

    struct_names = [name for name in _RENDER_TAB_SCENE_STRUCTS if getattr(source, name, None) is not None]
    struct_names += _render_tab_addon_scene_props(source)

    copied_values = 0
    failures: List[str] = []
    updated_scenes = 0
    for target in targets:
        if target == source or target.library is not None:
            continue

        # Some values are only valid once others are set (engine-specific enums, view
        # transforms that depend on the display device), so copy twice and only report
        # what still fails on the second pass.
        for attempt in range(2):
            pass_failures: List[str] = []
            pass_copied = 0
            try:
                target.render.engine = source.render.engine
            except Exception:
                pass_failures.append("render.engine")
            for name in struct_names:
                src_struct = getattr(source, name, None)
                dst_struct = getattr(target, name, None)
                if src_struct is None or dst_struct is None:
                    continue
                pass_copied += _copy_rna_struct(
                    src_struct,
                    dst_struct,
                    name,
                    pass_failures,
                    skip=skip_render_prop if name == "render" else None,
                )

        copied_values += pass_copied
        failures.extend(f"{target.name}: {path}" for path in pass_failures)
        updated_scenes += 1

    return {
        'updated_scenes': updated_scenes,
        'copied_values': copied_values,
        'failures': failures,
        'structs': struct_names,
    }


# ---------------------------------------------------------------------------
# Collection utilities (instances, deep copies, decompose, merge, duplicate)
# ---------------------------------------------------------------------------

def get_instanced_collection(obj: Optional[bpy.types.Object]) -> Optional[bpy.types.Collection]:
    """Return the collection an object instances, or None."""
    if obj is None:
        return None
    if getattr(obj, "instance_type", None) == 'COLLECTION' and getattr(obj, "instance_collection", None):
        return obj.instance_collection
    return None


def get_selected_collection_instances(context: bpy.types.Context) -> List[bpy.types.Object]:
    """Selected collection-instance objects, with the active object first when it is one."""
    instances = [obj for obj in context.selected_objects if get_instanced_collection(obj) is not None]
    active = context.active_object
    if active is not None and active in instances:
        instances.remove(active)
        instances.insert(0, active)
    return instances


def _collection_tree(root: bpy.types.Collection) -> List[bpy.types.Collection]:
    """Return root and all nested child collections, each once, parents before children."""
    ordered: List[bpy.types.Collection] = []
    seen: Set[int] = set()
    stack = [root]
    while stack:
        coll = stack.pop(0)
        if coll.as_pointer() in seen:
            continue
        seen.add(coll.as_pointer())
        ordered.append(coll)
        stack.extend(coll.children)
    return ordered


def _collection_tree_objects(root: bpy.types.Collection) -> List[bpy.types.Object]:
    """All objects in a collection tree, each once."""
    objects: List[bpy.types.Object] = []
    seen: Set[int] = set()
    for coll in _collection_tree(root):
        for obj in coll.objects:
            if obj.as_pointer() not in seen:
                seen.add(obj.as_pointer())
                objects.append(obj)
    return objects


def _collection_tree_visibility(root: bpy.types.Collection) -> Tuple[Set[int], Set[int]]:
    """Return pointers of objects reachable through viewport-visible / render-visible collections.

    Mirrors how a collection instance draws: an object hidden by one of its
    collections inside the tree is only shown if another path reaches it.
    """
    visible_viewport: Set[int] = set()
    visible_render: Set[int] = set()

    def _walk(coll: bpy.types.Collection, hidden_vp: bool, hidden_render: bool, depth: int) -> None:
        if depth > 64:
            return
        hidden_vp = hidden_vp or coll.hide_viewport
        hidden_render = hidden_render or coll.hide_render
        for obj in coll.objects:
            if not hidden_vp:
                visible_viewport.add(obj.as_pointer())
            if not hidden_render:
                visible_render.add(obj.as_pointer())
        for child in coll.children:
            _walk(child, hidden_vp, hidden_render, depth + 1)

    _walk(root, False, False, 0)
    return visible_viewport, visible_render


def _remap_pointer_props(struct: Any, id_map: Dict[int, bpy.types.ID]) -> None:
    """Point any writable ID pointer on `struct` at its copy when the target was copied."""
    if struct is None:
        return
    for prop in struct.bl_rna.properties:
        if prop.type != 'POINTER' or prop.is_readonly or prop.identifier == "rna_type":
            continue
        try:
            value = getattr(struct, prop.identifier)
        except AttributeError:
            continue
        if isinstance(value, bpy.types.ID):
            replacement = id_map.get(value.as_pointer())
            if replacement is not None:
                try:
                    setattr(struct, prop.identifier, replacement)
                except (AttributeError, TypeError, ValueError, RuntimeError):
                    pass


def _remap_modifier_inputs(modifier: bpy.types.Modifier, id_map: Dict[int, bpy.types.ID]) -> None:
    """Remap object/collection inputs of a Geometry Nodes modifier (IDProperties or 5.2+ inputs)."""
    container = _modifier_input_container(modifier)
    if container is not None:
        for prop in container.bl_rna.properties:
            item = getattr(container, prop.identifier, None)
            value = getattr(item, "value", None) if item is not None else None
            if isinstance(value, bpy.types.ID):
                replacement = id_map.get(value.as_pointer())
                if replacement is not None:
                    try:
                        item.value = replacement
                    except (AttributeError, TypeError, ValueError, RuntimeError):
                        pass
        return
    for key in list(modifier.keys()):
        value = modifier[key]
        if isinstance(value, bpy.types.ID):
            replacement = id_map.get(value.as_pointer())
            if replacement is not None:
                modifier[key] = replacement


def _remap_animation_drivers(id_block: bpy.types.ID, id_map: Dict[int, bpy.types.ID]) -> None:
    anim = getattr(id_block, "animation_data", None)
    if anim is None:
        return
    for fcurve in anim.drivers:
        for variable in fcurve.driver.variables:
            for target in variable.targets:
                if target.id is not None:
                    replacement = id_map.get(target.id.as_pointer())
                    if replacement is not None:
                        target.id = replacement


def _remap_object_references(obj: bpy.types.Object, id_map: Dict[int, bpy.types.ID]) -> None:
    """Repoint an object's internal references (parent, modifiers, constraints, drivers, data)."""
    # Assigning `parent` through RNA resets the parent inverse; keep the original one.
    parent_inverse = obj.matrix_parent_inverse.copy()
    _remap_pointer_props(obj, id_map)
    obj.matrix_parent_inverse = parent_inverse
    for modifier in obj.modifiers:
        _remap_pointer_props(modifier, id_map)
        if modifier.type == 'NODES':
            _remap_modifier_inputs(modifier, id_map)
    for constraint in obj.constraints:
        _remap_pointer_props(constraint, id_map)
        for target in getattr(constraint, "targets", ()):
            _remap_pointer_props(target, id_map)
    _remap_animation_drivers(obj, id_map)
    if obj.data is not None:
        _remap_pointer_props(obj.data, id_map)
        _remap_animation_drivers(obj.data, id_map)


def _copy_objects(
    objects: List[bpy.types.Object],
    id_map: Dict[int, bpy.types.ID],
) -> List[Tuple[bpy.types.Object, bpy.types.Object]]:
    """Copy objects with their own object data (materials stay shared).

    Objects that shared data in the source keep sharing one copy. Internal
    references are remapped through `id_map`, which is updated in place.
    Returns (source, copy) pairs; copies are not linked to any collection.
    """
    pairs: List[Tuple[bpy.types.Object, bpy.types.Object]] = []
    for src in objects:
        dst = src.copy()
        if src.data is not None:
            data_copy = id_map.get(src.data.as_pointer())
            if data_copy is None:
                data_copy = src.data.copy()
                id_map[src.data.as_pointer()] = data_copy
            dst.data = data_copy
        id_map[src.as_pointer()] = dst
        pairs.append((src, dst))
    for _src, dst in pairs:
        _remap_object_references(dst, id_map)
    return pairs


def _copy_collection_shell(src: bpy.types.Collection, name: Optional[str] = None) -> bpy.types.Collection:
    """Copy a collection's settings (offset, flags, color, custom props) without its contents."""
    dst = src.copy()
    for obj in list(dst.objects):
        dst.objects.unlink(obj)
    for child in list(dst.children):
        dst.children.unlink(child)
    if name:
        dst.name = name
    return dst


def deep_copy_collection(
    src: bpy.types.Collection,
    name: Optional[str] = None,
) -> Tuple[bpy.types.Collection, Dict[int, bpy.types.ID], List[Tuple[bpy.types.Object, bpy.types.Object]]]:
    """Fully duplicate a collection tree: child collections, objects and object data.

    The copy is independent of the source (editing it never changes the
    original) and is not linked into any scene. Returns (root copy, id_map,
    object pairs).
    """
    id_map: Dict[int, bpy.types.ID] = {}
    tree = _collection_tree(src)
    for coll in tree:
        id_map[coll.as_pointer()] = _copy_collection_shell(coll, name if coll == src else None)

    pairs = _copy_objects(_collection_tree_objects(src), id_map)

    for coll in tree:
        dst_coll = id_map[coll.as_pointer()]
        for obj in coll.objects:
            dst_coll.objects.link(id_map[obj.as_pointer()])
        for child in coll.children:
            dst_coll.children.link(id_map[child.as_pointer()])
        _remap_pointer_props(dst_coll, id_map)
    return id_map[src.as_pointer()], id_map, pairs


def get_collection_parents(coll: bpy.types.Collection) -> List[bpy.types.Collection]:
    """Collections (including scene master collections) that have `coll` as a direct child."""
    parents: List[bpy.types.Collection] = []
    for scene in bpy.data.scenes:
        if any(child == coll for child in scene.collection.children):
            parents.append(scene.collection)
    for candidate in bpy.data.collections:
        if any(child == coll for child in candidate.children):
            parents.append(candidate)
    return parents


def _find_layer_collection(layer_coll: bpy.types.LayerCollection, coll: bpy.types.Collection):
    if layer_coll.collection == coll:
        return layer_coll
    for child in layer_coll.children:
        found = _find_layer_collection(child, coll)
        if found is not None:
            return found
    return None


def _copy_layer_collection_state(src: bpy.types.Collection, dst: bpy.types.Collection) -> None:
    """Match exclude/hide/holdout/indirect-only of `dst` to `src` in every view layer."""
    for scene in bpy.data.scenes:
        for view_layer in scene.view_layers:
            src_layer = _find_layer_collection(view_layer.layer_collection, src)
            dst_layer = _find_layer_collection(view_layer.layer_collection, dst)
            if src_layer is None or dst_layer is None:
                continue
            for attr in ("exclude", "hide_viewport", "holdout", "indirect_only"):
                try:
                    setattr(dst_layer, attr, getattr(src_layer, attr))
                except (AttributeError, TypeError, RuntimeError):
                    pass


def link_collection_like(src: bpy.types.Collection, dst: bpy.types.Collection) -> int:
    """Link `dst` under the same parents as `src` and mirror its view-layer state."""
    parents = get_collection_parents(src)
    for parent in parents:
        if not any(child == dst for child in parent.children):
            parent.children.link(dst)
    _copy_layer_collection_state(src, dst)
    return len(parents)


def unique_collection_name(base: str) -> str:
    """Return `base` if unused, else the first free `base.001`-style name."""
    if base not in bpy.data.collections:
        return base
    index = 1
    while f"{base}.{index:03d}" in bpy.data.collections:
        index += 1
    return f"{base}.{index:03d}"


def _detach_children_keep_transform(
    obj: bpy.types.Object,
    new_parent: Optional[bpy.types.Object] = None,
) -> None:
    """Move obj's children to `new_parent` (or no parent) without moving them visually."""
    parent_world = new_parent.matrix_world.copy() if new_parent is not None else None
    for child in list(obj.children):
        _set_world_transform(child, child.matrix_world.copy(), new_parent, parent_world)


def _can_bake_into_data(obj: bpy.types.Object) -> bool:
    """True when obj's data is its own and can take a transform (mesh, curve, ...)."""
    data = obj.data
    return data is not None and data.library is None and data.users == 1 and hasattr(data, "transform")


def _transform_data(data: bpy.types.ID, matrix: Matrix) -> None:
    """Transform object data, shape keys included where the data type has them."""
    try:
        data.transform(matrix, shape_keys=True)
    except TypeError:
        data.transform(matrix)


def _is_identity(matrix: Matrix, tolerance: float = 1e-5) -> bool:
    identity = Matrix.Identity(4)
    return all(abs(matrix[r][c] - identity[r][c]) <= tolerance for r in range(4) for c in range(4))


def _set_world_transform(
    obj: bpy.types.Object,
    world: Matrix,
    parent: Optional[bpy.types.Object],
    parent_world: Optional[Matrix],
    children: Optional[List[bpy.types.Object]] = None,
    allow_bake: bool = False,
) -> bool:
    """Parent `obj` and place it at exactly `world`, without relying on matrix_world.

    `parent_world` must be the parent's true world matrix; fresh copies still
    carry their source's matrix_world until the next depsgraph update.

    Loc/rot/scale cannot hold shear (non-uniform scale over rotation). Any
    shear left over goes into the parent inverse when there is a parent, or is
    baked into the object's own data when `allow_bake` is set (with `children`
    compensated). Returns False only when the placement had to be approximated.
    """
    obj.parent = parent
    obj.matrix_parent_inverse.identity()
    has_parent = parent is not None and parent_world is not None
    local = parent_world.inverted_safe() @ world if has_parent else world.copy()

    loc, rot, scale = local.decompose()
    basis = Matrix.LocRotScale(loc, rot, scale)
    obj.matrix_basis = basis
    residual = basis.inverted_safe() @ local
    if _is_identity(residual):
        return True

    if has_parent:
        # world = parent_world @ parent_inverse @ basis
        obj.matrix_parent_inverse = local @ basis.inverted_safe()
        return True

    data = obj.data
    if allow_bake and _can_bake_into_data(obj):
        _transform_data(data, residual)
        for child in children or ():
            child.matrix_parent_inverse = residual @ child.matrix_parent_inverse
        return True
    return False


def _place_root_copies(
    pairs: List[Tuple[bpy.types.Object, bpy.types.Object]],
    id_map: Dict[int, bpy.types.ID],
    transform: Matrix,
    new_parent: Optional[bpy.types.Object] = None,
    new_parent_world: Optional[Matrix] = None,
) -> int:
    """Move copies whose parent was not copied so they sit at `transform @ source world`.

    Children of copied objects keep their local transforms and follow their
    (copied) parents automatically. Returns how many placements were approximate.
    """
    approximate = 0
    for src, dst in pairs:
        parent = src.parent
        if parent is not None and parent.as_pointer() in id_map:
            continue
        children = [child for _s, child in pairs if child.parent == dst]
        if not _set_world_transform(
            dst, transform @ src.matrix_world, new_parent, new_parent_world, children, allow_bake=True
        ):
            approximate += 1
    return approximate


def _instance_space(instancer: bpy.types.Object) -> Matrix:
    """World matrix applied to an instanced collection's contents."""
    coll = instancer.instance_collection
    return instancer.matrix_world @ Matrix.Translation(-Vector(coll.instance_offset))


def _decompose_into(
    coll: bpy.types.Collection,
    transform: Matrix,
    target_collections: List[bpy.types.Collection],
    new_parent: Optional[bpy.types.Object],
    new_parent_world: Optional[Matrix],
    recursive: bool,
    depth: int,
) -> Tuple[List[bpy.types.Object], int]:
    """Copy `coll`'s contents into `target_collections`, placed by `transform`.

    Root copies are parented to `new_parent` (whose true world matrix is
    `new_parent_world`). Returns (every object created, nested ones included;
    number of placements that had to be approximated).
    """
    objects = _collection_tree_objects(coll)
    visible_vp, visible_render = _collection_tree_visibility(coll)
    copied_ptrs = {obj.as_pointer() for obj in objects}

    # Nested instances are expanded in place of the instancer when recursing; the
    # instancer is only kept (as a plain empty) when other copied objects hang off it.
    nested: List[bpy.types.Object] = []
    if recursive and depth < 32:
        nested = [obj for obj in objects if get_instanced_collection(obj) is not None]
    drop = {
        obj.as_pointer()
        for obj in nested
        if not any(child.as_pointer() in copied_ptrs for child in obj.children)
    }

    id_map: Dict[int, bpy.types.ID] = {}
    pairs = _copy_objects([obj for obj in objects if obj.as_pointer() not in drop], id_map)
    approximate = _place_root_copies(pairs, id_map, transform, new_parent, new_parent_world)

    created: List[bpy.types.Object] = []
    for src, dst in pairs:
        for target in target_collections:
            target.objects.link(dst)
        dst.hide_viewport = src.hide_viewport or src.as_pointer() not in visible_vp
        dst.hide_render = src.hide_render or src.as_pointer() not in visible_render
        if recursive and src in nested:
            dst.instance_type = 'NONE'
            dst.instance_collection = None
        created.append(dst)

    for src in nested:
        kept = id_map.get(src.as_pointer())
        if kept is not None:
            # The kept empty sits exactly at transform @ source world.
            nested_parent, nested_parent_world = kept, transform @ src.matrix_world
        else:
            nested_parent, nested_parent_world = new_parent, new_parent_world
        nested_created, nested_approximate = _decompose_into(
            src.instance_collection,
            transform @ _instance_space(src),
            target_collections,
            nested_parent,
            nested_parent_world,
            recursive,
            depth + 1,
        )
        created.extend(nested_created)
        approximate += nested_approximate
    return created, approximate


def decompose_collection_instance(
    instancer: bpy.types.Object,
    recursive: bool = True,
) -> Tuple[List[bpy.types.Object], int]:
    """Replace a collection instance with editable copies of its contents, in place.

    The instanced collection itself is left untouched. Copies get their own
    object data, land in the instancer's collections at exactly the same world
    transforms, and keep the instancer's parent. The instancer is removed.
    Returns (created objects, number of approximated placements).
    """
    coll = get_instanced_collection(instancer)
    if coll is None:
        return [], 0
    target_collections = list(instancer.users_collection)
    created, approximate = _decompose_into(
        coll,
        _instance_space(instancer),
        target_collections,
        instancer.parent,
        instancer.parent.matrix_world.copy() if instancer.parent else None,
        recursive,
        0,
    )
    _detach_children_keep_transform(instancer, instancer.parent)
    bpy.data.objects.remove(instancer)
    return created, approximate


def merge_collection_instances(
    instancers: List[bpy.types.Object],
    name: str,
) -> Tuple[Optional[bpy.types.Collection], int]:
    """Merge the collections of several instances into one new collection.

    The first instancer is kept and now instances the merged collection; the
    others are removed. Contents are copied (sources untouched) and transformed
    so the result looks identical. Returns (new collection, number of
    approximated placements).
    """
    instancers = [obj for obj in instancers if get_instanced_collection(obj) is not None]
    if len(instancers) < 2:
        return None, 0

    keeper = instancers[0]
    keeper_coll = keeper.instance_collection
    keeper_offset = Vector(keeper_coll.instance_offset)
    keeper_space_inv = (keeper.matrix_world @ Matrix.Translation(-keeper_offset)).inverted_safe()

    merged = bpy.data.collections.new(name or unique_collection_name(f"{keeper_coll.name}_merged"))
    merged.instance_offset = keeper_offset
    approximate = 0

    for instancer in instancers:
        source = instancer.instance_collection
        copy_root, id_map, pairs = deep_copy_collection(source)
        transform = keeper_space_inv @ _instance_space(instancer)
        approximate += _place_root_copies(pairs, id_map, transform)
        for obj in list(copy_root.objects):
            merged.objects.link(obj)
        for child in list(copy_root.children):
            merged.children.link(child)
        bpy.data.collections.remove(copy_root)

    link_collection_like(keeper_coll, merged)
    keeper.instance_collection = merged
    for instancer in instancers[1:]:
        _detach_children_keep_transform(instancer, keeper)
        bpy.data.objects.remove(instancer)
    return merged, approximate


def duplicate_instanced_collection(
    instancers: List[bpy.types.Object],
    name: str,
) -> Optional[bpy.types.Collection]:
    """Deep-copy the first instancer's collection and point matching instancers at it.

    Only the given instancers that use that same collection are switched; all
    other instances in the file keep the original.
    """
    instancers = [obj for obj in instancers if get_instanced_collection(obj) is not None]
    if not instancers:
        return None
    source = instancers[0].instance_collection
    new_coll, _id_map, _pairs = deep_copy_collection(source, name or unique_collection_name(source.name))
    link_collection_like(source, new_coll)
    for instancer in instancers:
        if instancer.instance_collection == source:
            instancer.instance_collection = new_coll
    return new_coll


def get_object_collection(obj: bpy.types.Object) -> Optional[bpy.types.Collection]:
    """The first real (non scene-master) collection that directly holds `obj`."""
    masters = {scene.collection.as_pointer() for scene in bpy.data.scenes}
    for coll in obj.users_collection:
        if coll.as_pointer() not in masters:
            return coll
    return None


_POINT_OBJECT_TYPES = {'EMPTY', 'LIGHT', 'CAMERA', 'SPEAKER', 'LIGHT_PROBE'}


def _collect_collection_points(
    coll: bpy.types.Collection,
    depsgraph: bpy.types.Depsgraph,
    transform: Matrix,
    points: List[Vector],
    depth: int,
) -> None:
    """Add bounding points of what `coll` draws (viewport-visible parts, nested instances
    included) to `points`, in the space given by `transform`."""
    visible, _ = _collection_tree_visibility(coll)
    for obj in _collection_tree_objects(coll):
        if obj.as_pointer() not in visible or obj.hide_viewport:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        matrix = transform @ evaluated.matrix_world
        nested = get_instanced_collection(obj)
        if nested is not None and depth < 16:
            before = len(points)
            nested_space = matrix @ Matrix.Translation(-Vector(nested.instance_offset))
            _collect_collection_points(nested, depsgraph, nested_space, points, depth + 1)
            if len(points) > before:
                continue
        if obj.type in _POINT_OBJECT_TYPES:
            points.append(matrix.translation.copy())
            continue
        points.extend(matrix @ Vector(corner) for corner in evaluated.bound_box)


def _collection_world_bounds(
    coll: bpy.types.Collection,
    depsgraph: bpy.types.Depsgraph,
) -> Optional[Tuple[Vector, Vector]]:
    """(min, max) of everything a collection tree draws, modifiers and nested instances
    included, in collection space (= world space for objects placed directly in the scene).

    Works for collections excluded from the view layer as long as something instances
    them, since the depsgraph still evaluates their objects for the instance.
    """
    points: List[Vector] = []
    _collect_collection_points(coll, depsgraph, Matrix.Identity(4), points, 0)
    if not points:
        return None
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi


def _iter_layer_collections(layer_coll: bpy.types.LayerCollection, coll: bpy.types.Collection):
    """Every layer collection for `coll` (a collection linked twice has two)."""
    if layer_coll.collection == coll:
        yield layer_coll
    for child in layer_coll.children:
        yield from _iter_layer_collections(child, coll)


def get_collection_instancers(coll: bpy.types.Collection) -> List[bpy.types.Object]:
    return [obj for obj in bpy.data.objects if get_instanced_collection(obj) == coll]


def replace_collection_with_instance(
    context: bpy.types.Context,
    coll: bpy.types.Collection,
    pivot: str = 'BOTTOM_CENTER',
) -> Tuple[bpy.types.Object, bool]:
    """Unload `coll` from the scene and put an instance of it in exactly the same place.

    The collection is excluded in every view layer of the scene (it stays in the
    outliner, so it can be re-enabled or edited). The instance empty goes into
    the collection's parent. `pivot` sets the instance offset and empty location:
    'BOTTOM_CENTER', 'CENTER', 'ACTIVE', 'CURSOR' or 'KEEP' (existing offset).
    If other objects already instance the collection, its offset is kept so they
    don't move. Returns (instance object, offset_was_forced_to_keep).
    """
    scene = context.scene
    forced_keep = False
    if pivot != 'KEEP' and get_collection_instancers(coll):
        pivot, forced_keep = 'KEEP', True

    offset = Vector(coll.instance_offset)
    if pivot == 'CURSOR':
        offset = scene.cursor.location.copy()
    elif pivot == 'ACTIVE' and context.active_object is not None:
        offset = context.active_object.matrix_world.translation.copy()
    elif pivot in {'BOTTOM_CENTER', 'CENTER', 'ACTIVE'}:
        bounds = _collection_world_bounds(coll, context.evaluated_depsgraph_get())
        if bounds is not None:
            lo, hi = bounds
            offset = (lo + hi) * 0.5
            if pivot != 'CENTER':
                offset.z = lo.z
    coll.instance_offset = offset
    return instance_collection_in_place(scene, coll), forced_keep


def instance_collection_in_place(scene: bpy.types.Scene, coll: bpy.types.Collection) -> bpy.types.Object:
    """Exclude `coll` in every view layer of `scene` and add an instance of it that draws
    exactly where the collection was, keeping its instance offset.

    The instance empty goes into the collection's parent in that scene (or the scene
    collection) and sits at the instance offset.
    """
    scene_tree = {scene.collection.as_pointer()}
    scene_tree.update(c.as_pointer() for c in scene.collection.children_recursive)
    parents = [p for p in get_collection_parents(coll) if p.as_pointer() in scene_tree]
    target = parents[0] if parents else scene.collection

    instancer = bpy.data.objects.new(coll.name, None)
    instancer.instance_type = 'COLLECTION'
    instancer.instance_collection = coll
    instancer.empty_display_size = 0.5
    instancer.location = Vector(coll.instance_offset)  # draws at location - offset + source = source
    target.objects.link(instancer)

    for view_layer in scene.view_layers:
        for layer_coll in _iter_layer_collections(view_layer.layer_collection, coll):
            layer_coll.exclude = True
    return instancer


_TRANSFORM_PATHS = {
    "location", "rotation_euler", "rotation_quaternion", "rotation_axis_angle", "scale",
    "delta_location", "delta_rotation_euler", "delta_rotation_quaternion", "delta_scale",
    "matrix_world", "matrix_basis",
}


def _has_animated_transform(obj: bpy.types.Object) -> bool:
    """True when keyframes or drivers drive the object's transform (and would undo edits)."""
    anim = obj.animation_data
    if anim is None:
        return False
    paths = [driver.data_path for driver in anim.drivers]
    action = anim.action
    if action is not None:
        fcurves = None
        try:
            from bpy_extras.anim_utils import action_get_channelbag_for_slot
            channelbag = action_get_channelbag_for_slot(action, getattr(anim, "action_slot", None))
            fcurves = channelbag.fcurves if channelbag is not None else None
        except (ImportError, AttributeError, TypeError):
            fcurves = getattr(action, "fcurves", None)
        if fcurves is not None:
            paths.extend(fc.data_path for fc in fcurves)
    return any(path in _TRANSFORM_PATHS for path in paths)


def collection_anchor_point(
    coll: bpy.types.Collection,
    depsgraph: bpy.types.Depsgraph,
    mode: str = 'BOTTOM_CENTER',
) -> Optional[Vector]:
    """Anchor in collection space: 'BOTTOM_CENTER' or 'CENTER' of the bounds, or 'ORIGIN'."""
    if mode == 'ORIGIN':
        return Vector((0.0, 0.0, 0.0))
    bounds = _collection_world_bounds(coll, depsgraph)
    if bounds is None:
        return None
    lo, hi = bounds
    anchor = (lo + hi) * 0.5
    if mode == 'BOTTOM_CENTER':
        anchor.z = lo.z
    return anchor


def set_collection_anchor(coll: bpy.types.Collection, anchor: Vector) -> Dict[str, int]:
    """Move `coll`'s instance offset (its anchor) to `anchor`, in collection space, without
    anything moving: every instance of the collection in the file is shifted to compensate.

    An instance draws at instancer.matrix_world @ T(-offset), so with d = new - old offset
    the instancer needs matrix_world @ T(d). That is location += basis_3x3 @ d, which is
    exact and independent of parenting. Children of an instancer get T(-d) folded into
    their parent inverse so they stay put too.

    Returns counts: 'instances' compensated, 'linked' (library instancers that could not be
    edited and will appear to move), 'animated' (transform driven by keys/drivers).
    """
    delta = Vector(anchor) - Vector(coll.instance_offset)
    result = {"instances": 0, "linked": 0, "animated": 0}
    if delta.length == 0.0:
        result["instances"] = len(get_collection_instancers(coll))
        return result

    correction = Matrix.Translation(-delta)
    for instancer in get_collection_instancers(coll):
        if instancer.library is not None:
            result["linked"] += 1
            continue
        if _has_animated_transform(instancer):
            result["animated"] += 1
        instancer.location = instancer.location + instancer.matrix_basis.to_3x3() @ delta
        for child in instancer.children:
            if child.library is None:
                child.matrix_parent_inverse = correction @ child.matrix_parent_inverse
        result["instances"] += 1
    coll.instance_offset = anchor
    return result


# ---------------------------------------------------------------------------
# Apply an instance's rotation/scale to its collection.
#
# An instance draws its collection's contents at W @ T(-o) @ contents (W the
# instancer's world matrix, o the instance offset). With A the rotation/scale to
# apply, the contents are transformed by K = T(o) @ A @ T(-o) (about the anchor,
# so o stays put) and every instancer gets W' = W @ A^-1:
#     W @ A^-1 @ T(-o) @ K = W @ A^-1 @ T(-o) @ T(o) @ A @ T(-o) = W @ T(-o)
# so every instance draws exactly as before. The instance A came from ends up
# with no rotation/scale. A child collection c in the tree gets o_c' = K @ o_c;
# its instances need the same W @ A^-1, since T(-o_c) @ K^-1 @ T(K @ o_c) = A^-1.
# W @ A^-1 is a change of matrix_basis (basis @ A^-1), so it is exact whatever
# the instancer is parented to.
# ---------------------------------------------------------------------------

def instance_apply_matrix(instancer: bpy.types.Object, rotation: bool, scale: bool) -> Matrix:
    """The rotation and/or scale of an instance's own transform (its matrix_basis, like
    Ctrl+A), as a 4x4 linear transform to apply to its collection."""
    basis = instancer.matrix_basis
    if rotation and scale:
        return basis.to_3x3().to_4x4()
    _loc, rot, size = basis.decompose()
    if rotation:
        return rot.to_matrix().to_4x4()
    if scale:
        return Matrix.Diagonal(size).to_4x4()
    return Matrix.Identity(4)


def _is_loc_rot_scale(matrix: Matrix) -> bool:
    """True when `matrix` is exactly loc/rot/scale (no shear), as _set_world_transform sees it."""
    loc, rot, scale = matrix.decompose()
    return _is_identity(Matrix.LocRotScale(loc, rot, scale).inverted_safe() @ matrix)


def _has_constraints(obj: bpy.types.Object) -> bool:
    return any(con.enabled and con.influence > 0.0 for con in obj.constraints)


def _tree_instancers(tree: List[bpy.types.Collection]) -> List[bpy.types.Object]:
    """Every object instancing a collection of `tree`."""
    tree_ptrs = {c.as_pointer() for c in tree}
    return [
        obj for obj in bpy.data.objects
        if (nested := get_instanced_collection(obj)) is not None and nested.as_pointer() in tree_ptrs
    ]


def apply_collection_transform_problems(
    coll: bpy.types.Collection,
    apply: Matrix,
    active: Optional[bpy.types.Object] = None,
) -> List[str]:
    """Reasons `apply` cannot be applied to `coll` without something moving (empty when it can).

    Nothing is changed. Checked: the collection's objects can be transformed as one block
    (none linked, shared with or parented to objects outside, animated or constrained at the
    top level), every top-level object can hold its new transform (or take shear into its
    own data), and every instance can hold the inverse (shear needs a parent to absorb it).
    """
    if coll.library is not None or coll.override_library is not None:
        return ["the collection is linked from a library"]
    if abs(apply.to_3x3().determinant()) < 1e-12:
        return ["the instance has zero scale"]

    offset = Vector(coll.instance_offset)
    transform = Matrix.Translation(offset) @ apply @ Matrix.Translation(-offset)
    inverse = apply.inverted()
    tree = _collection_tree(coll)
    tree_ptrs = {c.as_pointer() for c in tree}
    objects = _collection_tree_objects(coll)
    object_ptrs = {obj.as_pointer() for obj in objects}

    problems: List[str] = []
    for obj in objects:
        if obj.library is not None:
            problems.append(f"object '{obj.name}' is linked from a library")
            continue
        outside = [c for c in obj.users_collection if c.as_pointer() not in tree_ptrs]
        if outside:
            problems.append(f"object '{obj.name}' is also in collection '{outside[0].name}'")
        if obj.parent is not None and obj.parent.as_pointer() not in object_ptrs:
            problems.append(f"object '{obj.name}' is parented to '{obj.parent.name}' outside the collection")
        stray = [child for child in obj.children if child.as_pointer() not in object_ptrs]
        if stray:
            problems.append(f"object '{stray[0].name}' outside the collection is parented to '{obj.name}'")
        nested = get_instanced_collection(obj)
        if nested is not None and nested.as_pointer() in tree_ptrs:
            problems.append(f"object '{obj.name}' instances '{nested.name}', which is inside the collection")
        if obj.parent is not None:
            continue  # follows its parent
        if _has_animated_transform(obj):
            problems.append(f"object '{obj.name}' has an animated transform")
        if _has_constraints(obj):
            problems.append(f"object '{obj.name}' has constraints")
        if not _is_loc_rot_scale(transform @ obj.matrix_basis) and not _can_bake_into_data(obj):
            problems.append(
                f"object '{obj.name}' would need shear (non-uniform scale over its rotation) "
                f"and its data can't take it"
            )

    for instancer in _tree_instancers(tree):
        if instancer.as_pointer() in object_ptrs:
            continue  # reported above
        if instancer.library is not None:
            problems.append(f"instance '{instancer.name}' is linked from a library")
            continue
        if instancer.parent is None and not _is_loc_rot_scale(instancer.matrix_basis @ inverse):
            if instancer == active:
                problems.append(
                    "rotation can't be applied on its own while the instance has non-uniform "
                    "scale; apply rotation and scale together"
                )
            else:
                problems.append(
                    f"instance '{instancer.name}' would need shear to stay in place (its "
                    f"rotation/scale differs non-uniformly from the active instance's)"
                )
    return problems


def _post_multiply_basis(obj: bpy.types.Object, matrix: Matrix) -> None:
    """Make obj's world matrix W @ matrix, exactly when it is representable: its basis takes
    the loc/rot/scale part and its parent inverse (if parented) any leftover shear.
    Children keep their world transforms."""
    old_basis = obj.matrix_basis.copy()
    target = old_basis @ matrix
    loc, rot, scale = target.decompose()
    new_basis = Matrix.LocRotScale(loc, rot, scale)
    if obj.parent is not None and not _is_identity(new_basis.inverted_safe() @ target):
        # W = Pw @ Pinv @ basis: Pinv' @ new_basis must equal Pinv @ target.
        obj.matrix_parent_inverse = obj.matrix_parent_inverse @ target @ new_basis.inverted_safe()
        change = matrix
    elif obj.parent is not None:
        change = matrix
    else:
        change = old_basis.inverted_safe() @ new_basis
    obj.matrix_basis = new_basis
    undo = change.inverted_safe()
    for child in obj.children:
        if child.library is None:
            child.matrix_parent_inverse = undo @ child.matrix_parent_inverse


def apply_collection_transform(coll: bpy.types.Collection, apply: Matrix) -> Dict[str, int]:
    """Apply the linear transform `apply` (rotation/scale) to `coll`'s contents about its
    anchor, compensating every instance of the collection (and of its child collections) in
    the file so that nothing moves. Check `apply_collection_transform_problems` first.

    Returns counts: 'instances' adjusted, 'animated' instances whose keys/drivers were left
    alone, 'baked' objects whose shear went into their own data.
    """
    offset = Vector(coll.instance_offset)
    transform = Matrix.Translation(offset) @ apply @ Matrix.Translation(-offset)
    inverse = apply.inverted()
    tree = _collection_tree(coll)
    objects = _collection_tree_objects(coll)
    object_ptrs = {obj.as_pointer() for obj in objects}
    instancers = [obj for obj in _tree_instancers(tree) if obj.as_pointer() not in object_ptrs]

    result = {"instances": 0, "animated": 0, "baked": 0}
    for obj in objects:
        if obj.parent is not None:
            continue  # follows its parent
        target = transform @ obj.matrix_basis
        if not _is_loc_rot_scale(target):
            result["baked"] += 1
        _set_world_transform(obj, target, None, None, list(obj.children), allow_bake=True)

    for child in tree:
        child.instance_offset = transform @ Vector(child.instance_offset)

    for instancer in instancers:
        if _has_animated_transform(instancer):
            result["animated"] += 1
        _post_multiply_basis(instancer, inverse)
        result["instances"] += 1
    return result


# ---------------------------------------------------------------------------
# Collection stage: a dedicated scene where every asset collection sits in its
# own spot, so collections can be edited in place.
#
# A collection's objects are shared by every scene and file that uses it, so a
# collection is put in its spot by moving its contents there and moving its
# instance offset by the same amount. Instances anywhere (any scene, any file
# linking the collection) draw at instancer @ T(-offset) @ contents, which does
# not change, so nothing moves outside the stage.
# ---------------------------------------------------------------------------

STAGE_SCENE_KEY = "custom_utils_collection_stage"
STAGE_SETTINGS_KEY = "custom_utils_stage_settings"
STAGE_RETURN_SCENE_KEY = "custom_utils_stage_return_scene"
STAGE_LABELS_KEY = "custom_utils_stage_labels"
STAGE_LABEL_TARGET_KEY = "custom_utils_stage_label_for"
STAGE_DEFAULT_NAME = "Collection Stage"

STAGE_DEFAULT_SETTINGS: Dict[str, Any] = {
    "spacing": 2.0,
    "snap": 1.0,
    "row_width": 0.0,
    "sort": 'NAME',
    "labels": True,
    "label_size": 0.5,
}

_LOCATION_PATHS = {"location", "delta_location", "matrix_world", "matrix_basis"}
_LABEL_CHAR_WIDTH = 0.6  # rough width of one label character, as a fraction of text size


def get_stage_scene() -> Optional[bpy.types.Scene]:
    """The file's collection stage scene, if it has one."""
    for scene in bpy.data.scenes:
        if scene.get(STAGE_SCENE_KEY):
            return scene
    return None


def get_stage_settings(
    stage: Optional[bpy.types.Scene], defaults: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Layout settings stored on the stage (`defaults`, else built-in defaults, for any missing value)."""
    settings = dict(STAGE_DEFAULT_SETTINGS)
    if defaults:
        settings.update({key: value for key, value in defaults.items() if key in settings})
    stored = stage.get(STAGE_SETTINGS_KEY) if stage is not None else None
    if stored is not None:
        for key in settings:
            if key in stored:
                settings[key] = stored[key]
    return settings


def _ensure_stage_scene(context: bpy.types.Context, name: str) -> bpy.types.Scene:
    stage = get_stage_scene()
    if stage is None:
        stage = bpy.data.scenes.new(name or STAGE_DEFAULT_NAME)
        stage[STAGE_SCENE_KEY] = True
        if context.scene is not None:
            stage.world = context.scene.world
            stage.unit_settings.system = context.scene.unit_settings.system
            stage.unit_settings.scale_length = context.scene.unit_settings.scale_length
    return stage


def _stage_labels_collection(stage: bpy.types.Scene, create: bool) -> Optional[bpy.types.Collection]:
    for child in stage.collection.children:
        if child.get(STAGE_LABELS_KEY):
            return child
    if not create:
        return None
    labels = bpy.data.collections.new("Stage Labels")
    labels[STAGE_LABELS_KEY] = True
    labels.hide_select = True
    stage.collection.children.link(labels)
    return labels


def get_stage_collections(stage: Optional[bpy.types.Scene]) -> List[bpy.types.Collection]:
    """Collections placed on the stage (direct children of its scene collection)."""
    if stage is None:
        return []
    return [child for child in stage.collection.children if not child.get(STAGE_LABELS_KEY)]


def find_stage_candidates() -> List[bpy.types.Collection]:
    """Local collections used as assets: instanced by any object, or marked as an asset."""
    instanced = {
        obj.instance_collection.as_pointer()
        for obj in bpy.data.objects
        if get_instanced_collection(obj) is not None
    }
    return [
        coll for coll in bpy.data.collections
        if coll.library is None
        and coll.override_library is None
        and not coll.get(STAGE_LABELS_KEY)
        and (coll.as_pointer() in instanced or coll.asset_data is not None)
    ]


def _has_animated_location(obj: bpy.types.Object) -> bool:
    anim = obj.animation_data
    if anim is None:
        return False
    paths = [driver.data_path for driver in anim.drivers]
    action = anim.action
    if action is not None:
        fcurves = None
        try:
            from bpy_extras.anim_utils import action_get_channelbag_for_slot
            channelbag = action_get_channelbag_for_slot(action, getattr(anim, "action_slot", None))
            fcurves = channelbag.fcurves if channelbag is not None else None
        except (ImportError, AttributeError, TypeError):
            fcurves = getattr(action, "fcurves", None)
        if fcurves is not None:
            paths.extend(fc.data_path for fc in fcurves)
    return any(path in _LOCATION_PATHS for path in paths)


def _stage_move_problem(coll: bpy.types.Collection) -> Optional[str]:
    """Why the collection's contents cannot be moved as one rigid block, or None."""
    if coll.library is not None or coll.override_library is not None:
        return "linked from a library"
    tree_ptrs = {c.as_pointer() for c in _collection_tree(coll)}
    objects = _collection_tree_objects(coll)
    object_ptrs = {obj.as_pointer() for obj in objects}
    for obj in objects:
        if obj.library is not None:
            return f"object '{obj.name}' is linked from a library"
        outside = [c for c in obj.users_collection if c.as_pointer() not in tree_ptrs]
        if outside:
            return f"object '{obj.name}' is also in '{outside[0].name}'"
        if obj.parent is not None and obj.parent.as_pointer() not in object_ptrs:
            return f"object '{obj.name}' is parented to '{obj.parent.name}' outside the collection"
        if obj.parent is None and _has_animated_location(obj):
            return f"object '{obj.name}' has an animated location"
    return None


def _layer_tree_shows(layer_coll, coll: bpy.types.Collection, excluded: bool = False) -> bool:
    """True when `coll` is linked somewhere under `layer_coll` and not excluded there."""
    excluded = excluded or layer_coll.exclude
    if layer_coll.collection == coll and not excluded:
        return True
    return any(_layer_tree_shows(child, coll, excluded) for child in layer_coll.children)


def _layer_tree_shows_part(layer_coll, root: bpy.types.Collection, tree_ptrs: Set[int], excluded: bool = False) -> Optional[str]:
    """Name of a collection in `root`'s tree that is shown without going through `root`."""
    if layer_coll.collection == root:
        return None
    excluded = excluded or layer_coll.exclude
    if not excluded and layer_coll.collection.as_pointer() in tree_ptrs:
        return layer_coll.collection.name
    for child in layer_coll.children:
        found = _layer_tree_shows_part(child, root, tree_ptrs, excluded)
        if found:
            return found
    return None


def _scenes_showing(coll: bpy.types.Collection, skip: bpy.types.Scene) -> List[bpy.types.Scene]:
    """Scenes other than `skip` where the collection is linked and visible (not excluded)."""
    return [
        scene for scene in bpy.data.scenes
        if scene != skip
        and any(_layer_tree_shows(vl.layer_collection, coll) for vl in scene.view_layers)
    ]


def _direct_use_problem(coll: bpy.types.Collection, stage: bpy.types.Scene) -> Optional[str]:
    """A child collection shown on its own in another scene would move there; report it."""
    tree_ptrs = {c.as_pointer() for c in _collection_tree(coll)} - {coll.as_pointer()}
    if not tree_ptrs:
        return None
    for scene in bpy.data.scenes:
        if scene == stage:
            continue
        for view_layer in scene.view_layers:
            part = _layer_tree_shows_part(view_layer.layer_collection, coll, tree_ptrs)
            if part:
                return f"child collection '{part}' is shown on its own in scene '{scene.name}'"
    return None


def move_collection_contents(coll: bpy.types.Collection, delta: Vector) -> None:
    """Translate everything in `coll`'s tree by `delta` and move every instance offset in
    the tree by the same amount, so instances of these collections don't move.

    Callers must check `_stage_move_problem` first: every top-level object of the tree is
    then unparented, and moving its location moves it (and its children) by exactly delta.
    """
    for obj in _collection_tree_objects(coll):
        if obj.parent is None:
            obj.location = obj.location + delta
    for child in _collection_tree(coll):
        child.instance_offset = Vector(child.instance_offset) + delta


def _snap_up(value: float, step: float) -> float:
    return math.ceil(value / step - 1e-6) * step if step > 0 else value


def _snap_down(value: float, step: float) -> float:
    return math.floor(value / step + 1e-6) * step if step > 0 else value


def _label_width(coll: bpy.types.Collection, settings: Dict[str, Any]) -> float:
    if not settings["labels"]:
        return 0.0
    return len(coll.name) * settings["label_size"] * _LABEL_CHAR_WIDTH


def _label_space(settings: Dict[str, Any]) -> float:
    """Depth kept free in front of each item for its label."""
    if not settings["labels"]:
        return 0.0
    return settings["label_size"] * 1.5


def _pack_stage_items(
    items: List[Tuple[bpy.types.Collection, Vector, Vector]],
    origin_x: float,
    top_y: float,
    settings: Dict[str, Any],
    row_width: float,
) -> Dict[int, Vector]:
    """Shelf-pack items in rows along +X, rows stepping toward -Y, all resting on Z=0.

    Offsets are snapped to the grid step without letting items get closer than the
    spacing: X/Z round away from the previous item/the ground, Y toward the row's front.
    Returns {collection pointer: delta}.
    """
    spacing = settings["spacing"]
    snap = settings["snap"]
    label_space = _label_space(settings)
    deltas: Dict[int, Vector] = {}
    cursor_x = origin_x
    row_top = top_y
    row_bottom = top_y
    row_has_items = False
    for coll, lo, hi in items:
        width = max(hi.x - lo.x, _label_width(coll, settings))
        if row_has_items and cursor_x + width - origin_x > row_width:
            row_top = row_bottom - label_space - spacing
            row_bottom = row_top
            cursor_x = origin_x
            row_has_items = False
        delta = Vector((
            _snap_up(cursor_x - lo.x, snap),
            _snap_down(row_top - hi.y, snap),
            _snap_up(-lo.z, snap),
        ))
        deltas[coll.as_pointer()] = delta
        cursor_x = lo.x + delta.x + width + spacing
        row_bottom = min(row_bottom, lo.y + delta.y)
        row_has_items = True
    return deltas


def _footprint(coll: bpy.types.Collection, lo: Vector, hi: Vector, settings: Dict[str, Any]) -> Tuple[float, float, float, float]:
    """(min x, min y, max x, max y) an item occupies on the stage, label included."""
    return (
        lo.x,
        lo.y - _label_space(settings),
        max(hi.x, lo.x + _label_width(coll, settings)),
        hi.y,
    )


def _rebuild_stage_labels(
    stage: bpy.types.Scene,
    placed: List[Tuple[bpy.types.Collection, Vector, Vector]],
    settings: Dict[str, Any],
) -> None:
    labels = _stage_labels_collection(stage, create=settings["labels"])
    if labels is not None:
        for obj in list(labels.objects):
            data = obj.data
            bpy.data.objects.remove(obj)
            if data is not None and data.users == 0:
                bpy.data.curves.remove(data)
    if not settings["labels"]:
        if labels is not None:
            bpy.data.collections.remove(labels)
        return
    size = settings["label_size"]
    for coll, lo, _hi in placed:
        curve = bpy.data.curves.new(f"Label {coll.name}", 'FONT')
        curve.body = coll.name
        curve.size = size
        curve.align_x = 'LEFT'
        label = bpy.data.objects.new(f"Label {coll.name}", curve)
        label[STAGE_LABEL_TARGET_KEY] = coll.name
        label.location = (lo.x, lo.y - size * 1.1, 0.0)
        label.hide_select = True
        labels.objects.link(label)


def _bounds_or_offset(coll: bpy.types.Collection, depsgraph: bpy.types.Depsgraph) -> Tuple[Vector, Vector]:
    bounds = _collection_world_bounds(coll, depsgraph)
    if bounds is None:
        offset = Vector(coll.instance_offset)
        return offset.copy(), offset.copy()
    return bounds


def _outermost(collections: List[bpy.types.Collection]) -> Tuple[List[bpy.types.Collection], Dict[int, bpy.types.Collection]]:
    """Split collections into those not nested in another one of them, and
    {nested collection pointer: the outer collection that contains it}."""
    containing: Dict[int, bpy.types.Collection] = {}
    for outer in collections:
        for child in outer.children_recursive:
            containing.setdefault(child.as_pointer(), outer)
    top = [coll for coll in collections if coll.as_pointer() not in containing]
    nested = {coll.as_pointer(): containing[coll.as_pointer()] for coll in collections if coll.as_pointer() in containing}
    return top, nested


def update_collection_stage(
    context: bpy.types.Context,
    targets: Optional[List[bpy.types.Collection]] = None,
    relayout: bool = False,
    instance_direct_uses: bool = True,
    anchor: str = 'KEEP',
    settings: Optional[Dict[str, Any]] = None,
    stage_name: str = STAGE_DEFAULT_NAME,
    default_settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create or update the collection stage.

    targets=None adds every asset collection not yet on the stage (see
    `find_stage_candidates`); a list sends exactly those collections, placing them in
    free space even if they are already on the stage. Collections already on the stage
    stay where they are unless `relayout` repacks them all.

    A collection is placed by moving its contents and instance offset together (see
    `move_collection_contents`). Where it is shown directly (not instanced) in another
    scene, it would move there, so with `instance_direct_uses` it is replaced in that
    scene by an instance in the same place; otherwise it is skipped. Collections nested
    in another stage collection ride along with it. `anchor` ('KEEP', 'BOTTOM_CENTER',
    'CENTER') sets the instance offset of targets that nothing instances yet.
    `settings=None` uses the layout saved on the stage, or `default_settings` for a
    new stage.

    Returns a report dict: stage, added, moved, instanced, skipped [(name, reason)],
    nested [(name, outer name)], absorbed, overlaps [(a, b)].
    """
    stage = _ensure_stage_scene(context, stage_name)
    if settings is None:
        settings = get_stage_settings(stage, default_settings)
    stage[STAGE_SETTINGS_KEY] = settings
    report: Dict[str, Any] = {
        "stage": stage, "added": [], "moved": 0, "instanced": [], "skipped": [],
        "nested": [], "absorbed": [], "overlaps": [],
    }

    existing = get_stage_collections(stage)
    if targets is None:
        existing_ptrs = {coll.as_pointer() for coll in existing}
        new = [coll for coll in find_stage_candidates() if coll.as_pointer() not in existing_ptrs]
    else:
        new = []
        for coll in targets:
            if coll is not None and coll not in new:
                new.append(coll)
        new_ptrs = {coll.as_pointer() for coll in new}
        existing = [coll for coll in existing if coll.as_pointer() not in new_ptrs]
    new_ptrs = {coll.as_pointer() for coll in new}

    top, nested = _outermost(existing + new)
    for coll in existing + new:
        outer = nested.get(coll.as_pointer())
        # Only worth reporting for collections the user asked to send; found asset
        # collections nested in a stage collection simply ride along with it.
        if outer is not None and targets is not None and coll.as_pointer() in new_ptrs:
            report["nested"].append((coll.name, outer.name))

    # Two stage items sharing a child collection can't be placed apart.
    owners: Dict[int, List[bpy.types.Collection]] = {}
    for coll in top:
        for part in _collection_tree(coll):
            owners.setdefault(part.as_pointer(), []).append(coll)
    shared: Dict[int, str] = {}
    for part_ptr, colls in owners.items():
        if len(colls) > 1:
            for coll in colls:
                other = next(c for c in colls if c != coll)
                shared.setdefault(coll.as_pointer(), f"shares a child collection with '{other.name}'")

    movable: List[bpy.types.Collection] = []
    fixed: List[bpy.types.Collection] = []
    for coll in top:
        is_new = coll.as_pointer() in new_ptrs
        if not is_new and not relayout:
            fixed.append(coll)
            continue
        problem = (
            shared.get(coll.as_pointer())
            or _stage_move_problem(coll)
            or _direct_use_problem(coll, stage)
        )
        if problem is None and not instance_direct_uses:
            scenes = _scenes_showing(coll, stage)
            if scenes:
                problem = f"shown directly in scene '{scenes[0].name}'"
        if problem is not None:
            report["skipped"].append((coll.name, problem))
            if not is_new:
                fixed.append(coll)
            continue
        movable.append(coll)

    # A stage collection nested in a skipped one stays on the stage as it is.
    for coll in existing:
        if coll.as_pointer() in nested and not any(
            coll in outer.children_recursive for outer in fixed + movable
        ):
            fixed.append(coll)

    # Link before measuring so the stage depsgraph evaluates everything (modifiers included).
    for coll in movable:
        if not any(child == coll for child in stage.collection.children):
            stage.collection.children.link(coll)
            report["added"].append(coll.name)
    stage.view_layers[0].update()
    depsgraph = stage.view_layers[0].depsgraph
    bounds = {coll.as_pointer(): _bounds_or_offset(coll, depsgraph) for coll in fixed + movable}

    if anchor != 'KEEP' and targets is not None:
        for coll in movable:
            if coll.as_pointer() in new_ptrs and not get_collection_instancers(coll):
                lo, hi = bounds[coll.as_pointer()]
                point = (lo + hi) * 0.5
                if anchor == 'BOTTOM_CENTER':
                    point.z = lo.z
                coll.instance_offset = point

    # Instance direct uses before moving: the instance sits at the old offset, and the
    # move shifts contents and offset together, so it keeps drawing in place.
    for coll in movable:
        for scene in _scenes_showing(coll, stage):
            instance_collection_in_place(scene, coll)
            report["instanced"].append((scene.name, coll.name))

    if settings["sort"] == 'SIZE':
        def _area(coll):
            lo, hi = bounds[coll.as_pointer()]
            return -(hi.x - lo.x) * (hi.y - lo.y)
        movable.sort(key=lambda c: (_area(c), c.name.lower()))
    else:
        movable.sort(key=lambda c: c.name.lower())

    spacing = settings["spacing"]
    footprints = [_footprint(c, *bounds[c.as_pointer()], settings) for c in fixed]
    if footprints:
        origin_x = min(fp[0] for fp in footprints)
        top_y = min(fp[1] for fp in footprints) - spacing
    else:
        origin_x, top_y = 0.0, 0.0
    row_width = settings["row_width"]
    if row_width <= 0.0:
        area, widest = 0.0, 0.0
        for coll in fixed + movable:
            lo, hi = bounds[coll.as_pointer()]
            width = max(hi.x - lo.x, _label_width(coll, settings)) + spacing
            area += width * (hi.y - lo.y + _label_space(settings) + spacing)
            widest = max(widest, width)
        row_width = max(math.sqrt(area), widest)
        if footprints:
            row_width = max(row_width, max(fp[2] for fp in footprints) - origin_x)

    deltas = _pack_stage_items(
        [(c, *bounds[c.as_pointer()]) for c in movable], origin_x, top_y, settings, row_width
    )
    for coll in movable:
        delta = deltas[coll.as_pointer()]
        if delta.length > 0.0:
            move_collection_contents(coll, delta)
            report["moved"] += 1
        lo, hi = bounds[coll.as_pointer()]
        bounds[coll.as_pointer()] = (lo + delta, hi + delta)

    # Stage collections now nested inside a placed one are part of it.
    placed_ptrs = {coll.as_pointer() for coll in fixed + movable}
    for coll in get_stage_collections(stage):
        if coll.as_pointer() not in placed_ptrs and coll.as_pointer() in nested:
            outer = nested[coll.as_pointer()]
            if outer.as_pointer() in placed_ptrs:
                stage.collection.children.unlink(coll)
                report["absorbed"].append(coll.name)

    placed = [(c, *bounds[c.as_pointer()]) for c in fixed + movable]
    _rebuild_stage_labels(stage, placed, settings)

    boxes = [(c.name, _footprint(c, lo, hi, settings)) for c, lo, hi in placed]
    for i, (name_a, a) in enumerate(boxes):
        for name_b, b in boxes[i + 1:]:
            if a[0] < b[2] - 1e-4 and b[0] < a[2] - 1e-4 and a[1] < b[3] - 1e-4 and b[1] < a[3] - 1e-4:
                report["overlaps"].append((name_a, name_b))
    return report
