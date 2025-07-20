import os
import re
import json
import csv
import mathutils
import math
import zipfile
import datetime
import time
import traceback

import bpy
import bmesh

import struct
import imghdr

from itertools import groupby
from . import utills
from . import os_utils
from . import logger


def exception_handler(func):
    def wrapper(*args, **kwargs):
        global start_time
        result = []
        try:
            result = func(*args, **kwargs)
            t = round(time.time() - start_time, 2)
            logger.add(f"completed function - {func.__name__}, timestamp={t} сек.")
        except Exception as e:
            logger.add_error(e, msg=f"Непредвиденная ошибка во время {func.__name__}!")
        return result
    return wrapper

class HighpolyChecks():
    def __init__(self):
        self.hp_checks = dict()
        self.hp_checks_by_ids = dict()
        self.hp_result_report = ""
        self._hp_fbx_files: list[FbxFile] = []
        self._oks_count = 0
        self.address = ""
        self.root_path = ""
        self._start_time = 0
        self.bl_operator = None

    def add_checks(self, checks_pack):
        for check in checks_pack:
            if check.name not in self.hp_checks.keys():
                self.hp_checks[check.name] = []
            self.hp_checks[check.name].append(check)
        
        for check in checks_pack:
            if check.paragraph_ids[0] not in self.hp_checks_by_ids.keys():
                self.hp_checks_by_ids[check.paragraph_ids[0]] = []
            self.hp_checks_by_ids[check.paragraph_ids[0]].append(check)

    def run_meshes_check(self, fbx_files, oks_count, bl_operator):
        self._hp_fbx_files = fbx_files
        self._oks_count = oks_count
        self.bl_operator = bl_operator
        
        for fbx in self._hp_fbx_files:
            obj = fbx.main_mesh
            if not obj:
                continue
            fbx.create_udim_set()

        hp_checks = []
        self._start_time = time.time()
        hp_checks.extend(self._check_meshes_transforms())
        hp_checks.extend(self._check_polycount())
        hp_checks.extend(self._check_duplicates())
        hp_checks.extend(self._check_texel_dencity())
        hp_checks.extend(self._check_naming_masks())
        hp_checks.extend(self._check_fbx_objects())
        hp_checks.extend(self._udim_numbers_check())
        hp_checks.extend(self._check_glasses_uv())
        hp_checks.extend(self._check_materials())
        hp_checks.extend(self._check_lights())
        hp_checks.extend(self._check_collision())
        hp_checks.extend(CheckUtils.check_files(False, self.root_path))
        hp_checks.extend(self._check_flipped())
        hp_checks.extend(self._check_json_properties())
        hp_checks.extend(self._check_pivot())
        hp_checks.extend(self._check_png())
        hp_checks.extend(CheckUtils.check_color_attributes(self._hp_fbx_files))

        self.add_checks(hp_checks)
        # self.generate_result()

    def _time_stamp(self, msg):
        # t = (datetime.datetime.now() - self._start_time)
        t = round(time.time() - self._start_time, 2)
        logger.add(f"{msg}, {t} сек.")
        # if self.bl_operator:
        #     self.bl_operator.report({'INFO'}, f"Выполняется расчет: {msg}, {t} сек.")
        #     for area in bpy.context.window.screen.areas:
        #         if area.type == 'VIEW_3D':
        #             area.tag_redraw()

    def generate_result(self):
        msg1 = ""
        msg2 = ""
        msg_only_errors = ""

        for key in sorted(self.hp_checks):
            verified_all = all([ch.verified for ch in self.hp_checks[key]])
            verified_all_string = str(verified_all).ljust(6, " ")
            header = key.ljust(70, ".")
            count = sum([ch.checked_count for ch in self.hp_checks[key]])
            err_count = sum([len(ch.error_list) for ch in self.hp_checks[key]])
            # msg1 += f"{header}{verified_all_string} (Проверено {self.hp_checks[key][0].units_text}: {count}, ошибок:{err_count}) (пункт требований: {self.hp_checks[key][0].paragraph})\n"
            msg1 += f"{header}{verified_all_string} ({self.hp_checks[key][0].paragraph})\n"
            if verified_all:
                continue
            # msg2 += f"\n{header}{verified_all_string} (Проверено {self.hp_checks[key][0].units_text}: {count}, ошибок:{err_count}) (пункт требований: {self.hp_checks[key][0].paragraph})\n"
            # msg2 += f"\n{header}{verified_all_string} ({self.hp_checks[key][0].paragraph})\n"
            msg2 += f"\n{key} ({self.hp_checks[key][0].paragraph})\n"
            msg_only_errors += f"\n{key} ({self.hp_checks[key][0].paragraph})\n"
            err_lines = ""
            for check in self.hp_checks[key]:
                if not check.verified:
                    err_lines += f"    {check.directory}\n"
                    for err in check.error_list:
                        err_lines += f"        {err}\n"
            msg2 += err_lines
            msg_only_errors += err_lines
        
        start = "----------------------Высокополигональная модель---------------------------"
        end = "-----------------------------------------------------------------------------"
        # logger.add(f"\n\n{start}\nПроверки:\n{msg1}\nОшибки:\n{msg2}\n{end}\n")
        # self.hp_result_report = f"\n\n{start}\nПроверки:\n{msg1}\nОшибки:\n{msg2}\n{end}\n{msg_only_errors}\n{end}"
        self.hp_result_report = f"\n\n{start}\nПроверки:\n{msg1}\n\nОшибки:\n{msg2}\n{end}"

    @exception_handler
    def _udim_numbers_check(self):
        checks = []
        for fbx in self._hp_fbx_files:
            obj = fbx.main_mesh
            if not obj:
                continue
            
            check1 = Check("Проверка UDIM. Целостность нумерации", fbx.name, True, "таблица 2, п. 5, п/п 2.1.3", "файлов", ["2.5.2.1.3б"])
            check3 = Check("Проверка UDIM. Разрешение текстурных наборов", fbx.name, True, "таблица 2, п. 5, п/п 1.2, 1.3, 3.1.1, 3.1.2", "файлов", ["2.5.1.2"])
            check4 = Check("Проверка UDIM. Разрешение текстурных наборов", fbx.name, True, "таблица 2, п. 5, п/п 1.2, 1.3, 3.1.1, 3.1.2", "файлов", ["2.5.1.3"])
            checks.append(check1)
            checks.append(check3)
            checks.append(check4)
            
            check1.checked_count = len(fbx.udim_set.diffuse_set) + len(fbx.udim_set.erm_set) + len(fbx.udim_set.normal_set)
            if not all(fbx.udim_set.diffuse_set) or not all(fbx.udim_set.erm_set) or not all(fbx.udim_set.normal_set):
                check1.add_error("Diffuse  ERM      Normal   ")
                collection = fbx.udim_set.collection
                for i in range(fbx.udim_set.sets_count):
                    s = ""
                    for k in range(3):
                        num = str(CheckUtils.udim_number(collection[i][k])) if collection[i][k] != None else "...."
                        s += str(num).ljust(9, ' ')
                    check1.add_error(s)
                continue # ???
            
            for i, file in enumerate(fbx.udim_set.diffuse_set):
                check1.checked_count += 3
                if CheckUtils.udim_number(fbx.udim_set.diffuse_set[i]) != CheckUtils.udim_number(fbx.udim_set.erm_set[i]) != CheckUtils.udim_number(fbx.udim_set.normal_set[i]):
                    check1.verified = False
                if i != 0 and CheckUtils.udim_number(fbx.udim_set.diffuse_set[i]) != CheckUtils.udim_number(fbx.udim_set.diffuse_set[i-1]) + 1:
                    check1.verified = False
            
            for set in fbx.udim_set.collection:
                set_resolutions = []
                for i in range(3):
                    check3.checked_count += 1
                    tup = CheckUtils.get_image_size(os.path.join(fbx.root, set[i]))
                    
                    try:
                        for res in tup:
                            if int(res) not in [256, 2048, 4096]:
                                check3.add_error(f"Недопустимое разрешение: {set[i]} ({res})")
                        if tup[0] != tup[1]:
                            check3.add_error(f"Текстура не квадратная: {set[i]} ({tup[0]}x{tup[1]})")
                        set_resolutions.append(int(tup[0]))
                    except:
                        check3.add_error(f"Не удалось получить разрешение текстуры {set[i]}")
                
                if len(set_resolutions) == 3:
                    ref_res = max(set_resolutions)
                    for res in set_resolutions:
                        if res == 256:
                            continue
                        if res != ref_res:
                            check4.add_error(f"Не допускается использовать разные разрешения в одной плитке (udim: {set[0][-8:-4]})")
            
        return checks

    @exception_handler
    def _check_meshes_transforms(self):
        checks = []
        for fbx in self._hp_fbx_files:
            check = Check("Проверка геометрии. Трансформации", fbx.name, True, "таблица 2, п. 3 п/п 21, п. 9, п/п 3", "мешей", ["2.3.21"])
            checks.append(check)
            check2 = Check("Проверка геометрии. Трансформации", fbx.name, True, "таблица 2, п. 3 п/п 21, п. 9, п/п 3", "мешей", ["2.9.3"])
            checks.append(check2)
            CheckUtils.check_fbx_meshes_transforms(fbx, check)
            for err in check.error_list:
                if "Location" in err:
                    check2.add_error(err)
        return checks

    @exception_handler
    def _check_polycount(self):
        checks = []
        for fbx in self._hp_fbx_files:
            check1 = Check("Проверка геометрии. Количество полигонов", fbx.name, True, "таблица 2, п. 3, п/п 12, п. 13, п/п 10-12", "полигонов", ["2.3.12"]) # 2 mln
            check12 = Check("Проверка геометрии. Количество полигонов", fbx.name, True, "таблица 2, п. 3, п/п 12, п. 13, п/п 10-12", "полигонов", ["2.13.10"])
            check13 = Check("Проверка геометрии. Количество полигонов", fbx.name, True, "таблица 2, п. 3, п/п 12, п. 13, п/п 10-12", "полигонов", ["2.13.11"])
            check2 = Check("Проверка геометрии. Триангуляция полигонов", fbx.name, True, "таблица 2, п. 3, п/п 19", "полигонов", ["2.3.19"])
            checks.append(check1)
            checks.append(check12)
            checks.append(check13)
            checks.append(check2)
            CheckUtils.check_polycount(fbx, check1, check2, 2000000, check12, check13)
        return checks

    @exception_handler
    def _check_duplicates(self):
        checks = []
        for fbx in self._hp_fbx_files:
            check1 = Check("Проверка геометрии. Дубликаты вершин", fbx.name, True, "таблица 2, п. 3, п/п 13", "мешей", ["2.3.13"])
            checks.append(check1)

            # bpy.ops.object.select_all(action='DESELECT')
            for obj in fbx.meshes:
                if obj.type != 'MESH':
                    continue
                check1.checked_count += 1
                deleted_verts_count = CheckUtils.get_count_doubles(obj)
                if deleted_verts_count > 0:
                    check1.add_error(f"{obj.name}: {deleted_verts_count} шт. дубликатов вершин")
        return checks

    @exception_handler
    def _check_texel_dencity(self):
        checks = []
        for fbx in self._hp_fbx_files:
            obj = fbx.main_mesh
            if not obj:
                continue
            
            check0 = Check("Проверка UDIM. Обязательный набор", obj.name, True, "таблица 2, п. 5, п/п 1.4.1", "полигонов", ["2.5.1.4.1"])
            check1 = Check("Проверка UDIM. Выход за границы", obj.name, True, "таблица 2, п. 5, п/п 2.1.5", "полигонов", ["2.5.2.1.5"])
            check1.checked_count = len(obj.data.polygons)
            check2 = Check("Проверка UDIM. Плотность пикселей", obj.name, True, "таблица 2, п. 6, п/п 1", "полигонов", ["2.6.1"])
            check2.checked_count = len(obj.data.polygons)
            check3 = Check("Проверка UDIM. Неиспользуемые текстуры", obj.name, True, "таблица 2, п. 5, п/п 1.8", "", ["2.5.1.8"])

            checks.append(check0)
            checks.append(check1)
            checks.append(check2)
            checks.append(check3)

            if len(fbx.udim_set.diffuse_set) == 0 or len(fbx.udim_set.erm_set) == 0 or len(fbx.udim_set.normal_set) == 0:
                check0.add_error("Обязательный набор текстур - Diffuse, ERM, Normal. Не все виды текстур найдены")

            CheckUtils.check_texel(fbx, obj, check1, check2, check3, True)

        return checks

    @exception_handler
    def _check_naming_masks(self):
        checks = []
        # adress = self._fbx_files[0].name
        adress = self.address
        if not adress:
            for fbx in self._hp_fbx_files:
                if "ground" in fbx.name.lower() and "light" not in fbx.name.lower():
                    adress = fbx.name.replace("_Ground", "")
                    adress = adress.replace("SM_", "")
                    self.address = adress
                else:
                    pass
                    # re.search(r"SM_(\w+)_\d\d\d|SM_(\w+)_Ground|SM_(\w+)", fbx.name)
        
        has_adress_num = False
        adress_num = ""
        
        for fbx in self._hp_fbx_files:
            check1 = Check("Проверка наименований. Fbx, geojson, zip", fbx.name, True, "таблица 2, п. 10, п/п 4.1", "файлов", ["2.10.4.1"])
            checks.append(check1)
            check2 = Check("Проверка наименований. Объекты геометрии", fbx.name, True, "таблица 2, п. 10, п/п 4.2, 4.5, 4.6", "обьектов", ["2.10.4.2"])
            checks.append(check2)
            check22 = Check("Проверка наименований. Источники освещения ОКС", fbx.name, True, "таблица 2, п. 10, п/п 4.2, 4.5, 4.6", "обьектов", ["2.10.4.5"])
            checks.append(check22)
            check23 = Check("Проверка наименований. Источники освещения Ground", fbx.name, True, "таблица 2, п. 10, п/п 4.2, 4.5, 4.6", "обьектов", ["2.10.4.6"])
            checks.append(check23)
            check3 = Check("Проверка наименований. Материалы", fbx.name, True, "таблица 2, п. 10, п/п 4.4", "материалов", ["2.10.4.4"])
            checks.append(check3)
            check4 = Check("Проверка наименований. Текстуры", fbx.name, True, "таблица 2, п. 10, п/п 4.3", "текстур", ["2.10.4.3"])
            checks.append(check4)
            check5 = Check("Проверка наименований. Индекс ОКС", fbx.name, True, "таблица 1, п. 3, п/п 7", "текстур", ["1.3.7"])
            checks.append(check5)

            address_with_num = adress
            if self._oks_count > 1 and "Ground" not in fbx.name:
                has_adress_num = True
                adress_num = r"_\d\d\d"
                address_with_num = fbx.name.replace("SM_", "").replace("_Light", "")
                if "light" not in fbx.name.lower() and not fbx.name[-3:].isdigit():
                    check5.add_error(f"{fbx.file_name}")
                if adress not in fbx.name:
                    check1.add_error(f"{fbx.name} : адрес ОКС не соответствует адресу благоустройства")
            elif "Ground" in fbx.name:
                has_adress_num = False
                adress_num = ""

            if "ground" in fbx.name.lower() and "light" not in fbx.name.lower():
                check1.checked_count += 3
                CheckUtils.check_mask_re(check1, fbx.file_name, "SM_" + adress + "_Ground" + r".fbx")
                CheckUtils.check_mask_re(check1, fbx.json_name, "SM_" + adress + "_Ground" + ".geojson")
                CheckUtils.check_mask_re(check1, fbx.zip_name, "SM_" + adress + "_Ground" + ".zip")

            elif "ground" in fbx.name.lower() and "light" in fbx.name.lower():
                check1.checked_count += 1
                CheckUtils.check_mask_re(check1, fbx.file_name, "SM_" + adress + "_Ground" + "_Light" + ".fbx")

                # CheckUtils.check_mask(check1, fbx.file_name, "SM_" + adress + "_Ground" + "_Light", ".fbx")
            elif "light" in fbx.name.lower():
                check1.checked_count += 1
                if has_adress_num:
                    # CheckUtils.check_mask_re(check1, fbx.file_name, "SM_" + adress + r"_\d\d\d" + "_Light" + ".fbx")
                    CheckUtils.check_mask_re(check1, fbx.file_name, "SM_" + address_with_num + "_Light" + ".fbx")
                else:
                    CheckUtils.check_mask_re(check1, fbx.file_name, "SM_" + adress + "_Light" + ".fbx")
            else:
                check1.checked_count += 3
                if has_adress_num:
                    # CheckUtils.check_mask_re(check1, fbx.file_name, "SM_" + adress + r"_\d\d\d" + ".fbx")
                    # CheckUtils.check_mask_re(check1, fbx.json_name, "SM_" + adress + r"_\d\d\d" + ".geojson")
                    # CheckUtils.check_mask_re(check1, fbx.zip_name, "SM_" + adress + r"_\d\d\d" + ".zip")
                    CheckUtils.check_mask_re(check1, fbx.file_name, "SM_" + address_with_num + ".fbx")
                    CheckUtils.check_mask_re(check1, fbx.json_name, "SM_" + address_with_num + ".geojson")
                    CheckUtils.check_mask_re(check1, fbx.zip_name, "SM_" + address_with_num + ".zip")
                else:
                    CheckUtils.check_mask_re(check1, fbx.file_name, "SM_" + adress + ".fbx")
                    CheckUtils.check_mask_re(check1, fbx.json_name, "SM_" + adress + ".geojson")
                    CheckUtils.check_mask_re(check1, fbx.zip_name, "SM_" + adress + ".zip")
            
            if "Ground" in fbx.name:
                ground_suf = "_Ground"
            else:
                ground_suf = ""

            for mesh in fbx.meshes:
                check2.checked_count += 1
                check3.checked_count += 1
                # mat = mesh.active_material

                if mesh.type == 'MESH':
                    for mat in mesh.data.materials:
                        if "ucx" in mesh.name.lower():
                            continue
                        # ground
                        if "Ground" in mesh.name and "Glass" not in mesh.name:
                            CheckUtils.check_mask_re(check3, mat.name, "M_" + adress + "_Ground" + r"_\d")
                        elif "Ground" in mesh.name and "Glass" in mesh.name:
                            CheckUtils.check_mask_re(check3, mat.name, "M_" + adress + "_GroundGlass" + r"_\d")
                        
                        # main
                        elif "Main" in mesh.name and "Glass" not in mesh.name:
                            if has_adress_num:
                                # CheckUtils.check_mask_re(check3, mat.name, "M_" + adress + r"_\d\d\d" + "_Main" + r"_\d")
                                CheckUtils.check_mask_re(check3, mat.name, "M_" + address_with_num + "_Main" + r"_\d")
                            else:
                                CheckUtils.check_mask_re(check3, mat.name, "M_" + adress + "_Main" + r"_\d")
                        elif "Main" in mesh.name and "Glass" in mesh.name:
                            if has_adress_num:
                                # CheckUtils.check_mask_re(check3, mat.name, "M_" + adress + r"_\d\d\d" + "_MainGlass" + r"_\d")
                                CheckUtils.check_mask_re(check3, mat.name, "M_" + address_with_num + "_MainGlass" + r"_\d")
                            else:
                                CheckUtils.check_mask_re(check3, mat.name, "M_" + adress + "_MainGlass" + r"_\d")
                        
                        else:
                            check3.add_error(f"Не удалось проверить имя материала {mesh.name}")

                # light
                light_check = check23 if "ground" in fbx.name.lower() else check22
                if "Root" in mesh.name:
                    # CheckUtils.check_mask_re(light_check, mesh.name, adress + adress_num + ground_suf + "_Root")
                    CheckUtils.check_mask_re(light_check, mesh.name, address_with_num + ground_suf + "_Root")
                elif "Omni" in mesh.name:
                    # CheckUtils.check_mask_re(light_check, mesh.name, adress + adress_num + ground_suf + "_Omni" + r"_\d\d\d")
                    CheckUtils.check_mask_re(light_check, mesh.name, address_with_num + ground_suf + "_Omni" + r"_\d\d\d")
                elif "Spot" in mesh.name:
                    # CheckUtils.check_mask_re(light_check, mesh.name, adress + adress_num + ground_suf + "_Spot" + r"_\d\d\d")
                    CheckUtils.check_mask_re(light_check, mesh.name, address_with_num + ground_suf + "_Spot" + r"_\d\d\d")
                
                # collision
                elif "UCX" in mesh.name and "Ground" not in mesh.name:
                    # CheckUtils.check_mask_re(check2, mesh.name, "UCX_" + "SM_" + adress + adress_num + "_Main" + r"_\d\d\d")
                    CheckUtils.check_mask_re(check2, mesh.name, "UCX_" + "SM_" + address_with_num + "_Main" + r"_\d\d\d")
                elif "UCX" in mesh.name and "Ground" in mesh.name:
                    CheckUtils.check_mask_re(check2, mesh.name, "UCX_" + "SM_" + adress + "_Ground" + r"_\d\d\d")
                
                # ground
                elif "Ground" in mesh.name and "Glass" not in mesh.name:
                    CheckUtils.check_mask_re(check2, mesh.name, "SM_" + adress + "_Ground")
                    # CheckUtils.check_mask_re(check3, mat.name, "M_" + adress + "_Ground" + r"_\d")
                elif "Ground" in mesh.name and "Glass" in mesh.name:
                    CheckUtils.check_mask_re(check2, mesh.name, "SM_" + adress + "_GroundGlass")
                    # CheckUtils.check_mask_re(check3, mat.name, "M_" + adress + "_GroundGlass" + r"_\d")
                
                # main
                elif "Main" in mesh.name and "Glass" not in mesh.name:
                    if has_adress_num:
                        # CheckUtils.check_mask_re(check2, mesh.name, "SM_" + adress + r"_\d\d\d" + "_Main")
                        CheckUtils.check_mask_re(check2, mesh.name, "SM_" + address_with_num + "_Main")
                        # CheckUtils.check_mask_re(check3, mat.name, "M_" + adress + r"_\d\d\d" + "_Main" + r"_\d")
                    else:
                        CheckUtils.check_mask_re(check2, mesh.name, "SM_" + adress + "_Main")
                        # CheckUtils.check_mask_re(check3, mat.name, "M_" + adress + "_Main" + r"_\d")
                elif "Main" in mesh.name and "Glass" in mesh.name:
                    if has_adress_num:
                        # CheckUtils.check_mask_re(check2, mesh.name, "SM_" + adress + r"_\d\d\d" + "_MainGlass")
                        CheckUtils.check_mask_re(check2, mesh.name, "SM_" + address_with_num + "_MainGlass")
                        # CheckUtils.check_mask_re(check3, mat.name, "M_" + adress + r"_\d\d\d" + "_MainGlass" + r"_\d")
                    else:
                        CheckUtils.check_mask_re(check2, mesh.name, "SM_" + adress + "_MainGlass")
                        # CheckUtils.check_mask_re(check3, mat.name, "M_" + adress + "_MainGlass" + r"_\d")
                
                else:
                    check2.add_error(f"Не удалось проверить имя меша {mesh.name} (возможно отсутствует суффикс Main)")
            
            ucx_counter = 0
            light_counter = 0
            for err in reversed(check2.error_list):
                if "UCX" in err:
                    if ucx_counter > 5:
                        check2.error_list.remove(err)
                    else:
                        ucx_counter += 1
                if "Omni" in err or "Spot" in err:
                    if light_counter > 5:
                        check2.error_list.remove(err)
                    else:
                        light_counter += 1

            set = fbx.udim_set
            if set:
                for image_name in set.diffuse_set:
                    if image_name == None:
                        continue
                    check4.checked_count += 1
                    # CheckUtils.check_mask_re(check4, image_name, "T_" + adress + adress_num + ground_suf + "_Diffuse" + r"_\d" + r".\d\d\d\d" + ".png")
                    CheckUtils.check_mask_re(check4, image_name, "T_" + address_with_num + ground_suf + "_Diffuse" + r"_\d" + r".\d\d\d\d" + ".png")
                for image_name in set.erm_set:
                    if image_name == None:
                        continue
                    check4.checked_count += 1
                    # CheckUtils.check_mask_re(check4, image_name, "T_" + adress + adress_num + ground_suf + "_ERM" + r"_\d" + r".\d\d\d\d" + ".png")
                    CheckUtils.check_mask_re(check4, image_name, "T_" + address_with_num + ground_suf + "_ERM" + r"_\d" + r".\d\d\d\d" + ".png")
                for image_name in set.normal_set:
                    if image_name == None:
                        continue
                    check4.checked_count += 1
                    # CheckUtils.check_mask_re(check4, image_name, "T_" + adress + adress_num + ground_suf + "_Normal" + r"_\d" + r".\d\d\d\d" + ".png")
                    CheckUtils.check_mask_re(check4, image_name, "T_" + address_with_num + ground_suf + "_Normal" + r"_\d" + r".\d\d\d\d" + ".png")
            
        return checks

    @exception_handler
    def _check_fbx_objects(self):
        checks = []
        for fbx in self._hp_fbx_files:
            check1 = Check("Проверка FBX. Состав файла", fbx.name, True, "таблица 2, п. 3, п/п 1-3", "", ["2.3.1а"])
            checks.append(check1)
            check12 = Check("Проверка FBX. Состав файла", fbx.name, True, "таблица 2, п. 3, п/п 1-3", "", ["2.3.3"])
            checks.append(check12)
            check13 = Check("Проверка FBX. Состав файла", fbx.name, True, "таблица 2, п. 3, п/п 1-3", "", ["2.3.10"])
            checks.append(check13)

            check2 = Check("Проверка FBX. Коллизии", fbx.name, True, "таблица 2, п. 13, п/п 3", "", ["2.13.3"])
            checks.append(check2)

            check3 = Check("Проверка FBX. Основная геометрия", fbx.name, True, "таблица 2, п. 3, п/п 7", "", ["2.3.7"])
            checks.append(check3)

            check4 = Check("Проверка FBX. Остекление", fbx.name, True, "таблица 2, п. 3, п/п 5-6", "", ["2.8.1"])
            checks.append(check4)
            # check5 = Check("Проверка FBX. Остекление", fbx.name, True, "таблица 2, п. 3, п/п 5-6", "", ["2.3.6"])
            # checks.append(check5)

            glass_count = 0
            ucx_count = 0
            other_count = 0
            fbx_name = fbx.name.lower()
            for obj in fbx.meshes:
                obj_name = obj.name.lower()
                if "light" in fbx_name:
                    if obj.type != 'LIGHT' and obj.type != 'EMPTY':
                        check1.add_error(f"Лишний объект: {obj.name} ({obj.type})")
                else:
                    if obj.parent != None:
                        check13.add_error(f"{obj.parent.name}: Объекты геометрии не должны иметь иерархических связей между собой")
                    if obj.type != 'MESH':
                        check1.add_error(f"Лишний объект: {obj.name} ({obj.type})")
                        continue
                    if "ucx" in obj_name:
                        ucx_count += 1
                    elif "glass" in obj_name:
                        glass_count += 1
                    else:
                        other_count += 1

            if "light" not in fbx_name:
                # if "ground" not in fbx_name:
                #     if glass_count == 0:
                #         check4.add_error(f"{fbx.name}: Не найдено остекление MainGlass для объекта ОКС")
                if ucx_count == 0:
                    check2.add_error("Не найдено геометрии коллизий")
                if other_count != 1:
                    check3.add_error(f"Вся геометрия (кроме остекления и коллизий) должна быть объединена в единый меш (Main или Ground). Найдено объектов геометрии - {other_count} шт.")
            if glass_count > 1:
                check4.add_error(f"{fbx.name}: Остекление необходимо объединять в единый объект. Мешей остекления найдено: {glass_count} шт.")

            if fbx.objects_actions_count > 0:
                check1.add_error(f"Лишние анимации: {fbx.objects_actions_count} шт.")
            if fbx.objects_cameras_count > 0:
                check1.add_error(f"Лишние камеры: {fbx.objects_cameras_count} шт.")
            if fbx.objects_collections_count > 1:
                check12.add_error(f"Лишние коллекции: {fbx.objects_collections_count - 1} шт.")
            
        return checks

    @exception_handler
    def _check_glasses_uv(self):
        checks = []
        for fbx in self._hp_fbx_files:
            obj = None
            for mesh in fbx.meshes:
                if "Glass" in mesh.name:
                    obj = mesh
            if not obj:
                continue

            check1 = Check("Проверка UDIM. Остекление", fbx.name, True, "таблица 2, п. 5, п/п 2.2.1", "", ["2.5.2.2.1а"])
            checks.append(check1)
            # check2 = Check("Проверка UDIM. Остекление. Вертикальная ориентация", fbx.name, True, "таблица 2, п. 5, п/п 2.2.3", "", ["2.5.2.2.3"])
            # checks.append(check2)

            bpy.ops.object.mode_set(mode='OBJECT')
            face_count = len(obj.data.polygons)

            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(obj.data)
            # bmesh.ops.triangulate(bm, faces=bm.faces[:])
            bm.faces.ensure_lookup_table()

            loops = []
            try:
                for x in range(face_count):
                    for loop in bm.faces[x].loops:
                        loops.append(loop[bm.loops.layers.uv.active].uv)
                        # loops.append(loop[layer].uv)
            except:
                check1.add_error(f"Can`t find UVmap, obj={obj.name}")
                continue

            udim_nums = [CheckUtils.uv_to_udim_number(loops[i].x, loops[i].y) for i in range(len(loops))]
            if any(num != 1001 for num in udim_nums):
                check1.add_error("UV-развертка остекления вне UDIM плитки 1001")
            
            bpy.ops.object.mode_set(mode='OBJECT')

            # bpy.ops.object.mode_set(mode='OBJECT')
            # me = obj.data
            # uv_layer = me.uv_layers.active.data
            # vertical_error_count = 0
            # vector_up = mathutils.Vector((0, 0, 1.0))
            # for poly in me.polygons:
            #     if round(math.degrees(poly.normal.angle(vector_up)) / 20) * 20 == 0:
            #         continue
            #     points_uv = []
            #     points_g = []
            #     points = []
            #     for i in poly.loop_indices:
            #         v_ind = me.loops[i].vertex_index
            #         point = me.vertices[v_ind]
            #         points.append(point)
            #         points_g.append((v_ind, round(point.co.z, 2)))
            #         points_uv.append((v_ind, round(uv_layer[i].uv.y, 3)))

            #     check = True 
            #     for i in range(len(points)):
            #         dist = (points[i].co - points[(i + 1) % len(points)].co).length
            #         if dist < 0.05:
            #             check = False
            #             break
            #     if not check:
            #         continue

            #     points_uv.sort(key=lambda x: (x[1], x[0]))
            #     points_g.sort(key=lambda x: (x[1], x[0]))
            #     for i in range(len(points_uv)):
            #         if points_uv[i][0] != points_g[i][0]:
            #             vertical_error_count += 1
            #             check2.verified = False
            #             break

            # if (not check2.verified):
            #     check2.add_error(f"UV-развертка остекления должна быть направлена вертикально. Неверно направлены: {vertical_error_count} шт.")

        return checks

    @exception_handler
    def _check_materials(self):
        checks = []
        for fbx in self._hp_fbx_files:
            check1 = Check("Проверка UDIM. Наличие UV-развертки (UV-maps, UV-layers)", fbx.name, True, "таблица 2, п. 5, п/п 2.1.3, 2.2.6", "", ["2.5.2.1.3а"])
            checks.append(check1)
            check12 = Check("Проверка UDIM. Наличие UV-развертки (UV-maps, UV-layers)", fbx.name, True, "таблица 2, п. 5, п/п 2.1.3, 2.2.6", "", ["2.5.2.2.6"])
            checks.append(check12)
            check2 = Check("Проверка материалов. Количество материалов стекло максимум", fbx.name, True, "таблица 2, п. 8, п/п 2, п. 13, п/п 7", "", ["2.8.2"])
            checks.append(check2)
            check22 = Check("Проверка материалов. Количество материалов коллизии", fbx.name, True, "таблица 2, п. 8, п/п 2, п. 13, п/п 7", "", ["2.13.7"])
            checks.append(check22)
            check23 = Check("Проверка материалов. Количество материалов максимум", fbx.name, True, "таблица 2, п. 8, п/п 2, п. 13, п/п 7", "", ["2.4.7"])
            checks.append(check23)
            check24 = Check("Проверка материалов. Количество материалов максимум", fbx.name, True, "таблица 2, п. 8, п/п 2, п. 13, п/п 7", "", ["2.4.4"])
            checks.append(check24)
            check3 = Check("Проверка материалов. Ссылки", fbx.name, True, "таблица 2, п. 4, п/п 3", "", ["2.4.3"])
            checks.append(check3)
            check4 = Check("Проверка материалов. Текстуры в Glass", fbx.name, True, "таблица 2, п. 4, п/п 3", "", ["2.4.2"])
            checks.append(check4)

            ucx_err = 0
            ucx_with_material_count = 0
            for obj in fbx.meshes:
                if obj.type != 'MESH':
                    continue
                uvmap_count = len(obj.data.uv_layers)
                # max_count = 0 if "UCX" in obj.name else 1
                if "UCX" in obj.name:
                    if uvmap_count > 0:
                        ucx_err += 1
                else:
                    if uvmap_count > 1:
                        check1.add_error(f"{obj.name} - Более одной UV-развертки")
                    elif uvmap_count == 0:
                        check1.add_error(f"{obj.name} - Не найдено UV-развертки")
                
                if "Glass" in obj.name:
                    if len(obj.data.materials) > 7:
                        check2.add_error(f"{obj.name}: Более 7 материалов остекления")
                elif "UCX" in obj.name:
                    if len(obj.data.materials) > 0:
                        ucx_with_material_count += 1
                        # check22.add_error(f"{obj.name}: У геометрии коллизий не должно быть материала")
                elif len(obj.data.materials) > 7:
                    check23.add_error(f"{obj.name}: Более 7 материалов")
                elif len(obj.data.materials) == 0:
                    check23.add_error(f"{obj.name}: отсутствует материал")
                # elif len(fbx.udim_set.diffuse_set) <= 100 and len(obj.data.materials) > 1:
                elif len(obj.data.materials) > 1:
                    check24.add_error(f"{obj.name}: Более 1 материала допустимо использовать при кол-ве текстур более 100 шт. на один fbx файл")

                for mat in obj.data.materials:
                    bsdf = CheckUtils.get_bsdf(mat)
                    if not bsdf:
                        continue
                    for inp in bsdf.inputs:
                        if inp.is_linked and inp.name != "Normal":
                            check3.add_error(f"Лишняя ссылка в материале {mat.name} ({inp.name})")
                
                    found_tex_node = False
                    for node in mat.node_tree.nodes:
                        if node.bl_static_type == 'TEX_IMAGE':
                            found_tex_node = True
                    if found_tex_node:
                        check4.add_error(f"{mat.name}: материалы не должны включать в себя текстуры")
            
            if ucx_with_material_count:
                check22.add_error(f"У геометрии коллизий не должно быть материала. Коллизий с материалом - {ucx_with_material_count} шт.")

            if ucx_err:
                check12.add_error(f"У объектов коллизий не должно быть UV-развертки. Коллизий с разверткой: {ucx_err} шт.")
            
        return checks

    @exception_handler
    def _check_lights(self):
        checks = []
        for fbx in self._hp_fbx_files:
            check1 = Check("Проверка освещения. Иерархия", fbx.name, True, "таблица 2, п. 15, п/п 9", "", ["2.15.9"])
            checks.append(check1)

            check2 = Check("Проверка освещения. Типы источников и дальность распространения", fbx.name, True, "таблица 2, п. 15, п/п 6, 8", "", ["2.15.6"])
            checks.append(check2)
            check22 = Check("Проверка освещения. Типы источников и дальность распространения", fbx.name, True, "таблица 2, п. 15, п/п 6, 8", "", ["2.15.8"])
            checks.append(check22)

            check3 = Check("Проверка освещения. Количество", fbx.name, True, "таблица 2, п. 15, п/п 3", "", ["2.15.3"])
            checks.append(check3)

            if "Light" not in fbx.name:
                continue

            lights_count = 0
            for obj in fbx.meshes:
                if obj.type == 'EMPTY':
                    if obj.parent != None:
                        check1.add_error(f"{obj.name}: Root не должен иметь родительских объектов")
                    continue
                if obj.type != 'LIGHT':
                    check1.verified = False
                    continue

                if obj.parent == None:
                    check1.add_error(f"{obj.name}: Источники освещения должны находиться в корневом элементе Root")

                lights_count += 1

                if obj.data.use_custom_distance:
                    check22.add_error(f"{obj.name}: Дальность распространения необходимо отключать")

                if obj.data.type != 'POINT' and obj.data.type != 'SPOT':
                    check2.add_error(f"{obj.name}: Тип источника освещения не соответствует. Допустимы только точечные или конические источники")
            
            if lights_count > 50:
                check3.add_error(f"Более 50 источников освещения")
        return checks

    @exception_handler
    def _check_collision(self):
        checks = []
        for fbx in self._hp_fbx_files:

            check1 = Check("Проверка коллизий. Замкнутость, выпуклость", fbx.name, True, "таблица 2, п. 13, п/п 1", "", ["2.13.1"])
            checks.append(check1)

            # check2 = Check("Проверка коллизий. Выпуклость", fbx.name, True, "", "")
            # checks.append(check2)

            check3 = Check("Проверка коллизий. Нумерация", fbx.name, True, "таблица 2, п. 10, п/п 4.2", "", ["2.10.4.2"])
            checks.append(check3)

            check4 = Check("Проверка коллизий. Пересечения", fbx.name, True, "таблица 2, п. 13, п/п 4", "", ["2.13.4"])
            checks.append(check4)

            ucx_nums = []
            unclosed_nums = []
            non_convex_nums = []
            for obj in fbx.meshes:
                if "UCX" not in obj.name:
                    continue
                
                num_str = obj.name[-3:]
                if num_str.isdigit():
                    ucx_nums.append(int(num_str))
                
                me = obj.data
                if len(me.vertices) - len(me.edges) + len(me.polygons) != 2:
                    # check1.add_error(f"{obj.name}: Незамкнутая геометрия")
                    unclosed_nums.append(num_str)
                    continue

                # bpy.context.view_layer.objects.active = obj
                # bpy.ops.object.mode_set(mode='EDIT')
                # bm = bmesh.from_edit_mesh(obj.data)
                # bm.faces.ensure_lookup_table()

                # for edge in bm.edges:
                #     if not edge.is_manifold:
                #         check1.add_error(f"{obj.name}: Незамкнутая геометрия")
                #         break
                # bpy.ops.object.mode_set(mode='OBJECT')
                # if not check1.verified:
                #     continue

                if not CheckUtils.check_mesh_convex(obj):
                    # check1.add_error(f"{obj.name}: Невыпуклая геометрия")
                    non_convex_nums.append(num_str)
            
            if unclosed_nums:
                nums = ", ".join(unclosed_nums)
                check1.add_error(f"Незамкнутая геометрия. {len(unclosed_nums)} шт., номера коллизий - {nums}.")
            if non_convex_nums:
                nums = ", ".join(non_convex_nums)
                check1.add_error(f"Невыпуклая геометрия. {len(non_convex_nums)} шт., номера коллизий - {nums}.")


            list2 = list(reversed(fbx.meshes))
            intersections = []
            for obj_1 in fbx.meshes:
                if obj_1.type != "MESH" or "UCX" not in obj_1.name:
                    continue
                for obj_2 in list2:
                    if obj_2.type != "MESH" or obj_2 == obj_1 or "UCX" not in obj_2.name:
                        continue
                    # if "Ground" in obj_1.name and "Ground" not in obj_2.name or "Ground" not in obj_1.name and "Ground" in obj_2.name:
                    #     continue
                    intersection = CheckUtils.check_bvh_intersection(obj_1, obj_2)
                    if intersection:
                        # check4.add_error(f"Пересечение коллизий {obj_1.name[-3:]} и {obj_2.name[-3:]}")
                        intersections.append(f"({obj_1.name[-3:]} и {obj_2.name[-3:]})")
                        # logger.add(f"{obj_1.name}{'' if intersection else ' DOES NOT'} intersect {obj_2.name}")
                list2.pop()
            if intersections:
                if len(intersections) > 15:
                    nums = ", ".join(intersections[:15]) + ", и т. д."
                else:
                    nums = ", ".join(intersections)
                check4.add_error(f"Пересечение коллизий. {len(intersections)} шт., номера коллизий - {nums}")

            check1.error_list.sort()
            ucx_nums.sort()
            if ucx_nums and ucx_nums[0] != 1:
                check3.add_error(f"Ошибка нумерации коллизий (номер {ucx_nums[0]})")
            for i in range(1, len(ucx_nums)):
                if ucx_nums[i] != ucx_nums[i-1] + 1:
                    check3.add_error(f"Ошибка нумерации коллизий (номер {ucx_nums[i]})")
                    # break
        return checks

    @exception_handler
    def _check_flipped(self):
        checks = []
        # for fbx in self._hp_fbx_files:
        #     check1 = Check("Проверка UDIM. Зеркальные острова", fbx.name, True, "таблица 2, п. 5, п/п 2.1.4", "", ["2.5.2.1.4"])
        #     checks.append(check1)

        #     for obj in fbx.meshes:
        #         if obj.type != 'MESH' or not len(obj.data.uv_layers) or "ucx" in obj.name.lower():
        #             continue
        #         bpy.ops.object.mode_set(mode='OBJECT')
        #         bpy.context.view_layer.objects.active = obj
        #         bpy.ops.object.mode_set(mode='EDIT')
        #         bm = bmesh.from_edit_mesh(obj.data)
        #         uv_layer = bm.loops.layers.uv.verify()

        #         sel_faces = [f for f in bm.faces]
        #         flipped_count = CheckUtils.get_flipped_count(sel_faces, uv_layer)
        #         if flipped_count > 0:
        #             check1.add_error(f"{obj.name}: зеркальных полигонов - {flipped_count} шт.")

        # try:
        #     bpy.ops.object.mode_set(mode='OBJECT')
        # except:
        #     pass
        return checks

    @exception_handler
    def _check_json_properties(self):
        checks = []
        for fbx in self._hp_fbx_files:
            # check1 = Check("Проверка geojson. Код функционального назначения", fbx.name, True, "", "", ["2.2.1"])
            # checks.append(check1)
            check2 = Check("Проверка geojson. Поля", fbx.name, True, "", "", ["2.2.1"])
            checks.append(check2)

            jsonData = fbx.json_data
            if not jsonData:
                # logger.add(F"Не удалось получить данные из geojson файла {fbx.file_name}")
                if "light" not in fbx.name.lower():
                    check2.add_error(f"Не удалось получить данные из geojson файла {fbx.json_name}")
                continue

            fno_code = jsonData["features"][0]["properties"]["FNO_code"]
            fno_name = jsonData["features"][0]["properties"]["FNO_name"]
            fno_code_strip = fno_code.replace(" ", "")
            fno_name_strip = fno_name.replace(" ", "")

            if "ground" in fbx.name.lower():
                if fno_code_strip != "000":
                    check2.add_error(f"Для благоустройства рекомендуется использовать FNO_code - \"000\"")
                continue
            
            root_dir = os_utils.get_documents_dir()
            with open(os.path.join(root_dir, r"fno_codes_utf8.csv"), encoding='utf-8-sig') as csvfile:
                rows = csv.reader(csvfile, delimiter=';')
                
                code_len = len(fno_code_strip)
                if code_len not in [3, 6, 9]:
                    check2.add_error(f"{fno_code}: код не соответствует шаблонам - XXX, XXX XXX, XXX XXX XXX")
                    return checks
                
                column_ind = int(code_len / 3 * 2 - 1)
                found = False
                for row in rows:
                    if row[column_ind].replace(" ", "") == fno_code_strip:
                        found = True
                        # logger.add(f"Found code {row[column_ind]} with name {row[column_ind-1]}")
                        if fno_name_strip != row[column_ind-1].replace(" ", ""):
                            check2.add_error(f"{fno_code}: код не соответсвует наименованию\n{fno_name}, должно быть\n{row[column_ind-1]}")
                if not found:
                    check2.add_error(f"{fno_code}: код не найден в классификаторе")
            
            props = ["address", "okrug", "rajon", "name", "developer", "designer", "cadNum", 
                     "FNO_code", "FNO_name", "ZU_area", "h_relief", "h_otn", "h_abs", "s_obsh", 
                     "s_naz", "s_podz", "spp_gns", "act_AGR", "imageBase64"]
            for prop in jsonData["features"][0]["properties"]:
                if prop in props:
                    props.remove(prop)
            for prop in props:
                check2.add_error(f"Не найдено свойство \"{prop}\"")
        return checks

    @exception_handler
    def _check_pivot(self):
        checks = []
        for fbx in self._hp_fbx_files:
            obj = fbx.main_mesh
            if not obj:
                continue

            check1 = Check("Проверка геометрии. Точка отсчета", fbx.name, True, "таблица 2, п. 9, п/п 4", "", ["2.9.4а"])
            checks.append(check1)

            dim_x = obj.dimensions.x
            dim_y = obj.dimensions.y

            center = sum((mathutils.Vector(b) for b in obj.bound_box), mathutils.Vector())
            center /= 8

            offset_x = round(center.x * obj.scale.x / dim_x * 100, 2)
            offset_y = round(center.y * obj.scale.y / dim_y * 100, 2)

            if offset_x > 10  or offset_y > 10:
                check1.add_error(f"Точка отсчета смещена относительно геометрического центра (ось x: {offset_x}%, ось y: {offset_y}%)")

        return checks

    @exception_handler
    def _check_png(self):
        checks = []
        for fbx in self._hp_fbx_files:
            check1 = Check("Проверка png. ERM, Normal. Альфа-канал", fbx.name, True, "таблица 2, п. 5, п/п 1.6", "файлов", ["2.5.1.6"])
            checks.append(check1)
            check2 = Check("Проверка png. Заглушки. Альфа-канал", fbx.name, True, "таблица 2, п. 5, п/п 3.3", "файлов", ["2.5.3.3"])
            checks.append(check2)
            check3 = Check("Проверка png. Заглушки. Один цвет", fbx.name, True, "таблица 2, п. 5, п/п 3.4", "файлов", ["2.5.3.4"])
            checks.append(check3)

            set = fbx.udim_set
            if set:
                for image_name in set.diffuse_set:
                    if image_name == None:
                        continue
                    imPath = os.path.join(fbx.root, image_name)
                    res = CheckUtils.get_image_size(os.path.join(imPath))[0]
                    if res == 256:
                        im = bpy.data.images.load(imPath, check_existing=True)
                        if not CheckUtils.is_one_color_image(im):
                            check3.add_error(f"{image_name}: многоцветная заглушка")
                        if CheckUtils.image_has_alpha(im):
                            check2.add_error(f"{image_name}: заглушка с альфа-каналом")
                for image_name in set.erm_set:
                    if image_name == None:
                        continue
                    imPath = os.path.join(fbx.root, image_name)
                    im = bpy.data.images.load(imPath, check_existing=True)
                    if CheckUtils.image_has_alpha(im):
                        check1.add_error(f"{image_name}: карта ERM с альфа-каналом")
                    if im.size[0] == 256:
                        if not CheckUtils.is_one_color_image(im):
                            check3.add_error(f"{image_name}: многоцветная заглушка")
                for image_name in set.normal_set:
                    if image_name == None:
                        continue
                    imPath = os.path.join(fbx.root, image_name)
                    im = bpy.data.images.load(imPath, check_existing=True)
                    if CheckUtils.image_has_alpha(im):
                        check1.add_error(f"{image_name}: карта Normal с альфа-каналом")
                    if im.size[0] == 256:
                        if not CheckUtils.is_one_color_image(im):
                            check3.add_error(f"{image_name}: многоцветная заглушка")
        return checks

