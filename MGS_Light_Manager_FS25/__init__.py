bl_info = {
    'name': 'MGS Light Manager for FS25',
    'author': 'MyGameSteam',
    'blender': (3, 0, 0),
    'version': (1, 1, 2),
    'description': 'Manage FS25 light UV types and UV tile adjustments.',
    'warning': 'This tool modifies UV maps directly. Use with caution.',
    'location': 'UV Editor > Sidebar > MGS',
    'category': 'Game Engine',
    'license': 'GPL-3.0'
}

# Licensed under the GNU General Public License, version 3 (GPLv3)

import bpy
import bmesh
import math


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def get_edit_mesh_objects(context):
    """
    Return every unique mesh object currently participating in Edit Mode.

    This is the important part for multi-object UV editing.
    """

    objects = getattr(
        context,
        "objects_in_mode_unique_data",
        None
    )

    if objects:
        return [
            obj
            for obj in objects
            if obj is not None and obj.type == 'MESH'
        ]

    objects = getattr(
        context,
        "objects_in_mode",
        None
    )

    if objects:
        return [
            obj
            for obj in objects
            if obj is not None and obj.type == 'MESH'
        ]

    obj = context.edit_object

    if obj is not None and obj.type == 'MESH':
        return [obj]

    return []


def uv_sync_enabled(context):
    try:
        return bool(
            context.scene.tool_settings.use_uv_select_sync
        )
    except AttributeError:
        return False


def uv_loop_selected(
    context,
    bm,
    face,
    loop,
    uv_layer
):
    """
    Detect UV selection across supported Blender versions.

    Blender 3.x / 4.x:
        BMLoopUV.select / select_edge

    Blender 5.x:
        BMLoop.uv_select_vert
        BMLoop.uv_select_edge
        BMFace.uv_select
    """

    # -------------------------------------------------------------------------
    # Blender 5.x+
    # -------------------------------------------------------------------------

    if bpy.app.version >= (5, 0, 0):

        try:
            if not bm.uv_select_sync_valid:
                bm.uv_select_sync_from_mesh()
        except (AttributeError, RuntimeError):
            pass

        try:
            if loop.uv_select_vert:
                return True
        except AttributeError:
            pass

        try:
            if loop.uv_select_edge:
                return True
        except AttributeError:
            pass

        try:
            if face.uv_select:
                return True
        except AttributeError:
            pass

        # UV Sync Selection
        if uv_sync_enabled(context):
            return bool(loop.vert.select)

        return False

    # -------------------------------------------------------------------------
    # Blender 3.x / 4.x
    # -------------------------------------------------------------------------

    luv = loop[uv_layer]

    try:
        if luv.select:
            return True
    except AttributeError:
        pass

    try:
        if luv.select_edge:
            return True
    except AttributeError:
        pass

    # When UV Sync Selection is enabled,
    # mesh selection becomes authoritative.
    if uv_sync_enabled(context):
        try:
            return bool(loop.vert.select)
        except AttributeError:
            return False

    return False


def get_selected_uv_loops(
    context,
    bm,
    uv_layer
):
    selected = []

    for face in bm.faces:

        for loop in face.loops:

            if uv_loop_selected(
                context,
                bm,
                face,
                loop,
                uv_layer
            ):
                selected.append(loop)

    return selected


def get_all_uv_loops(bm):
    return [
        loop
        for face in bm.faces
        for loop in face.loops
    ]



def get_mesh_selected_uv_loops(bm, uv_layer):
    """
    Return UV loops corresponding to geometry currently selected in the 3D View.

    Face selection is preferred because UVs belong to face corners. For vertex
    or edge selection modes, a loop is included when its vertex or edge is
    selected. This works across every object participating in multi-object
    Edit Mode and avoids relying on stale UV-editor selection state.
    """
    selected = []
    seen = set()

    for face in bm.faces:
        face_selected = bool(face.select)

        for loop in face.loops:
            include = face_selected

            if not include:
                try:
                    include = bool(loop.vert.select)
                except AttributeError:
                    pass

            if not include:
                try:
                    include = bool(loop.edge.select)
                except AttributeError:
                    pass

            if include:
                key = loop.index
                if key not in seen:
                    seen.add(key)
                    selected.append(loop)

    return selected


