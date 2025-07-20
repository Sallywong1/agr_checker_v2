import os

import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import FloatVectorProperty, StringProperty, PointerProperty, IntProperty, FloatProperty, BoolProperty, CollectionProperty, EnumProperty

from . import ui_utills
from . import utills
from . import check_highpoly_lowpoly
from . import os_utils
from . import properties
from . import check_report
from . import logger
from . import view_tools


class ShowChecklist(Operator):
    bl_idname = "agr.show_checklist"
    bl_label = "show_checklist"
    # bl_description = "show_checklist"
    # bl_options = {'REGISTER', 'UNDO'}

    category_name: StringProperty()
    highpoly: BoolProperty()
    geojson_list: BoolProperty(default=False)

    tooltip: StringProperty()

    @classmethod
    def description(cls, context, operator):
        return operator.tooltip

    def execute(self, context):
        
        scene_props = context.scene.agr_scene_properties

        if self.category_name:
            if self.geojson_list:
                categories = scene_props.geojson_categories
            else:
                categories = scene_props.checklist_hp_props.categories if self.highpoly else scene_props.checklist_lp_props.categories
            
            for cat in categories:
                if cat.name == self.category_name:
                    cat.drow_collection = not cat.drow_collection
        
        return {'FINISHED'}

class CheckboxTestOperator(Operator):
    bl_idname = "agr.checkbox_test_operator"
    bl_label = ""
    # bl_description = "show_checklist"
    # bl_options = {'REGISTER', 'UNDO'}

    tooltip: StringProperty()
    # check: BoolProperty()
    is_highpoly: BoolProperty()
    category: StringProperty()
    index: IntProperty()

    geojson_list: BoolProperty(default=False)

    @classmethod
    def description(cls, context, operator):
        return operator.tooltip

    def execute(self, context):
        ui_utills.update_checks_from_text_editor(context)


        # self.check = not self.check
        if self.geojson_list:
            categories = context.scene.agr_scene_properties.geojson_categories
        else:
            if self.is_highpoly:
                categories = context.scene.agr_scene_properties.checklist_hp_props.categories
            else:
                categories = context.scene.agr_scene_properties.checklist_lp_props.categories
        for cat in categories:
            if cat.name == self.category:
                # value = not cat.collection[self.index].check
                # cat.collection[self.index].check = value
                # self.check = value
                item = cat.collection[self.index]

                state_string = item.check_state
                state_int = utills.CHECK_STATE_ITEMS.index(state_string)
                # state_int = utills.CHECK_STATE_ITEMS[state_string]
                if self.geojson_list and state_int == 0:
                    value = (state_int + 2) % 3
                else:
                    value = (state_int + 1) % 3
                item.check_state = utills.CHECK_STATE_ITEMS[value]
                if not item.auto:
                    item.errors_count = 1 if value == 2 else 0
                # self.check = True if value == 1 else False
                item.check = True if value == 1 else False
                # logger.add(cat.collection[self.index].description)
                # logger.add(f"errors count={cat.collection[self.index].errors_count}")
                ui_utills.update_text_by_id(context, item)

                logger.add(f"edit check is_highpoly={self.is_highpoly} geojson_list={self.geojson_list} {item.req_num}, state={item.check_state}, index_in_category={item.index_in_category}")

                # context.scene.agr_scene_properties.unlock_auto_checks = False
        
        return {'FINISHED'}