class LowpolyChecks():
    def __init__(self):
        self.lp_checks = dict()
        self.lp_checks_by_ids = dict()
        self._lp_fbx_files: list[FbxFile] = []
        self.lp_result_report = ""
        self.address = ""
        self.root_path = ""
        self.by_collections = False
    
    def run_checks(self, lp_fbx_files):
        self._lp_fbx_files = lp_fbx_files
        lp_checks = []
        lp_checks.extend(self._check_naming_masks())
        lp_checks.extend(self._check_transforms())
        lp_checks.extend(self._check_polycount())
        lp_checks.extend(self._check_duplicates())
        lp_checks.extend(self._check_texel_dencity())
        lp_checks.extend(self._check_fbx_objects())
        lp_checks.extend(CheckUtils.check_files(True, self.root_path))
        lp_checks.extend(self._check_materials())
        lp_checks.extend(self._check_images())
        lp_checks.extend(CheckUtils.check_color_attributes(lp_fbx_files))

        for check in lp_checks:
            if check.name not in self.lp_checks:
                self.lp_checks[check.name] = []
            self.lp_checks[check.name].append(check)
        
        for check in lp_checks:
            if check.paragraph_ids[0] not in self.lp_checks_by_ids:
                self.lp_checks_by_ids[check.paragraph_ids[0]] = []
            self.lp_checks_by_ids[check.paragraph_ids[0]].append(check)

        self._generate_result()

    def _generate_result(self):
        msg1 = ""
        msg2 = ""
        msg_only_errors = ""

        for key in sorted(self.lp_checks):
            verified_all = all([ch.verified for ch in self.lp_checks[key]])
            verified_all_string = str(verified_all).ljust(6, " ")
            header = key.ljust(70, ".")
            count = sum([ch.checked_count for ch in self.lp_checks[key]])
            err_count = sum([len(ch.error_list) for ch in self.lp_checks[key]])
            paragraph = f"({self.lp_checks[key][0].paragraph})" if self.lp_checks[key][0].paragraph else ""
            # msg1 += f"{header}{verified_all_string} (Проверено {self.lp_checks[key][0].units_text}: {count}, ошибок:{err_count}) (пункт требований: {self.lp_checks[key][0].paragraph})\n"
            msg1 += f"{header}{verified_all_string} {paragraph}\n"
            if verified_all:
                continue
            # msg2 += f"\n{header}{verified_all_string} (Проверено {self.lp_checks[key][0].units_text}: {count}, ошибок:{err_count}) {paragraph}\n"
            # msg2 += f"\n{header}{verified_all_string} {paragraph}\n"
            msg2 += f"\n{key} {paragraph}\n"
            msg_only_errors += f"\n{key} {paragraph}\n"
            err_lines = ""
            for check in self.lp_checks[key]:
                if not check.verified:
                    err_lines += f"    {check.directory}\n"
                    for err in check.error_list:
                        err_lines += f"        {err}\n"
            msg2 += err_lines
            msg_only_errors += err_lines
        
        start = "-----------------------Низкополигональная модель---------------------------"
        end = "-----------------------------------------------------------------------------"
        # logger.add(f"\n\n{start}\nПроверки:\n{msg1}\nОшибки:\n{msg2}\n{end}\n")
        # self.hp_result_report = f"\n\n{start}\nПроверки:\n{msg1}\nОшибки:\n{msg2}\n{end}\n{msg_only_errors}\n{end}"
        self.lp_result_report = f"\n\n{start}\nПроверки:\n{msg1}\n\nОшибки:\n{msg2}\n{end}"

    @exception_handler
    def _check_naming_masks(self): 
        checks = []
        # adress = self._fbx_files[0].name
        adress = self.address

        if not adress:
            for fbx in self._lp_fbx_files:
                if "ground" in fbx.name.lower():
                    adress = "_".join(fbx.name.split("_")[1:-1])
                    self.address = adress
        
        common_address = adress
        
        for fbx in self._lp_fbx_files:
            check0 = Check("Проверка наименований. Zip", fbx.name, True, "таблица 2, п. 10, п/п 3.1-2", "файлов", ["2.10.3.1"])
            check1 = Check("Проверка наименований. Fbx", fbx.name, True, "таблица 2, п. 10, п/п 3.1-2", "файлов", ["2.10.3.2"])
            check2 = Check("Проверка наименований. Объекты геометрии", fbx.name, True, "таблица 2, п. 10, п/п 3.3", "обьектов", ["2.10.3.3"])
            check3 = Check("Проверка наименований. Материалы", fbx.name, True, "таблица 2, п. 10, п/п 3.5", "материалов", ["2.10.3.5"])
            check4 = Check("Проверка наименований. Текстуры", fbx.name, True, "таблица 2, п. 10, п/п 3.4", "текстур", ["2.10.3.4"])
            check5 = Check("Проверка fbx-файлов. Упаковка текстур в fbx", fbx.name, True, "таблица 2, п. 5, п/п 1", "", ["2.5.1"])
            check6 = Check("Проверка текстур. Разрешение", fbx.name, True, "таблица 2, п. 5, п/п 2, 4", "", ["2.5.2"])
            check7 = Check("Проверка текстур. Альфа канал", fbx.name, True, "", "текстур", ["2.5.5"])
            checks.extend([check0, check1, check2, check3, check4, check5, check6, check7])

            if common_address not in fbx.name:
                check1.add_error(f"{fbx.name} : адрес ОКС не соответствует адресу благоустройства")
            adress = "_".join(fbx.name.split("_")[1:-1])

            if "ground" in fbx.name.lower():
                check1.checked_count += 2
                CheckUtils.check_mask_re(check1, fbx.file_name, r"\d\d\d\d_" + adress + "_Ground" + ".fbx")
                # if not self.by_collections:
                CheckUtils.check_mask_re(check0, fbx.zip_name, r"\d\d\d\d_" + adress + ".zip")
            else:
                check1.checked_count += 3
                CheckUtils.check_mask_re(check1, fbx.file_name, r"\d\d\d\d_" + adress + r"_\d\d" + ".fbx")

            # if "Ground" in fbx.name:
            for obj in fbx.meshes:
                if obj.type != 'MESH':
                    continue
                suf = CheckUtils.lp_get_suffix(obj)
                ground_lp_blender_suf = ".001" if self.by_collections and ("ground." in obj.name.lower() or "groundglass" in obj.name.lower()) else ""
                CheckUtils.check_mask_re(check2, obj.name, "SM_" + adress + suf + ground_lp_blender_suf)

                for mat in obj.data.materials:
                    if "glass" in obj.name.lower():
                        # if re.match(r".\d\d\d$", mat.name):
                        #     pass
                        CheckUtils.check_mask_re(check3, mat.name, r"M_Glass_\d\d")
                    else:
                        CheckUtils.check_mask_re(check3, mat.name, "M_" + adress + suf + r"_\d{1,2}" + ground_lp_blender_suf)
                    bsdf = CheckUtils.get_bsdf(mat)
                    if not bsdf:
                        continue
                    for i, tex_symbol in [(0, "d"), (1, "m"), (2, "r"), (4, "o"), (5, "n")]:
                        inp = bsdf.inputs[i]
                        if not inp.is_linked:
                            continue
                        node = inp.links[0].from_node
                        if node.bl_static_type == 'NORMAL_MAP':
                            if not node.inputs[1].is_linked:
                                continue
                            else:
                                node = node.inputs[1].links[0].from_node
                        if node.bl_static_type == 'TEX_IMAGE':
                            im_name = os.path.split(node.image.filepath)[1]
                            # CheckUtils.check_mask_re(check4, im_name, "T" + mat.name[1:-1] + tex_symbol + r"_\d" + ".png")
                            CheckUtils.check_mask_re(check4, im_name, "T_" + adress + suf + "_" + tex_symbol + r"_\d{1,2}" + ".png")
                            if node.outputs[1].is_linked:
                                check7.add_error(f"Альфа-канал изображений запрещен к использованию {im_name}")
                            if len(node.image.packed_files) == 0:
                                check5.add_error(f"Текстура {im_name} не упакована в файл FBX")
                            if node.image.size[0] != node.image.size[1] or node.image.size[0] not in [128, 256, 512, 1024, 2048]:
                                check6.add_error(f"{im_name}: недопустимое разрешение {node.image.size[0]}x{node.image.size[1]}")

        return checks

    @exception_handler
    def _check_transforms(self):
        checks = []
        for fbx in self._lp_fbx_files:
            check = Check("Проверка геометрии. Трансформации", fbx.name, True, "таблица 2, п. 3, п/п 16", "мешей", ["2.3.16"])
            checks.append(check)
            CheckUtils.check_fbx_meshes_transforms(fbx, check, True)
        return checks

    @exception_handler
    def _check_polycount(self):
        checks = []
        for fbx in self._lp_fbx_files:
            check1 = Check("Проверка геометрии. Количество полигонов", fbx.name, True, "таблица 2, п. 3, п/п 6", "полигонов", ["2.3.6"])
            check2 = Check("Проверка геометрии. Триангуляция полигонов", fbx.name, True, "таблица 2, п. 3, п/п 12", "полигонов", ["2.3.12"])
            checks.append(check1)
            checks.append(check2)

            if "ground" in fbx.name.lower():
                CheckUtils.check_polycount(fbx, check1, check2, 180000)
            else:
                CheckUtils.check_polycount(fbx, check1, check2, 150000)
        
        return checks

    @exception_handler
    def _check_duplicates(self):
        checks = []
        for fbx in self._lp_fbx_files:
            check1 = Check("Проверка геометрии. Дубликаты вершин", fbx.name, True, "таблица 2, п. 3, п/п 7", "мешей", ["2.3.7"])
            checks.append(check1)

            # bpy.ops.object.select_all(action='DESELECT')
            for obj in fbx.meshes:
                if obj.type != 'MESH':
                    continue
                check1.checked_count += 1
                deleted_verts_count = CheckUtils.get_count_doubles(obj)
                if deleted_verts_count > 0:
                    check1.add_error(f"{obj.name}: {deleted_verts_count} шт. дубликатов вершин")
        return checks

    @exception_handler
    def _check_texel_dencity(self):
        checks = []
        for fbx in self._lp_fbx_files:
            if "ground" not in fbx.name.lower():
                continue
            for obj in fbx.meshes:
                end_string = "_ground.001" if self.by_collections else "_ground"
                if not obj.name.lower().endswith(end_string):
                    continue
                check2 = Check("Проверка UV-развертки. Плотность пикселей", obj.name, True, "таблица 2, п. 6, п/п 1", "полигонов", ["2.6.1"])
                check2.checked_count = len(obj.data.polygons)
                checks.append(check2)

                check1 = Check("empty", "empty", True, "empty", "empty", [])
                check3 = check1

                bsdf = CheckUtils.get_bsdf(obj.active_material)
                if not bsdf:
                    continue
                resolution = bsdf.inputs[0].links[0].from_node.image.size[0]

                CheckUtils.check_texel(fbx, obj, check1, check2, check3, False, resolution)

        return checks

    @exception_handler
    def _check_fbx_objects(self):
        checks = []
        check2 = Check("Проверка файлов. Количество fbx", "", True, "таблица 2, п. 1, п/п 2", "", ["2.1.2"])
        checks.append(check2)
        check4 = Check("Проверка файлов. Благоустройство", "", True, "таблица 2, п. 1, п/п 4-5, п. 3, п/п 3", "", ["2.1.5"])
        checks.append(check4)
        check5 = Check("Проверка файлов. Благоустройство 2", "", True, "таблица 2, п. 1, п/п 4-5, п. 3, п/п 3", "", ["2.3.3"])
        checks.append(check5)

        ground_count = 0

        if len(self._lp_fbx_files) > 21:
            check2.add_error(f"Количество fbx-файлов превышает 21")

        for fbx in self._lp_fbx_files:
            check1 = Check("Проверка FBX. лишние обьекты", fbx.name, True, "таблица 2, п. 1, п/п 3, п. 3, п/п 5", "", ["2.1.3"])
            checks.append(check1)
            check6 = Check("Проверка FBX. иерархические связи", fbx.name, True, "таблица 2, п. 1, п/п 3, п. 3, п/п 5", "", ["2.3.5"])
            checks.append(check6)

            check3 = Check("Проверка FBX. Состав файла благоустройства", fbx.name, True, "таблица 2, п. 1, п/п 4", "", ["2.1.4"])
            checks.append(check3)

            if "ground" in fbx.name.lower():
                ground_count += 1
                required_meshes = ["Ground", "GroundEl", "Flora"]
                for obj in fbx.meshes:
                    obj_name = obj.name.lower()
                    if "ground" in obj_name and "groundel" not in obj_name and "glass" not in obj_name:
                        if ("Ground" in required_meshes): required_meshes.remove("Ground")
                    elif "groundel" in obj_name and "glass" not in obj_name:
                        if ("GroundEl" in required_meshes): required_meshes.remove("GroundEl")
                    elif "flora" in obj_name:
                        if ("Flora" in required_meshes): required_meshes.remove("Flora")
                for mesh in required_meshes:
                    check3.add_error(f"Неверный состав файла благоустройства. Отсутствует меш {mesh}")

            for obj in fbx.meshes:
                if obj.type != 'MESH':
                    check1.add_error(f"Лишний объект: {obj.name} ({obj.type})")
                if obj.parent != None:
                    check6.add_error(f"{obj.parent.name}: Объекты геометрии не должны иметь иерархических связей между собой")
            
            if fbx.objects_actions_count > 0:
                check1.add_error(f"Лишние анимации: {fbx.objects_actions_count} шт.")
            if fbx.objects_cameras_count > 0:
                check1.add_error(f"Лишние камеры: {fbx.objects_cameras_count} шт.")
            if fbx.objects_collections_count > 1:
                check1.add_error(f"Лишние коллекции: {fbx.objects_collections_count - 1} шт.")

        if ground_count == 0:
            check4.add_error("Файлы благоустройства - неотъемлемая часть АГР и являются обязательными к исполнению.")
        elif ground_count > 1:
            check5.add_error("Благоустройство, его элементы и элементы растительности должны быть сформированы в отдельный файл fbx")

        return checks

    @exception_handler
    def _check_materials(self):
        checks = []
        for fbx in self._lp_fbx_files:
            check0 = Check("Проверка материалов. Количество благо", fbx.name, True, "2.4.5, 2.4.6, 2.5.10", "", ["2.5.10"])
            checks.append(check0)
            check1 = Check("Проверка материалов. Количество материалов остекления", fbx.name, True, "2.4.5, 2.4.6, 2.5.10", "", ["2.4.6"])
            checks.append(check1)
            check3 = Check("Проверка текстур. Разрешение в наборе", fbx.name, True, "таблица 2, п. 5, п/п 2, 4", "", ["2.5.7"])
            checks.append(check3)
            check32 = Check("Проверка текстур. Разрешение элементов благоустройства", fbx.name, True, "таблица 2, п. 5, п/п 2, 4", "", ["2.5.11"])
            checks.append(check32)
            check4 = Check("Проверка текстур. Остекление", fbx.name, True, "таблица 2, п. 4, п/п 2", "", ["2.4.2"])
            checks.append(check4)
            check5 = Check("Проверка материалов. Количество", fbx.name, True, "", "", ["2.5.9"])
            checks.append(check5)
            check6 = Check("Проверка материалов. flora, обязательно diffuse", fbx.name, True, "", "", ["2.5.12"])
            checks.append(check6)

            for obj in fbx.meshes:
                obj_name = obj.name.lower()
                if obj.type != 'MESH':
                    continue
                uvmap_count = len(obj.data.uv_layers)
                mat_count = len(obj.data.materials)

                if "ground" in obj_name and "groundel" not in obj_name and "glass" not in obj_name:
                    if mat_count > 20:
                        check0.add_error(f"{obj.name}: количество материалов благоустройства больше 20")
                elif "glass" in obj_name:
                    if mat_count > 7:
                        check1.add_error(f"{obj.name}: количество материалов остекления больше 7")
                elif mat_count > 1:
                    check5.add_error(f"{obj.name}: количество материалов больше 1")

                textures = []
                for mat in obj.data.materials:
                    sizes = []
                    for node in mat.node_tree.nodes:
                        if node.bl_static_type == 'TEX_IMAGE':
                            # im_name = os.path.split(node.image.filepath)[1]
                            im_size = node.image.size[0]
                            sizes.append(im_size)
                            textures.append(im_size)
                    if any([sizes[i] != sizes[0] for i in range(len(sizes))]):
                        check3.add_error(f"{mat.name}: все текстуры в материале должны иметь одинаковый размер")
                    if "groundel" in obj_name and any([s > 512 for s in sizes]):
                        check32.add_error(f"{obj.name}: для элементов благоустройства разрешение текстур должно быть не более 512px")
                    if "glass" in obj_name and len(sizes) > 0:
                        check4.add_error(f"{obj.name}: полупрозрачные детали не должны включать в себя текстуры")
                    if "flora" in obj.name.lower():
                        bsdf = CheckUtils.get_bsdf(mat)
                        if not bsdf:
                            continue
                        metallic_input = bsdf.inputs[1]
                        if metallic_input.is_linked:
                            check6.add_error(f"Для Flora нельзя использовать карту metallic")
                        roughness_input = bsdf.inputs[2]
                        if roughness_input.is_linked:
                            check6.add_error(f"Для Flora нельзя использовать карту roughness")
                        
                        diffuse_input = bsdf.inputs[0]
                        if not diffuse_input.is_linked:
                            check6.add_error(f"{mat.name}: отсутствует карта диффузного цвета")
                            continue
                        from_node = diffuse_input.links[0].from_node
                        if from_node.bl_static_type == 'TEX_IMAGE' and from_node.image == None:
                            check6.add_error(f"{mat.name}: отсутствует карта диффузного цвета")

        return checks

    @exception_handler
    def _check_images(self):
        checks = []
        # if not self.by_collections:
        #     check1 = Check("Проверка fbx-файлов. Неиспользуемые текстуры (кол-во материалов = кол-во сетов)", "", True, "", "", ["2.4.5"])
        #     checks.append(check1)
        #     # check2 = Check("Проверка текстур. Альфа-канал", "", True, "", "")
        #     # checks.append(check2)

        #     images = list(bpy.data.images)
        #     for mat in bpy.data.materials:
        #         any_image_in_mat = 0
        #         for node in mat.node_tree.nodes:
        #             if node.bl_static_type == 'TEX_IMAGE':
        #                 any_image_in_mat += 1
        #                 if node.outputs[0].is_linked and node.image in images:
        #                     images.remove(node.image)
        #                 else:
        #                     im_name = os.path.split(node.image.filepath)[1]
        #                     check1.add_error(f"{im_name} ({node.image.name}): изображение не связано с параметрами материала {mat.name}")
        #         if any_image_in_mat == 0 and "glass" not in mat.name.lower():
        #             check1.add_error(f"{mat.name}: не найдено текстур в материале")
        #     for im in images:
        #         im_name = os.path.split(im.filepath)[1]
        #         check1.add_error(f"{im_name} ({im.name}): изображение не используется")

        return checks

