import bpy
from bpy.types import Camera, Collection, Context, Object, Operator, Scene
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
            ShowMessageBox("You must select a camera as the active object.", title="Error", icon='ERROR')
            return {'CANCELLED'}

        self.saved_settings = save_render_settings(context, camera_object=active_object)

        self.tiles = generate_tiles(context, self.saved_settings)
        if not self.tiles:
            ShowMessageBox("No tiles to render.")
            return {'CANCELLED'}

        # create an Empty to parent all the new cameras onto
        parent_empty = self.make_empty(context, camera_object=active_object)

        # split cameras
        new_cameras: List[Object] = []
        for tile in self.tiles:
            new_camera = self.split_camera(context, camera_object=active_object, tile=tile)
            new_cameras.append(new_camera)

        # parent the cameras onto the Empty
        self.deselect_all(context)
        for camera in new_cameras:
            camera.select_set(True)
        parent_empty.select_set(True)
        context.view_layer.objects.active = parent_empty
        bpy.ops.object.parent_set(type='OBJECT')

        ShowMessageBox(f"Selected camera has been split into {len(new_cameras)} new cameras")

        return {'FINISHED'}

    def deselect_all(self, context: Context):
        for obj in context.view_layer.objects.selected:
            obj: Object
            obj.select_set(False)

    def split_camera(self, context: Context, camera_object: Object, tile: RenderTile) -> Object:
        tile_settings: TileCameraSplitSettings = tile.tile_settings

        self.deselect_all(context)

        # select original camera
        camera_object.select_set(True)
        context.view_layer.objects.active = camera_object

        # duplicate camera
        bpy.ops.object.duplicate()

        # apply settings to new camera
        new_camera: Object = context.view_layer.objects.active
        new_camera.name = tile_settings.camera_name

        camera_data: Camera = new_camera.data
        camera_data.lens_unit = 'MILLIMETERS'
        camera_data.lens = tile_settings.f_len
        camera_data.dof.aperture_fstop = tile_settings.fstop
        camera_data.shift_x = tile_settings.shift_x
        camera_data.shift_y = tile_settings.shift_y

        return new_camera

    def make_empty(self, context: Context, camera_object: Object) -> Object:
        # put the empty in the same location as the original camera
        camera_location = camera_object.location
        bpy.ops.object.empty_add(type='PLAIN_AXES', align='WORLD', location=camera_location, scale=(1, 1, 1))
        empty: Object = context.view_layer.objects.active
        empty.name = f"{self.saved_settings.old_camera_name}_Split"

        # link the Empty to all the same collections as the parent camera
        for collection in camera_object.users_collection:
            collection: Collection
            try:
                collection.objects.link(empty)
            except RuntimeError:
                # the object might already be in this collection
                pass

        # add the Empty to the same parent as the original camera, if it has one
        if camera_object.parent:
            parent_object = camera_object.parent

            self.deselect_all(context)

            empty.select_set(True)
            parent_object.select_set(True)
            context.view_layer.objects.active = parent_object
            bpy.ops.object.parent_set(type='OBJECT')

        return empty