class EditCheckButton(Operator):
    bl_idname = "agr.edit_check_button"
    bl_label = ""
    bl_description = "Add comment"
    # bl_options = {'REGISTER', 'UNDO'}

    tooltip: StringProperty()
    # check: BoolProperty()
    is_highpoly: BoolProperty()
    category: StringProperty()
    index: IntProperty()

    img_update_bool: BoolProperty()
    window_showed: BoolProperty()

    # user_text: StringProperty()
    # user_text_code: StringProperty()

    @classmethod
    def description(cls, context, operator):
        return operator.tooltip
    
    def invoke(self, context, event):
        # self.user_text = self.user_text_code
        self.window_showed = True
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=200)

    def execute(self, context):
        # context.window_manager.invoke_props_dialog(self)
        # self.user_text_code = self.user_text
        # return {'CANCELLED'}
        ui_utills.update_text_by_id(context, 0)
        self.window_showed = False
        return {'FINISHED'}
    
    def draw(self, context):
        layout = self.layout
        # layout.label(text=str(self.index))
        # layout.label(text=self.tooltip)
        # ui_utills.drow_label_multiline(context, self.tooltip, layout)
        # layout.prop(self, "user_text", text="Комментарий")
        # ui_utills.drow_label_multiline(context, self.user_text, layout)
        
        if self.is_highpoly:
            categories = context.scene.agr_scene_properties.checklist_hp_props.categories
        else:
            categories = context.scene.agr_scene_properties.checklist_lp_props.categories
        for cat in categories:
            if cat.name == self.category:
                item: properties.CUSTOM_objectCollection = cat.collection[self.index]
                layout.label(text=item.req_num + "  " + item.name)
                layout.prop(item, "user_comment", text="Комментарий")
                ui_utills.drow_label_multiline(context, cat.collection[self.index].user_comment, layout)

                for i, im_prop in enumerate(item.error_images):
                    # if im_prop.name in ui_utills.checks_icons:
                    if im_prop.name in ui_utills.icons_by_checks:
                        # icon_id = ui_utills.checks_icons[im_prop.name].icon_id
                        # icon_id = im_prop.image.preview.icon_id
                        icon_id = ui_utills.icons_by_checks[im_prop.name][im_prop.name].icon_id

                        box = layout.box()

                        buttons_row = box.row()

                        buttons_row.label(text=f"Image {i+1} ")

                        del_button = buttons_row.operator("agr.modify_image_check_button", text="", icon='TRASH')
                        del_button.option_text = "del"
                        del_button.image_index = i
                        del_button.category = cat.name
                        del_button.index = item.index_in_category
                        del_button.is_highpoly = item.highpoly

                        # replace_button = buttons_row.operator("agr.modify_image_check_button", text="", icon='ARROW_LEFTRIGHT')
                        # replace_button.option_text = "replace"
                        # replace_button.image_index = i
                        # replace_button.category = cat.name
                        # replace_button.index = item.index_in_category
                        # replace_button.is_highpoly = item.highpoly

                        # show_button = buttons_row.operator("agr.modify_image_check_button", text="", icon='HIDE_OFF')
                        # show_button.option_text = "show"
                        # show_button.image_index = i
                        # show_button.category = cat.name
                        # show_button.index = item.index_in_category
                        # show_button.is_highpoly = item.highpoly

                        icon_row = box.row()
                        # icon_row.scale_y = 0.5
                        icon_row.template_icon(icon_value=icon_id, scale=10)
                        # box.prop(im_prop, "comment")
                    layout.separator(type='LINE')

                # if item.img_name in ui_utills.icons:
                #     icon_id = ui_utills.icons[item.img_name].icon_id
                #     # layout.label(icon_value=icon_id)
                #     layout.template_icon(icon_value=icon_id, scale=12)

                # if item.img_name in bpy.data.textures:
                #     col = layout.column()
                #     col.template_preview(bpy.data.textures[item.img_name])

                    # if self.window_showed:
                    #     col.scale_y = 1.0
                    #     col.scale_y = 1.01
                    #     self.window_showed = False
                    # if self.img_update_bool:
                    #     col.scale_y = 1.0
                    #     self.img_update_bool = not self.img_update_bool
                    # else:
                    #     col.scale_y = 1.01
                    #     self.img_update_bool = not self.img_update_bool

                    # col.template_image(item, "image", bpy.data.textures[item.img_name].image_user)
                break

        # layout.label(text=self.user_text)
        # layout.template_popup_confirm("agr.edit_check_button", text="ok", cancel_text="cancel")

