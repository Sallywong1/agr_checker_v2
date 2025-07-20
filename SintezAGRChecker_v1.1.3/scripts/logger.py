import logging
import traceback

from . import os_utils


def initialize(proj_path):
    # global file_path_txt
    # path = os_utils._get_project_path()
    # print(f"initialize logger _get_project_path {path}")
    # if not path:
    #     return
    if os_utils.check_models_path():
        # path = os_utils.get_logger_fullpath()
        print(f"initialize logger path {os_utils.get_logger_fullpath_txt()}")
        # logging.basicConfig(level=logging.DEBUG, filename=path, filemode="w")
        # file_path_txt = os_utils.get_logger_fullpath_txt()
        open(os_utils.get_logger_fullpath_txt(), 'w').close()

def add(msg):
    # logging.info(msg)
    if os_utils.check_models_path():
        print(msg)
        with open(os_utils.get_logger_fullpath_txt(), 'a') as f:
            f.write(msg + "\n")

def add_error(e: Exception, msg=""):
    print(f"{msg} ({e})")
    print(traceback.format_exc())
    # logging.error(str(e), exc_info=True)
    if os_utils.check_models_path():
        with open(os_utils.get_logger_fullpath_txt(), 'a') as f:
            f.write(f"{msg} ({e})" + "\n")
            f.write(traceback.format_exc() + "\n")