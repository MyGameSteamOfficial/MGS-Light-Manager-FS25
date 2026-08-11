bl_info = {
    'name': 'MGS Light Manager for FS25',
    'author': 'MyGameSteam',
    'blender': (3, 0, 0),
    'version': (1, 1, 0),
    'description': 'Manage FS25 light UV types and UV tile adjustments.',
    'warning': 'This tool modifies UV maps directly. Use with caution.',
    'location': 'UV Editor > Sidebar > MGS',
    'category': 'Game Engine',
    'license': 'GPL-3.0'
}

# Licensed under the GNU General Public License, version 3 (GPLv3)
# Full license text available in the LICENSE file or at https://www.gnu.org/licenses/gpl-3.0.txt

import bpy
import bmesh
import math


# -----------------------------------------------------------------------------
# Compatibility helpers
# -----------------------------------------------------------------------------

def _get_edit_bmesh(context):
    obj = context.edit_object

    if obj is None or obj.type != 'MESH':
        return None, None, None, 'A mesh object must be in Edit Mode.'

    if obj.mode != 'EDIT':
        return None, None, None, 'The mesh must be in Edit Mode.'

    bm = bmesh.from_edit_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.active

    if uv_layer is None:
        return None, None, None, 'The active mesh has no UV map.'

    return obj, bm, uv_layer, None


def _uv_loop_selected(bm, face, loop, uv_layer):
    """Return whether a UV loop is selected on both legacy Blender and 5.x."""

    # Blender 5.0+ moved UV selection off BMLoopUV and onto BMLoop/BMFace.
    if bpy.app.version >= (5, 0, 0):
        # Keep the BMesh UV selection state synchronized before reading it.
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

        # When UV Sync Selection is enabled, mesh selection is authoritative.
        if context_uv_sync_enabled():
            return face.select and loop.vert.select

        return False

    # Blender 3.x / 4.x legacy UV selection API.
    luv = loop[uv_layer]
    try:
        return bool(luv.select or luv.select_edge)
    except AttributeError:
        return bool(getattr(luv, 'select', False))


def context_uv_sync_enabled():
    try:
        return bool(bpy.context.scene.tool_settings.use_uv_select_sync)
    except AttributeError:
        return False


def _selected_uv_loops(bm, uv_layer):
    selected = []
    for face in bm.faces:
        for loop in face.loops:
            if _uv_loop_selected(bm, face, loop, uv_layer):
                selected.append(loop)
    return selected


def _all_uv_loops(bm):
    return [loop for face in bm.faces for loop in face.loops]


def _translate_loops(obj, bm, uv_layer, loops, du, dv):
    if not loops:
        return False

    for loop in loops:
        uv = loop[uv_layer].uv
        uv.x += du
        uv.y += dv

    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
    return True


def _translate_selected(context, du, dv):
    obj, bm, uv_layer, error = _get_edit_bmesh(context)
    if error:
        return False, error

    loops = _selected_uv_loops(bm, uv_layer)
    if not loops:
        return False, 'Select one or more UVs first.'

    _translate_loops(obj, bm, uv_layer, loops, du, dv)
    return True, None


def _move_to_tile(context, target_u, target_v):
    """
    Move selected UVs to the requested FS25 tile.
    If no UVs are selected, move the complete active UV map instead.
    """
    obj, bm, uv_layer, error = _get_edit_bmesh(context)
    if error:
        return False, error

    selected = _selected_uv_loops(bm, uv_layer)
    loops = selected if selected else _all_uv_loops(bm)

    if not loops:
        return False, 'No UV data found.'

    # Match the original MGS behavior: use the first affected UV to determine
    # the current integer tile, then shift the entire affected selection as one.
    first_uv = loops[0][uv_layer].uv
    current_u = math.floor(first_uv.x)
    current_v = math.floor(first_uv.y)

    du = target_u - current_u
    dv = target_v - current_v

    _translate_loops(obj, bm, uv_layer, loops, du, dv)
    return True, None


# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------