class CheckUtils():
    @staticmethod
    @exception_handler
    def check_files(check_lp, root_path):
        all_checks = []
        for root, dirs, files in os.walk(root_path):
            check1 = Check("Проверка файлов. Формат", "", True, "таблица 2, п.1, п/п 2", "", ["2.1.2"])
            all_checks.append(check1)

            check2 = Check("Проверка файлов. Размер архивов", "", True, "таблица 2, п. 1, п/п 1", "", ["2.1.1"])
            all_checks.append(check2)

            check3 = Check("Проверка наименований. Недопустимые символы", "", True, "таблица 2, п. 10, п/п 1-2", "", ["2.10.1"])
            all_checks.append(check3)

            check4 = Check("Проверка наименований. Длина", "", True, "таблица 2, п. 10, п/п 1-2", "", ["2.10.2"])
            all_checks.append(check4)

            lp_dir = os.path.basename(root)[:4].isdigit()
            root_dir = root == root_path
            if lp_dir != check_lp:
                continue

            for file in files:
                if ".blend" in file:
                    continue
                if os_utils.CHECKLIST_DATA_FOLDER_NAME in root:
                    continue
                if root_dir and file.endswith(".zip"):
                    lp_file = file[:4].isdigit()
                    if lp_file != check_lp:
                        continue
                    check2.checked_count += 1
                    file_size = os.path.getsize(os.path.join(root, file))
                    max_size = 1024 * 1048576 if check_lp else 500 * 1048576
                    if file_size > max_size:
                        check2.add_error(f"{file} ({file_size / 1048576} Mb)")
                elif root_dir and not file.endswith(".zip"):
                    check1.add_error(file)
                
                formats = ["fbx", "FBX"] if lp_dir else ["fbx", "FBX", "geojson", "GEOJSON", "png", "PNG"]
                if not root_dir and file.split(".")[-1] not in formats:
                    check1.add_error(file)
                
                if re.search(r'[^a-zA-Z0-9_.]', file):
                    check3.add_error(f"Недопустимые символы: {file}")
                if len(file) > 254:
                    check4.add_error(f"Недопустимая длина имени файла: {file}")
            
            for check in all_checks:
                check.directory = os.path.basename(root)
                if check.directory == "":
                    check.directory = root
        return all_checks

    @staticmethod
    def create_udim_sets(root):
        udim_set = UdimSet()
        files = [f for f in os.listdir(root) if ".png" in f.lower()]
        if not files:
            return udim_set

        count = max([CheckUtils.udim_number(f) for f in files]) - 1000
        udim_set.sets_count = count
        udim_set.diffuse_set = [None for _ in range(count)]
        udim_set.erm_set = [None for _ in range(count)]
        udim_set.normal_set = [None for _ in range(count)]

        for file in files:
            ind = CheckUtils.udim_number(file) - 1000 - 1
            if "diffuse" in file.lower() or "basecolor" in file.lower().replace(" ", ""):
                # udim_set.diffuse_set.append(file)
                udim_set.diffuse_set[ind] = file
            elif "ERM" in file:
                udim_set.erm_set[ind] = file
            elif "normal" in file.lower():
                udim_set.normal_set[ind] = file

        for set in udim_set.collection:
            max_res = 0
            for file in set:
                if file == None:
                    continue
                num = CheckUtils.udim_number(file)
                res = CheckUtils.get_image_size(os.path.join(root, file))[0]
                if res > max_res:
                    max_res = res
            if max_res != 0:
                udim_set.resolutions_by_number[num] = max_res
        return udim_set

    @staticmethod
    def udim_number(name):
        num_str = name.split(".")[1]
        try:
            num = int(num_str)
        except:
            num = 0
        return num
        # return int(name[-8:-4])
    
    @staticmethod
    def get_image_size(fname):
        '''Determine the image type of fhandle and return its size.
        from draco'''
        with open(fname, 'rb') as fhandle:
            head = fhandle.read(24)
            if len(head) != 24:
                return
            if imghdr.what(fname) == 'png':
                check = struct.unpack('>i', head[4:8])[0]
                if check != 0x0d0a1a0a:
                    return
                width, height = struct.unpack('>ii', head[16:24])
            else:
                return
            return width, height

    @staticmethod
    def get_count_doubles(obj):
        # bpy.ops.object.mode_set(mode='OBJECT')
        obj.hide_set(False)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        # bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.faces.ensure_lookup_table()

        double_dist = 0.0015
        select = bmesh.ops.find_doubles(bm, verts=bm.verts, keep_verts=[], dist=double_dist)
        return len(select["targetmap"])

    @staticmethod
    def uv_to_udim_number(x, y):
        return 1000 + math.floor(y) * 10 + math.ceil(x)

    @staticmethod
    def check_mask_re(check, name, mask):
        name = CheckUtils.file_name_lower_extention(name)
        result = re.match(mask, name)
        if not result or result.group(0) != name:
            out_msk = mask.replace(r"\d{1,2}", "N").replace(r"\d", "N")
            check.add_error(f"-->{name}, должно быть \n           {out_msk}\n")
    
    @staticmethod
    def file_name_lower_extention(file_name):
        extention = file_name.split(".")[-1]
        name = ".".join(file_name.split(".")[:-1])
        extentions = ["png", "fbx", "geojson", "zip"]
        if extention.lower() in extentions:
            file_name_new = name + "." + extention.lower()
            return file_name_new
        else:
            return file_name

    @staticmethod
    def check_mesh_convex(obj):
        me = obj.data
        tolerance = max([obj.dimensions.x, obj.dimensions.y, obj.dimensions.z]) / 10
        # if len(me.vertices) - len(me.edges) + len(me.polygons) != 2:
            # logger.add("Неверная топология")
            # return False
        for poly in me.polygons:
            verts = []
            for i in poly.loop_indices:
                v_ind = me.loops[i].vertex_index
                verts.append(me.vertices[v_ind])
            t1 = verts[0].co
            t2 = verts[1].co
            t3 = verts[2].co

            a = t1.y*(t2.z - t3.z) + t2.y*(t3.z - t1.z) + t3.y*(t1.z - t2.z)
            b = t1.z*(t2.x - t3.x) + t2.z*(t3.x - t1.x) + t3.z*(t1.x - t2.x)
            c = t1.x*(t2.y - t3.y) + t2.x*(t3.y - t1.y) + t3.x*(t1.y - t2.y)
            d =-( t1.x * (t2.y * t3.z - t3.y * t2.z) + t2.x * (t3.y * t1.z - t1.y * t3.z) + t3.x * (t1.y * t2.z - t2.y * t1.z))
            
            prev = 0
            for vert in me.vertices:
                if vert in verts:
                    continue
                v = vert.co
                value = v.x * a + v.y * b + v.z * c + d
                dist_coef = math.sqrt(a*a + b*b + c*c)
                if dist_coef == 0:
                    continue
                dist = value / dist_coef

                if dist < tolerance and dist > -tolerance:
                    continue
                
                if prev == 0:
                    prev = value
                if value * prev < -0.001:
                    return False
            
        return True

    @staticmethod
    def check_fbx_meshes_transforms(fbx, check, ignore_location=False):
        errors = []
        for obj in fbx.meshes:
            if "spot" in obj.name.lower() or "omni" in obj.name.lower():
                continue
            check.checked_count += 1
            vector_one = mathutils.Vector((1.0, 1.0, 1.0))
            if not ignore_location and obj.location.length_squared > 0.0001:
                errors.append(["Location", obj.name[:3], obj.name, f"{round(obj.location.x, 3)}, {round(obj.location.y, 3)}, {round(obj.location.z, 3)}"])
            rotation_vector = mathutils.Vector((obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z))
            if rotation_vector.length_squared > 0.001:
                errors.append(["Rotation", obj.name[:3], obj.name, f"{round(math.degrees(rotation_vector.x), 3)}, {round(math.degrees(rotation_vector.y), 3)}, {round(math.degrees(rotation_vector.z), 3)}"])
            if abs(obj.scale.length_squared - vector_one.length_squared) > 0.001:
                errors.append(["Scale", obj.name[:3], obj.name, f"{round(obj.scale.x, 3)}, {round(obj.scale.y, 3)}, {round(obj.scale.z, 3)}"])
    
        errors = sorted(errors, key=lambda i: i[1])

        for key, group_items in groupby(errors, lambda i: i[1]):
            if "UCX" in key:
                group_items_list = list(group_items)
                check.add_error(f"{group_items_list[0][2]}, {group_items_list[0][0]}={group_items_list[0][3]}")
                check.add_error(f"...")
                check.add_error(f"{group_items_list[-1][2]}, {group_items_list[-1][0]}={group_items_list[-1][3]}")
            else:
                for item in group_items:
                    check.add_error(f"{item[2]}, {item[0]}={item[3]}")

    @staticmethod
    def get_bsdf(mat):
        bsdf = None
        for node in mat.node_tree.nodes:
            if node.bl_idname == 'ShaderNodeBsdfPrincipled':
                bsdf = node
                break
        return bsdf

    @staticmethod
    def check_polycount(fbx, check1, check2, max_polycount, hp_check_ucx=None, hp_check_ucx2=None):
        polycount = 0
        ucx_polycount = 0
        nontriscount = 0

        # errors = []
        nontris_by_obj = dict()
        for obj in fbx.meshes:
            if obj.type != 'MESH':
                continue
            mesh = obj.data
            for poly in mesh.polygons:
                if "UCX" in obj.name:
                    ucx_polycount += 1
                else:
                    polycount += 1
                if len(poly.vertices) > 3:
                    if obj.name not in nontris_by_obj.keys():
                        nontris_by_obj[obj.name] = 1
                    else:
                        nontris_by_obj[obj.name] += 1
                    nontriscount += 1
        
        check1.checked_count = polycount + ucx_polycount
        check2.checked_count = polycount + ucx_polycount

        if polycount > max_polycount:
            check1.add_error(f"{fbx.name}: {polycount} полигонов, должно быть не более {max_polycount}")
        
        if hp_check_ucx:
            if polycount < 50000:
                if ucx_polycount > 15000:
                    hp_check_ucx2.add_error(f"{fbx.name}: {polycount} полигонов коллизий (максимальное кол-во полигонов - {15000})")
            else:
                if ucx_polycount > polycount * 0.05:
                    hp_check_ucx.add_error(f"{fbx.name}: {polycount} полигонов коллизий (максимальное кол-во полигонов - {round(polycount * 0.05)})")

        if nontriscount > 0:
            for key in nontris_by_obj:
                check2.add_error(f"{key}: не треугольных полигонов={nontris_by_obj[key]}")

    @staticmethod
    def check_texel(fbx, obj, check1, check2, check3, highpoly=True, resolution_lowpoly=0):
        if highpoly:
            if all([v == 256 for v in fbx.udim_set.resolutions_by_number.values()]):
                return
            calculated_obj_td_area, td_errors_less, td_errors_greater, udim_errors, not_uvmap_errors, udim_used_errors = CheckUtils._calculate_td(obj, fbx.udim_set.resolutions_by_number, True)
        else:
            calculated_obj_td_area, td_errors_less, td_errors_greater, udim_errors, not_uvmap_errors, udim_used_errors = CheckUtils._calculate_td(obj, {1001:resolution_lowpoly}, False)

        if calculated_obj_td_area:
            # average_td = sum(calculated_obj_td_area)/len(calculated_obj_td_area)
            # td_min = min(calculated_obj_td_area)
            # td_max = max(calculated_obj_td_area)
            # check2.directory += f" (Средняя плотность пикселей={round(average_td, 2)}, минимальная={round(td_min, 2)}, максимальная={round(td_max, 2)})"
            # check2.directory += f" (без учета опущенных вниз полигонов по периметру благоустройства)"
            pass
        else:
            check2.add_error(f"Не удалось вычислить texel dencity")

        if td_errors_less:
            for key in td_errors_less:
                if highpoly:
                    check2.add_error(f"UDIM {key}: полигоны < 512 px/m - {len(td_errors_less[key][1])} шт., Средняя плотность - {round(sum(td_errors_less[key][1])/len(td_errors_less[key][1]), 2)} px/m, Суммарная площадь - {round(sum(td_errors_less[key][2]), 2)} м2 (Разрешение текстуры - {td_errors_less[key][0]})")
                else:
                    check2.add_error(f"{obj.name}: полигоны < 10 px/m - {len(td_errors_less[key][1])} шт., Средняя плотность - {round(sum(td_errors_less[key][1])/len(td_errors_less[key][1]), 2)} px/m, Суммарная площадь - {round(sum(td_errors_less[key][2]), 2)} м2 (Разрешение текстуры - {td_errors_less[key][0]})")
        if td_errors_greater:
            for key in td_errors_greater:
                if highpoly:
                    check2.add_error(f"UDIM {key}: полигоны > 1706 px/m - {len(td_errors_greater[key][1])} шт., Средняя плотность - {round(sum(td_errors_greater[key][1])/len(td_errors_greater[key][1]), 2)} px/m, Суммарная площадь - {round(sum(td_errors_greater[key][2]), 2)} м2 (Разрешение текстуры - {td_errors_greater[key][0]})")
                else:
                    check2.add_error(f"{obj.name}: полигоны > 40 px/m - {len(td_errors_greater[key][1])} шт., Средняя плотность - {round(sum(td_errors_greater[key][1])/len(td_errors_greater[key][1]), 2)} px/m, Суммарная площадь - {round(sum(td_errors_greater[key][2]), 2)} м2 (Разрешение текстуры - {td_errors_greater[key][0]})")
        if udim_errors:
            check1.add_error(f"Полигоны выходящие за границы UDIM: {len(udim_errors)} шт. ")
            check1.add_error("Ориентировочные координаты в UV пространстве:")
            uv_min = min(udim_errors)
            uv_max = max(udim_errors)
            check1.add_error(f"    Минимальная точка по x uv=({round(uv_min[0], 2)}, {round(uv_min[1], 2)}), Максимальная точка по x uv=({round(uv_max[0], 2)}, {round(uv_max[1], 2)})")
        if udim_used_errors:
            # Неиспользуемая текстура, UDIM 
            nums = ", ".join(udim_used_errors)
            check3.add_error(f"Неиспользуемые текстуры. Номера UDIM - {nums}")

    @staticmethod
    def _calculate_td(obj, udim_resolutions, highpoly):
        # udim_resolutions = {1001: 4096, 1002: 256, 1003: 2048}
        out_udim_errors = []
        td_errors_less = dict()
        td_errors_greater = dict()
        not_uvmap_errors = []
        calculated_obj_td_list = []

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True, properties=False)
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.faces.ensure_lookup_table()

        face_count = len(obj.data.polygons)
        udims_used = set()

        vector_up = mathutils.Vector((0, 0, 1.0))

        for x in range(0, face_count):
            if not highpoly and round(math.degrees(obj.data.polygons[x].normal.angle(vector_up))) == 90:
                continue
            area = 0
            loops = []
            try:
                for loop in bm.faces[x].loops:
                    loops.append(loop[bm.loops.layers.uv.active].uv)
            except:
                not_uvmap_errors.append(f"cant find BMLayerItem in bm.loops.layers.uv.active={bm.loops.layers.uv.active}, obj={obj.name}")
                continue
            loops_count = len(loops)
            a = loops_count - 1

            if highpoly:
                udim_nums = [CheckUtils.uv_to_udim_number(loops[i].x, loops[i].y) for i in range(loops_count)]
                [udims_used.add(num) for num in udim_nums]
                # check if all points fall into one tile and tile exist in udims
                if not all(num == udim_nums[0] for num in udim_nums) or udim_nums[0] not in udim_resolutions.keys():
                    [out_udim_errors.append((loops[i].x, loops[i].y)) for i in range(loops_count)]
                    continue
                udim_num = udim_nums[0]
            else:
                udim_num = 1001

            largest_side = udim_resolutions[udim_num]
            if largest_side == None:
                continue
            if largest_side <= 256:
                continue
            
            for b in range(0, loops_count):
                area += (loops[a].x + loops[b].x) * (loops[a].y - loops[b].y)
                a = b
            
            area = abs(0.5 * area)
            gm_area = obj.data.polygons[x].area

            if gm_area > 0 and area > 0:
                aspect_ratio = 1
                texel_density = ((largest_side / math.sqrt(aspect_ratio)) * math.sqrt(area))/(math.sqrt(gm_area)*100) / bpy.context.scene.unit_settings.scale_length
            else:
                texel_density = 0.0001

            texel_density = texel_density * 100

            if highpoly:
                texel_min, texel_max = 512, 1706
            else:
                texel_min, texel_max = 10, 40
            if texel_density < texel_min:
                if udim_num not in td_errors_less.keys():
                    td_errors_less[udim_num] = [largest_side, [], []]
                td_errors_less[udim_num][1].append(round(texel_density, 2))
                td_errors_less[udim_num][2].append(round(gm_area, 2))
                # td_errors.append(f"texel density error {texel_density} px/m, udim:{udim_num}, tex_size={largest_side}px, sqrt_area={math.sqrt(gm_area)}m")
            elif texel_density > texel_max:
                if udim_num not in td_errors_greater.keys():
                    td_errors_greater[udim_num] = [largest_side, [], []]
                td_errors_greater[udim_num][1].append(round(texel_density, 2))
                td_errors_greater[udim_num][2].append(round(gm_area, 2))
                # td_errors.append(f"texel density error {texel_density} px/m, udim:{udim_num}, tex_size={largest_side}px, sqrt_area={math.sqrt(gm_area)}m")

            # td_area_list = texel_density
            calculated_obj_td_list.append(texel_density)

        udim_used_errors = []
        for key in udim_resolutions.keys():
            if key not in udims_used:
                udim_used_errors.append(f"{key}")

        bpy.ops.object.mode_set(mode='OBJECT')

        return calculated_obj_td_list, td_errors_less, td_errors_greater, out_udim_errors, not_uvmap_errors, udim_used_errors

    @staticmethod
    def lp_get_suffix(mesh):
        if "flora" in mesh.name.lower():
            return r"_Flora"
        elif "groundel" in mesh.name.lower() and "glass" in mesh.name.lower():
            return r"_GroundElGlass"
        elif "groundel" in mesh.name.lower():
            return r"_GroundEl"
        elif "groundglass" in mesh.name.lower():
            return r"_GroundGlass"
        elif "ground" in mesh.name.lower():
            return r"_Ground"
        elif "glass" in mesh.name.lower():
            return r"_\d\d\d_MainGlass"
        else:
            return r"_\d\d\d_Main"

    @staticmethod
    def create_bvh_tree_from_object(obj):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world)
        bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm)
        bm.free()
        return bvh

    @staticmethod
    def check_bvh_intersection(obj_1, obj_2):
        bvh1 = CheckUtils.create_bvh_tree_from_object(obj_1)
        bvh2 = CheckUtils.create_bvh_tree_from_object(obj_2)
        return bvh1.overlap(bvh2)

    @staticmethod
    def _is_polygon_flipped(points):
        area = 0.0
        for i in range(len(points)):
            uv1 = points[i]
            uv2 = points[(i + 1) % len(points)]
            a = uv1.x * uv2.y - uv1.y * uv2.x
            area = area + a
        if area < 0:
            # clock-wise
            return True
        return False

    @staticmethod
    def get_flipped_count(faces, uv_layer):
        flipped_uvs_count = 0
        for f in faces:
            polygon = [l[uv_layer].uv.copy() for l in f.loops]
            if CheckUtils._is_polygon_flipped(polygon):
                flipped_uvs_count += 1
        return flipped_uvs_count

    @staticmethod
    def image_has_alpha(bl_img):
        b = 32 if bl_img.is_float else 8
        return (
            bl_img.depth == 2*b or   # Grayscale+Alpha
            bl_img.depth == 4*b      # RGB+Alpha
        )

    @staticmethod
    def is_one_color_image(bl_img):
        def rnd(v):
            return round(v, 3)
        pixels = bl_img.pixels[:]
        prev_px = [rnd(pixels[0]), rnd(pixels[1]), rnd(pixels[2]), rnd(pixels[3])]
        cur_px = [rnd(pixels[4]), 0, 0, 0]
        for i, p in enumerate(pixels):
            if i < 5:
                continue
            cur_px[i % 4] = rnd(p)
            if i % 4 == 0:
                if prev_px != cur_px:
                    return False
                    break
                prev_px = cur_px
        return True

    @staticmethod
    def arrange_nodes(node_tree, principled_node):
        def get_linked_nodes(node):
            nonlocal all_nodes
            from_nodes = []
            for i, inp in enumerate(node.inputs):
                for k, link in enumerate(inp.links):
                    if link.from_node not in from_nodes and link.from_node not in all_nodes:
                        from_nodes.append(link.from_node)
                        all_nodes.append(link.from_node)
            return from_nodes
        
        base_spacing = 350
        vertical_spacing = 300
        
        bsdf_loc = principled_node.location
        all_nodes = []
        from_nodes = get_linked_nodes(principled_node)
        u = 0
        for node in from_nodes:
            node.location = (bsdf_loc[0] - base_spacing, bsdf_loc[1] - vertical_spacing * (u - 1))
            u += 1
            u2 = 0
            for n2 in get_linked_nodes(node):
                n2.location = (node.location[0] - base_spacing, node.location[1] - vertical_spacing * (u2))
                u2 += 1
                u3 = 0
                for n3 in get_linked_nodes(n2):
                    n3.location = (n2.location[0] - base_spacing, n2.location[1] - vertical_spacing * (u3))
                    u3 += 1
                    u4 = 0
                    for n4 in get_linked_nodes(n3):
                        n4.location = (n3.location[0] - base_spacing, n3.location[1] - vertical_spacing * (u4))
                        u4 += 1

    @staticmethod
    def check_color_attributes(fbx_files):
        checks = []
        for fbx in fbx_files:
            check = Check("Проверка FBX. Color attributes", fbx.name, True, "", "", ["4.1.1"])
            checks.append(check)
            ucx_errors = []
            for obj in fbx.meshes:
                if obj.type != 'MESH':
                    continue
                if len(obj.data.color_attributes) > 0:
                    if "ucx" in obj.name.lower():
                        if len(ucx_errors) < 5:
                            ucx_errors.append(f"{obj.name}")
                    else:
                        check.add_error(f"{obj.name}")
            for er in ucx_errors:
                check.add_error(er)
            if len(ucx_errors) == 5:
                check.add_error("и т. д.")
        return checks