class ModifyImageCheckButton(Operator):
    bl_idname = "agr.modify_image_check_button"
    bl_label = ""
    bl_description = "modify_image"
    # bl_options = {'REGISTER', 'UNDO'}

    is_highpoly: BoolProperty()
    category: StringProperty()
    index: IntProperty()

    # item: PointerProperty(type=CUSTOM_objectCollection)

    image_index: IntProperty()

    option_text: StringProperty()

    def execute(self, context):
        if self.is_highpoly:
            categories = context.scene.agr_scene_properties.checklist_hp_props.categories
        else:
            categories = context.scene.agr_scene_properties.checklist_lp_props.categories
        for cat in categories:
            if cat.name == self.category:
                item: properties.CUSTOM_objectCollection = cat.collection[self.index]
        if self.option_text == "del":
            logger.add(f"ModifyImageCheckButton del operator")
            for im in item.error_images:
                pass

            # ui_utills.del_icon(item.error_images[self.image_index].full_path, item.error_images[self.image_index].name)
            req_name = "_".join(item.error_images[0].image.name.split("_")[:-1])
            ui_utills.clean_icons_by_check_name(req_name)

            os.remove(item.error_images[self.image_index].full_path)
            bpy.data.images.remove(item.error_images[self.image_index].image)
            item.error_images.remove(self.image_index)
            for i, im_prop in enumerate(item.error_images):
                if i >= self.image_index:
                    extention = im_prop.image.name.split(".")[-1]
                    new_name = "_".join(im_prop.image.name.split("_")[:-1]) + "_" + str(i) + "." + extention
                    full_path_new = os.path.join(os.path.split(im_prop.full_path)[0], new_name)
                    os.rename(im_prop.full_path, full_path_new)
                    im_prop.name = new_name
                    im_prop.image.name = new_name
                    im_prop.full_path = full_path_new
                    im_prop.image.filepath = full_path_new
                    im_prop.image.reload()
                    logger.add(f"new path = {full_path_new}")

                ui_utills.add_icon(im_prop.full_path, im_prop.name)

            logger.add(f"item images after del {item.error_images}")
            for im_prop in item.error_images:
                logger.add(f"{im_prop.name}  {im_prop.image}  {im_prop.full_path}")

        elif self.option_text == "replace":
            logger.add(f"ModifyImageCheckButton replace operator")

        elif self.option_text == "show":
            pass
        return {'FINISHED'}

class AddImageCheckButton(Operator):
    bl_idname = "agr.add_image_check_button"
    bl_label = ""
    bl_description = "Add Image"
    # bl_options = {'REGISTER', 'UNDO'}

    # check: BoolProperty()
    is_highpoly: BoolProperty()
    category: StringProperty()
    index: IntProperty()

    @classmethod
    def poll(cls, context):
        return os_utils.check_models_path()

    def execute(self, context):
        # output_file = "C:\\D\\bim_work\\sintez\\test_UI_Images\\output_test.png"
        # bpy.context.scene.render.image_settings.file_format = "PNG"
        # bpy.ops.render.render(write_still=True, use_viewport=True)
        # bpy.data.images["Render Result"].save_render(output_file)

        if not context.scene.agr_scene_properties.path:
            self.report({'WARNING'}, f"Для работы со скриншотами укажите папку объекта!")
            return {'FINISHED'}

        if self.is_highpoly:
            categories = context.scene.agr_scene_properties.checklist_hp_props.categories
        else:
            categories = context.scene.agr_scene_properties.checklist_lp_props.categories

        item: properties.CUSTOM_objectCollection = None
        for cat in categories:
            if cat.name == self.category:
                item = cat.collection[self.index]
                break
        if not item:
            return

        hp_lp_prefix = "HP" if self.is_highpoly else "LP"
        new_ind = len(item.error_images)
        im_name = f"AGRChecker_{hp_lp_prefix}_{item.req_num}_{new_ind}.png"
        dir_path = os_utils.get_checks_data_dir()
        file_path = os.path.join(dir_path, im_name)
        # file_path = context.scene.agr_scene_properties.path + "AGRChecker_Screenshots\\" + im_name
        bpy.context.scene.render.filepath = file_path

        for a in bpy.context.screen.areas:
            if a.type == 'VIEW_3D':
                for r in a.regions:
                    if r.type == 'WINDOW':
                        bpy.context.scene.render.resolution_x = r.width
                        bpy.context.scene.render.resolution_y = r.height
                        # logger.add(f"Viewport dimensions: {r.width}x{r.height}, approximate aspect rato: {round(r.width/r.height, 2)}")
        # bpy.context.scene.render.resolution_x = 1024
        # bpy.context.scene.render.resolution_y = 1024

        bpy.ops.render.opengl(write_still=True)
        # im1 = bpy.data.images.load(file_path, check_existing=True)
        im1 = bpy.data.images.load(file_path)
        logger.add(f"bpy.data.images.load {im1.name}")

        # im_prop = CUSTOM_objectCollection_Image()
        im_prop = item.error_images.add()
        im_prop.name = im_name
        im_prop.image = im1
        im_prop.full_path = file_path

        ui_utills.add_icon(file_path, im_name)

        logger.add(f"item images after add {item.error_images}")
        for im_prop in item.error_images:
            logger.add(f"{im_prop.name}  {im_prop.image}  {im_prop.full_path}")

        # for cat in categories:
        #     if cat.name == self.category:
        #         logger.add(f"set img name to check {im1.name}")
        #         cat.collection[self.index].img_name = im1.name
        #         ui_utills.add_icon(file_path, im_name)
        #         break

        # for cat in categories:
        #     if cat.name == self.category:
        #         logger.add(f"set img name to check {im1.name}")
        #         cat.collection[self.index].img_name = im1.name
        #         # cat.collection[self.index].image = im1
        #         # texture = bpy.data.textures.get(im_name)
        #         # if not texture:
        #         #     texture = bpy.data.textures.new(name=im_name, type="IMAGE")
        #         #     texture.extension = 'CLIP'
        #         #     # texture.repeat_x = im1.size[0] / im1.size[1]
        #         # texture.image = im1

        #         ui_utills.add_icon(file_path, im_name)
        #         break

        # if 'Render Result' in bpy.data.images:
        #     bpy.data.images['Render Result'].name = f"AGR_{self.category}_{self.index}_0"
        
        return {'FINISHED'}

