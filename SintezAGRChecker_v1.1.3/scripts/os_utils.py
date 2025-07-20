import os

import bpy #noqa
import addon_utils #noqa

from . import logger

CHECKLIST_DATA_FOLDER_NAME = "AGRChecker_data"

def _get_project_path():
    models_path = bpy.path.abspath(bpy.context.scene.agr_scene_properties.path)
    # if not models_path.strip():
    #     models_path = bpy.path.abspath("//")
    return models_path

def get_checks_data_dir():
    return os.path.join(_get_project_path(), CHECKLIST_DATA_FOLDER_NAME)

# def get_logger_fullpath():
#     return os.path.join(_get_project_path(), CHECKLIST_DATA_FOLDER_NAME, "checker_log.log")

def get_logger_fullpath_txt():
    dir_path = os.path.join(_get_project_path(), CHECKLIST_DATA_FOLDER_NAME)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return os.path.join(dir_path, "checker_log.txt")

def get_addon_root_dir():
    path = ""
    for mod in addon_utils.modules():
        if mod.bl_info.get("name") == "SINTEZ AGR Checker":
            path = mod.__file__.replace("__init__.py", "")
            break
    return path

def get_documents_dir():
    return os.path.join(get_addon_root_dir(), "documents")

def check_models_path(bl_operator=None):
    path = _get_project_path()
    if path:
        return True
    else:
        if bl_operator:
            bl_operator.report({'WARNING'}, f"Укажите путь к папке с zip-архивами или сохрание этот blend файл рядом с архивами!")
        return False