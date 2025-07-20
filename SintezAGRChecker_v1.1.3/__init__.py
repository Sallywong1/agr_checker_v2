bl_info = {
    "name": "AGR Model Checker",
    "author": "SINTEZ.SPACE",
    "version": (1, 1, 3),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > AGR Checker",
    "description": "AGR Model Checker",
    "warning": "",
    "doc_url": "",
    "category": "",
}

import os
import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import FloatVectorProperty, StringProperty, PointerProperty, IntProperty, FloatProperty, BoolProperty, CollectionProperty, EnumProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector
import addon_utils
from bpy.utils import previews

from .scripts import model_preparer
from .scripts import selection
from .scripts import ui_utills
from .scripts import properties
from .scripts import operators
from .scripts import logger
from .scripts import os_utils
from .scripts import utills


class VIEW3D_PT_Parent:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "SINTEZ AGR"
    # bl_options = {"DEFAULT_CLOSED"}

class VIEW3D_PT_Main(VIEW3D_PT_Parent, bpy.types.Panel):
    bl_idname = 'Panel_Main'
    # bl_space_type = 'VIEW_3D'
    # bl_region_type = 'UI'
    # bl_category = 'AGR Checker'
    bl_label = 'SINTEZ AGR Checker'

    def draw(self, context):
        # self.layout.prop(context.scene.agr_scene_properties, "Address")
        scene = context.scene
        scene_properties = scene.agr_scene_properties
        layout = self.layout
        

        #"C:\Users\maxko\OneDrive\Рабочий стол\temp\circumference.png"
        # if ui_utills.images:
        #     layout.template_preview(bpy.data.images[ui_utills.images[0].name])

        
        # if 'testPluginTexture' in bpy.data.textures:
        #     layout.label(text=bpy.data.textures['testPluginTexture'].name)
        #     layout.template_preview(bpy.data.textures['testPluginTexture'])

        # if 'testPluginTexture2' in bpy.data.textures:
        #     layout.label(text=bpy.data.textures['testPluginTexture2'].name)
        #     layout.template_preview(bpy.data.textures['testPluginTexture2'])
        row = layout.row()
        # row.alignment = 'LEFT'
        row.template_icon(icon_value=ui_utills.plugin_icons['sintez_alpha.png'].icon_id, scale=2.2)
        # row.alignment = 'RIGHT'

        col = row.column()
        col.scale_x = 0.45
        help_op = col.operator('wm.url_open', text='Инструкция', icon='HELP')
        help_op.url = 'https://docs.google.com/document/d/1VxtQ8otPxo6o2OmFUX0WOyl8yOaw9vqSFpaFBZsPG1c/edit?usp=sharing'
        dev_row = col.row(align=True)
        sintez_op = dev_row.operator('wm.url_open', text='Разработчик', icon='URL')
        sintez_op.url = 'https://sintez.space/plugins'
        donate_op = dev_row.operator('wm.url_open', text='Поддержать', icon_value=ui_utills.plugin_icons['red_heart_icon.png'].icon_id) # red_heart_icon.png
        donate_op.url = 'https://boosty.to/synthesismoscow'
        layout.separator(type='LINE')
        
        layout.label(text="Подготовка моделей")
        layout.prop(scene_properties, "path", text="Архивы АГР")
        # layout.separator(type='LINE')
        row = layout.row()
        row.operator(operator="agr.run_calculate_all", icon='PLAY', text="Проверить все файлы АГР (очищает blender файл)")
        row.scale_y = 1.5
        import_row = layout.row()
        import_row.operator(operator="agr.clear_blender_file_button", icon='TRASH', text="Очистить файл")
        import_row.operator(operator="agr.import_models_button", icon='IMPORT', text="Импортировать модели")
        # row.operator(operator="agr.run_calculate_all", icon_value=ui_utills.icons['test_icon.png'].icon_id)
        # layout.label(icon_value=ui_utills.icons['sintez_alpha.png'].icon_id)

        # layout.operator(operator="agr.run_calculate_all_collections", icon_value=ui_utills.icons['test_icon_2.png'].icon_id)
        # layout.operator(operator="agr.run_calculate_all_collections", icon='OUTLINER_COLLECTION')
        layout.separator(type='LINE')
        layout.label(text="Отображение модели")
        layout.prop(scene_properties, "view_mode", expand=True)
        row = layout.row()

        show_lp_icon = 'HIDE_OFF' if context.scene.agr_scene_properties.show_lp else 'HIDE_ON'
        row.prop(context.scene.agr_scene_properties, "show_lp", text="НПМ", icon=show_lp_icon)

        show_hp_icon = 'HIDE_OFF' if context.scene.agr_scene_properties.show_hp else 'HIDE_ON'
        row.prop(context.scene.agr_scene_properties, "show_hp", text="ВПМ", icon=show_hp_icon)

        show_ucx_icon = 'HIDE_OFF' if context.scene.agr_scene_properties.show_ucx else 'HIDE_ON'
        row.prop(context.scene.agr_scene_properties, "show_ucx", text="UCX", icon=show_ucx_icon)

        show_glass_icon = 'HIDE_OFF' if context.scene.agr_scene_properties.show_glass else 'HIDE_ON'
        row.prop(context.scene.agr_scene_properties, "show_glass", text="Glass", icon=show_glass_icon)

        # show_glass_grid_icon = 'HIDE_OFF' if context.scene.agr_scene_properties.show_glass_grid else 'HIDE_ON'
        # layout.prop(context.scene.agr_scene_properties, "show_glass_grid", text="Стекло сетка", icon=show_glass_grid_icon)

        layout.operator(operator="agr.glass_all_gray", text="Все стекла белые")
        # layout.operator(operator="agr.test_debug", text="import fbx")

        layout.separator(type='LINE')
        # layout.prop(scene_properties, "check_author", text="Проверяющий")
        layout.label(text="Отчет об ошибках")
        row = layout.row()
        row.operator(operator="agr.save_report_button_operator", text="Сохранить отчет")
        # row.operator(operator="agr.load_report_button_operator")
        row.operator(operator="agr.show_project_folder_button_operator", text="Показать папку")
        # layout.prop(scene_properties, "load_report_path", text="Load report")
        layout.separator(type='LINE')

