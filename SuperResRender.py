import bpy
import os
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

class MergeTile(NamedTuple):
    dimensions: tuple
    offset: tuple
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

    # print("\nRendering tile:")
    # print(f"tile_x: {tile_x}, tile_y: {tile_y}")
    # print(f"Camera focal length: {f_len}mm")
    # print(f"offset x: {x}, offset y: {y}")
    # print(f"shift x: {shift_x}, shift_y: {shift_y}")

    render.filepath = filepath
    # render.image_settings.file_format = 'PNG'
    render.image_settings.file_format = 'OPEN_EXR'
    render.resolution_percentage = 100
    render.resolution_x = tile_x
    render.resolution_y = tile_y
    cam.data.lens_unit = 'MILLIMETERS'
    cam.data.lens = f_len
    cam.data.shift_x = shift_x
    cam.data.shift_y = shift_y

    # Render tile
    # print("Rendering tile %s ..." % filepath)
    bpy.ops.render.render("INVOKE_DEFAULT", write_still = True)


def do_merge_tiles(context, tiles):
    scene = context.scene

    render = scene.render

    res_x = render.resolution_x
    res_y = render.resolution_y

    try:
        print(f"Allocating {res_x * res_y * 4} image pixels...")
        final_image_pixels = [0.] * res_x * res_y * 4

        for (dimensions, offset, filepath) in tiles:
            print("\n--- New tile:")

            tile_x, tile_y = dimensions
            offset_x, offset_y = offset

            print(f"Dimensions: {tile_x}x{tile_y}")
            print(f"Offset: {offset_x}, {offset_y}")
            print(f"File path: {filepath}")

            try:
                tile_image = bpy.data.images.load(filepath, check_existing=False)
                image_x, image_y = tile_image.size

                print(f"Loaded image tile: {filepath}")
                print(f"Loaded image dimensions: {image_x}x{image_y}")

                if not (image_x == tile_x and image_y == tile_y):
                    raise RuntimeError(f"Image tile {filepath} has incorrect dimensions ({image_x}x{image_y})! Expected ({tile_x}x{tile_y}).")

                if not tile_image.channels == 4:
                    raise RuntimeError(f"Image tile {filepath} has incorrect number of channels ({tile_image.channels})! Expected 4.")

                # Copy the pixels
                tile_pixels = list(tile_image.pixels)
                for y in range(tile_y):
                    # Copy a row
                    source_pixel_start = y * tile_x * 4
                    source_pixel_end = source_pixel_start + (tile_x * 4)
                    # print(f"  Row {y}: {source_pixel_start}-{source_pixel_end}")

                    target_y = offset_y + y
                    target_pixel_start = (target_y * res_x + offset_x) * 4
                    target_pixel_end = target_pixel_start + (tile_x * 4)
                    # print(f"  Target: {offset_x}, {target_y}: {target_pixel_start}-{target_pixel_end}")

                    final_image_pixels[target_pixel_start:target_pixel_end] = tile_pixels[source_pixel_start:source_pixel_end]

                print("Copied image tile data OK.")

            finally:
                bpy.data.images.remove(tile_image)

    except Exception as e:
        print(e)
        raise

    final_image_name = "super_res_render_output"
    final_image_ext = '.png' # TODO
    final_image_filepath = "//super_res_render_output" # TODO
    final_image_filepath = bpy.path.ensure_ext(final_image_filepath, final_image_ext)
    final_image_filepath = os.path.realpath(bpy.path.abspath(final_image_filepath))

    if final_image_name in bpy.data.images.keys():
        bpy.data.images.remove(bpy.data.images[final_image_name])

    if len(final_image_pixels) == res_x * res_y * 4:
        print("Final image pixels count OK")
    else:
        print(f"Got {len(final_image_pixels)} pixels; expected {res_x * res_y * 4}.")

    final_image = bpy.data.images.new(final_image_name, alpha=True, width=res_x, height=res_y)
    final_image.alpha_mode = 'STRAIGHT'
    final_image.pixels = final_image_pixels
    final_image.filepath_raw = final_image_filepath
    # final_image.file_format = render.image_settings.file_format
    final_image.file_format = 'PNG' # TODO
    final_image.save()

    return