class Check():
    def __init__(self, name, directory, verified, paragraph, units_text, paragraph_ids):
        self.name = name
        self.directory = directory
        self.verified = verified
        self.paragraph = paragraph
        self.units_text = units_text
        self.paragraph_ids = paragraph_ids

        self.comment = ""
        self.error_list = []
        self.checked_count = 0
    
    def add_error(self, err):
        self.verified = False
        self.error_list.append(err)

class UdimSet():
    def __init__(self):
        self.diffuse_set = []
        self.erm_set = []
        self.normal_set = []
        self.resolutions_by_number = dict()
        self.sets_count = 0
    
    @property
    def collection(self):
        result = []
        for i in range(len(self.diffuse_set)):
            result.append((self.diffuse_set[i], self.erm_set[i], self.normal_set[i]))
        return result

class ModelPreparer():
    def __init__(self):
        self.hp_fbx_files = []
        self.lp_fbx_files = []
        self.oks_count = 0
        self.prepare_checks = []
        self.root_path = ""
        self.by_collections = False
    
    def check_if_has_lp_hp(self):
        has_lp = False
        has_hp = False
        if self.by_collections:
            for col in bpy.data.collections:
                if col.name[:4].isdigit():
                    has_lp = True
                if col.name.startswith("SM_"):
                    has_hp = True
                if has_lp and has_hp:
                    return has_lp, has_hp
        else:
            for root, dirs, files in os.walk(self.root_path):
                for file in files:
                    if file[:4].isdigit():
                        has_lp = True
                    if file.startswith("SM_"):
                        has_hp = True
                    if has_lp and has_hp:
                        return has_lp, has_hp
        return has_lp, has_hp

    @exception_handler
    def unzip(self):
        # items = [f for f in os.listdir(bpy.path.abspath("//")) if os.path.isfile(os.path.join(root, f))]
        if not self.by_collections:
            root = self.root_path
            items = [f for f in os.listdir(root)]
            for item in items:
                # if item[:4].isdigit(): # low poly not extract
                #     continue
                if item.endswith(".zip"):
                    if "Ground" not in item and not item[:4].isdigit():
                        self.oks_count += 1
                    if item[:-4] not in items:
                        logger.add(f"Извлечение архива {item}")
                        with zipfile.ZipFile(os.path.join(root, item), 'r') as zip_ref:
                            zip_ref.extractall(os.path.join(root, item[:-4]).rstrip())

    @exception_handler
    def import_lowpoly_models(self, firstImport=True):
        if self.by_collections:
            for collection in bpy.data.collections:
                if collection.name[:4].isdigit():
                    image_path = ""
                    zip_name = "unknown"
                    for root, dirs, files in os.walk(self.root_path):
                        if root == collection.name.replace(".fbx", ""):
                            image_path = root
                            zip_name = os.path.basename(root) + ".zip"

                    fbx = FbxFile(collection.name, image_path)
                    fbx.meshes = collection.all_objects
                    fbx.zip_name = zip_name
                    self.lp_fbx_files.append(fbx)
        else:
            if firstImport:
                self._clear_blender_file()
            for root, dirs, files in os.walk(self.root_path):
                for file in files:
                    if file[:4].isdigit() and file.lower().endswith(".fbx"): # low poly
                        if firstImport:
                            temp_objects = bpy.data.objects[:]
                            actions_count = len(bpy.data.actions)
                            cameras_count = len(bpy.data.cameras)
                            collections_count = len(bpy.data.collections)
                        # else:
                        collection = bpy.data.collections.new(file)
                        bpy.context.scene.collection.children.link(collection)
                        bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[-1]
                        bpy.ops.import_scene.fbx(filepath = os.path.join(root, file))
                        if firstImport:
                            fbx = FbxFile(file, root)
                            fbx.meshes = set(bpy.data.objects) - set(temp_objects)
                            fbx.objects_actions_count = len(bpy.data.actions) - actions_count
                            fbx.objects_cameras_count = len(bpy.data.cameras) - cameras_count
                            fbx.objects_collections_count = len(bpy.data.collections) - collections_count
                            fbx.zip_name = os.path.basename(root) + ".zip"
                            self.lp_fbx_files.append(fbx)
                            mat_names_to_remove = set()
                            for obj in fbx.meshes:
                                for i, mat in enumerate(obj.data.materials):
                                    if mat.name.lower().startswith("m_glass") and mat.name.endswith(".001") and mat.name.replace(".001", "") in bpy.data.materials:
                                        mat_names_to_remove.add(mat.name)
                                        obj.data.materials[i] = bpy.data.materials[mat.name.replace(".001", "")]
                            for mat_name in mat_names_to_remove:
                                bpy.data.materials.remove(bpy.data.materials[mat_name])
        [logger.add("imported lowpoly: " + fbx.file_name) for fbx in self.lp_fbx_files]

    @exception_handler
    def import_highpoly_models(self, clear=True):
        if self.by_collections:
            for collection in bpy.data.collections:
                if collection.name.startswith("SM_"):
                    image_path = ""
                    json_name = ""
                    zip_name = ""
                    for root, dirs, files in os.walk(self.root_path):
                        col_name = collection.name.replace(".fbx", "")
                        # logger.add(f"root compare {col_name}   {root}")
                        if root.endswith(collection.name.replace(".fbx", "").replace("_Light", "")):
                            image_path = root
                            for file in files:
                                if file.endswith(".geojson"):
                                    json_name = file
                            zip_name = os.path.basename(root) + ".zip"

                    fbx = FbxFile(collection.name, image_path)
                    fbx.meshes = collection.all_objects
                    # fbx.zip_name = collection.name.replace(".fbx", "").replace("_Light", "") + ".zip"
                    fbx.zip_name = zip_name
                    # fbx.json_name = collection.name.replace(".fbx", "").replace("_Light", "") + ".geojson"
                    fbx.json_name = json_name
                    fbx.json_data = ModelPreparer._get_json_data(os.path.join(image_path, fbx.json_name))
                    self.hp_fbx_files.append(fbx)
                    # logger.add(f"updated highpoly images and json: {image_path} {zip_name} {fbx.file_name} {json_name}")
        else:
            if clear:
                self._clear_blender_file()
            root_fbx_geojson = dict()
            for root, dirs, files in os.walk(self.root_path):
                root_fbx_geojson[root] = [[], None]
                json_count = 0
                for file in files:
                    if file[:4].isdigit(): # low poly
                        continue
                    if file.lower().endswith(".fbx"):
                        temp_objects = bpy.data.objects[:]
                        actions_count = len(bpy.data.actions)
                        cameras_count = len(bpy.data.cameras)
                        collections_count = len(bpy.data.collections)
                        collection = bpy.data.collections.new(file)
                        bpy.context.scene.collection.children.link(collection)
                        bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[-1]
                        bpy.ops.import_scene.fbx(filepath = os.path.join(root, file))
                        fbx = FbxFile(file, root)

                        fbx.meshes = list(set(bpy.data.objects) - set(temp_objects))
                        fbx.objects_actions_count = len(bpy.data.actions) - actions_count
                        fbx.objects_cameras_count = len(bpy.data.cameras) - cameras_count
                        fbx.objects_collections_count = len(bpy.data.collections) - collections_count

                        fbx.zip_name = os.path.basename(root) + ".zip"
                        self.hp_fbx_files.append(fbx)
                        root_fbx_geojson[root][0].append(fbx)
                    elif file.endswith(".geojson"):
                        json_count += 1
                        root_fbx_geojson[root][1] = file
                # check1 = Check("Проверка файлов. Наличие geojson.", root, True, "таблица 2, п. 1, п/п 2", "", ["2.1.2"])
                # self.prepare_checks.append(check1)
                # if json_count > 1:
                    # check1.add_error("Более одного geojson файла")
        
            [logger.add("imported highpoly: " + fbx.file_name) for fbx in self.hp_fbx_files]

            for key in root_fbx_geojson:
                # check2 = Check("Проверка файлов. Наличие geojson.", key, True, "таблица 2, п. 1, п/п 2", "", ["2.1.2"])
                # self.prepare_checks.append(check2)

                fbx_json = root_fbx_geojson[key]
                if len(fbx_json[0]) == 0:
                    continue
                if fbx_json[1] != None:
                    for fbx in fbx_json[0]:
                        fbx.json_data = ModelPreparer._get_json_data(os.path.join(key, fbx_json[1]))
                        fbx.json_name = fbx_json[1]
                else:
                    # check2.add_error("Файл geojson не обнаружен")
                    pass

    @exception_handler
    def fix_coordinates(self):
        buildingsCoordinates = []
        groundCoord = [0, 0]

        for fbx in self.hp_fbx_files:
            jsonData = fbx.json_data
            if not jsonData:
                logger.add(F"Не удалось получить данные из geojson файла {fbx.file_name}")
                continue
            coordZ_string = jsonData["features"][0]["properties"]['h_relief']
            coordZ = float(coordZ_string.replace(",", "."))
            coordString = jsonData["features"][0]["geometry"]["coordinates"]
            coord = [float(coordString[0]), float(coordString[1]), coordZ]
            if "Ground" in fbx.name:
                groundCoord = coord
            else:
                buildingsCoordinates.append([fbx, coord])
        
        for fbx in self.hp_fbx_files:
            for obj in fbx.meshes:
                if "UCX" in obj.name:
                    obj.hide_set(True)

        # relative coorfinates
        # if groundCoord[0] != 0:
        #     for bCoord in buildingsCoordinates:
        #         logger.add(f"Корректировка координат для {bCoord[0].file_name}")
        #         for obj in bCoord[0].meshes:
        #             if obj.type == 'MESH' or obj.type == 'EMPTY':
        #                 obj.location.x += bCoord[1][0] - groundCoord[0]
        #                 obj.location.y += bCoord[1][1] - groundCoord[1]

        # absolute coordinates
        for fbx in self.hp_fbx_files:
            if "Ground" in fbx.name and groundCoord[0] != 0:
                logger.add(f"Корректировка координат для {fbx.name}")
                for obj in fbx.meshes:
                    if obj.type == 'MESH' or obj.type == 'EMPTY':
                        obj.location.x = groundCoord[0]
                        obj.location.y = groundCoord[1]
                        obj.location.z = groundCoord[2]
        for bCoord in buildingsCoordinates:
            logger.add(f"Корректировка координат для {bCoord[0].file_name}")
            for obj in bCoord[0].meshes:
                if obj.type == 'MESH' or obj.type == 'EMPTY':
                    obj.location.x = bCoord[1][0]
                    obj.location.y = bCoord[1][1]
                    obj.location.z = bCoord[1][2]

    @exception_handler
    def material_textures_set(self):
        for fbx in self.hp_fbx_files:
            for obj in fbx.meshes:
                if not fbx.json_data:
                    continue
                if "glass" in obj.name.lower():
                    # check1 = Check("Проверка geojson. Параметры остекления", obj.name, True, "", "", ["2.2.1"])
                    # self.prepare_checks.append(check1)
                    logger.add(f"Назначение материалов для {obj.name}")
                    try:
                        json_glasses = fbx.json_data["features"][0]["Glasses"][0]
                        for mat in obj.data.materials:
                            bsdf = CheckUtils.get_bsdf(mat)
                            if not bsdf:
                                continue
                            if mat.name in json_glasses.keys():
                                json_glass = json_glasses[mat.name]
                                
                                color_dict = json_glass["color_RGB"]
                                red = float(color_dict['Red'].replace(',', '.'))
                                green = float(color_dict['Green'].replace(',', '.'))
                                blue = float(color_dict['Blue'].replace(',', '.'))
                                bsdf.inputs[0].default_value = [red / 255, green / 255, blue / 255, 1.0]
                                bsdf.inputs[1].default_value = float(json_glass['metallicity'].replace(',', '.'))
                                bsdf.inputs[2].default_value = float(json_glass['roughness'].replace(',', '.'))
                                bsdf.inputs[3].default_value = float(json_glass['refraction'].replace(',', '.'))
                                bsdf.inputs[4].default_value = float(json_glass['transparency'].replace(',', '.'))
                            else:
                                # check1.add_error(f"В файле geojson не найдено описание материала {mat.name}")
                                logger.add(f"В файле geojson не найдено описание материала {mat.name}")
                                bsdf.inputs[0].default_value = [1.0, 1.0, 1.0, 1.0]
                                bsdf.inputs[1].default_value = 0.6
                                bsdf.inputs[2].default_value = 0
                                # bsdf.inputs[3].default_value = float(json_glass['refraction'].replace(',', '.'))
                                bsdf.inputs[4].default_value = 0.4
                                pass
                    except Exception as e:
                        logger.add(f"Не удалось наначить параметры материала остекления ({e})")
                        # check1.add_error(f"Не удалось наначить параметры материала остекления ({e})")

            obj = fbx.main_mesh
            if not obj or not fbx.udim_set.collection or not all(fbx.udim_set.collection[0]):
                continue

            logger.add(f"Назначение материалов для {obj.name}")

            diffusePath = os.path.join(fbx.root, fbx.udim_set.collection[0][0])
            ermPath = os.path.join(fbx.root, fbx.udim_set.collection[0][1])
            normalPath = os.path.join(fbx.root, fbx.udim_set.collection[0][2])
            
            diffuse = bpy.data.images.load(diffusePath, check_existing=True)
            erm = bpy.data.images.load(ermPath, check_existing=True)
            normal = bpy.data.images.load(normalPath, check_existing=True)
            normal.colorspace_settings.name = "Non-Color"
            erm.colorspace_settings.name = "Non-Color"
            
            diffuse.source = "TILED"
            erm.source = "TILED"
            normal.source = "TILED"
            
            mat = obj.active_material
            if not mat:
                logger.add(f"Не удалось назначить материалы для {obj.name}")
                continue
            self._clear_nodes(mat)
            
            principled_BSDF = CheckUtils.get_bsdf(mat)
            if not principled_BSDF:
                continue
            
            diffuse_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
            diffuse_node.image = diffuse
            mat.node_tree.links.new(diffuse_node.outputs[0], principled_BSDF.inputs[0])
            mat.node_tree.links.new(diffuse_node.outputs[0], principled_BSDF.inputs[26])
            mat.node_tree.links.new(diffuse_node.outputs[1], principled_BSDF.inputs[4])
            
            erm_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
            erm_node.image = erm
            
            sep_node = mat.node_tree.nodes.new('ShaderNodeSeparateColor')
            mat.node_tree.links.new(erm_node.outputs[0], sep_node.inputs[0])
            mat.node_tree.links.new(sep_node.outputs[0], principled_BSDF.inputs[27])
            mat.node_tree.links.new(sep_node.outputs[1], principled_BSDF.inputs[2])
            mat.node_tree.links.new(sep_node.outputs[2], principled_BSDF.inputs[1])
            
            normal_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
            normal_node.image = normal
            sep_node2 = mat.node_tree.nodes.new('ShaderNodeSeparateColor')
            mat.node_tree.links.new(normal_node.outputs[0], sep_node2.inputs[0])

            math_node = mat.node_tree.nodes.new('ShaderNodeMath')
            math_node.operation = 'SUBTRACT'
            math_node.inputs[0].default_value = 1
            mat.node_tree.links.new(sep_node2.outputs[1], math_node.inputs[1])

            combine_node = mat.node_tree.nodes.new('ShaderNodeCombineColor')
            mat.node_tree.links.new(sep_node2.outputs[0], combine_node.inputs[0])
            mat.node_tree.links.new(math_node.outputs[0], combine_node.inputs[1])
            mat.node_tree.links.new(sep_node2.outputs[2], combine_node.inputs[2])

            normal_map_node = mat.node_tree.nodes.new('ShaderNodeNormalMap')
            
            mat.node_tree.links.new(combine_node.outputs[0], normal_map_node.inputs[1])
            mat.node_tree.links.new(normal_map_node.outputs[0], principled_BSDF.inputs[5])

            CheckUtils.arrange_nodes(mat.node_tree, principled_BSDF)

    def _clear_blender_file(self):
        for img in reversed(bpy.data.images):
            bpy.data.images.remove(img)
        for obj in reversed(bpy.data.objects):
            bpy.data.objects.remove(obj)
        for mesh in reversed(bpy.data.meshes):
            bpy.data.meshes.remove(mesh)
        for material in reversed(bpy.data.materials):
            bpy.data.materials.remove(material)
        for col in reversed(bpy.data.collections):
            bpy.data.collections.remove(col)

    def _clear_nodes(self, mat):
        for node in mat.node_tree.nodes:
            if node.bl_idname == 'ShaderNodeBsdfPrincipled' or 'ShaderNodeOutputMaterial':
                continue
            # if node.name == "Principled BSDF" or node.name == "Material Output":
            #     continue
            mat.node_tree.nodes.remove(node)

    @staticmethod
    def _get_json_data(path_string):
        # path_string = bpy.path.abspath("//" + name + "\\" + name + ".geojson")
        try:
            with open(path_string, encoding='utf-8-sig') as f:
                return json.load(f)
        except:
            return None
    
    def clear_highpoly_before_check_by_collections(self):
        for fbx in self.hp_fbx_files:
            for obj in fbx.meshes:
                if obj.type == 'MESH':
                    for mat in obj.data.materials:
                        self._clear_nodes(mat)
                # obj.hide_set(False)
                # obj.location.x = 0
                # obj.location.y = 0
                # obj.location.z = 0
    
    def clear_images(self):
        for img in reversed(bpy.data.images):
            if ".1001" in img.name:
                logger.add(f"image romove {img.name}")
                bpy.data.images.remove(img)

