import bpy
from bpy.types import Camera, Context, Object, Operator, Scene
from typing import List

from .SRR_Settings import SRR_Settings
from .utils.message_box import ShowMessageBox
from .utils.render_tiles import RenderTile, TileCameraSplitSettings, generate_tiles
from .utils.saved_render_settings import SavedRenderSettings, save_render_settings


class SRR_OT_SplitCamera(Operator):
    bl_idname = "render.superres_splitcam"
    bl_label = "Split Active Camera"
    bl_description = "Subdivides the active Camera"

    tiles: List[RenderTile] = None
    saved_settings: SavedRenderSettings = None

    def execute(self, context: Context):
        active_object: Object = bpy.context.active_object
        if not active_object or active_object.type != 'CAMERA':
            ShowMessageBox("You must select a camera as the active object.", title="Error", icon='WARN')
            return {'CANCELLED'}

        self.saved_settings = save_render_settings(context, camera_object=active_object)

        self.tiles = generate_tiles(context, self.saved_settings)
        if not self.tiles:
            ShowMessageBox("No tiles to render.")
            return {'CANCELLED'}

        for tile in self.tiles:
            print(str(tile))
            self.split_camera(context, camera_object=active_object, tile=tile)

        self.report({'INFO'}, "Selected camera has been split")

        return {'FINISHED'}

    def split_camera(self, context: Context, camera_object: Object, tile: RenderTile):
        tile_settings: TileCameraSplitSettings = tile.tile_settings

        # deselect everything
        for o in context.view_layer.objects.selected:
            o: Object
            o.select_set(False)

        # select original camera
        camera_object.select_set(True)
        context.view_layer.objects.active = camera_object

        # duplicate camera
        bpy.ops.object.duplicate()

        # apply settings to new camera
        new_camera = context.view_layer.objects.active
        new_camera.name = tile_settings.camera_name

        camera_data: Camera = new_camera.data
        camera_data.lens_unit = 'MILLIMETERS'
        camera_data.lens = tile_settings.f_len
        camera_data.dof.aperture_fstop = tile_settings.fstop
        camera_data.shift_x = tile_settings.shift_x
        camera_data.shift_y = tile_settings.shift_y
