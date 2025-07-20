
import os
import bpy
from bpy.types import Operator

class ImportModelsOperator(Operator):
    bl_idname = "agr.import_models"
    bl_label = "Import models"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    # @classmethod
    # def poll(cls, context):
    #     ob = context.active_object
    #     return(ob and ob.type == 'MESH' and context.mode == 'EDIT_MESH')

    def execute(self, context):
        for root, dirs, files in os.walk(bpy.path.abspath("//")):
            for file in files:
                if file[:4].isdigit(): # low poly
                    continue
                if file.endswith(".fbx"):
                    bpy.ops.import_scene.fbx(filepath = root + "\\" + file)
                    print(f"import {file}")
                    print(f"scene property Address = {context.scene.agr_scene_properties.Address}")
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)