class ErrorsButtonOperator(Operator):
    bl_idname = "agr.checklist_errors"
    bl_label = ""
    # bl_description = "show_checklist"
    # bl_options = {'REGISTER', 'UNDO'}

    tooltip: StringProperty()

    @classmethod
    def description(cls, context, operator):
        return operator.tooltip

    def execute(self, context):
        
        return {'FINISHED'}

class CheckHelpLinkOperator(Operator):
    bl_idname = "agr.check_help_link"
    bl_label = ""
    bl_description = "Открыть ссылку со справкой и рекомендациями по данному пункту"
    # bl_options = {'REGISTER', 'UNDO'}

    is_highpoly: BoolProperty()
    category: StringProperty()
    index: IntProperty()

    def execute(self, context):
        if self.is_highpoly:
            categories = context.scene.agr_scene_properties.checklist_hp_props.categories
        else:
            categories = context.scene.agr_scene_properties.checklist_lp_props.categories
        for cat in categories:
            if cat.name == self.category:
                item: properties.CUSTOM_objectCollection = cat.collection[self.index]
        return {'FINISHED'}

class SaveReportButtonOperator(Operator):
    bl_idname = "agr.save_report_button_operator"
    bl_label = "Save report"
    bl_description = f"Сохранить отчет в файл Word и текстовый файл (в папку рядом с моделями - {os_utils.CHECKLIST_DATA_FOLDER_NAME})"
    # bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return os_utils.check_models_path()

    def execute(self, context):
        if os_utils.check_models_path(self):
            check_report.save_report_txt_file(context, self)
        return {'FINISHED'}

class LoadReportButtonOperator(Operator):
    bl_idname = "agr.load_report_button_operator"
    bl_label = "Save report"
    bl_description = "Сохранить отчет в txt файл (в папку с моделями)"
    # bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return os_utils.check_models_path()

    def execute(self, context):
        # ui_utills.save_report_txt_file(context)
        return {'FINISHED'}

class ShowProjectFolderButtonOperator(Operator):
    bl_idname = "agr.show_project_folder_button_operator"
    bl_label = "Show folder"
    bl_description = "Открыть папку с отчетом"
    # bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return os_utils.check_models_path()

    def execute(self, context):
        ui_utills.show_project_folder(context)
        return {'FINISHED'}

class ClearChecklist(Operator):
    bl_idname = "agr.clear_checklist"
    bl_label = "clear_checklist"
    bl_description = "Очистить чеклист и обновить все пункты требований"
    # bl_options = {'REGISTER', 'UNDO'}

    highpoly: BoolProperty()

    def execute(self, context):
        scene_props = context.scene.agr_scene_properties
        # scene.custom.clear()
        # scene.custom2.clear()
        # scene.custom_categories.clear()
        if self.highpoly:
            scene_props.checklist_hp_props.categories.clear()
        else:
            scene_props.checklist_lp_props.categories.clear()
        
        UpdateRequrements.update_requrements(self.highpoly)

        return {'FINISHED'}

