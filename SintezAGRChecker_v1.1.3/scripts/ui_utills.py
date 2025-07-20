import textwrap
import bpy
import datetime
import os
from bpy.utils import previews

from . import utills
from . import check_report
from . import os_utils
from . import logger

plugin_icons = previews.new()

plugin_icons.load(
    name='sintez_alpha.png',
    path=os.path.join(os_utils.get_addon_root_dir(), "icons", "sintez_alpha.png"),
    path_type='IMAGE'
)

plugin_icons.load(
    name='red_heart_icon.png',
    path=os.path.join(os_utils.get_addon_root_dir(), "icons", "red_heart_icon.png"),
    path_type='IMAGE'
)

icons_by_checks = dict()

# checks_icons = previews.new()
# pathes_names = []

lp_help_links = {
    '2.3.8': 'https://docs.google.com/document/d/18iZ-7TDL0xvJe8AWA6LQKIuEwZeQTXCNrKBMiY3F5vA/edit?usp=sharing', # normals
    '2.3.16': 'https://docs.google.com/document/d/1qa7e7sfpp4sZ1pWQUXcwXoGpqHd4QbBFXi_1q33CjiY/edit?usp=sharing', # трансформы применить
    '2.3.17': 'https://docs.google.com/document/d/1Frvn9L2ppDk3aAAF32pQbcY-HoOLUkvVFa18Iiby7i8/edit?usp=sharing', # сглаживание
    '2.4.1': 'https://docs.google.com/document/d/1OSYwm13hvhjk5WS1Ayh4WtCOzlQ3VU-XLN-R5DzNqWQ/edit?usp=sharing', # материалы стандартные
    '2.8.2': 'https://docs.google.com/document/d/1zjwvnv-8LfQQnQTb4MIg4Vu3w5ZHNqValwkqUIbJ2jM/edit?usp=sharing', # координаты
}

def add_icon(path, name):
    logger.add(f"add icon {name}  {path}")
    logger.add("icons_by_checks")
    for key in icons_by_checks:
        logger.add(f"    {key}: {icons_by_checks[key]}")
        for key2 in icons_by_checks[key]:
            logger.add(f"        {key2}  {icons_by_checks[key][key2]}")
    if name in icons_by_checks.keys():
        previews.remove(icons_by_checks[name])
    #     icons_by_checks[name].clear()
    # else:
    icons_by_checks[name] = previews.new()
    icons_by_checks[name].load(name, path, 'IMAGE')

    logger.add("icons_by_checks 2")
    for key in icons_by_checks:
        logger.add(f"    {key}: {icons_by_checks[key]}")
        for key2 in icons_by_checks[key]:
            icons_by_checks[key][key2].reload()
            logger.add(f"        {key2}  {icons_by_checks[key][key2]}")

def clean_icons_by_check_name(check_name):
    key_to_del = []
    for key in icons_by_checks:
        if check_name in key:
            previews.remove(icons_by_checks[key])
            key_to_del.append(key)
    for key in key_to_del:
        icons_by_checks.pop(key)

def del_icon(del_path, del_name):
    if del_name in icons_by_checks.keys():
        previews.remove(icons_by_checks[del_name])
    
    logger.add("icons_by_checks 3 after del")
    for key in icons_by_checks:
        logger.add(f"    {key}: {icons_by_checks[key]}")
        for key2 in icons_by_checks[key]:
            icons_by_checks[key][key2].reload()
            logger.add(f"        {key2}  {icons_by_checks[key][key2]}")