class FbxFile():
    def __init__(self, name, root):
        self.file_name = name
        self.root = root
        self.meshes = []
        # self.main_mesh
        self.udim_set = None
        self.json_data = None
        self.json_name = ""
        self.zip_name = ""

        self.objects_actions_count = 0
        self.objects_cameras_count = 0
        self.objects_collections_count = 0
        self.objects_materials = []
        self.objects_images = []

    def create_udim_set(self):
        self.udim_set = CheckUtils.create_udim_sets(self.root)
    
    @property
    def name(self):
        return self.file_name[:-4]
    
    @property
    def main_mesh(self):
        if self.file_name[:4].isdigit():
            return None
        for mesh in self.meshes:
            mesh_name = mesh.name.lower()
            if mesh.type != 'MESH' or "ucx" in mesh_name or "light" in mesh_name or "glass" in mesh_name:
                continue
            
            if "main" in mesh_name:
                return mesh
            if "ground" in mesh_name:
                return mesh
        return None

class ProjectData():
    def __init__(self):
        self.address = ""
        self.json_address = ""
        self.json_project_name = ""

def clear_blender_file():
    preparer = ModelPreparer()
    preparer._clear_blender_file()

def import_models():
    global start_time
    start_time = time.time()

    root_path = os_utils._get_project_path()
    if not root_path:
        return
    preparer = ModelPreparer()
    preparer.root_path = root_path
    preparer.by_collections = False

    has_lp, has_hp = preparer.check_if_has_lp_hp()
    preparer.unzip()

    # preparer.clear_images()
    
    if has_hp:
        preparer.import_highpoly_models(clear=False)
        for fbx in preparer.hp_fbx_files:
            obj = fbx.main_mesh
            if not obj:
                continue
            fbx.create_udim_set()
        preparer.fix_coordinates()
        preparer.material_textures_set()
    else:
        # preparer._clear_blender_file()
        pass

    if has_lp:
        preparer.import_lowpoly_models(firstImport=False)

