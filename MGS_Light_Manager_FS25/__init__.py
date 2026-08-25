bl_info = {
    'name': 'MGS Light Manager for FS25',
    'author': 'MyGameSteam',
    'blender': (3, 0, 0),
    'version': (1, 1, 1),
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


def move_selected_uvs(
    context,
    delta_u,
    delta_v
):
    """
    Move selected UVs across ALL mesh objects currently in Edit Mode.

    Examples:

    Two objects + A in UV Editor:
        both UV sets move.

    One island selected:
        only that island moves.

    UV selection across several objects:
        all selected UVs move.
    """

    objects = get_edit_mesh_objects(context)

    if not objects:
        return False, "No mesh objects are in Edit Mode."

    moved_anything = False

    for obj in objects:

        bm = bmesh.from_edit_mesh(obj.data)

        uv_layer = bm.loops.layers.uv.active

        if uv_layer is None:
            continue

        selected = get_selected_uv_loops(
            context,
            bm,
            uv_layer
        )

        if not selected:
            continue

        for loop in selected:

            uv = loop[uv_layer].uv

            uv.x += delta_u
            uv.y += delta_v

        bmesh.update_edit_mesh(
            obj.data,
            loop_triangles=False,
            destructive=False
        )

        moved_anything = True

    if not moved_anything:
        return False, "No UVs are selected."

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
    Move the current selected UVs to a target FS25 tile.

    Selection may span several objects.

    All selected UVs move by the SAME offset so their relative
    positions remain unchanged.
    """

    objects = get_edit_mesh_objects(context)

    if not objects:
        return False, "No mesh objects are in Edit Mode."

    affected = []

    # Gather selected UVs from every object.
    for obj in objects:

        bm = bmesh.from_edit_mesh(obj.data)

        uv_layer = bm.loops.layers.uv.active

        if uv_layer is None:
            continue

        selected = get_selected_uv_loops(
            context,
            bm,
            uv_layer
        )

        if selected:

            affected.append(
                (
                    obj,
                    bm,
                    uv_layer,
                    selected
                )
            )

    # No explicit UV selection.
    #
    # Preserve older MGS behavior by falling back to the active object's
    # complete UV map.
    if not affected:

        obj = context.edit_object

        if obj is None or obj.type != 'MESH':
            return False, "No UV data found."

        bm = bmesh.from_edit_mesh(obj.data)

        uv_layer = bm.loops.layers.uv.active

        if uv_layer is None:
            return False, "The active mesh has no UV map."

        loops = get_all_uv_loops(bm)

        if not loops:
            return False, "No UV data found."

        affected.append(
            (
                obj,
                bm,
                uv_layer,
                loops
            )
        )

    # Use the first affected UV to determine which tile the
    # selected group currently occupies.
    first_obj, first_bm, first_uv_layer, first_loops = affected[0]

    first_uv = first_loops[0][first_uv_layer].uv

    current_u = math.floor(first_uv.x)
    current_v = math.floor(first_uv.y)

    delta_u = target_u - current_u
    delta_v = target_v - current_v

    # Apply the exact same offset to every selected UV across every object.
    for obj, bm, uv_layer, loops in affected:

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
    MGS_PT_LightPanel,
    MGS_OT_MoveDown,
    MGS_OT_MoveUp,
    MGS_OT_MoveLeft,
    MGS_OT_MoveRight,
    MGS_OT_MoveCenter,
    MGS_OT_MoveLight
)


register, unregister = (
    bpy.utils.register_classes_factory(
        classes
    )
)
