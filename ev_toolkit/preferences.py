"""Add-on preferences for EV Toolkit.

Four tabs:
- Pie Menus: what goes in each of the eight directions of every pie, their hotkeys,
  icons, and Blender's own (global) pie behavior.
- Interface: which menus and buttons the addon adds to Blender's UI.
- Tools: the options tools start with (Measure, Geometry Nodes, Render).
- Collections: the options collection tools and the Collection Stage start with.

Tool defaults: an operator option backed by a preference is declared with
SKIP_SAVE (so Blender doesn't reuse the last run's value instead) and filled in from
the preference by `apply_operator_defaults` when the tool starts, unless the caller
set it explicitly. The redo panel still changes it for that one run.
"""

from typing import Dict, NamedTuple, Tuple

import bpy
import rna_keymap_ui
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty

from . import catalog
from . import functions as fn


ADDON_ID = __package__


# --- Option choices shared with the operators, so both always offer the same items ---

REPLACE_PIVOT_ITEMS = [
    ('BOTTOM_CENTER', "Bottom Center", "Bottom center of the collection's bounds"),
    ('CENTER', "Bounds Center", "Center of the collection's bounds"),
    ('ACTIVE', "Active Object", "Origin of the active object"),
    ('CURSOR', "3D Cursor", "Location of the 3D cursor"),
    ('KEEP', "Instance Offset", "Keep the collection's current instance offset"),
]

RESET_ANCHOR_ITEMS = [
    ('BOTTOM_CENTER', "Bottom Center", "Bottom center of the collection's bounds"),
    ('CENTER', "Bounds Center", "Center of the collection's bounds"),
    ('CURSOR', "3D Cursor", "The 3D cursor, as seen through the selected instance"),
    ('ORIGIN', "Collection Origin", "The collection's own origin (no offset)"),
]

STAGE_ANCHOR_ITEMS = [
    ('KEEP', "Keep", "Keep the current instance offset"),
    ('BOTTOM_CENTER', "Bottom Center", "Bottom center of the collection's bounds"),
    ('CENTER', "Bounds Center", "Center of the collection's bounds"),
]

STAGE_SORT_ITEMS = [
    ('NAME', "Name", "Alphabetical"),
    ('SIZE', "Size", "Largest footprint first (tighter packing)"),
]


# --- Pie menus ---

# Blender fills pie slots in this order.
PIE_DIRECTIONS = ("west", "east", "south", "north", "north_west", "north_east", "south_west", "south_east")

PIE_DIRECTION_LABELS = {
    "west": "Left", "east": "Right", "south": "Bottom", "north": "Top",
    "north_west": "Top Left", "north_east": "Top Right",
    "south_west": "Bottom Left", "south_east": "Bottom Right",
}

# The preferences grid mirrors the pie: (direction or None for the center cell).
PIE_GRID = (
    ("north_west", "north", "north_east"),
    ("west", None, "east"),
    ("south_west", "south", "south_east"),
)


# Keymaps a pie hotkey can live in. Mode keymaps are checked before "3D View", so a
# pie that replaces a built-in key (G, R, S) must go in the mode keymaps holding it.
KEYMAP_LABELS = {
    "Object Mode": "Object Mode",
    "Mesh": "Edit Mode (Mesh)",
}


class PieSpec(NamedTuple):
    id: str
    menu: str  # Menu bl_idname
    title: str
    key: str  # default hotkey
    icons: bool  # default for "Show Icons"
    slots: Dict[str, str]  # default action key per direction; missing directions are empty
    keymaps: Tuple[str, ...] = ("Object Mode",)  # one hotkey per keymap (mode)


def _transform_slots(prefix: str) -> Dict[str, str]:
    return {"west": f"{prefix}_X", "east": f"{prefix}_Y", "south": f"{prefix}_Z", "north": prefix}


