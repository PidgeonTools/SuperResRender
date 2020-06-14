# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name" : "[Pidgeon Tools] Super Resolution Render",
    "author" : "Kevin Lorengel, Chris Bond (Kamikaze)",
    "description" : "Render in extreme resolution!",
    "blender" : (2, 83, 0),
    "version" : (0, 0, 1),
    "location" : "Properties > RenderSettings > SuperResRender",
    "warning" : "",
    "category" : "Render"
}

import bpy
import time
from bpy.types import (
    Operator,
    PropertyGroup,
)
from bpy.props import (
    BoolProperty,
    EnumProperty,
    PointerProperty,
)
from math import ceil
from typing import NamedTuple


SUBDIVISION_SIZES = (
    ('1', "2 x 2", "Break the render into 2 x 2 tiles"),
    ('2', "4 x 4", "Break the render into 4 x 4 tiles"),
    ('3', "8 x 8", "Break the render into 8 x 8 tiles"),
    ('4', "16 x 16", "Break the render into 16 x 16 tiles"),
)


class SuperResRenderSettings(PropertyGroup):
    subdivisions: EnumProperty(
        name="Tiles",
        items=SUBDIVISION_SIZES,
        default='1',
        description="Subdivisions of rendered image into tiles"
    )

    # private state
    is_rendering: BoolProperty(
        name="Rendering",
        description="Currently rendering",
        default=False
    )
    should_stop: BoolProperty(
        name="Stop",
        description="User requested stop",
        default=False
    )


class RenderTile(NamedTuple):
    dimensions: tuple
    f_len: float
    shift: tuple
    filepath: str

class SavedRenderSettings(NamedTuple):
    old_file_path: str
    old_file_format: str
    old_resolution_percentage: int
    old_res_x: int
    old_res_y: int
    old_shift_x: float
    old_shift_y: float
    old_focal_length: float
    old_focal_unit: str
    old_camera_name: str


def save_render_settings(context):
    scene = context.scene
    cam = scene.camera
    render = scene.render

    return SavedRenderSettings(
        old_file_path = render.filepath,
        old_file_format = render.image_settings.file_format,
        old_resolution_percentage = render.resolution_percentage,
        old_res_x = render.resolution_x,
        old_res_y = render.resolution_y,
        old_shift_x = cam.data.shift_x,
        old_shift_y = cam.data.shift_y,
        old_focal_length = cam.data.lens,
        old_focal_unit = cam.data.lens_unit,
        old_camera_name = cam.name,
    )


def restore_render_settings(context, settings: SavedRenderSettings):
    scene = context.scene
    cam = scene.camera
    render = scene.render

    render.filepath = settings.old_file_path
    render.image_settings.file_format = settings.old_file_format
    render.resolution_percentage = settings.old_resolution_percentage 
    render.resolution_x = settings.old_res_x
    render.resolution_y = settings.old_res_y
    cam.data.shift_x = settings.old_shift_x
    cam.data.shift_y = settings.old_shift_y
    cam.data.lens_unit = settings.old_focal_unit
    cam.data.lens = settings.old_focal_length
    cam.name = settings.old_camera_name


def do_render_tile(context, settings: RenderTile):
    scene = context.scene
    cam = scene.camera
    render = scene.render

    # Rename Camera
    cam.name = "SuperResRenderCam"

    # Prepare render settings
    (tile_x, tile_y) = settings.dimensions
    f_len = settings.f_len
    # (x, y) = settings.tile_offset
    (shift_x, shift_y) = settings.shift
    filepath = settings.filepath

    print('\nRendering tile:')
    print(f'tile_x: {tile_x}, tile_y: {tile_y}')
    print(f'Camera focal length: {f_len}mm')
    # print(f'offset x: {x}, offset y: {y}')
    print(f'shift x: {shift_x}, shift_y: {shift_y}')

    render.filepath = filepath
    # render.image_settings.file_format = 'PNG'
    render.resolution_percentage = 100
    render.resolution_x = tile_x
    render.resolution_y = tile_y
    cam.data.lens_unit = 'MILLIMETERS'
    cam.data.lens = f_len
    cam.data.shift_x = shift_x
    cam.data.shift_y = shift_y

    # Render tile
    print('Rendering tile %s ...' % filepath)
    bpy.ops.render.render("INVOKE_DEFAULT", write_still = True)