def get_mesh_selection_targets(context):
    """
    Gather selected mesh geometry from every mesh in multi-object Edit Mode.

    The 3D View mesh selection is the source of truth:
      - one selected light -> one light moves
      - two selected lights -> both move
      - Select All -> all move
    """
    targets = []

    for obj in get_edit_mesh_objects(context):
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active

        if uv_layer is None:
            continue

        loops = get_mesh_selected_uv_loops(bm, uv_layer)

        if loops:
            targets.append((obj, bm, uv_layer, loops))

    return targets


_mgs_last_selection_source = "MESH"
_mgs_tracker_running = False


def _area_under_mouse(context, event):
    """
    Return the actual Blender area and WINDOW region under the mouse.
    event.mouse_x / mouse_y are window coordinates.
    """
    window = context.window
    screen = window.screen if window is not None else None

    if screen is None:
        return None, None

    x = event.mouse_x
    y = event.mouse_y

    for area in screen.areas:
        if not (
            area.x <= x < area.x + area.width
            and area.y <= y < area.y + area.height
        ):
            continue

        for region in area.regions:
            if (
                region.type == 'WINDOW'
                and region.x <= x < region.x + region.width
                and region.y <= y < region.y + region.height
            ):
                return area, region

        return area, None

    return None, None


class MGS_OT_SelectionSourceTracker(bpy.types.Operator):
    bl_idname = "mgs.selection_source_tracker"
    bl_label = "MGS Selection Source Tracker"
    bl_options = {'INTERNAL'}

    _mouse_selection_source = None

    def invoke(self, context, event):
        global _mgs_tracker_running

        if _mgs_tracker_running:
            return {'CANCELLED'}

        _mgs_tracker_running = True
        self._mouse_selection_source = None
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        global _mgs_last_selection_source

        # Mouse selection:
        # Remember which editor the gesture STARTED in, then commit that source
        # on RELEASE. This catches click-to-deselect, shift-click selection and
        # normal click selection while ignoring clicks on the MGS sidebar.
        if event.type in {'LEFTMOUSE', 'RIGHTMOUSE'}:
            if event.value == 'PRESS':
                area, region = _area_under_mouse(context, event)

                if region is not None:
                    if area.type == 'VIEW_3D':
                        self._mouse_selection_source = "MESH"
                    elif area.type == 'IMAGE_EDITOR':
                        self._mouse_selection_source = "UV"
                    else:
                        self._mouse_selection_source = None
                else:
                    self._mouse_selection_source = None

            elif event.value == 'RELEASE':
                if self._mouse_selection_source is not None:
                    _mgs_last_selection_source = self._mouse_selection_source

                self._mouse_selection_source = None

        # Keyboard selection commands are committed immediately according to
        # the editor under the mouse. A/B/C cover select-all, box and circle
        # selection; Alt+A is still event type A and is therefore included.
        elif (
            event.value == 'PRESS'
            and event.type in {'A', 'B', 'C'}
        ):
            area, region = _area_under_mouse(context, event)

            if region is not None:
                if area.type == 'VIEW_3D':
                    _mgs_last_selection_source = "MESH"
                elif area.type == 'IMAGE_EDITOR':
                    _mgs_last_selection_source = "UV"

        return {'PASS_THROUGH'}


def start_selection_source_tracker():
    global _mgs_tracker_running

    if _mgs_tracker_running:
        return None

    try:
        bpy.ops.mgs.selection_source_tracker('INVOKE_DEFAULT')
    except RuntimeError:
        return 0.5

    return None


def get_operation_targets(context):
    """
    Both arrows and preset buttons use this exact same target resolver.

    Last selection action in UV Editor:
        operate only on selected UVs.

    Last selection action in 3D View:
        operate only on selected mesh geometry.

    UV Sync enabled:
        mesh selection is Blender's source of truth.
    """
    global _mgs_last_selection_source

    objects = get_edit_mesh_objects(context)

    if not objects:
        return []

    if uv_sync_enabled(context):
        return get_mesh_selection_targets(context)

    if _mgs_last_selection_source == "UV":
        uv_targets = []

        for obj in objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.active

            if uv_layer is None:
                continue

            selected_uvs = get_selected_uv_loops(
                context,
                bm,
                uv_layer
            )

            if selected_uvs:
                uv_targets.append(
                    (obj, bm, uv_layer, selected_uvs)
                )

        return uv_targets

    return get_mesh_selection_targets(context)


