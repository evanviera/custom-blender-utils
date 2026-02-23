import bpy
"""Utility functions for the Custom Utilities Blender addon.

This module encapsulates shared functionality used by operators, such as
measuring distances, handling mouse clicks/raycast, transformation clipboard
operations, and origin adjustments.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from mathutils import Vector, Color, Euler, Quaternion
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

def handle_mouse_click(context: bpy.types.Context, event: bpy.types.Event, operator: bpy.types.Operator) -> None:
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
            print(f"Distance: {distance:.2f}")
            operator.report({'INFO'}, f"Distance: {distance:.2f}")
            bpy.context.window_manager.clipboard = f"{distance:.2f}"
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


def get_default_geometry_nodes_export_filepath(node_group_name: str) -> str:
    """Return a default JSON path for GN export based on the current blend path."""
    blend_path = bpy.data.filepath
    if blend_path:
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


def _capture_modifier_inputs(modifier: bpy.types.Modifier) -> Tuple[Dict[str, Any], Dict[str, str]]:
    inputs: Dict[str, Any] = {}
    input_labels: Dict[str, str] = {}

    base_labels = _modifier_visible_input_labels(modifier)
    if not base_labels:
        return inputs, input_labels

    allowed_keys = set(base_labels.keys())

    for key in modifier.keys():
        if key == '_RNA_UI':
            continue
        if key not in allowed_keys:
            continue
        try:
            value = modifier[key]
        except Exception:
            continue

        serialized = _serialize_value(value)
        if serialized is _UNSUPPORTED:
            continue
        inputs[key] = serialized

        input_labels[key] = base_labels.get(key, key)

    return inputs, input_labels


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
        }
        entry_inputs, entry_input_labels = _capture_modifier_inputs(modifier)
        entry['inputs'] = entry_inputs
        entry['input_labels'] = entry_input_labels
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
) -> Dict[str, int]:
    applied = 0
    skipped_missing = 0
    skipped_type = 0

    current_keys = set(modifier.keys())
    for key, stored_value in stored_inputs.items():
        if key not in current_keys:
            skipped_missing += 1
            continue

        value = _deserialize_value(stored_value)
        if value is None and isinstance(stored_value, dict) and stored_value.get('__id_ref__'):
            skipped_type += 1
            continue

        try:
            modifier[key] = value
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