PIES = (
    PieSpec(
        "utilities", "VIEW3D_MT_pie_utilities", "Utilities Pie", 'V', False,
        {
            "west": "MEASURE",
            "east": "COPY_TRANSFORMS",
            "south": "PASTE_TRANSFORMS",
            "north": "GN_COPY",
            "north_west": "GN_PASTE",
            "north_east": "ORIGIN_BOTTOM",
            "south_west": "REMOVE_DUPLICATE_MATERIALS",
            "south_east": catalog.NONE_KEY,
        },
    ),
    PieSpec(
        "collections", "VIEW3D_MT_pie_collections", "Collections Pie", 'C', True,
        {
            "west": "DECOMPOSE_COLLECTION",
            "east": "MERGE_COLLECTIONS",
            "south": "MOVE_TO_COLLECTION",
            "north": "EDIT_COLLECTION",
            "north_west": "DUPLICATE_COLLECTION",
            "north_east": "REPLACE_WITH_INSTANCE",
            "south_west": "RESET_ANCHOR",
            "south_east": "STAGE_SEND",
        },
    ),
    PieSpec(
        "select_linked", "VIEW3D_MT_pie_select_linked", "Select Linked Pie", 'D', False,
        {
            "west": "SELECT_LINKED_MATERIAL",
            "east": "SELECT_LINKED_DATA",
            "south": "SELECT_CHILDREN",
            "north": "SELECT_SAME_TYPE",
            "north_west": "SELECT_SAME_COLOR",
            "north_east": "SELECT_ACTIVE_CAMERA",
            "south_west": "SELECT_SAME_LIGHT_TYPE",
            "south_east": "SELECT_LINKED_INSTANCE",
        },
    ),
    PieSpec(
        "select_loops", "VIEW3D_MT_pie_select_loops", "Select Loops Pie", 'D', False,
        {
            "west": "SELECT_EDGE_LOOPS",
            "east": "SELECT_EDGE_RINGS",
            "south": "SELECT_LESS",
            "north": "SELECT_MORE",
        },
        keymaps=("Mesh",),
    ),
    PieSpec("move", "VIEW3D_MT_pie_move", "Move Pie", 'G', False, _transform_slots("MOVE"), ("Object Mode", "Mesh")),
    PieSpec("rotate", "VIEW3D_MT_pie_rotate", "Rotate Pie", 'R', False, _transform_slots("ROTATE"), ("Object Mode", "Mesh")),
    PieSpec("scale", "VIEW3D_MT_pie_scale", "Scale Pie", 'S', False, _transform_slots("SCALE"), ("Object Mode", "Mesh")),
)

PIES_BY_ID = {spec.id: spec for spec in PIES}


def pie_slot_prop(pie_id: str, direction: str) -> str:
    return f"{pie_id}_pie_{direction}"


def pie_icons_prop(pie_id: str) -> str:
    return f"{pie_id}_pie_icons"


def pie_expanded_prop(pie_id: str) -> str:
    return f"{pie_id}_pie_expanded"


def pie_default_slot(spec: PieSpec, direction: str) -> str:
    return spec.slots.get(direction, catalog.NONE_KEY)


def pie_slot_actions(context: bpy.types.Context, pie_id: str):
    """(direction, action key) for every slot of a pie, in Blender's fill order."""
    prefs = get_prefs(context)
    spec = PIES_BY_ID[pie_id]
    for direction in PIE_DIRECTIONS:
        key = getattr(prefs, pie_slot_prop(pie_id, direction)) if prefs else pie_default_slot(spec, direction)
        yield direction, key


def pie_shows_icons(context: bpy.types.Context, pie_id: str) -> bool:
    prefs = get_prefs(context)
    return getattr(prefs, pie_icons_prop(pie_id)) if prefs else PIES_BY_ID[pie_id].icons


# --- Access helpers used by operators and UI ---

def get_prefs(context: bpy.types.Context = None):
    """This addon's preferences, or None if unavailable (e.g. while unregistering)."""
    context = context or bpy.context
    preferences = getattr(context, "preferences", None)
    if preferences is None:
        return None
    addon = preferences.addons.get(ADDON_ID)
    return addon.preferences if addon is not None else None


def pref(context: bpy.types.Context, name: str, fallback):
    prefs = get_prefs(context)
    return getattr(prefs, name, fallback) if prefs is not None else fallback


def apply_operator_defaults(operator: bpy.types.Operator, context: bpy.types.Context, mapping: Dict[str, str]) -> None:
    """Fill operator options from preferences ({operator prop: preference prop}).

    Options the caller set explicitly (or that a redo already set) are left alone.
    """
    prefs = get_prefs(context)
    if prefs is None:
        return
    props = operator.properties
    for op_prop, pref_prop in mapping.items():
        if not props.is_property_set(op_prop):
            setattr(operator, op_prop, getattr(prefs, pref_prop))


_STAGE_LAYOUT_PREFS = {
    "spacing": "stage_spacing",
    "snap": "stage_snap",
    "row_width": "stage_row_width",
    "sort": "stage_sort",
    "labels": "stage_labels",
    "label_size": "stage_label_size",
}