class VIEW3D_PT_Checklist_Settings(VIEW3D_PT_Parent, bpy.types.Panel):
    bl_parent_id = "Panel_Main"
    bl_label = 'Настройки чеклиста'
    bl_options = {"DEFAULT_CLOSED"}
 
    def draw(self, context):
        scene = context.scene
        scene_properties = scene.agr_scene_properties
        layout = self.layout
        layout.prop(scene_properties, "Address")

        row = layout.row()
        # layout.prop(context.scene.agr_scene_properties, "experimental_checks", text="Экспериментальные проверки")
        layout.prop(context.scene.agr_scene_properties, "unlock_auto_checks", text="Разблокировать автопроверки", icon='AUTO')
        show_req_nums_icon = 'HIDE_OFF' if context.scene.agr_scene_properties.show_req_nums else 'HIDE_ON'
        layout.prop(context.scene.agr_scene_properties, "show_req_nums", text="Отображать номера проверок", icon=show_req_nums_icon)

class VIEW3D_PT_Checklist_Lowpoly(VIEW3D_PT_Parent, bpy.types.Panel):
    bl_parent_id = "Panel_Main"
    bl_label = 'НПМ Чеклист'

    def draw(self, context):
        if os_utils.check_models_path():
            ui_utills.drow_checklist(False, context, self.layout)
        else:
            ui_utills.drow_label_multiline(context, "Укажите путь к архивам, чтобы начать работу с чеклистом!", self.layout)
            # self.layout.label(text="Укажите путь к архивам, чтобы начать работу с чеклистом!")