def run(bl_operator, address, root_path, by_collections):
    global start_time
    start_time = time.time()
    # address = ""
    # address = input("Введите адрес обьекта (переменная address, используемая в наименованиях) и нажмите Enter (оставьте пустым для автоматического определения):\n")
    # if not root_path.strip():
    #     root_path = bpy.path.abspath("//")

    project_data = ProjectData()
    lp_result, hp_result = None, None

    if not root_path:
        return (lp_result, hp_result, project_data)

    preparer = ModelPreparer()
    preparer.root_path = root_path
    preparer.by_collections = by_collections

    has_lp, has_hp = preparer.check_if_has_lp_hp()
    preparer.unzip()

    preparer.clear_images()
    if has_lp:
        preparer.import_lowpoly_models()
        lowpoly_checks = LowpolyChecks()
        lowpoly_checks.by_collections = by_collections
        lowpoly_checks.address = address
        lowpoly_checks.root_path = root_path
        lowpoly_checks.run_checks(preparer.lp_fbx_files)
        lp_result = lowpoly_checks.lp_checks_by_ids
        project_data.address = lowpoly_checks.address

    if has_hp:
        preparer.import_highpoly_models()
        if by_collections:
            preparer.clear_highpoly_before_check_by_collections()

        highpoly_checks = HighpolyChecks()
        highpoly_checks.address = address
        highpoly_checks.root_path = root_path
        highpoly_checks.run_meshes_check(preparer.hp_fbx_files, preparer.oks_count, bl_operator)

        preparer.fix_coordinates()
        preparer.material_textures_set()

        highpoly_checks.add_checks(preparer.prepare_checks)
        highpoly_checks.generate_result()
        hp_result = highpoly_checks.hp_checks_by_ids

        project_data.address = highpoly_checks.address

    if has_lp and has_hp:
        preparer.import_lowpoly_models(firstImport=False)

    if has_lp:
        logger.add(lowpoly_checks.lp_result_report)
    if has_hp:
        logger.add(highpoly_checks.hp_result_report)

    return (lp_result, hp_result, project_data)

start_time = 0

if __name__ == "__main__":
    run()