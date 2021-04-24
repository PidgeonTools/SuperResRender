import bpy
from bpy.types import Context
from typing import NamedTuple


class SavedRenderSettings(NamedTuple):
    old_file_path: str
    old_file_format: str
    old_resolution_percentage: int
    old_res_x: int
    old_res_y: int
    old_shift_x: float
    old_shift_y: float
    old_aperture_fstop: float
    old_focal_length: float
    old_focal_unit: str
    old_use_border: bool
    old_use_crop_to_border: bool
    old_border_min_x: float
    old_border_min_y: float
    old_border_max_x: float
    old_border_max_y: float


def save_render_settings(context: Context):
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
        old_aperture_fstop = cam.data.dof.aperture_fstop,
        old_focal_length = cam.data.lens,
        old_focal_unit = cam.data.lens_unit,
        old_use_border = render.use_border,
        old_use_crop_to_border = render.use_crop_to_border,
        old_border_min_x = render.border_min_x,
        old_border_min_y = render.border_min_y,
        old_border_max_x = render.border_max_x,
        old_border_max_y = render.border_max_y,
    )


def restore_render_settings(context: Context, settings: SavedRenderSettings):
    scene = context.scene
    cam = scene.camera
    render = scene.render

    render.filepath = settings.old_file_path
    render.image_settings.file_format = settings.old_file_format
    render.resolution_percentage = settings.old_resolution_percentage 
    render.resolution_x = settings.old_res_x
    render.resolution_y = settings.old_res_y
    render.use_border = settings.old_use_border
    render.use_crop_to_border = settings.old_use_crop_to_border
    render.border_min_x = settings.old_border_min_x
    render.border_min_y = settings.old_border_min_y
    render.border_max_x = settings.old_border_max_x
    render.border_max_y = settings.old_border_max_y
    cam.data.shift_x = settings.old_shift_x
    cam.data.shift_y = settings.old_shift_y
    cam.data.dof.aperture_fstop = settings.old_aperture_fstop
    cam.data.lens_unit = settings.old_focal_unit
    cam.data.lens = settings.old_focal_length