def move_selected_uvs(
    context,
    delta_u,
    delta_v
):
    """
    Move UVs corresponding to currently selected 3D mesh geometry across all
    objects participating in multi-object Edit Mode.
    """

    targets = get_operation_targets(context)

    if not targets:
        return False, "No mesh geometry is selected in the 3D View."

    for obj, bm, uv_layer, loops in targets:
        for loop in loops:
            uv = loop[uv_layer].uv
            uv.x += delta_u
            uv.y += delta_v

        bmesh.update_edit_mesh(
            obj.data,
            loop_triangles=False,
            destructive=False
        )

    return True, None


# -----------------------------------------------------------------------------
# Preset movement
# -----------------------------------------------------------------------------

def move_uvs_to_tile(
    context,
    target_u,
    target_v
):
    """
    Assign selected 3D mesh geometry to a target FS25 UV tile.

    Each UV keeps its exact local position inside its current tile. Only the
    integer tile coordinate is replaced. This allows selected light parts that
    currently occupy different tiles to converge into the same target tile
    without changing their UV layout, shape, scale, or relative position
    inside a tile.
    """

    targets = get_operation_targets(context)

    if not targets:
        return False, "No mesh geometry is selected in the 3D View."

    moved_anything = False

    for obj, bm, uv_layer, loops in targets:
        if not loops:
            continue

        for loop in loops:
            uv = loop[uv_layer].uv

            # Preserve the UV's local position within its current 1x1 tile.
            local_u = uv.x - math.floor(uv.x)
            local_v = uv.y - math.floor(uv.y)

            # Replace only the tile coordinate.
            uv.x = target_u + local_u
            uv.y = target_v + local_v

        bmesh.update_edit_mesh(
            obj.data,
            loop_triangles=False,
            destructive=False
        )

        moved_anything = True

    if not moved_anything:
        return False, "No UV data found."

    return True, None


# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------

class MGS_PT_LightPanel(bpy.types.Panel):

    bl_label = "MGS Light Types"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'MGS'

    button1 = "Default Light"
    button2 = "Default Light & High Beam"
    button3 = "High Beam"
    button4 = "Bottom Light"
    button5 = "Top Light"
    button6 = "DRL"
    button7 = "Turn Light Left"
    button8 = "Turn Light Right"

    button9 = "Back Light"
    button10 = "Brake Light"
    button11 = "Back & Brake Light"
    button12 = "Reverse Light"
    button13 = "Work Light Front"
    button14 = "Work Light Back"
    button15 = "Work Light Additional"
    button16 = "Work Light Additional 2"

    def draw(self, context):

        layout = self.layout

        layout.label(
            text="Selectable Light Type"
        )

        row = layout.row()

        col_left = row.column()
        col_right = row.column()

        col_left.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button1
        ).location = "0 / 0"

        col_left.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button2
        ).location = "1 / 0"

        col_left.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button3
        ).location = "2 / 0"

        col_left.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button4
        ).location = "3 / 0"

        col_left.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button5
        ).location = "4 / 0"

        col_left.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button6
        ).location = "5 / 0"

        col_left.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button7
        ).location = "6 / 0"

        col_left.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button8
        ).location = "7 / 0"

        col_right.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button9
        ).location = "0 / 1"

        col_right.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button10
        ).location = "1 / 1"

        col_right.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button11
        ).location = "2 / 1"

        col_right.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button12
        ).location = "3 / 1"

        col_right.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button13
        ).location = "4 / 1"

        col_right.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button14
        ).location = "5 / 1"

        col_right.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button15
        ).location = "6 / 1"

        col_right.operator(
            "mgs.move_light",
            icon='LIGHT',
            text=self.button16
        ).location = "7 / 1"

        layout.separator()

        layout.label(
            text="Move UV:"
        )

        col_main = layout.column(
            align=True
        )

        row_top = col_main.row(
            align=True
        )

        row_top.scale_y = 1.5
        row_top.alignment = 'CENTER'

        row_top.operator(
            "mgs.move_up",
            icon='TRIA_UP',
            text=""
        )

        row_middle = col_main.row(
            align=True
        )

        row_middle.alignment = 'CENTER'

        row_middle.operator(
            "mgs.move_left",
            icon='TRIA_LEFT',
            text=""
        )

        row_middle.operator(
            "mgs.move_center",
            text="●",
            emboss=False
        )

        row_middle.operator(
            "mgs.move_right",
            icon='TRIA_RIGHT',
            text=""
        )

        row_bottom = col_main.row(
            align=True
        )

        row_bottom.scale_y = 1.5
        row_bottom.alignment = 'CENTER'

        row_bottom.operator(
            "mgs.move_down",
            icon='TRIA_DOWN',
            text=""
        )


