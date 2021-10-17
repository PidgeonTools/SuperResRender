import bpy
from bpy.types import Context
import gc
import os
from array import array
from math import ceil
from typing import List, NamedTuple

from ..SRR_Settings import SRR_Settings
from .file import get_file_ext, get_tile_filepath, get_tile_suffix


class MergeTile(NamedTuple):
    dimensions: tuple
    offset: tuple
    filepath: str


def generate_tiles_for_merge(context: Context) -> List[MergeTile]:
    scene = context.scene

    render = scene.render
    settings: SRR_Settings = scene.srr_settings

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
    tiles: List[MergeTile] = []
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

            tile_suffix = get_tile_suffix(current_col, current_row)
            filepath = get_tile_filepath(tile_suffix)
            tile = MergeTile(
                dimensions = (tile_x, tile_y),
                offset = (offset_x, offset_y),
                filepath = filepath,
            )

            tiles.append(tile)

            offset_x += max_tile_x

    return tiles


def do_merge_tiles(context: Context, tiles: List[MergeTile]) -> None:
    scene = context.scene

    render = scene.render

    res_x = render.resolution_x
    res_y = render.resolution_y

    # Potentially free up memory from a previous merge
    final_image_name = "super_res_render_output"
    if final_image_name in bpy.data.images.keys():
        print("Removing previous merge image from Blender's memory...")
        try:
            final_image = bpy.data.images[final_image_name]
            final_image.buffers_free()
        except Exception as e:
            print("Error freeing previous merge image:", e)
        finally:
            bpy.data.images.remove(final_image)
            final_image = None
            gc.collect()

    try:
        print(f"Allocating storage for {res_x * res_y * 4} floats ({res_x * res_y} output pixels)...")
        final_image_pixels = array('f', [0.0, 0.0, 0.0, 0.0] * res_x * res_y)
        bytes_allocated = final_image_pixels.buffer_info()[1] * final_image_pixels.itemsize
        print(f"Allocated {bytes_allocated / 1024 / 1024:,.2f} MBytes of memory.\n")

        for (dimensions, offset, filepath) in tiles:
            tile_x, tile_y = dimensions
            offset_x, offset_y = offset

            print(f"Loading tile: {filepath}")

            try:
                tile_image = bpy.data.images.load(filepath, check_existing=False)
                image_x, image_y = tile_image.size

                if not (image_x == tile_x and image_y == tile_y):
                    raise RuntimeError(f"Image tile {filepath} has incorrect dimensions {image_x}x{image_y}! Expected {tile_x}x{tile_y}.")

                if not tile_image.channels == 4:
                    raise RuntimeError(f"Image tile {filepath} has {tile_image.channels} channels! Expected 4.")

                # Copy the pixels
                tile_pixels = list(tile_image.pixels)

                for y in range(tile_y):
                    # Copy a row
                    source_pixel_start = y * tile_x * 4
                    source_pixel_end = source_pixel_start + (tile_x * 4)

                    target_y = offset_y + y
                    target_pixel_start = (target_y * res_x + offset_x) * 4
                    target_pixel_end = target_pixel_start + (tile_x * 4)

                    final_image_pixels[target_pixel_start:target_pixel_end] = array('f', tile_pixels[source_pixel_start:source_pixel_end])

                del tile_pixels
                print(f"Copied {tile_x * tile_y} pixels OK.")

            finally:
                tile_image.buffers_free()
                bpy.data.images.remove(tile_image)
                del tile_image

    except Exception as e:
        print("Error compositing image tiles:", e)
        raise

    # Free up any memory still held by loaded images
    print("\nFreeing image memory...")
    gc.collect()

    if not len(final_image_pixels) == res_x * res_y * 4:
        raise RuntimeError(f"Got {len(final_image_pixels)} pixels; expected {res_x * res_y * 4}.")

    final_image_ext = get_file_ext(render.image_settings.file_format)
    final_image_filepath = "//super_res_render_output" # TODO: allow customisation of output path - GitHub issue #1
    final_image_filepath = bpy.path.ensure_ext(final_image_filepath, final_image_ext)
    final_image_filepath = os.path.realpath(bpy.path.abspath(final_image_filepath))

    print(f'Composited output OK. Saving to "{final_image_filepath}" ...')

    final_image = bpy.data.images.new(final_image_name, alpha=True, float_buffer=True, width=res_x, height=res_y)
    final_image.alpha_mode = 'STRAIGHT'
    final_image.colorspace_settings.name = 'Linear'
    final_image.generated_type = 'BLANK'
    final_image.filepath_raw = final_image_filepath
    final_image.file_format = render.image_settings.file_format

    if bpy.app.version < (2, 83):
        # Poor users that haven't upgraded to 2.83, I hope you have more than 26 gigs of RAM...
        final_image.pixels[:] = final_image_pixels.tolist()
    else:
        # This is so. much. better.!
        final_image.pixels.foreach_set(final_image_pixels)

    final_image.save_render(final_image_filepath)

    del final_image_pixels
    final_image.buffers_free()
    bpy.data.images.remove(final_image)
    final_image = None
    gc.collect()