class VIEW3D_PT_Checklist_Highpoly(VIEW3D_PT_Parent, bpy.types.Panel):
    bl_parent_id = "Panel_Main"
    bl_label = 'ВПМ Чеклист'
 
    def draw(self, context):
        if os_utils.check_models_path():
            ui_utills.drow_checklist(True, context, self.layout)
        else:
            ui_utills.drow_label_multiline(context, "Укажите путь к архивам, чтобы начать работу с чеклистом!", self.layout)
            # self.layout.label(text="Укажите путь к архивам, чтобы начать работу с чеклистом!")

class VIEW3D_PT_Check_Geojson(VIEW3D_PT_Parent, bpy.types.Panel):
    bl_parent_id = "Panel_Main"
    bl_label = 'Проверка Geojson'
    bl_options = {"DEFAULT_CLOSED"}
 
    def draw(self, context):
        if not os_utils.check_models_path():
            ui_utills.drow_label_multiline(context, "Укажите путь к архивам, чтобы начать работу с чеклистом!", self.layout)
            return
        
        scene = context.scene
        scene_properties = scene.agr_scene_properties
        layout = self.layout

        layout.label(text="Параметры для проверки Geojson")
        layout.prop(scene_properties, "geojson_ZU_area", text="ZU_area")
        layout.prop(scene_properties, "geojson_h_relief", text="h_relief")
        layout.prop(scene_properties, "geojson_s_obsh", text="s_obsh")
        layout.prop(scene_properties, "geojson_s_naz", text="s_naz")
        layout.prop(scene_properties, "geojson_s_podz", text="s_podz")
        layout.prop(scene_properties, "geojson_spp_gns", text="spp_gns")

        layout.operator(operator="agr.check_geojson", text="Проверить!")

        categories = context.scene.agr_scene_properties.geojson_categories

        layout.separator(type='LINE')

        if not categories:
            return

        rows_count = len(categories[0].collection) + 1
        columns_count = len(categories) + 1

        box = layout.box()
        row = box.row()
        cols = [row.column() for i in range(columns_count)]
        for i in range(columns_count):
            for j in range(rows_count):
                if i == 0 and j == 0:
                    cols[i].label(text="")
                elif i == 0:
                    cols[0].label(text=categories[0].collection[j-1].name)
                elif j == 0:
                    name = categories[i-1].name if categories[i-1].name else "ОКС"
                    cols[i].label(text=name)
                else:
                    # cols[i].label(text=categories[i-1].collection[j-1].description)

                    cell = cols[i].row()
                    item = categories[i-1].collection[j-1]
                    op_icon = 'CHECKMARK'
                    if item.check_state == "undefined":
                        op_icon = 'BLANK1'
                    elif item.check_state == "verified":
                        op_icon = 'CHECKMARK'
                    elif item.check_state == "failed":
                        # op_icon = 'PANEL_CLOSE'
                        op_icon = 'X'
                    cell.alignment='LEFT'
                    cell.alert = True if item.check_state == utills.CHECK_STATE_ITEMS[2] else False
                    cell.enabled = not item.auto or context.scene.agr_scene_properties.unlock_auto_checks
                    # check_op = cell.operator(operator="agr.checkbox_test_operator", icon=op_icon, text=item.description, emboss=False)
                    check_op = cell.operator(operator="agr.checkbox_test_operator", text=item.description, emboss=False)
                    # check_op.tooltip = item.description
                    check_op.tooltip = ""
                    check_op.category = item.category
                    check_op.index = j - 1
                    # check_op.is_highpoly = item.highpoly
                    check_op.geojson_list = True
                    

        return
        for cat in categories:
            row = layout.row()
            # row.emboss = 'NONE'
            icon = 'TRIA_DOWN' if cat.drow_collection else 'TRIA_RIGHT'
            show_op = row.operator(
                operator='agr.show_checklist',
                icon=icon, # RIGHTARROW, DOWNARROW_HLT
                text='',
                emboss=False
            )
            show_op.tooltip = cat.name
            # show_op.highpoly = is_highpoly
            show_op.geojson_list = True
            cat_num = ".".join(cat.collection[0].req_num.split(".")[:2]) + " "
            show_op.category_name = cat.name
            row.label(text=f"{cat_num}  {cat.name}")
            # row.operator(operator='agr.show_checklist', text='31', )
            if any([item[1].check_state == "failed" for item in cat.collection.items()]):
                row.label(text="", icon='ERROR')
            else:
                row.label(text="", icon='BLANK1')
            row.progress(text=cat.progress_text, factor=cat.progress, type = 'BAR')
            if cat.drow_collection:
                # show_op.icon = 'RIGHTARROW'
                box = layout.box()
                for i, item in enumerate(cat.collection):
                    req_row = box.row()
                    req_row.alignment='LEFT'
                    # req_row.emboss = 'NONE_OR_STATUS'
                    if not item.check:
                        # req_row.alert = True
                        pass
                    op_icon = 'CHECKMARK'
                    if item.check_state == "undefined":
                        op_icon = 'BLANK1'
                    elif item.check_state == "verified":
                        op_icon = 'CHECKMARK'
                    elif item.check_state == "failed":
                        # op_icon = 'PANEL_CLOSE'
                        op_icon = 'X'
                    # op_icon = 'CHECKMARK' if item[1].check else 'BLANK1'
                    # op_icon = 'CHECKBOX_HLT' if item[1].check else 'CHECKBOX_DEHLT'
                    check_op_split = req_row.split()
                    check_op_split.alignment='LEFT'
                    
                    check_op_split.alert = True if item.check_state == utills.CHECK_STATE_ITEMS[2] else False
                    req_num = item.req_num + "  " if context.scene.agr_scene_properties.show_req_nums else ""
                    check_op = check_op_split.operator("agr.checkbox_test_operator", icon=op_icon, text=str(i) + req_num + item.name, emboss=False)
                    check_op.tooltip = item.description
                    check_op.category = item.category
                    check_op.index = i
                    check_op.is_highpoly = item.highpoly
                    # req_row.prop(item[1], "check", text=item[1].name)
                    check_op_split.enabled = not item.auto or context.scene.agr_scene_properties.unlock_auto_checks
                    if item.auto:
                        req_row.label(icon='AUTO')
                    if item.check_state == utills.CHECK_STATE_ITEMS[2]:
                        # edit_op = req_row.operator("agr.edit_check_button", icon='WINDOW', text="", emboss=False)
                        edit_op = req_row.operator("agr.edit_check_button", icon='GREASEPENCIL', text="", emboss=False)
                        edit_op.index = i
                        edit_op.category = item.category
                        edit_op.tooltip = item.user_comment
                        edit_op.is_highpoly = item.highpoly
                        # edit_op.user_text = item[1].user_comment

                        add_img_op = req_row.operator("agr.add_image_check_button", icon='RESTRICT_RENDER_OFF', text="", emboss=False)
                        add_img_op.index = i
                        add_img_op.category = item.category
                        add_img_op.is_highpoly = item.highpoly
                    # elif item.check_state == utills.CHECK_STATE_ITEMS[0]:
                    # if not is_highpoly and item.req_num in lp_help_links.keys():
                    #     help_op = req_row.operator("wm.url_open", icon='HELP', text="", emboss=False)
                    #     help_op.url = lp_help_links[item.req_num]
                        
                    # req_row.label(text=item[1].name)
                    if item.auto and not item.check and item.errors_count > 0:
                        # split = req_row.split()
                        # req_row.alignment='RIGHT'
                        right_row = req_row.split(factor=0.6)
                        right_row.alignment='RIGHT'
                        right_row.alert = True
                        # right_row.label(text="", icon='ERROR')
                        # right_row.label(text="31")
                        err_op = right_row.operator("agr.checklist_errors", text=str(item.errors_count))
                        err_op.tooltip = item.errors_text
                        # req_row.alignment='EXPAND'
                # box.separator()
            # self.layout.template_list("CUSTOM_UL_req_list", "", cat, "collection", cat, "collection_index", rows=5)

