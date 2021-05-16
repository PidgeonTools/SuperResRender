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
    "name" : "[Pidgeon Tools] Super Resolution Render",
    "author" : "Kevin Lorengel, Chris Bond (Kamikaze)",
    "description" : "Render in extreme resolution!",
    "blender" : (2, 92, 0),
    "version" : (1, 2, 0),
    "location" : "Properties > Output > SuperResRender",
    "warning" : "",
    "category" : "Render"
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
from .SRR_Panel import (
    SRR_UI_PT_Panel,
)


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
    SRR_UI_PT_Panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.srr_settings = PointerProperty(type=SRR_Settings)

    bpy.app.handlers.load_post.append(load_handler)

def unregister():
    del bpy.types.Scene.srr_settings

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