def generate_tiles(context, saved_settings):
    scene = context.scene

    cam = scene.camera
    render = scene.render
    settings = scene.srr_settings

    # Get image dimensions
    res_x = render.resolution_x
    res_y = render.resolution_y
    focal_length = saved_settings.old_focal_length

    # Calculate things
    # Divisions | Tiling | Tile Count
    #     1     |   2x2  |      4
    #     2     |   4x4  |     16
    #     3     |   8x8  |     64
    #     4     |  16x16 |    256
    number_divisions = int(settings.subdivisions)

    tiles_per_side = 2 ** number_divisions
    total_tiles = tiles_per_side ** 2
    max_tile_x = ceil(res_x / tiles_per_side)
    max_tile_y = ceil(res_y / tiles_per_side)
    last_tile_x = res_x - (max_tile_x * (tiles_per_side - 1))
    last_tile_y = res_y - (max_tile_y * (tiles_per_side - 1))
    print(f'number_divisions: {number_divisions}')
    print(f'tiles: {tiles_per_side}x{tiles_per_side} = {total_tiles} tiles')
    print(f'tile size: {max_tile_x}x{max_tile_y}px')
    print(f'last tile size: {last_tile_x}x{last_tile_y}px')

    def get_offset(col, row, tile_x, tile_y, is_last_col, is_last_row):
        offset_x = res_x - (tile_x / 2) if is_last_col else (col + 0.5) * tile_x
        offset_y = res_y - (tile_y / 2) if is_last_row else (row + 0.5) * tile_y
        return (offset_x, offset_y)

    def get_shift(x, y, tile_x, tile_y):
        widest_aspect = tile_x if tile_x >= tile_y else tile_y
        shift_x = ((-res_x / 2) + x) / widest_aspect
        shift_y = ((res_y / 2) - y) / widest_aspect
        return (shift_x, shift_y)

    # Create tiles
    tiles = []
    for current_row in range(tiles_per_side):
        # Start a new row
        is_last_row = current_row == (tiles_per_side - 1)

        for current_col in range(tiles_per_side):
            # Start a new column
            is_last_col = current_col == (tiles_per_side - 1)

            print(f'row {current_row}, col {current_col}')
            print(f'Last row? {"YES" if is_last_row else "no"} Last col? {"YES" if is_last_col else "no"}')

            # Set Resolution (and aspect ratio)
            tile_x = last_tile_x if is_last_col else max_tile_x
            tile_y = last_tile_y if is_last_row else max_tile_y
            print(f'tile_x: {tile_x}, tile_y: {tile_y}')

            # Set CameraZoom
            f_len = focal_length * res_x / tile_x if tile_x >= tile_y else focal_length * res_x / tile_y
            print(f'Camera focal length: {f_len}mm')

            # Set Camera Shift
            (x, y) = get_offset(current_col, current_row, tile_x, tile_y, is_last_col, is_last_row)
            print(f'offset x: {x}, offset y: {y}')
            (shift_x, shift_y) = get_shift(x, y, tile_x, tile_y)
            print(f'shift_x: {shift_x}')
            print(f'shift_y: {shift_y}')

            # Render
            filepath = f'//PartRenders\\Part{(current_row + 1):02}R{(current_col + 1):02}C'
            tile = RenderTile(
                dimensions = (tile_x, tile_y),
                f_len = f_len,
                shift = (shift_x, shift_y),
                filepath = filepath,
            )

            tiles.append(tile)

    return tiles


# Modal (Timer loop)