def stage_layout_defaults(context: bpy.types.Context) -> Dict:
    """Layout settings a new Collection Stage starts with."""
    prefs = get_prefs(context)
    settings = dict(fn.STAGE_DEFAULT_SETTINGS)
    if prefs is not None:
        for key, pref_name in _STAGE_LAYOUT_PREFS.items():
            settings[key] = getattr(prefs, pref_name)
    return settings


def stage_scene_name(context: bpy.types.Context) -> str:
    name = pref(context, "stage_scene_name", fn.STAGE_DEFAULT_NAME).strip()
    return name or fn.STAGE_DEFAULT_NAME


# --- Keymaps ---

addon_keymaps = []


def _find_pie_item(km: bpy.types.KeyMap, menu: str):
    for kmi in km.keymap_items:
        if kmi.idname == "wm.call_menu_pie" and getattr(kmi.properties, "name", "") == menu:
            return kmi
    return None


def register_keymaps():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        return
    for spec in PIES:
        for keymap_name in spec.keymaps:
            km = kc.keymaps.get(keymap_name)
            if km is None:
                km = kc.keymaps.new(name=keymap_name, space_type='EMPTY')
            kmi = _find_pie_item(km, spec.menu)
            if kmi is None:
                kmi = km.keymap_items.new("wm.call_menu_pie", type=spec.key, value='PRESS')
                kmi.properties.name = spec.menu
            addon_keymaps.append((km, kmi))


def unregister_keymaps():
    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except (ReferenceError, RuntimeError):
            pass
    addon_keymaps.clear()


def _find_user_keymap_item(context: bpy.types.Context, keymap_name: str, menu: str):
    """The user-keyconfig copy of a pie hotkey (the one users edit), as (keyconfig, keymap, item)."""
    kc = context.window_manager.keyconfigs.user
    km = kc.keymaps.get(keymap_name) if kc else None
    if km is None:
        return kc, None, None
    return kc, km, _find_pie_item(km, menu)


# --- Operators used by the preferences UI ---