class UpdateRequrements(Operator):
    bl_idname = "agr.update_requrements"
    bl_label = "update_requrements"
    # bl_description = "update_requrements"
    # bl_options = {'REGISTER', 'UNDO'}

    highpoly: BoolProperty()

    def execute(self, context):
        UpdateRequrements.update_requrements(self.highpoly)
        return {'FINISHED'}
    
    @classmethod
    def update_requrements(cls, highpoly):
        if highpoly:
            data = utills.get_requirements_data(True)
            categories_collection = bpy.context.scene.agr_scene_properties.checklist_hp_props.categories
        else:
            data = utills.get_requirements_data(False)
            categories_collection = bpy.context.scene.agr_scene_properties.checklist_lp_props.categories

        categories = dict()
        for row in data:
            if row["category"] not in categories.keys():
                categories[row["category"]] = []
            categories[row["category"]].append(row)
        
        if len(categories_collection) == 0:
            # categories_collection.clear()
            # categories = set(item["category"] for item in data)
            for cat_key in categories.keys():
                cat = categories_collection.add()
                cat.name = cat_key
                for i, row in enumerate(categories[cat_key]):
                    item = cat.collection.add()
                    item.req_id = row["req_id"]
                    item.req_num = row["req_num"]
                    item.category = cat_key
                    item.name = row["name"]
                    item.description = row["description"]
                    item.auto = False if row["auto"] == "0" else True
                    item.recomendation = False if row["recomendation"] == "0" else True
                    item.help_link = row["help_link"]
                    item.highpoly = highpoly
                    item.index_in_category = i
                    # logger.add(f"item add cat={item.category}, id={item.req_num}, ind={item.index_in_category}")
            categories_collection[0].collection[0].check = False
        else:
            for cat in categories_collection:
                for item in cat.collection:
                    for row in categories[item.category]:
                        if row["req_num"] == item.req_num:
                            item.name = row["name"]
                            item.description = row["description"]
                            item.auto = False if row["auto"] == "0" else True
                            item.recomendation = False if row["recomendation"] == "0" else True

class ImportModelsButton(Operator):
    bl_idname = "agr.import_models_button"
    bl_label = "Import AGR zip-files (clean blender file)"
    bl_description = "ОСТОРОЖНО! Запуск импорта очищает текущий бленрер файл и импортирует модели из указанного пути. Для ВПМ корректирует координаты и материалы в соответствии с geojson."

    @classmethod
    def poll(cls, context):
        return os_utils.check_models_path()

    def execute(self, context):
        if os_utils.check_models_path(self):
            check_highpoly_lowpoly.import_models()
            bpy.ops.view3d.view_selected()
        return {'FINISHED'}

class ClearBlenderFileButton(Operator):
    bl_idname = "agr.clear_blender_file_button"
    bl_label = "Clean blender file"
    bl_description = "Очищает текущий бленрер файл от коллекций, геометрии, материалов и текстур"

    # @classmethod
    # def poll(cls, context):
    #     return os_utils.check_models_path()

    def execute(self, context):
        check_highpoly_lowpoly.clear_blender_file()
        return {'FINISHED'}

class RunCalculate_all(Operator):
    bl_idname = "agr.run_calculate_all"
    bl_label = "Check AGR zip-files (clean blender file)"
    bl_description = "ОСТОРОЖНО! Запуск проверок очищает текущий бленрер файл и импортирует модели из указанного пути. После выполнения проверок заполняет чеклист и фиксирует ошибки. Для ВПМ корректирует координаты и материалы в соответствии с geojson."

    @classmethod
    def poll(cls, context):
        return os_utils.check_models_path()

    def execute(self, context):
        if os_utils.check_models_path(self):
            utills.calculate_all_checks(context, self, False)
            bpy.ops.view3d.view_selected()
        return {'FINISHED'}

class RunCalculate_all_collections(Operator):
    bl_idname = "agr.run_calculate_all_collections"
    bl_label = "Check AGR by collections"
    bl_description = "Обновляет проверки, если все модели расположены на сцене по коллекциям (каждая коллекция соответствует отдельному fbx-файлу). Так же для обновления проверок необходим путь (задается выше либо автоматически) к папкам с текстурами и geojson-файлами"

    @classmethod
    def poll(cls, context):
        return os_utils.check_models_path()

    def execute(self, context):
        if os_utils.check_models_path(self):
            utills.calculate_all_checks(context, self, True)
        return {'FINISHED'}

