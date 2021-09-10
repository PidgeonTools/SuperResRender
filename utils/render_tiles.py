import bpy
from bpy.types import Camera, Context, Object
from math import ceil
from typing import List, NamedTuple, Union

from ..SRR_Settings import SRR_Settings
from .saved_render_settings import SavedRenderSettings
from .file import get_tile_filepath, get_tile_suffix


class RenderTileCameraShiftSettings(NamedTuple):
    tile_x: int
    tile_y: int
    f_len: float
    fstop: float
    shift_x: float
    shift_y: float

class TileCameraSplitSettings(NamedTuple):
    camera_name: str
    f_len: float
    fstop: float
    shift_x: float
    shift_y: float

class RenderTileRenderBorderSettings(NamedTuple):
    border_min_x: float
    border_min_y: float
    border_max_x: float
    border_max_y: float

TileSettings = Union[
    RenderTileCameraShiftSettings,
    RenderTileRenderBorderSettings,
    TileCameraSplitSettings,
]

class RenderTile(NamedTuple):
    render_method: str # Python 3.8+: Literal['camshift', 'border', 'camsplit']
    tile_settings: TileSettings
    filepath: str
    file_format: str


def do_render_tile(context: Context, render_tile: RenderTile, camera_object: Object):
    scene = context.scene
    render = scene.render

    # Prepare render settings
    render.filepath = render_tile.filepath
    render.image_settings.file_format = render_tile.file_format

    if render_tile.render_method == 'camshift':
        camera_data: Camera = camera_object.data
        settings: RenderTileCameraShiftSettings = render_tile.tile_settings

        render.resolution_percentage = 100
        render.resolution_x = settings.tile_x
        render.resolution_y = settings.tile_y
        camera_data.lens_unit = 'MILLIMETERS'
        camera_data.lens = settings.f_len
        camera_data.dof.aperture_fstop = settings.fstop
        camera_data.shift_x = settings.shift_x
        camera_data.shift_y = settings.shift_y

    elif render_tile.render_method == 'border':
        settings: RenderTileRenderBorderSettings = render_tile.tile_settings

        render.use_border = True
        render.use_crop_to_border = True
        render.border_min_x = settings.border_min_x
        render.border_min_y = settings.border_min_y
        render.border_max_x = settings.border_max_x
        render.border_max_y = settings.border_max_y

    # Render tile
    # print("Rendering tile %s ..." % filepath)
    bpy.ops.render.render("INVOKE_DEFAULT", write_still = True)


def generate_tiles(context: Context, saved_settings: SavedRenderSettings) -> List[RenderTile]:
    scene = context.scene

    render = scene.render
    settings: SRR_Settings = scene.srr_settings

    # Get image dimensions
    res_x = render.resolution_x
    res_y = render.resolution_y
    focal_length = saved_settings.old_focal_length
    aperture_fstop = saved_settings.old_aperture_fstop
    existing_shift_x = saved_settings.old_shift_x
    existing_shift_y = saved_settings.old_shift_y
    aspect = res_x if res_x >= res_y else res_y
    shift_offset_x = existing_shift_x * aspect
    shift_offset_y = existing_shift_y * -aspect

    # Calculate things
    # Divisions | Tiling | Tile Count
    #     1     |   2x2  |      4
    #     2     |   4x4  |     16
    #     3     |   8x8  |     64
    #     4     |  16x16 |    256
    number_divisions = int(settings.subdivisions)

    tiles_per_side = 2 ** number_divisions
    ideal_tile_x = res_x / tiles_per_side
    ideal_tile_y = res_y / tiles_per_side
    max_tile_x = ceil(ideal_tile_x)
    max_tile_y = ceil(ideal_tile_y)
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

    def get_border(col, row, tile_x, tile_y, is_last_col, is_last_row):
        min_x = res_x - tile_x if is_last_col else col * tile_x
        max_x = res_x if is_last_col else (col + 1) * tile_x
        min_y = 0 if is_last_row else res_y - ((row + 1) * tile_y)
        max_y = tile_y if is_last_row else res_y - (row * tile_y)
        border_min_x = min_x / res_x
        border_max_x = max_x / res_x
        border_min_y = min_y / res_y
        border_max_y = max_y / res_y
        return (border_min_x, border_min_y, border_max_x, border_max_y)

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
            tile_settings: TileSettings = None
            tile_suffix = get_tile_suffix(current_col, current_row)

            # Set Resolution (and aspect ratio)
            tile_x = ideal_tile_x if settings.render_method == 'camsplit' else \
                last_tile_x if is_last_col else max_tile_x
            tile_y = ideal_tile_y if settings.render_method == 'camsplit' else \
                last_tile_y if is_last_row else max_tile_y
            # print(f"tile_x: {tile_x}, tile_y: {tile_y}")

            if settings.render_method in ['camshift', 'camsplit']:
                # Set CameraZoom
                f_len = focal_length * ((res_x / tile_x) if tile_x >= tile_y else (res_y / tile_y))
                # print(f"Camera focal length: {f_len}mm")
                fstop = aperture_fstop * (f_len / focal_length)
                # print(f"Camera fstop: {fstop}")

                # Set Camera Shift
                (x, y) = get_offset(current_col, current_row, tile_x, tile_y, is_last_col, is_last_row)
                x += shift_offset_x
                y += shift_offset_y
                # print(f"offset x: {x}, offset y: {y}")
                (shift_x, shift_y) = get_shift(x, y, tile_x, tile_y)
                # print(f"shift_x: {shift_x}")
                # print(f"shift_y: {shift_y}")

                if settings.render_method == 'camshift':
                    tile_settings = RenderTileCameraShiftSettings(
                        tile_x = tile_x,
                        tile_y = tile_y,
                        f_len = f_len,
                        fstop = fstop,
                        shift_x = shift_x,
                        shift_y = shift_y,
                    )
                elif settings.render_method == 'camsplit':
                    camera_name = f"{saved_settings.old_camera_name}{tile_suffix}"
                    tile_settings = TileCameraSplitSettings(
                        camera_name = camera_name,
                        f_len = f_len,
                        fstop = fstop,
                        shift_x = shift_x,
                        shift_y = shift_y,
                    )

            elif settings.render_method == 'border':
                (border_min_x, border_min_y, border_max_x, border_max_y) = get_border(
                    current_col, current_row, tile_x, tile_y, is_last_col, is_last_row)

                tile_settings = RenderTileRenderBorderSettings(
                    border_min_x = border_min_x,
                    border_min_y = border_min_y,
                    border_max_x = border_max_x,
                    border_max_y = border_max_y,
                )

            else:
                raise f"Unhandled render method {settings.render_method}"

            # Render
            filepath = get_tile_filepath(tile_suffix)
            tile = RenderTile(
                render_method = settings.render_method,
                tile_settings = tile_settings,
                filepath = filepath,
                file_format = 'OPEN_EXR',
            )

            tiles.append(tile)

    return tiles
