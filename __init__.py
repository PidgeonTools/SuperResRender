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
    "name": "Super Resolution Render (SRR)",
    "author": "Kevin Lorengel, Chris Bond (Kamikaze)",
    "description": "Render in extreme resolution!",
    "blender": (2, 92, 0),
    "version": (1, 3, 1),
    "location": "Properties > Output > SuperResRender",
    "warning": "",
    "category": "Render"
}

import bpy
from bpy.app.handlers import persistent
from bpy.props import PointerProperty

from .SRR_Settings import (
    SRR_RenderStatus,
    SRR_Settings,
)
from .SuperResRender import (
    SRR_OT_Render,
    SRR_OT_StopRender,
    SRR_OT_Merge,
)
from .SplitCamera import (
    SRR_OT_SplitCamera,
)
from .SRR_Panel import (
    SRR_UI_PT_Panel,
)
from . import addon_updater_ops


class DemoPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    # addon updater preferences

    auto_check_update: bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=True,
    )
    updater_intrval_months: bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0,
    )
    updater_intrval_days: bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31,
    )
    updater_intrval_hours: bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23,
    )
    updater_intrval_minutes: bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59,
    )

    def draw(self, context):
        layout = self.layout
        # col = layout.column() # works best if a column, or even just self.layout
        mainrow = layout.row()
        col = mainrow.column()

        # updater draw function
        # could also pass in col as third arg
        addon_updater_ops.update_settings_ui(self, context)

        # Alternate draw function, which is more condensed and can be
        # placed within an existing draw function. Only contains:
        #   1) check for update/update now buttons
        #   2) toggle for auto-check (interval will be equal to what is set above)
        # addon_updater_ops.update_settings_ui_condensed(self, context, col)

        # Adding another column to help show the above condensed ui as one column
        # col = mainrow.column()
        # col.scale_y = 2
        # col.operator("wm.url_open","Open webpage ").url=addon_updater_ops.updater.website


### Addon Registration


@persistent
def load_handler(dummy):
    try:
        settings: SRR_Settings = bpy.context.scene.srr_settings
        settings.status.is_rendering = False
        settings.status.should_stop = False
    except:
        pass


classes = (
    SRR_RenderStatus,
    SRR_Settings,
    SRR_OT_Render,
    SRR_OT_StopRender,
    SRR_OT_Merge,
    SRR_OT_SplitCamera,
    SRR_UI_PT_Panel,
    DemoPreferences,
)


def register():
    # addon updater code and configurations
    # in case of broken version, try to register the updater first
    # so that users can revert back to a working version
    addon_updater_ops.register(bl_info)

    # register the example panel, to show updater buttons
    for cls in classes:
        # to avoid blender 2.8 warnings
        addon_updater_ops.make_annotations(cls)
        bpy.utils.register_class(cls)

    bpy.types.Scene.srr_settings = PointerProperty(type=SRR_Settings)

    bpy.app.handlers.load_post.append(load_handler)


def unregister():
    del bpy.types.Scene.srr_settings
    # addon updater unregister
    addon_updater_ops.unregister()

    # register the example panel, to show updater buttons
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