class GlassAllGray(Operator):
    bl_idname = "agr.glass_all_gray"
    bl_label = "glass_all_gray"
    bl_description = "Для быстрого изменения параметров остекления ВПМ. Применяет ко всем стеклам одинаковый цвет (белый), шероховатость (0), металличность (0.6) и прозрачность (0.4)"

    def execute(self, context):
        view_tools.all_glass_gray()
        return {'FINISHED'}

class CheckGeojson(Operator):
    bl_idname = "agr.check_geojson"
    bl_label = "check_geojson"
    bl_description = ""

    def execute(self, context):
        def check_field(item, ZU_area, geojson_ZU_area):
            item.auto = True
            try:
                ZU_area = float(ZU_area.replace(",", "."))
                geojson_ZU_area = float(geojson_ZU_area.replace(",", "."))
            except:
                pass
            if ZU_area != geojson_ZU_area:
                item.check_state = utills.CHECK_STATE_ITEMS[2]
        # if highpoly:
        #     data = utills.get_requirements_data(True)
        #     categories_collection = bpy.context.scene.agr_scene_properties.checklist_hp_props.categories
        # else:
        #     data = utills.get_requirements_data(False)
        #     categories_collection = bpy.context.scene.agr_scene_properties.checklist_lp_props.categories

        # categories = dict()
        # for row in data:
        #     if row["category"] not in categories.keys():
        #         categories[row["category"]] = []
        #     categories[row["category"]].append(row)

        adress = ""
        for root, dirs, files in os.walk(os_utils._get_project_path()):
            for file in files:
                if file.endswith(".geojson"):
                    if "ground" in file.lower() and "light" not in file.lower():
                        adress = file.replace("_Ground", "").replace("SM_", "").replace(".geojson", "")
        
        jsons = dict()
        for root, dirs, files in os.walk(os_utils._get_project_path()):
            for file in files:
                if file.endswith(".geojson"):
                    json_data = check_highpoly_lowpoly.ModelPreparer._get_json_data(os.path.join(root, file))
                    jsons[file.replace(adress, "").replace(".geojson", "").replace("SM_", "")] = json_data

        agr_props = bpy.context.scene.agr_scene_properties
        json_cats = agr_props.geojson_categories
        json_cats.clear()

        # categories_collection.clear()
        # categories = set(item["category"] for item in data)
        for n, cat_key in enumerate(jsons.keys()):
            cat = json_cats.add()
            cat.name = cat_key

            # fno_code = jsonData["features"][0]["properties"]["FNO_code"]
            # fno_code = jsons[cat_key]["features"][0]["properties"]["FNO_code"]
            
            props_dict = jsons[cat_key]["features"][0]["properties"]
            for i, prop_key in enumerate(props_dict.keys()):
                if prop_key == "imageBase64":
                    continue

                item = cat.collection.add()

                if prop_key == "ZU_area" and agr_props.geojson_ZU_area:
                    check_field(item, props_dict[prop_key], agr_props.geojson_ZU_area)
                elif prop_key == "h_relief" and agr_props.geojson_h_relief:
                    check_field(item, props_dict[prop_key], agr_props.geojson_h_relief)
                elif prop_key == "s_obsh" and agr_props.geojson_s_obsh:
                    check_field(item, props_dict[prop_key], agr_props.geojson_s_obsh)
                elif prop_key == "s_naz" and agr_props.geojson_s_naz:
                    check_field(item, props_dict[prop_key], agr_props.geojson_s_naz)
                elif prop_key == "s_podz" and agr_props.geojson_s_podz:
                    check_field(item, props_dict[prop_key], agr_props.geojson_s_podz)
                elif prop_key == "spp_gns" and agr_props.geojson_spp_gns:
                    check_field(item, props_dict[prop_key], agr_props.geojson_spp_gns)
                elif prop_key == "FNO_code":
                    item.auto = True

                # item.req_id = row["req_id"]
                item.req_num = str(n + 1) + "." + str(i + 1)
                item.category = cat_key
                item.name = prop_key
                item.description = props_dict[prop_key]
                # item.auto = False if row["auto"] == "0" else True
                # item.recomendation = False if row["recomendation"] == "0" else True
                # item.help_link = row["help_link"]
                # item.highpoly = highpoly
                item.index_in_category = i
        
        return {'FINISHED'}