# -----------------------------------------------------------------------------
# Arrow operators
# -----------------------------------------------------------------------------

class MGS_OT_MoveBase:

    bl_options = {
        'REGISTER',
        'UNDO'
    }

    delta_u = 0.0
    delta_v = 0.0

    def execute(self, context):

        success, error = move_selected_uvs(
            context,
            self.delta_u,
            self.delta_v
        )

        if not success:

            self.report(
                {'WARNING'},
                error
            )

            return {'CANCELLED'}

        return {'FINISHED'}


class MGS_OT_MoveDown(
    MGS_OT_MoveBase,
    bpy.types.Operator
):

    bl_idname = 'mgs.move_down'
    bl_label = 'Move Light Down'

    delta_u = 0.0
    delta_v = -1.0


class MGS_OT_MoveUp(
    MGS_OT_MoveBase,
    bpy.types.Operator
):

    bl_idname = 'mgs.move_up'
    bl_label = 'Move Light Up'

    delta_u = 0.0
    delta_v = 1.0


class MGS_OT_MoveLeft(
    MGS_OT_MoveBase,
    bpy.types.Operator
):

    bl_idname = 'mgs.move_left'
    bl_label = 'Move Light Left'

    delta_u = -1.0
    delta_v = 0.0


class MGS_OT_MoveRight(
    MGS_OT_MoveBase,
    bpy.types.Operator
):

    bl_idname = 'mgs.move_right'
    bl_label = 'Move Light Right'

    delta_u = 1.0
    delta_v = 0.0


class MGS_OT_MoveCenter(
    bpy.types.Operator
):

    bl_idname = 'mgs.move_center'
    bl_label = 'Center Light'

    def execute(self, context):
        return {'FINISHED'}


# -----------------------------------------------------------------------------
# Light preset operator
# -----------------------------------------------------------------------------

class MGS_OT_MoveLight(
    bpy.types.Operator
):

    bl_idname = 'mgs.move_light'
    bl_label = 'Move Light to Custom Location'

    bl_options = {
        'REGISTER',
        'UNDO'
    }

    location: bpy.props.StringProperty()

    def execute(self, context):

        try:

            x_location, y_location = (
                self.location.split('/')
            )

            target_u = float(
                x_location.strip()
            )

            target_v = float(
                y_location.strip()
            )

        except (
            ValueError,
            AttributeError
        ):

            self.report(
                {'ERROR'},
                "Invalid light tile location."
            )

            return {'CANCELLED'}

        success, error = move_uvs_to_tile(
            context,
            target_u,
            target_v
        )

        if not success:

            self.report(
                {'WARNING'},
                error
            )

            return {'CANCELLED'}

        return {'FINISHED'}


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

classes = (
    MGS_OT_SelectionSourceTracker,
    MGS_PT_LightPanel,
    MGS_OT_MoveDown,
    MGS_OT_MoveUp,
    MGS_OT_MoveLeft,
    MGS_OT_MoveRight,
    MGS_OT_MoveCenter,
    MGS_OT_MoveLight
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    if not bpy.app.timers.is_registered(
        start_selection_source_tracker
    ):
        bpy.app.timers.register(
            start_selection_source_tracker,
            first_interval=0.25
        )


def unregister():
    global _mgs_tracker_running
    _mgs_tracker_running = False

    if bpy.app.timers.is_registered(
        start_selection_source_tracker
    ):
        bpy.app.timers.unregister(
            start_selection_source_tracker
        )

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