class VIEW3D_PT_TexelDencity(VIEW3D_PT_Parent, bpy.types.Panel):
    # bl_parent_id = "Panel_Main"
    # bl_label = 'Texel Dencity'
    # bl_options = {"DEFAULT_CLOSED"}

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "SINTEZ AGR"

    bl_idname = 'Panel_TexelDensity'
    bl_label = 'Texel Density'
    bl_options = {"DEFAULT_CLOSED"}
 
    def draw(self, context):
        # self.layout.label(text="Texel density")

        scene = context.scene
        scene_properties = scene.agr_scene_properties
        layout = self.layout

        row = self.layout.row(align=True)
        row.label(text="Значения для: ")
        lp = row.operator("agr.td_values_set", text="НПМ")
        lp.is_highpoly = False
        lp = row.operator("agr.td_values_set", text="ВПМ")
        lp.is_highpoly = True

        box = layout.box()

        row = box.row(align=True)
        row.label(text="Нижняя граница (px/m):")
        row.prop(scene_properties, "td_min", text="")
        row = box.row(align=True)
        row.label(text="Верхняя граница (px/m):")
        row.prop(scene_properties, "td_max", text="")
        row = box.row(align=True)
        row.label(text="Размер текстуры (px):")
        row.prop(scene_properties, "texture_size_enum", text="")
        texture_size_enum = context.scene.agr_scene_properties.texture_size_enum
        if texture_size_enum == "Custom":
            # row = box.row()
            # row.label(text="")
            row.prop(scene_properties, "texture_size", text="")

        self.layout.operator(
            operator='agr.select_texel_less',
            text='Выбрать полигоны МЕНЬШЕ допуска'
        )

        self.layout.operator(
            operator='agr.select_texel_greater',
            text='Выбрать полигоны БОЛЬШЕ допуска'
        )

        # self.layout.operator(
        #     operator='agr.select_out_udim',
        #     text='select_udim_out'
        # )