class CheckLowpolyCode(Operator):
    bl_idname = "agr.check_lowpoly_code"
    bl_label = "check_lowpoly_code"
    bl_description = "Найти код или показать улицы, найденные по четырехзначному коду в наименованиях НПМ. Если код не соответствует, необходимо разблокировать автопроверки в настройках и отметить ошибку в пункте 2.10.3.1"

    streets_code: StringProperty()
    streets: StringProperty()

    def execute(self, context):
        # code = None
        # for col in bpy.data.collections:
        #     if col.name[:4].isdigit():
        #         code = col.name[:4]
        #         self.streets_code = code
        # if code:
        #     streets_list = utills.get_lowpoly_streets_by_code(code)
        #     self.streets = "\n".join(streets_list)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        street_name = bpy.context.scene.agr_scene_properties.street_for_lowpoly_code
        if street_name:
            streets_list = utills.get_lowpoly_codes_by_street(street_name)
            self.streets = "\n".join(streets_list)
        else:
            code = None
            for col in bpy.data.collections:
                if col.name[:4].isdigit():
                    code = col.name[:4]
                    self.streets_code = code
            if code:
                streets_list = utills.get_lowpoly_streets_by_code(code)
                self.streets = "\n".join(streets_list)

        # self.user_text = self.user_text_code
        # self.window_showed = True
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=250)

    # def execute(self, context):
    #     # context.window_manager.invoke_props_dialog(self)
    #     # self.user_text_code = self.user_text
    #     # return {'CANCELLED'}
    #     ui_utills.update_text_by_id(context, 0)
    #     self.window_showed = False
    #     return {'FINISHED'}
    
    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Улицы, найденные по коду {self.streets_code}:")
        for row in self.streets.split("\n"):
            layout.label(text=row)
        # ui_utills.drow_label_multiline(context, self.streets, layout)

class TestDebugOperator(Operator):
    bl_idname = "agr.test_debug"
    bl_label = ""
    bl_description = ""

    def execute(self, context):
        # print(f"ensure_import_fbx {self.ensure_import_fbx()}")
        return {'FINISHED'}

    # def ensure_import_fbx(self):
    #     import sys
    #     import subprocess
    #     import site
    #     try:
    #         user_site_pkgs = site.getusersitepackages()
    #         if user_site_pkgs not in sys.path:
    #             sys.path.append(user_site_pkgs)
    #             sys.path.append(r"c:\users\maxko\appdata\roaming\blender foundation\blender\4.2\extensions\.local\lib\python3.11\site-packages")
    #         import fbx
    #         return True
    #     except Exception as e:
    #         try:
    #             print('installing package fbx')
    #             py_exec = sys.executable
    #             # subprocess.call([str(py_exec), "-m", "ensurepip", "--user"])
    #             # subprocess.call([str(py_exec), "-m", "pip", "install", "--upgrade", "pip"])
    #             subprocess.run([str(py_exec), "-m", "pip", "install", "--target", r"C:\Users\maxko\AppData\Roaming\Python\Python311\site-packages", "fbx-2020.3.7-cp311-none-win_amd64.whl", "--upgrade"])
    #             import fbx
    #             return True
            
            
    #         except Exception as e:
    #             print(e, f"Не удалось установить библиотеку fbx")
    #             return False
    
    # def ensure_import_pyfbx(self):
    #     import sys
    #     import subprocess
    #     import site
    #     try:
    #         user_site_pkgs = site.getusersitepackages()
    #         if user_site_pkgs not in sys.path:
    #             sys.path.append(user_site_pkgs)
    #         import pyfbx
    #         return True
    #     except Exception as e:
    #         try:
    #             print('installing package pyfbx')
    #             py_exec = sys.executable
    #             subprocess.call([str(py_exec), "-m", "ensurepip", "--user"])
    #             subprocess.call([str(py_exec), "-m", "pip", "install", "--upgrade", "pip"])
    #             subprocess.run([str(py_exec), "-m", "pip", "install", "py-fbx"])
    #             import pyfbx
    #             return True
            
    #         except Exception as e:
    #             print(e, f"Не удалось установить библиотеку pyfbx")
    #             return False