import bpy
from bpy.types import Panel
from math import ceil

from .SRR_Settings import SRR_RenderStatus, SRR_Settings


# Interface

class SRR_UI_PT_Panel(Panel):
    bl_label = "Super Res Render Frame"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"
    bl_category = "Pidgeon-Tools"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        render = scene.render
        settings: SRR_Settings = scene.srr_settings
        status: SRR_RenderStatus = settings.status

        res_x = render.resolution_x
        res_y = render.resolution_y

        number_divisions = int(settings.subdivisions)
        tiles_per_side = 2 ** number_divisions
        total_tiles = tiles_per_side ** 2
        ideal_tile_x = res_x / tiles_per_side
        ideal_tile_y = res_y / tiles_per_side
        max_tile_x = ceil(ideal_tile_x)
        max_tile_y = ceil(ideal_tile_y)

        panel_active = not status.is_rendering


        layout.separator()
        layout.label(text="Subdivide render:")

        col = layout.column(align=True)
        col.active = panel_active
        col.prop(settings, 'render_method')
        col.separator()
        col.prop(settings, "subdivisions")
        col.separator()

        if settings.render_method == 'camsplit':
            col = layout.column(align=True)
            col.label(text=f"Suggested resolution: {max_tile_x}px x {max_tile_y}px ({(100 / tiles_per_side):.3g}%)")

        else:
            col = layout.column(align=True)
            col.label(text=f"Max tile: {max_tile_x}px x {max_tile_y}px")

        col = layout.column(align=True)
        col.label(text=f"Total: {total_tiles} tiles")
        col.separator()

        if settings.render_method == 'camsplit':
            col = layout.column(align=True)
            col.operator('render.superres_splitcam', text="Split Active Camera", icon='MESH_GRID')

        else:
            col = layout.column(align=True)
            col.prop(settings, "start_tile")
            col.separator()

            col = layout.column(align=True)
            if status.is_rendering:
                col.label(text=f"{status.tiles_done} / {status.tiles_total} tiles rendered", icon='INFO')
                col.prop(status, "percent_complete")
                col.operator('render.superres_kill', text="Cancel", icon='CANCEL')
            else:
                col.operator('render.superres', text="Render Frame")
            col.separator()

            col = layout.column(align=True)
            col.active = panel_active
            col.operator('render.superres_merge', text="Merge Tiles", icon='MESH_GRID')

        layout.separator()
        col = layout.column()
        op = col.operator("wm.url_open", text="Support", icon="URL")
        op.url = "https://discord.gg/cnFdGQP"