class SRR_OT_Render(bpy.types.Operator):
    bl_idname = "render.superres"
    bl_label = "Super Render"
    bl_description = "Subdivides your Image"

    _timer = None
    stop = None
    rendering = None
    tiles = None
    saved_settings = None

    # Render callbacks
    def render_pre(self, scene, dummy):
        self.rendering = True

    def render_post(self, scene, dummy):
        # We're done with this tile.
        self.tiles.pop(0)
        # Move on to the next
        self.rendering = False

    def render_cancel(self, scene, dummy):
        self.stop = True

    def execute(self, context):
        scene = context.scene
        settings = scene.srr_settings

        # Reset state
        self.stop = False
        self.rendering = False
        settings.is_rendering = True
        settings.should_stop = False

        # Save settings
        self.saved_settings = save_render_settings(context)

        # Prepare tiles
        print('\n\n--------------')
        print('Preparing tiles...')
        self.tiles = generate_tiles(context, self.saved_settings)

        # Setup callbacks
        bpy.app.handlers.render_pre.append(self.render_pre)
        bpy.app.handlers.render_post.append(self.render_post)
        bpy.app.handlers.render_cancel.append(self.render_cancel)

        # Setup timer and modal
        self._timer = context.window_manager.event_timer_add(0.5, window=context.window)
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        scene = context.scene
        settings = scene.srr_settings

        if event.type == 'ESC':
            self.stop = True

        if event.type == 'TIMER':
            if True in (not self.tiles, self.stop is True, settings.should_stop is True):
                print('\n*** STOPPING!')
                # Remove callbacks & clean up
                bpy.app.handlers.render_pre.remove(self.render_pre)
                bpy.app.handlers.render_post.remove(self.render_post)
                bpy.app.handlers.render_cancel.remove(self.render_cancel)
                context.window_manager.event_timer_remove(self._timer)

                was_cancelled = True in (self.stop is True, settings.should_stop is True)
                settings.should_stop = False
                settings.is_rendering = False

                restore_render_settings(context, self.saved_settings)

                if was_cancelled:
                    return {'CANCELLED'}
                return {'FINISHED'}

            elif self.rendering is False:
                print('\n=== Ready to render!')
                tile = self.tiles[0]
                print(tile)

                do_render_tile(context, tile)

        # Allow stop button to cancel rendering rather than this modal
        return {'PASS_THROUGH'}


class SRR_OT_StopRender(bpy.types.Operator):
    bl_idname = "render.superres_kill"
    bl_label = "Stop Super Render"

    def execute(self, context):
        context.scene.srr_settings.should_stop = True

        return {'FINISHED'}


# Interface

class SRR_UI_PT_Panel(bpy.types.Panel):
    bl_idname = "SRR_PT_Render_Still"
    bl_label = "Render Frame"
    bl_category = "SuperResRender"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        render = scene.render
        settings = scene.srr_settings

        res_x = render.resolution_x
        res_y = render.resolution_y

        number_divisions = int(settings.subdivisions)
        tiles_per_side = 2 ** number_divisions
        total_tiles = tiles_per_side ** 2
        max_tile_x = ceil(res_x / tiles_per_side)
        max_tile_y = ceil(res_y / tiles_per_side)


        layout.separator()
        layout.label(text="Subdivide render:")

        col = layout.column(align=True)
        col.prop(settings, "subdivisions")

        col = layout.column(align=True)
        col.label(text="Max tile: %ipx x %ipx" % (max_tile_x, max_tile_y))

        col = layout.column(align=True)
        col.label(text="Total: %i tiles" % total_tiles)

        col = layout.column(align=True)
        col.separator()
        # col.operator('render.superres', text="Render Frame")
        if context.scene.srr_settings.is_rendering is True:
            col.operator('render.superres_kill', text='Cancel', icon='CANCEL')
        else:
            col.operator('render.superres', text='Render Frame')


# Addon Registration

classes = (
    SuperResRenderSettings,
    SRR_OT_Render,
    SRR_OT_StopRender,
    SRR_UI_PT_Panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.srr_settings = PointerProperty(
        type=SuperResRenderSettings
    )

def unregister():
    del bpy.types.Scene.srr_settings

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