def drow_checklist(is_highpoly, context, layout):
    if is_highpoly:
        categories = context.scene.agr_scene_properties.checklist_hp_props.categories
        checklist_props = context.scene.agr_scene_properties.checklist_hp_props
    else:
        categories = context.scene.agr_scene_properties.checklist_lp_props.categories
        checklist_props = context.scene.agr_scene_properties.checklist_lp_props

    layout.progress(text=checklist_props.progress_all_text, factor = checklist_props.progress_all, type='BAR')
    # layout.separator(type='LINE')
    row = layout.row()
    row.progress(text=checklist_props.progress_auto_text, factor = checklist_props.progress_auto, type='BAR')
    row.progress(text=checklist_props.progress_manual_text, factor = checklist_props.progress_manual, type='BAR')

    layout.separator(type='LINE')

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
        show_op.highpoly = is_highpoly
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

                if is_highpoly and item.req_num == "2.5.2.2.1а":
                    show_glass_grid_icon = 'HIDE_OFF' if context.scene.agr_scene_properties.show_glass_grid else 'HIDE_ON'
                    box.prop(context.scene.agr_scene_properties, "show_glass_grid", text="Стекла UV Color grid", icon=show_glass_grid_icon)
                elif not is_highpoly and item.req_num == "2.10.3.1":
                    code_row = box.row()
                    code_row.prop(context.scene.agr_scene_properties, "street_for_lowpoly_code", text="Улица")
                    code_row.operator("agr.check_lowpoly_code", text="Найти код", icon='VIEWZOOM')
                    pass

                check_op_split = req_row.split()
                check_op_split.alignment='RIGHT'
                
                check_op_split.alert = True if item.check_state == utills.CHECK_STATE_ITEMS[2] else False
                req_num = item.req_num + "  " if context.scene.agr_scene_properties.show_req_nums else ""
                check_op = check_op_split.operator("agr.checkbox_test_operator", icon=op_icon, text=req_num + item.name, emboss=False)
                check_op.tooltip = item.description
                check_op.category = item.category
                check_op.index = i
                check_op.is_highpoly = item.highpoly
                check_op.geojson_list = False
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
                if not is_highpoly and item.req_num in lp_help_links.keys():
                    help_op = req_row.operator("wm.url_open", icon='HELP', text="", emboss=False)
                    help_op.url = lp_help_links[item.req_num]
                    
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

    layout.separator(type='LINE')

    # upd_button = layout.operator(
    #     operator='agr.update_requrements',
    #     # icon='BLENDER',
    #     text='Update requrements from file'
    # )
    # upd_button.highpoly = is_highpoly

    clear_button = layout.operator(
        operator='agr.clear_checklist',
        # icon='BLENDER',
        text='Очистить/Обновить чеклист'
    )
    clear_button.highpoly = is_highpoly

def drow_label_multiline(context, text, parent):
    # logger.add(context.region.width)
    chars = int(200 / 7)   # 7 pix on 1 character
    # chars = int(context.region.width / 7)   # 7 pix on 1 character
    wrapper = textwrap.TextWrapper(width=chars)
    text_lines = wrapper.wrap(text=text)
    for text_line in text_lines:
        parent.label(text=text_line)

def show_project_folder(context):
    # models_path = os_utils._get_project_path()
    # if not models_path:
    #     return
    # path = os.path.realpath(models_path)
    if os_utils.check_models_path():
        path = os_utils.get_checks_data_dir()
        os.startfile(path)

def get_text_editor_text(context):
    text_name = "AGR Checker report"
    text_file = None
    for text in bpy.data.texts:
        if text_name in text.name:
            text_file = text
    if not text_file:
        bpy.ops.text.new()
        default_texts = []
        for text in bpy.data.texts:
            if "Text" in text.name:
                default_texts.append(text)
        text_file = default_texts[-1]
        text_file.name = text_name
    # context.space_data.text = bpy.data.texts[text.name]
    text_file.clear()
    for area in context.screen.areas:
        if area.type == "TEXT_EDITOR":
            area.spaces[0].text = bpy.data.texts[text_name]
            area.spaces[0].show_word_wrap = True
            logger.add(area.spaces)
            break
    return text_file

def generate_text_editor(context):
    msg_for_text_editor, msg_for_text_editor_2 = check_report._generate_report(context)

    text_name = "AGR Checker report"
    text_file = None
    for text in bpy.data.texts:
        if text_name in text.name:
            text_file = text
    if not text_file:
        bpy.ops.text.new()
        default_texts = []
        for text in bpy.data.texts:
            if "Text" in text.name:
                default_texts.append(text)
        text_file = default_texts[-1]
        text_file.name = text_name
    # context.space_data.text = bpy.data.texts[text.name]
    text_file.clear()
    for area in context.screen.areas:
        if area.type == "TEXT_EDITOR":
            area.spaces[0].text = bpy.data.texts[text_name]
            area.spaces[0].show_word_wrap = True
            # logger.add(area.spaces)
            break

    text_file.write(msg_for_text_editor)