classes = (
    properties.CUSTOM_objectCollection_Image,
    properties.CUSTOM_objectCollection,
    properties.CUSTOM_objectCollection_category,
    properties.ChecklistProperties,
    properties.AGRCheckerProperties,
    model_preparer.ImportModelsOperator,
    selection.SelectTexelLessOperator,
    selection.SelectTexelGreaterOperator,
    selection.SelectUdimOutOperator,
    selection.TDValuesSetOperator,
    VIEW3D_PT_Main,
    VIEW3D_PT_Checklist_Settings,
    VIEW3D_PT_Checklist_Lowpoly,
    VIEW3D_PT_Checklist_Highpoly,
    VIEW3D_PT_Check_Geojson,
    VIEW3D_PT_TexelDencity,
    operators.ShowChecklist,
    operators.UpdateRequrements,
    operators.ImportModelsButton,
    operators.ClearBlenderFileButton,
    operators.RunCalculate_all,
    operators.RunCalculate_all_collections,
    operators.ClearChecklist,
    operators.CheckboxTestOperator,
    operators.ErrorsButtonOperator,
    operators.CheckHelpLinkOperator,
    operators.EditCheckButton,
    operators.SaveReportButtonOperator,
    operators.ShowProjectFolderButtonOperator,
    operators.AddImageCheckButton,
    operators.ModifyImageCheckButton,
    operators.GlassAllGray,
    operators.CheckGeojson,
    operators.CheckLowpolyCode,
    operators.TestDebugOperator,
)


@bpy.app.handlers.persistent
def load_post_handler(dummy):
    pass
    # print("Event: load_post" + bpy.data.filepath)
    # logger.add("Event: load_post" + bpy.data.filepath)
    # ui_utills.update_images()

    # scene_props = bpy.context.scene.agr_scene_properties
    # scene_props.checklist_hp_props.categories.clear()
    # scene_props.checklist_lp_props.categories.clear()

    # operators.UpdateRequrements.update_requrements(True)
    # operators.UpdateRequrements.update_requrements(False)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.agr_scene_properties = PointerProperty(type=properties.AGRCheckerProperties)
    bpy.app.handlers.load_post.append(load_post_handler)

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass

    del bpy.types.Scene.agr_scene_properties
    bpy.app.handlers.load_post.remove(load_post_handler)

if __name__ == "__main__":
    register()

