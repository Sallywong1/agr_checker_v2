import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty, PointerProperty, IntProperty, FloatProperty, BoolProperty, CollectionProperty, EnumProperty

from . import utills
from . import ui_utills
from . import check_report
from . import operators
from . import logger
from . import view_tools

class CUSTOM_objectCollection_Image(PropertyGroup):
    name: StringProperty()
    image : PointerProperty(type=bpy.types.Image)
    comment: StringProperty()
    full_path: StringProperty()

class CUSTOM_objectCollection(PropertyGroup):
    def update_checklist(self, context):
        props = context.scene.agr_scene_properties.checklist_hp_props if self.highpoly else context.scene.agr_scene_properties.checklist_lp_props
        count_all = 0
        count_true = 0
        count_auto = 0
        count_auto_true = 0
        count_manual = 0
        count_manual_true = 0
        categories_collection = props.categories
        for cat in categories_collection:
            # cat_true = 0
            checked_count = 0
            for item in cat.collection:
                count_all += 1
                if item.check_state != utills.CHECK_STATE_ITEMS[0]:
                    checked_count += 1
                if item.auto:
                    count_auto += 1
                else:
                    count_manual += 1
                if item.check:
                    if item.auto: 
                        count_auto_true += 1
                    else:
                        count_manual_true += 1
                    # cat_true += 1
                    count_true += 1
            cat.progress = checked_count / len(cat.collection)
            # cat.progress_text = str(round(cat.progress * 100)) + "%"
            cat.progress_text = f"{checked_count}/{len(cat.collection)}"

        props.progress_all = count_true / count_all
        props.progress_all_text = "Требований выполнено: " + str(round(count_true / count_all * 100)) + "%" + f" ({count_true}/{count_all})"
        props.progress_auto = count_auto_true / count_auto
        props.progress_auto_text = "Авто: " + str(round(count_auto_true / count_auto * 100)) + "%" + f" ({count_auto_true}/{count_auto})"
        props.progress_manual = count_manual_true / count_manual
        props.progress_manual_text = "Ручные: " + str(round(count_manual_true / count_manual * 100)) + "%" + f" ({count_manual_true}/{count_manual})"


    #name: StringProperty() -> Instantiated by default
    obj_type: StringProperty()
    obj_id: IntProperty()
    check: BoolProperty(name="", description="Check description", update=update_checklist)
    check_state: EnumProperty(name="check_state", items=[("undefined", "undefined", ""), ("verified", "verified", ""), ("failed", "failed", "")])
    errors_text: StringProperty()
    errors_count: IntProperty()

    index_in_category: IntProperty()

    req_id: StringProperty()
    req_num: StringProperty()
    category: StringProperty()
    description: StringProperty()
    user_description: StringProperty()
    auto: BoolProperty()
    recomendation: BoolProperty()
    help_link: StringProperty()

    highpoly: BoolProperty()
    user_comment: StringProperty()

    img_name: StringProperty()
    image : PointerProperty(type=bpy.types.Image)
    error_images: CollectionProperty(type=CUSTOM_objectCollection_Image)

class CUSTOM_objectCollection_category(PropertyGroup):
    collection: CollectionProperty(type=CUSTOM_objectCollection)
    collection_index: IntProperty()
    progress: FloatProperty()
    progress_text: StringProperty()
    drow_collection: BoolProperty()

class ChecklistProperties(PropertyGroup):
    categories: CollectionProperty(type=CUSTOM_objectCollection_category)
    progress_all: FloatProperty()
    progress_all_text: StringProperty()
    progress_auto: FloatProperty()
    progress_auto_text: StringProperty()
    progress_manual: FloatProperty()
    progress_manual_text: StringProperty()