def update_checks_from_text_editor(context):
    def try_to_write_comment(is_comment):
        nonlocal categories
        nonlocal cur_comment
        nonlocal cur_req_num
        nonlocal cur_description
        if cur_req_num:
            # logger.add(f"try to write {cur_req_num}")
            req_num_found = False
            for cat in categories:
                for item in cat.collection:
                    if item.req_num == cur_req_num:
                        if is_comment:
                            item.user_comment = cur_comment.strip()
                            # logger.add(f"set comment to {cur_req_num} {item.name}, comment={cur_comment}")
                        else:
                            item.user_description = cur_description.strip()
                            # logger.add(f"set description to {cur_req_num} {item.name}, comment={cur_description}")
                        req_num_found = True
                        break
                if req_num_found:
                    break
            if not req_num_found:
                logger.add(f"dont found requirement {cur_req_num}")
        else:
            pass
            # logger.add(f"try to find empty requirement - '{cur_req_num}'")
        if is_comment:
            cur_comment = ""
            cur_req_num = ""
        else:
            cur_description = ""
    text_name = "AGR Checker report"
    text_file = None
    for text in bpy.data.texts:
        if text_name in text.name:
            text_file = text
    if not text_file:
        return
    is_highpoly = False
    categories = context.scene.agr_scene_properties.checklist_lp_props.categories
    cur_req_num = ""
    cur_comment = ""
    cur_description = ""
    cur_field = ""
    for i, line in enumerate(text_file.lines):
        if "Высокополигональная модель" in line.body:
            try_to_write_comment(True)
            is_highpoly = True
            categories = context.scene.agr_scene_properties.checklist_hp_props.categories
        elif line.body.startswith(f"----Ошибка"):
            try_to_write_comment(True)
            cur_req_num = line.body.split(" ")[3].strip(".")
        elif line.body.startswith(f"----Описание пункта:"):
            cur_field = "description"
        elif line.body.startswith(f"----Автоматичсеские ошибки:"):
            try_to_write_comment(False)
            cur_field = ""
        elif line.body.startswith(f"----Комментарий к ошибке:"):
            if cur_field == "description":
                try_to_write_comment(False)
            cur_field = "comment"
        else:
            if cur_field == "description":
                cur_description += line.body + "\n"
            elif cur_field == "comment":
                cur_comment += line.body + "\n"
        if i == len(text_file.lines) - 1:
            try_to_write_comment(True)

def update_text_by_id(context, item):
    generate_text_editor(context)
    return
    if item.check_state != utills.CHECK_STATE_ITEMS[2]:
        return
    id_str = item.req_num
    state = item.check_state
    name = item.name
    is_highpoly = item.highpoly
    logger.add(f"cur id_str={id_str}")
    text_name = "AGR Checker report"
    text_file = None
    for text in bpy.data.texts:
        if text_name in text.name:
            text_file = text
    if not text_file:
        return
    
    line_found = False
    cur_line_highpoly = None
    for line in text_file.lines:
        if "Низкополоигональная модель" in line.body:
            cur_line_highpoly = False
        if "Высокополигональная модель" in line.body:
            cur_line_highpoly = True
        if cur_line_highpoly != is_highpoly:
            continue
        
        if line.body.startswith(f"Пункт {item.req_num}"):
            line.body = f"Пункт {item.req_num}. {item.check_state}. {item.name}\n{item.user_comment}\n\n"
            line_found = True
            break
    highpoly_line_index = 0
    if not line_found:
        for i, line in enumerate(text_file.lines):
            if "Высокополигональная модель" in line.body:
                highpoly_line_index = i
        if not is_highpoly:
            text_file.cursor_set(highpoly_line_index - 1)
        else:
            text_file.cursor_set(len(text_file.lines) - 1)
        
        text_file.write(f"Пункт {item.req_num}. {item.check_state}. {item.name}\n{item.user_comment}\n\n")