class MGS_PT_LightPanel(bpy.types.Panel):
    bl_label = 'MGS Light Types'
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'MGS'

    button1 = 'Default Light'
    button2 = 'Default Light & High Beam'
    button3 = 'High Beam'
    button4 = 'Bottom Light'
    button5 = 'Top Light'
    button6 = 'DRL'
    button7 = 'Turn Light Left'
    button8 = 'Turn Light Right'

    button9 = 'Back Light'
    button10 = 'Brake Light'
    button11 = 'Back & Brake Light'
    button12 = 'Reverse Light'
    button13 = 'Work Light Front'
    button14 = 'Work Light Back'
    button15 = 'Work Light Additional'
    button16 = 'Work Light Additional 2'

    def draw(self, context):
        layout = self.layout

        layout.label(text='Selectable Light Type')

        row = layout.row()
        col_left = row.column()
        col_right = row.column()

        col_left.operator('mgs.move_light', icon='LIGHT', text=self.button1).location = '0 / 0'
        col_left.operator('mgs.move_light', icon='LIGHT', text=self.button2).location = '1 / 0'
        col_left.operator('mgs.move_light', icon='LIGHT', text=self.button3).location = '2 / 0'
        col_left.operator('mgs.move_light', icon='LIGHT', text=self.button4).location = '3 / 0'
        col_left.operator('mgs.move_light', icon='LIGHT', text=self.button5).location = '4 / 0'
        col_left.operator('mgs.move_light', icon='LIGHT', text=self.button6).location = '5 / 0'
        col_left.operator('mgs.move_light', icon='LIGHT', text=self.button7).location = '6 / 0'
        col_left.operator('mgs.move_light', icon='LIGHT', text=self.button8).location = '7 / 0'

        col_right.operator('mgs.move_light', icon='LIGHT', text=self.button9).location = '0 / 1'
        col_right.operator('mgs.move_light', icon='LIGHT', text=self.button10).location = '1 / 1'
        col_right.operator('mgs.move_light', icon='LIGHT', text=self.button11).location = '2 / 1'
        col_right.operator('mgs.move_light', icon='LIGHT', text=self.button12).location = '3 / 1'
        col_right.operator('mgs.move_light', icon='LIGHT', text=self.button13).location = '4 / 1'
        col_right.operator('mgs.move_light', icon='LIGHT', text=self.button14).location = '5 / 1'
        col_right.operator('mgs.move_light', icon='LIGHT', text=self.button15).location = '6 / 1'
        col_right.operator('mgs.move_light', icon='LIGHT', text=self.button16).location = '7 / 1'

        layout.separator()
        layout.label(text='Move UV:')

        col_main = layout.column(align=True)

        row_top = col_main.row(align=True)
        row_top.scale_y = 1.5
        row_top.alignment = 'CENTER'
        row_top.operator('mgs.move_up', icon='TRIA_UP', text='')

        row_middle = col_main.row(align=True)
        row_middle.alignment = 'CENTER'
        row_middle.operator('mgs.move_left', icon='TRIA_LEFT', text='')
        row_middle.operator('mgs.move_center', text='●', emboss=False)
        row_middle.operator('mgs.move_right', icon='TRIA_RIGHT', text='')

        row_bottom = col_main.row(align=True)
        row_bottom.scale_y = 1.5
        row_bottom.alignment = 'CENTER'
        row_bottom.operator('mgs.move_down', icon='TRIA_DOWN', text='')


# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------

class MGS_OT_MoveBase:
    bl_options = {'REGISTER', 'UNDO'}

    delta_u = 0.0
    delta_v = 0.0

    def execute(self, context):
        success, error = _translate_selected(context, self.delta_u, self.delta_v)
        if not success:
            self.report({'WARNING'}, error)
            return {'CANCELLED'}
        return {'FINISHED'}


class MGS_OT_MoveDown(MGS_OT_MoveBase, bpy.types.Operator):
    bl_idname = 'mgs.move_down'
    bl_label = 'Move Light Down'
    delta_u = 0.0
    delta_v = -1.0


class MGS_OT_MoveUp(MGS_OT_MoveBase, bpy.types.Operator):
    bl_idname = 'mgs.move_up'
    bl_label = 'Move Light Up'
    delta_u = 0.0
    delta_v = 1.0


class MGS_OT_MoveLeft(MGS_OT_MoveBase, bpy.types.Operator):
    bl_idname = 'mgs.move_left'
    bl_label = 'Move Light Left'
    delta_u = -1.0
    delta_v = 0.0


class MGS_OT_MoveRight(MGS_OT_MoveBase, bpy.types.Operator):
    bl_idname = 'mgs.move_right'
    bl_label = 'Move Light Right'
    delta_u = 1.0
    delta_v = 0.0


class MGS_OT_MoveCenter(bpy.types.Operator):
    bl_idname = 'mgs.move_center'
    bl_label = 'Center Light'

    def execute(self, context):
        return {'FINISHED'}


class MGS_OT_MoveLight(bpy.types.Operator):
    bl_idname = 'mgs.move_light'
    bl_label = 'Move Light to Custom Location'
    bl_options = {'REGISTER', 'UNDO'}

    location: bpy.props.StringProperty()

    def execute(self, context):
        try:
            x_location, y_location = self.location.split('/')
            target_u = float(x_location.strip())
            target_v = float(y_location.strip())
        except (ValueError, AttributeError):
            self.report({'ERROR'}, 'Invalid light tile location.')
            return {'CANCELLED'}

        success, error = _move_to_tile(context, target_u, target_v)
        if not success:
            self.report({'WARNING'}, error)
            return {'CANCELLED'}

        return {'FINISHED'}


classes = (
    MGS_PT_LightPanel,
    MGS_OT_MoveDown,
    MGS_OT_MoveUp,
    MGS_OT_MoveLeft,
    MGS_OT_MoveRight,
    MGS_OT_MoveCenter,
    MGS_OT_MoveLight,
)

register, unregister = bpy.utils.register_classes_factory(classes)
