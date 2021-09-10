import bpy
from typing import List

from bpy.types import Context, Operator, Scene, Timer

from .SRR_Settings import SRR_RenderStatus, SRR_Settings
from .utils.merge_tiles import do_merge_tiles, generate_tiles_for_merge
from .utils.message_box import ShowMessageBox
from .utils.saved_render_settings import (
    restore_render_settings,
    save_render_settings,
    SavedRenderSettings,
)
from .utils.render_tiles import RenderTile, do_render_tile, generate_tiles


# Modal (Timer loop)

class SRR_OT_Render(Operator):
    bl_idname = "render.superres"
    bl_label = "Super Render"
    bl_description = "Subdivides your Image"

    _timer: Timer = None
    stop: bool = False
    rendering: bool = False
    tiles: List[RenderTile] = None
    saved_settings: SavedRenderSettings = None

    # Render callbacks
    def render_pre(self, scene: Scene, dummy):
        self.rendering = True

    def render_post(self, scene: Scene, dummy):
        settings: SRR_Settings = scene.srr_settings
        status: SRR_RenderStatus = settings.status

        # We're done with this tile.
        self.tiles.pop(0)
        status.tiles_done += 1

        # Move on to the next
        self.rendering = False

    def render_cancel(self, scene: Scene, dummy):
        self.stop = True

    def execute(self, context: Context):
        scene = context.scene
        settings: SRR_Settings = scene.srr_settings
        status: SRR_RenderStatus = settings.status

        # Reset state
        self.stop = False
        self.rendering = False

        # Save settings
        self.saved_settings = save_render_settings(context, scene.camera)

        # Prepare tiles
        # print("\n\n--------------")
        # print("Preparing tiles...")
        self.tiles = generate_tiles(context, self.saved_settings)
        if settings.start_tile > 1:
            self.tiles = self.tiles[settings.start_tile - 1:]
        if not self.tiles:
            ShowMessageBox("No tiles to render.")
            return {'CANCELLED'}

        status.tiles_total = len(self.tiles)
        status.tiles_done = 0
        status.is_rendering = True
        status.should_stop = False

        # Setup callbacks
        bpy.app.handlers.render_pre.append(self.render_pre)
        bpy.app.handlers.render_post.append(self.render_post)
        bpy.app.handlers.render_cancel.append(self.render_cancel)

        # Setup timer and modal
        self._timer = context.window_manager.event_timer_add(0.5, window=context.window)
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def modal(self, context: Context, event):
        scene = context.scene
        settings: SRR_Settings = scene.srr_settings
        status: SRR_RenderStatus = settings.status

        if event.type == 'ESC':
            self.stop = True

        if event.type == 'TIMER':
            was_cancelled = self.stop or status.should_stop

            if was_cancelled or not self.tiles:
                # print("\n*** STOPPING!")
                # Remove callbacks & clean up
                bpy.app.handlers.render_pre.remove(self.render_pre)
                bpy.app.handlers.render_post.remove(self.render_post)
                bpy.app.handlers.render_cancel.remove(self.render_cancel)
                context.window_manager.event_timer_remove(self._timer)

                status.should_stop = False
                status.is_rendering = False

                restore_render_settings(context, self.saved_settings, scene.camera)

                if was_cancelled:
                    self.report({'WARNING'}, "Rendering aborted")
                    return {'CANCELLED'}

                self.report({'INFO'}, "Rendering done")
                ShowMessageBox("Rendering done!", "Success")
                return {'FINISHED'}

            elif self.rendering is False:
                # print("\n=== Ready to render!")
                tile = self.tiles[0]
                # print(tile)

                do_render_tile(context, tile, scene.camera)

        # Allow stop button to cancel rendering rather than this modal
        return {'PASS_THROUGH'}


class SRR_OT_StopRender(Operator):
    bl_idname = "render.superres_kill"
    bl_label = "Stop Super Render"

    def execute(self, context: Context):
        settings: SRR_Settings = context.scene.srr_settings
        status: SRR_RenderStatus = settings.status

        status.should_stop = True

        return {'FINISHED'}


class SRR_OT_Merge(Operator):
    bl_idname = "render.superres_merge"
    bl_label = "Super Res Merge Tiles"
    bl_description = "Merge rendered tiles into final resolution image"

    @classmethod
    def poll(cls, context: Context):
        scene = context.scene
        settings: SRR_Settings = scene.srr_settings
        status: SRR_RenderStatus = settings.status

        return not status.is_rendering

    def execute(self, context: Context):
        self.report({'INFO'}, "Merging tiles...")

        tiles = generate_tiles_for_merge(context)

        do_merge_tiles(context, tiles)

        self.report({'INFO'}, "Merge tiles done!")
        ShowMessageBox("Merging tiles done!", "Success")

        return {'FINISHED'}