def get_tile_filepath(context, col, row):
    file_extension = ".exr"
    filepath = f"//PartRenders\\Part_R{(row + 1):02}_C{(col + 1):02}{file_extension}"
    return filepath


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
    # print(f"number_divisions: {number_divisions}")
    # print(f"tiles: {tiles_per_side}x{tiles_per_side} = {total_tiles} tiles")
    # print(f"tile size: {max_tile_x}x{max_tile_y}px")
    # print(f"last tile size: {last_tile_x}x{last_tile_y}px")

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

            # print(f"row {current_row}, col {current_col}")
            # print(f"Last row? {"YES" if is_last_row else "no"} Last col? {"YES" if is_last_col else "no"}")

            # Set Resolution (and aspect ratio)
            tile_x = last_tile_x if is_last_col else max_tile_x
            tile_y = last_tile_y if is_last_row else max_tile_y
            # print(f"tile_x: {tile_x}, tile_y: {tile_y}")

            # Set CameraZoom
            f_len = focal_length * res_x / tile_x if tile_x >= tile_y else focal_length * res_x / tile_y
            # print(f"Camera focal length: {f_len}mm")

            # Set Camera Shift
            (x, y) = get_offset(current_col, current_row, tile_x, tile_y, is_last_col, is_last_row)
            # print(f"offset x: {x}, offset y: {y}")
            (shift_x, shift_y) = get_shift(x, y, tile_x, tile_y)
            # print(f"shift_x: {shift_x}")
            # print(f"shift_y: {shift_y}")

            # Render
            filepath = get_tile_filepath(context, current_col, current_row)
            tile = RenderTile(
                dimensions = (tile_x, tile_y),
                f_len = f_len,
                shift = (shift_x, shift_y),
                filepath = filepath,
            )

            tiles.append(tile)

    return tiles


def generate_tiles_for_merge(context):
    scene = context.scene

    render = scene.render
    settings = scene.srr_settings

    res_x = render.resolution_x
    res_y = render.resolution_y

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

    # Create tiles
    tiles = []
    offset_y = res_y
    for current_row in range(tiles_per_side):
        # Start a new row
        is_last_row = current_row == (tiles_per_side - 1)

        # Set vertical resolution
        tile_y = last_tile_y if is_last_row else max_tile_y
        # Set vertical offset (image data runs bottom-to-top)
        offset_y -= tile_y

        offset_x = 0

        for current_col in range(tiles_per_side):
            # Start a new column
            is_last_col = current_col == (tiles_per_side - 1)

            # Set horizontal resolution
            tile_x = last_tile_x if is_last_col else max_tile_x

            filepath = get_tile_filepath(context, current_col, current_row)
            tile = MergeTile(
                dimensions = (tile_x, tile_y),
                offset = (offset_x, offset_y),
                filepath = filepath,
            )

            tiles.append(tile)

            offset_x += max_tile_x

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
        # print("\n\n--------------")
        # print("Preparing tiles...")
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
                # print("\n*** STOPPING!")
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
                # print("\n=== Ready to render!")
                tile = self.tiles[0]
                # print(tile)

                do_render_tile(context, tile)

        # Allow stop button to cancel rendering rather than this modal
        return {'PASS_THROUGH'}


class SRR_OT_StopRender(bpy.types.Operator):
    bl_idname = "render.superres_kill"
    bl_label = "Stop Super Render"

    def execute(self, context):
        context.scene.srr_settings.should_stop = True

        return {'FINISHED'}


class SRR_OT_Merge(bpy.types.Operator):
    bl_idname = "render.superres_merge"
    bl_label = "Super Res Merge Tiles"
    bl_description = "Merge rendered tiles into final resolution image"

    @classmethod
    def poll(self, context):
        scene = context.scene
        settings = scene.srr_settings

        return not settings.is_rendering is True

    def execute(self, context):
        scene = context.scene
        settings = scene.srr_settings

        print("Merge tiles!")

        tiles = generate_tiles_for_merge(context)

        do_merge_tiles(context, tiles)

        print("Merge tiles done!")

        return {'FINISHED'}


# Interface

class SRR_UI_PT_Panel(bpy.types.Panel):

    bl_label = "Super Res Render Frame"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"
    bl_category = "Pidgeon-Tools"

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
        if context.scene.srr_settings.is_rendering is True:
            col.operator('render.superres_kill', text="Cancel", icon='CANCEL')
        else:
            col.operator('render.superres', text="Render Frame")

        col = layout.column(align=True)
        col.separator()
        col.operator('render.superres_merge', text="Merge Tiles", icon='MESH_GRID')


# Addon Registration

classes = (
    SuperResRenderSettings,
    SRR_OT_Render,
    SRR_OT_StopRender,
    SRR_OT_Merge,
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
