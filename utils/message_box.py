import bpy
from bpy.types import Context


def ShowMessageBox(message: str = "", title = "Information", icon = 'INFO'):

    def draw(self, context: Context):
        lines = message.splitlines()
        for line in lines:
            self.layout.label(text=line)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)