class CUSTOMUTILS_OT_reset_pie_layout(bpy.types.Operator):
    bl_idname = "custom_utils.reset_pie_layout"
    bl_label = "Reset Pie Layout"
    bl_description = "Put the default action back in every direction of this pie"
    bl_options = {'INTERNAL'}

    pie: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    clear: BoolProperty(
        name="Clear",
        description="Empty every direction instead of restoring the defaults",
        default=False,
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        prefs = get_prefs(context)
        spec = PIES_BY_ID.get(self.pie)
        if prefs is None or spec is None:
            return {'CANCELLED'}
        for direction in PIE_DIRECTIONS:
            value = catalog.NONE_KEY if self.clear else pie_default_slot(spec, direction)
            setattr(prefs, pie_slot_prop(spec.id, direction), value)
        context.preferences.is_dirty = True
        return {'FINISHED'}


# --- Preferences ---

class EVToolkitPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    tab: EnumProperty(
        name="Tab",
        items=[
            ('PIES', "Pie Menus", "Pie layouts and hotkeys", 'MENU_PANEL', 0),
            ('INTERFACE', "Interface", "Menus and buttons added to Blender", 'WINDOW', 1),
            ('TOOLS', "Tools", "Options the general tools start with", 'TOOL_SETTINGS', 2),
            ('COLLECTIONS', "Collections", "Options the collection and stage tools start with", 'OUTLINER_COLLECTION', 3),
        ],
        default='PIES',
    )

    # Pie slot and icon properties are added below the class, one per pie and direction.
    show_blender_pie_settings: BoolProperty(name="Blender Pie Settings", default=False)

    # Interface
    header_utilities_menu: BoolProperty(
        name="Utilities Menu",
        description="Show the Utilities menu in the 3D View header",
        default=True,
    )
    header_collections_menu: BoolProperty(
        name="Collections Menu",
        description="Show the Collections menu in the 3D View header",
        default=True,
    )
    render_copy_button: BoolProperty(
        name="Copy Render Settings Button",
        description="Show 'Copy Render Settings to All Scenes' at the top of the Render Properties tab",
        default=True,
    )
    outliner_send_to_stage: BoolProperty(
        name="Outliner 'Send to Stage'",
        description="Show 'Send to Stage' in the Outliner's collection right-click menu",
        default=True,
    )

    # Tools: Measure
    measure_precision: IntProperty(
        name="Decimal Places",
        description="Decimal places in the reported distance",
        default=2, min=0, max=6,
    )
    measure_copy_to_clipboard: BoolProperty(
        name="Copy to Clipboard",
        description="Copy the measured distance to the clipboard",
        default=True,
    )

    # Tools: Geometry Nodes
    gn_paste_exclude_active: BoolProperty(
        name="Paste: Exclude Active Object",
        description="Paste Geometry Nodes Attributes starts with the active object skipped",
        default=False,
    )
    gn_import_attach: BoolProperty(
        name="Import: Attach to Active Object",
        description="Import Geometry Nodes Network starts with 'Attach to Active Object' on",
        default=True,
    )
    gn_export_directory: StringProperty(
        name="Export Folder",
        description=(
            "Folder Export Geometry Nodes Network suggests. Empty: next to the .blend file "
            "(home folder if unsaved). '//' paths are relative to the .blend file"
        ),
        subtype='DIR_PATH',
        default="",
    )

    # Tools: Render
    render_include_output: BoolProperty(
        name="Include Output Properties",
        description="Copy Render Settings to All Scenes starts with Output tab settings included",
        default=False,
    )

    # Collections: collection tools
    decompose_nested: BoolProperty(
        name="Decompose: Nested Instances",
        description="Decompose Collection also decomposes collection instances nested inside",
        default=True,
    )
    replace_pivot: EnumProperty(
        name="Replace: Pivot",
        description="Where Replace with Instance puts the instance origin",
        items=REPLACE_PIVOT_ITEMS,
        default='BOTTOM_CENTER',
    )
    replace_top_level: BoolProperty(
        name="Replace: Top-Level Collection",
        description="Replace with Instance replaces the outermost collection instead of the direct one",
        default=False,
    )
    reset_anchor: EnumProperty(
        name="Reset Anchor: Anchor",
        description="Where Reset Collection Anchor puts the anchor point",
        items=RESET_ANCHOR_ITEMS,
        default='BOTTOM_CENTER',
    )

    # Collections: stage
    stage_scene_name: StringProperty(
        name="Scene Name",
        description="Name of the stage scene when it is first created (rename it any time afterwards)",
        default=fn.STAGE_DEFAULT_NAME,
    )
    stage_instance_direct_uses: BoolProperty(
        name="Update: Instance Direct Uses",
        description=(
            "Update Collection Stage replaces collections shown directly in other scenes with "
            "instances, instead of skipping them"
        ),
        default=True,
    )
    stage_open_after_update: BoolProperty(
        name="Update: Open Stage",
        description="Switch to the stage after Build / Update Collection Stage",
        default=True,
    )
    send_top_level: BoolProperty(
        name="Send: Top-Level Collection",
        description="Send to Stage sends the outermost collection of selected objects",
        default=False,
    )
    send_anchor: EnumProperty(
        name="Send: Anchor",
        description="Instance offset Send to Stage gives collections that nothing instances yet",
        items=STAGE_ANCHOR_ITEMS,
        default='KEEP',
    )
    send_open_stage: BoolProperty(
        name="Send: Open Stage",
        description="Switch to the stage after Send to Stage",
        default=False,
    )
    stage_spacing: FloatProperty(
        name="Spacing", description="Gap between collections", default=2.0, min=0.0,
        subtype='DISTANCE', unit='LENGTH',
    )
    stage_snap: FloatProperty(
        name="Grid Snap",
        description="Move collections only by multiples of this step. 0 disables snapping",
        default=1.0, min=0.0, subtype='DISTANCE', unit='LENGTH',
    )
    stage_row_width: FloatProperty(
        name="Row Width",
        description="Maximum width of a row of collections. 0 picks a roughly square layout",
        default=0.0, min=0.0, subtype='DISTANCE', unit='LENGTH',
    )
    stage_sort: EnumProperty(name="Order", items=STAGE_SORT_ITEMS, default='NAME')
    stage_labels: BoolProperty(name="Labels", description="Name label in front of each collection", default=True)
    stage_label_size: FloatProperty(
        name="Label Size", default=0.5, min=0.01, subtype='DISTANCE', unit='LENGTH',
    )

    # --- Drawing ---

    def draw(self, context):
        layout = self.layout
        layout.row().prop(self, "tab", expand=True)
        layout.separator()
        {
            'PIES': self._draw_pies,
            'INTERFACE': self._draw_interface,
            'TOOLS': self._draw_tools,
            'COLLECTIONS': self._draw_collections,
        }[self.tab](context, layout)

    @staticmethod
    def _section(layout, title, icon='NONE'):
        box = layout.box()
        box.label(text=title, icon=icon)
        col = box.column()
        col.use_property_split = True
        col.use_property_decorate = False
        return col

    def _draw_pies(self, context, layout):
        # Group the pies by the modes their hotkeys work in, in PIES order.
        sections = {}
        for spec in PIES:
            sections.setdefault(spec.keymaps, []).append(spec)
        for keymaps, specs in sections.items():
            layout.label(text=" & ".join(KEYMAP_LABELS.get(name, name) for name in keymaps))
            col = layout.column(align=True)
            for spec in specs:
                self._draw_pie(context, col, spec)
            layout.separator()

        box = layout.box()
        row = box.row()
        row.alignment = 'LEFT'
        row.prop(
            self, "show_blender_pie_settings",
            icon='DISCLOSURE_TRI_DOWN' if self.show_blender_pie_settings else 'DISCLOSURE_TRI_RIGHT',
            emboss=False,
        )
        if self.show_blender_pie_settings:
            col = box.column()
            col.label(text="Blender-wide settings: these affect every pie menu, not just this addon's.", icon='INFO')
            col.use_property_split = True
            col.use_property_decorate = False
            view = context.preferences.view
            col.prop(view, "pie_menu_radius", text="Radius")
            col.prop(view, "pie_menu_threshold", text="Threshold")
            col.prop(view, "pie_menu_confirm", text="Confirm Threshold")
            col.prop(view, "pie_tap_timeout", text="Tap Key Timeout")
            col.prop(view, "pie_initial_timeout", text="Recenter Timeout")
            col.prop(view, "pie_animation_timeout", text="Animation Timeout")

    def _draw_pie(self, context, layout, spec: PieSpec):
        box = layout.box()
        hotkeys = [(name, *_find_user_keymap_item(context, name, spec.menu)) for name in spec.keymaps]
        active_keys = [kmi.to_string() for _name, _kc, _km, kmi in hotkeys if kmi is not None and kmi.active]

        # Header (always shown): expand toggle, title, hotkey on/off per mode, current key.
        expanded_prop = pie_expanded_prop(spec.id)
        expanded = getattr(self, expanded_prop)
        header = box.row()
        header.prop(
            self, expanded_prop, text=spec.title, emboss=False,
            icon='DISCLOSURE_TRI_DOWN' if expanded else 'DISCLOSURE_TRI_RIGHT',
        )
        sub = header.row(align=True)
        sub.alignment = 'RIGHT'
        for name, _kc, _km, kmi in hotkeys:
            if kmi is not None:
                text = KEYMAP_LABELS.get(name, name) if len(hotkeys) > 1 else ""
                sub.prop(kmi, "active", text=text)
        sub.label(text=" / ".join(dict.fromkeys(active_keys)) or "Off", icon='KEYINGSET')
        if not expanded:
            return

        row = box.row()
        row.prop(self, pie_icons_prop(spec.id), text="Icons", toggle=True, icon='IMAGE_RGB_ALPHA')
        sub = row.row(align=True)
        op = sub.operator(CUSTOMUTILS_OT_reset_pie_layout.bl_idname, text="Reset", icon='LOOP_BACK')
        op.pie = spec.id
        op = sub.operator(CUSTOMUTILS_OT_reset_pie_layout.bl_idname, text="Clear", icon='X')
        op.pie = spec.id
        op.clear = True

        # Hotkeys: the standard keymap row (enable, key, modifiers, restore), one per mode.
        for name, kc, km, kmi in hotkeys:
            hotkey = box.column()
            if len(hotkeys) > 1:
                hotkey.label(text=KEYMAP_LABELS.get(name, name))
            if kmi is not None:
                hotkey.context_pointer_set("keymap", km)
                rna_keymap_ui.draw_kmi([], kc, km, kmi, hotkey, 0)
            else:
                hotkey.label(text="Hotkey not found; disable and re-enable the addon to restore it", icon='ERROR')

        # Slots, laid out like the pie itself.
        grid = box.grid_flow(row_major=True, columns=3, even_columns=True, even_rows=True, align=True)
        for row in PIE_GRID:
            for direction in row:
                if direction is None:
                    cell = grid.row()
                    cell.alignment = 'CENTER'
                    cell.label(text=" / ".join(dict.fromkeys(active_keys)) or "No hotkey", icon='KEYINGSET')
                    continue
                cell = grid.column(align=True)
                cell.label(text=PIE_DIRECTION_LABELS[direction])
                cell.prop(self, pie_slot_prop(spec.id, direction), text="")

        used = [getattr(self, pie_slot_prop(spec.id, d)) for d in PIE_DIRECTIONS]
        used = [key for key in used if key != catalog.NONE_KEY]
        duplicates = sorted({key for key in used if used.count(key) > 1})
        if duplicates:
            names = ", ".join(catalog.ACTIONS_BY_KEY[key].label for key in duplicates)
            box.label(text=f"In more than one direction: {names}", icon='INFO')

    def _draw_interface(self, context, layout):
        col = self._section(layout, "3D View Header", 'VIEW3D')
        col.prop(self, "header_utilities_menu")
        col.prop(self, "header_collections_menu")

        col = self._section(layout, "Other Editors", 'WINDOW')
        col.prop(self, "render_copy_button")
        col.prop(self, "outliner_send_to_stage")

        col = self._section(layout, "Hotkeys", 'KEYINGSET')
        col.label(text="Pie hotkeys are set per pie on the Pie Menus tab.")

    def _draw_tools(self, context, layout):
        layout.label(text="Options each tool starts with. The redo panel still changes them for one run.", icon='INFO')

        col = self._section(layout, "Measure Surface Point", 'DRIVER_DISTANCE')
        col.prop(self, "measure_precision")
        col.prop(self, "measure_copy_to_clipboard")

        col = self._section(layout, "Geometry Nodes", 'GEOMETRY_NODES')
        col.prop(self, "gn_paste_exclude_active", text="Paste: Exclude Active")
        col.prop(self, "gn_import_attach", text="Import: Attach to Active")
        col.prop(self, "gn_export_directory")

        col = self._section(layout, "Copy Render Settings to All Scenes", 'SCENE_DATA')
        col.prop(self, "render_include_output")

    def _draw_collections(self, context, layout):
        layout.label(text="Options each tool starts with. The redo panel still changes them for one run.", icon='INFO')

        col = self._section(layout, "Collection Tools", 'OUTLINER_COLLECTION')
        col.prop(self, "decompose_nested", text="Decompose: Nested Instances")
        col.prop(self, "replace_pivot", text="Replace with Instance: Pivot")
        col.prop(self, "replace_top_level", text="Replace with Instance: Top-Level")
        col.prop(self, "reset_anchor", text="Reset Anchor: Anchor")

        col = self._section(layout, "Collection Stage", 'SCENE_DATA')
        col.prop(self, "stage_scene_name")
        col.separator()
        col.prop(self, "stage_instance_direct_uses", text="Update: Instance Direct Uses")
        col.prop(self, "stage_open_after_update", text="Update: Open Stage")
        col.separator()
        col.prop(self, "send_top_level", text="Send: Top-Level Collection")
        col.prop(self, "send_anchor", text="Send: Anchor")
        col.prop(self, "send_open_stage", text="Send: Open Stage")

        col = self._section(layout, "New Stage Layout", 'SNAP_GRID')
        col.label(text="Used when a file gets its first stage; each stage then keeps its own layout.")
        col.prop(self, "stage_spacing")
        col.prop(self, "stage_snap")
        col.prop(self, "stage_row_width")
        col.prop(self, "stage_sort")
        col.prop(self, "stage_labels")
        sub = col.column()
        sub.active = self.stage_labels
        sub.prop(self, "stage_label_size")


def _add_pie_properties():
    annotations = EVToolkitPreferences.__annotations__
    items = catalog.action_enum_items()
    for spec in PIES:
        for direction in PIE_DIRECTIONS:
            annotations[pie_slot_prop(spec.id, direction)] = EnumProperty(
                name=f"{spec.title}: {PIE_DIRECTION_LABELS[direction]}",
                description=f"Action in the {PIE_DIRECTION_LABELS[direction].lower()} direction of the {spec.title}",
                items=items,
                default=pie_default_slot(spec, direction),
            )
        annotations[pie_icons_prop(spec.id)] = BoolProperty(
            name="Show Icons",
            description=f"Show icons in the {spec.title}",
            default=spec.icons,
        )
        annotations[pie_expanded_prop(spec.id)] = BoolProperty(
            name="Expanded",
            description=f"Show the layout and hotkey settings of the {spec.title}",
            default=False,
        )


_add_pie_properties()


classes = (
    CUSTOMUTILS_OT_reset_pie_layout,
    EVToolkitPreferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