class AGRCheckerProperties(PropertyGroup):
    def change_path(self, context):
        scene_props = bpy.context.scene.agr_scene_properties
        scene_props.checklist_hp_props.categories.clear()
        scene_props.checklist_lp_props.categories.clear()

        operators.UpdateRequrements.update_requrements(True)
        operators.UpdateRequrements.update_requrements(False)
        logger.initialize(self.path)

    def load_report(self, context):
        self.checklist_hp_props.categories.clear()
        self.checklist_lp_props.categories.clear()

        operators.UpdateRequrements.update_requrements(True)
        operators.UpdateRequrements.update_requrements(False)
        check_report.load_report(context)
    
    def change_view_mode(self, context):
        view3d = None
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                view3d = area.spaces[0]
                # area.spaces[0].shading.type = 'Solid'
        if not view3d:
            return
        
        if self.view_mode == "usual":
            view3d.shading.type = 'SOLID'
            view3d.overlay.show_face_orientation = False
            self.show_ucx = False
        elif self.view_mode == "textured":
            view3d.shading.type = 'MATERIAL'
            view3d.overlay.show_face_orientation = False
            self.show_ucx = False
        elif self.view_mode == "normals":
            view3d.shading.type = 'SOLID'
            view3d.overlay.show_face_orientation = True
            self.show_ucx = False
        elif self.view_mode == "ucx":
            view3d.shading.type = 'SOLID'
            view3d.overlay.show_face_orientation = False
            self.show_lp = False
            self.show_hp = True
            self.show_ucx = True
            for obj in bpy.data.objects:
                if "UCX" in obj.name:
                    mat = None
                    try:
                       mat = bpy.data.materials["AGR_UCX"]
                    except:
                       pass

                    if not mat:
                       mat = bpy.data.materials.new(name="AGR_UCX")
                       
                    mat.diffuse_color = [0, 0, 0.8, 0.4]
                    obj.data.materials.append(mat)
    
    def swith_show_lp(self, context):
        logger.add(f"self.show_lp={self.show_lp}")
        for col in bpy.data.collections:
            if col.name[:4].isdigit():
                col.hide_viewport = not self.show_lp
                # col.hide_select = self.show_lp

    def swith_show_hp(self, context):
        logger.add(f"self.show_hp={self.show_hp}")
        for col in bpy.data.collections:
            if col.name.startswith("SM_"):
                for obj in col.objects:
                    if "UCX" not in obj.name:
                        obj.hide_set(not self.show_hp)
                # col.hide_viewport = not self.show_hp
                # col.hide_select = self.show_hp
    
    def swith_show_ucx(self, context):
        logger.add(f"self.show_ucx={self.show_ucx}")
        for obj in bpy.data.objects:
            if "UCX" in obj.name:
                obj.hide_set(not self.show_ucx)
                if not self.show_ucx:
                    obj.data.materials.clear()

    def swith_show_glass(self, context):
        logger.add(f"self.show_glass={self.show_glass}")
        for obj in bpy.data.objects:
            if "Glass" in obj.name:
                obj.hide_set(not self.show_glass)
    
    def swith_glass_grid(self, context):
        if self.show_glass_grid:
            view_tools.show_glass_as_grid()
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    view3d = area.spaces[0]
                    # area.spaces[0].shading.type = 'Solid'
            if not view3d:
                return
            view3d.shading.type = 'MATERIAL'
        else:
            view_tools.show_glass_as_normal()

    calc_mode: EnumProperty(name="calc_mode", items=[("mode1", "mode1", ""), ("mode2", "mode2", ""), ("mode3", "mode3", "")])
    view_mode: EnumProperty(name="view_mode", update=change_view_mode, items=[("usual", "Обычный", ""), ("textured", "Текстуры", ""), ("normals", "Нормали", ""), ("ucx", "Коллизии", "")])
    show_lp: BoolProperty(default=True, update=swith_show_lp)
    show_hp: BoolProperty(default=True, update=swith_show_hp)
    show_ucx: BoolProperty(default=False, update=swith_show_ucx)
    show_glass: BoolProperty(default=True, update=swith_show_glass)
    show_glass_grid: BoolProperty(default=False, update=swith_glass_grid, description="Отображает стекла как сетку для проверки вертикальности, растяжек и пропорций.")

    Address: StringProperty(
        name="Address",
        description="Задайте переменную Address, которая будет применена к проверкам наименований. Если оставить поле пустым - определится автоматически.",
        default="",
        maxlen=1024,
        )
    
    path: bpy.props.StringProperty(
        name="Models path",
        description="Выберете папку в которой находятся zip-архивы (один НМП архив и несколько ВПМ архивов) и нет ничего лишнего. НПМ архив обязательно должен начинаться с 4-х значного кода. ВПМ архивы обязательно должны начинаться с префикса 'SM_'",
        subtype='DIR_PATH',
        update=change_path)
    
    load_report_path: bpy.props.StringProperty(
        name = "Report path",
        description="Загрузить отчет",
        subtype='FILE_PATH',
        update=load_report)
    
    check_author: StringProperty()
    
    td_min: IntProperty(
        name="td_min",
        description="",
        default=10,
        max=5000,
    )

    td_max: IntProperty(
        name="td_max",
        description="",
        default=40,
        max=5000,
    )

    texture_size: IntProperty(default=2048)
    texture_size_enum: EnumProperty(name="texture_size_enum", items=[("512", "512", ""), ("1024", "1024", ""), ("2048", "2048", ""), ("4096", "4096", ""), ("Custom", "Custom", "")])

    checklist_lp_props: PointerProperty(type=ChecklistProperties)
    checklist_hp_props: PointerProperty(type=ChecklistProperties)

    project_data_address: StringProperty()
    has_lowpoly: BoolProperty()
    has_highpoly: BoolProperty()

    unlock_auto_checks: BoolProperty(default=False)
    show_req_nums: BoolProperty(default=True)

    experimental_checks: BoolProperty(default=False, description="Включить в расчет экспериментальные проверки")

    geojson_ZU_area: StringProperty()
    geojson_h_relief: StringProperty()
    geojson_s_obsh: StringProperty()
    geojson_s_naz: StringProperty()
    geojson_s_podz: StringProperty()
    geojson_spp_gns: StringProperty()

    geojson_categories: CollectionProperty(type=CUSTOM_objectCollection_category)

    street_for_lowpoly_code: StringProperty(name="", description="Введите часть названия улицы/проспекта/переулка для поиска четырехзначного кода. Регистр не имеет значения. Если оставить поле пустым, поиск выдаст все улицы по текущему коду")