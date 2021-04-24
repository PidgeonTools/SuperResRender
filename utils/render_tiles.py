import bpy
from bpy.types import Context
from math import ceil
from typing import List, NamedTuple

from ..SRR_Settings import SRR_Settings
from .saved_render_settings import save_render_settings
from .file import get_tile_filepath


class RenderTile(NamedTuple):
    dimensions: tuple
    f_len: float
    fstop: float
    shift: tuple
    filepath: str
    file_format: str


def do_render_tile(context: Context, settings: RenderTile):
    scene = context.scene
    cam = scene.camera
    render = scene.render

    # Rename Camera
    cam.name = "SuperResRenderCam"

    # Prepare render settings
    (tile_x, tile_y) = settings.dimensions
    f_len = settings.f_len
    fstop = settings.fstop
    # (x, y) = settings.tile_offset
    (shift_x, shift_y) = settings.shift
    filepath = settings.filepath
    file_format = settings.file_format

    # print("\nRendering tile:")
    # print(f"tile_x: {tile_x}, tile_y: {tile_y}")
    # print(f"Camera focal length: {f_len}mm")
    # print(f"offset x: {x}, offset y: {y}")
    # print(f"shift x: {shift_x}, shift_y: {shift_y}")

    render.filepath = filepath
    render.image_settings.file_format = file_format
    render.resolution_percentage = 100
    render.resolution_x = tile_x
    render.resolution_y = tile_y
    cam.data.lens_unit = 'MILLIMETERS'
    cam.data.lens = f_len
    cam.data.dof.aperture_fstop = fstop
    cam.data.shift_x = shift_x
    cam.data.shift_y = shift_y

    # Render tile
    # print("Rendering tile %s ..." % filepath)
    bpy.ops.render.render("INVOKE_DEFAULT", write_still = True)


def generate_tiles(context: Context, saved_settings: save_render_settings) -> List[RenderTile]:
    scene = context.scene

    render = scene.render
    settings: SRR_Settings = scene.srr_settings

    # Get image dimensions
    res_x = render.resolution_x
    res_y = render.resolution_y
    focal_length = saved_settings.old_focal_length
    aperture_fstop = saved_settings.old_aperture_fstop

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
    tiles: List[RenderTile] = []
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
            fstop = aperture_fstop * (f_len / focal_length)
            # print(f"Camera fstop: {fstop}")

            # Set Camera Shift
            (x, y) = get_offset(current_col, current_row, tile_x, tile_y, is_last_col, is_last_row)
            # print(f"offset x: {x}, offset y: {y}")
            (shift_x, shift_y) = get_shift(x, y, tile_x, tile_y)
            # print(f"shift_x: {shift_x}")
            # print(f"shift_y: {shift_y}")

            # Render
            filepath = get_tile_filepath(current_col, current_row)
            tile = RenderTile(
                dimensions = (tile_x, tile_y),
                f_len = f_len,
                fstop = fstop,
                shift = (shift_x, shift_y),
                filepath = filepath,
                file_format = 'OPEN_EXR',
            )

            tiles.append(tile)

    return tiles
