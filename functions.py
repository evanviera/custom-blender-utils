import bpy
import json
from mathutils import Vector
from bpy_extras.io_utils import axis_conversion


transformations_clipboard = {}

def clear_transformations():
    global transformations_clipboard
    transformations_clipboard = {}

def copy_transformations(obj):
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

def paste_transformations(obj):
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

# Function to set the origin to the center bottom of the bounding box
def set_origin_to_bottom_center(obj):
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