
import os
import bpy
import bmesh
from bpy.types import Operator
from bpy.props import StringProperty, PointerProperty, IntProperty, FloatProperty, BoolProperty, CollectionProperty, EnumProperty

from .utills import create_udim_sets, _td_errors
from . import logger

class TDValuesSetOperator(Operator):
    bl_idname = "agr.td_values_set"
    bl_label = "td_values_set"
    bl_description = "Заполнить значения нижней и верхней границы"
    bl_options = {'REGISTER', 'UNDO'}

    is_highpoly: BoolProperty()

    def execute(self, context):
        props = context.scene.agr_scene_properties
        if self.is_highpoly:
            props.td_min = 512
            props.td_max = 1706
        else:
            props.td_min = 10
            props.td_max = 40
        return {'FINISHED'}

class SelectTexelLessOperator(Operator):
    bl_idname = "agr.select_texel_less"
    bl_label = "select_texel_less"
    bl_description = "Показать полигоны у выбранного обьекта с плотностью пикселей меньше допустимой"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return(ob and ob.type == 'MESH')

    def execute(self, context):
        obj = bpy.context.active_object
        name = obj.name.replace("_Main", "")

        td_min = context.scene.agr_scene_properties.td_min
        td_max = context.scene.agr_scene_properties.td_max
        texture_size_enum = context.scene.agr_scene_properties.texture_size_enum
        if texture_size_enum == "Custom":
            texture_size = context.scene.agr_scene_properties.texture_size
        else:
            texture_size = int(texture_size_enum)

        td_less_indices, td_greater_indices = _td_errors(obj, texture_size, td_min, td_max)
        # logger.add(f"out_udim_errors count = {len(out_udim_face_indices)}")
        logger.add(f"err_faces count = {len(td_less_indices)}")

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.mesh.select_mode(type="FACE")
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        bm.faces.ensure_lookup_table()
        for i in td_less_indices:
            # obj.data.polygons[i].select = True
            bm.faces[i].select = True

        bmesh.update_edit_mesh(me)

        # for root, dirs, files in os.walk(bpy.path.abspath("//")):
        #     if os.path.basename(root) == name:
        #         udim_set = create_udim_sets(root)
        #         logger.add(f"udim_set = {udim_set.resolutions_by_number}")

        #         td_min = context.scene.agr_scene_properties.td_min
        #         td_max = context.scene.agr_scene_properties.td_max

        #         td_less_indices, td_greater_indices, out_udim_face_indices = _td_errors(obj, udim_set.resolutions_by_number, True, td_min, td_max)
        #         logger.add(f"out_udim_errors count = {len(out_udim_face_indices)}")
        #         logger.add(f"err_faces count = {len(td_less_indices)}")
                
        #         bpy.ops.object.mode_set(mode='EDIT')
        #         bpy.ops.mesh.select_all(action = 'DESELECT')
        #         bpy.ops.mesh.select_mode(type="FACE")
        #         me = obj.data
        #         bm = bmesh.from_edit_mesh(me)
        #         bm.faces.ensure_lookup_table()
        #         for i in td_less_indices:
        #             # obj.data.polygons[i].select = True
        #             bm.faces[i].select = True

        #         bmesh.update_edit_mesh(me)
            
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)

class SelectTexelGreaterOperator(Operator):
    bl_idname = "agr.select_texel_greater"
    bl_label = "select_texel_greater"
    bl_description = "Показать полигоны у выбранного обьекта с плотностью пикселей больше допустимой"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return(ob and ob.type == 'MESH')

    def execute(self, context):
        obj = bpy.context.active_object
        name = obj.name.replace("_Main", "")

        td_min = context.scene.agr_scene_properties.td_min
        td_max = context.scene.agr_scene_properties.td_max
        texture_size_enum = context.scene.agr_scene_properties.texture_size_enum
        if texture_size_enum == "Custom":
            texture_size = context.scene.agr_scene_properties.texture_size
        else:
            texture_size = int(texture_size_enum)
        td_less_indices, td_greater_indices = _td_errors(obj, texture_size, td_min, td_max)
        # logger.add(f"out_udim_errors count = {len(out_udim_face_indices)}")
        logger.add(f"err_faces count = {len(td_greater_indices)}")

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.mesh.select_mode(type="FACE")
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        bm.faces.ensure_lookup_table()
        for i in td_greater_indices:
            # obj.data.polygons[i].select = True
            bm.faces[i].select = True

        bmesh.update_edit_mesh(me)

        # for root, dirs, files in os.walk(bpy.path.abspath("//")):
        #     if os.path.basename(root) == name:
        #         udim_set = create_udim_sets(root)
        #         logger.add(f"udim_set = {udim_set.resolutions_by_number}")

        #         td_min = context.scene.agr_scene_properties.td_min
        #         td_max = context.scene.agr_scene_properties.td_max

        #         td_less_indices, td_greater_indices, out_udim_face_indices = _td_errors(obj, udim_set.resolutions_by_number, True, td_min, td_max)
        #         logger.add(f"out_udim_errors count = {len(out_udim_face_indices)}")
        #         logger.add(f"err_faces count = {len(td_greater_indices)}")
                
        #         bpy.ops.object.mode_set(mode='EDIT')
        #         bpy.ops.mesh.select_all(action = 'DESELECT')
        #         bpy.ops.mesh.select_mode(type="FACE")
        #         me = obj.data
        #         bm = bmesh.from_edit_mesh(me)
        #         bm.faces.ensure_lookup_table()
        #         for i in td_greater_indices:
        #             # obj.data.polygons[i].select = True
        #             bm.faces[i].select = True

        #         bmesh.update_edit_mesh(me)
            
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)

class SelectUdimOutOperator(Operator):
    bl_idname = "agr.select_out_udim"
    bl_label = "select_out_udim"
    bl_description = "select_out_udim"
    bl_options = {'REGISTER', 'UNDO'}

    # @classmethod
    # def poll(cls, context):
    #     ob = context.active_object
    #     return(ob and ob.type == 'MESH' and context.mode == 'EDIT_MESH')

    def execute(self, context):
        # obj = bpy.context.active_object
        # name = obj.name.replace("_Main", "")
        # for root, dirs, files in os.walk(bpy.path.abspath("//")):
        #     if os.path.basename(root) == name:
        #         udim_set = create_udim_sets(root)
        #         logger.add(f"udim_set = {udim_set.resolutions_by_number}")

        #         td_min = context.scene.agr_scene_properties.td_min
        #         td_max = context.scene.agr_scene_properties.td_max

        #         td_less_indices, td_greater_indices, out_udim_face_indices = _td_errors_by_udim(obj, udim_set.resolutions_by_number, True, td_min, td_max)
        #         logger.add(f"out_udim_errors count = {len(out_udim_face_indices)}")
        #         logger.add(f"err_faces count = {len(td_greater_indices)}")
                
        #         bpy.ops.object.mode_set(mode='EDIT')
        #         bpy.ops.mesh.select_all(action = 'DESELECT')
        #         bpy.ops.mesh.select_mode(type="FACE")
        #         me = obj.data
        #         bm = bmesh.from_edit_mesh(me)
        #         bm.faces.ensure_lookup_table()
        #         for i in out_udim_face_indices:
        #             # obj.data.polygons[i].select = True
        #             bm.faces[i].select = True

        #         bmesh.update_edit_mesh(me)
            
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)