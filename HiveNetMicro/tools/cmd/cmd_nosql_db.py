#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
支持HiveNetNoSql库的数据库工具命令实现

@module cmd_nosql_db
@file cmd_nosql_db.py
"""
import os
import sys
import json
import traceback
from HiveNetCore.generic import CResult
from HiveNetCore.i18n import _
from HiveNetConsole.base_cmd import CmdBaseFW
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.tools.utils.nosql_db import NoSqlDbTools


class CmdNoSqlDb(CmdBaseFW):
    """
    支持HiveNetNoSql库的数据库工具命令
    """

    #############################
    # 需具体实现类覆盖实现的类
    #############################
    def _init(self, **kwargs):
        """
        实现类需要覆盖实现的初始化函数
        @param {kwargs} - 传入初始化参数字典（config.xml的init_para字典）
        @throws {exception-type} - 如果初始化异常应抛出异常
        """
        # 自定义初始化函数中设置命令的映射关系，并且请不要重载 _cmd_dealfun 函数
        self._CMD_DEALFUN_DICT = {
            'nosql_set_driver': self._cmd_nosql_set_driver,
            'nosql_create_db': self._cmd_nosql_create_db,
            'nosql_convert_init_file': self._cmd_nosql_convert_init_file,
            'nosql_init_database': self._cmd_nosql_init_database,
            'nosql_init_data': self._cmd_nosql_init_data
        }

        self._nosql_db_tools: NoSqlDbTools = self._console_global_para['nosql_db_tools']

    #############################
    # 命令执行函数
    #############################
    def _cmd_nosql_set_driver(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        设置NoSql驱动对象

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象，可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象
            shell_cmd {bool} - 如果传入参数有该key，且值为True，代表是命令行直接执行，非进入控制台执行
        @returns {CResult} - 命令执行结果，可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的print_str属性要求框架进行打印处理
        """
        _adapter_id = cmd_para.strip()  # 适配器id
        if _adapter_id == '':
            prompt_obj.prompt_print(
                _('You must pass NoSql adapter_id'))
            return CResult(code='21006', i18n_msg_paras=('adapter_id'))

        try:
            self._nosql_db_tools.set_nosql_driver(adapter_id=_adapter_id)
            prompt_obj.prompt_print(_('Set NoSql driver to [$1]', _adapter_id))
            return CResult(code='00000')
        except:
            prompt_obj.prompt_print(
                '%s: %s' % (_('set_nosql_driver error'), traceback.format_exc())
            )
            return CResult(code='29999')

    def _cmd_nosql_create_db(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        NoSql创建数据库

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象，可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象
            shell_cmd {bool} - 如果传入参数有该key，且值为True，代表是命令行直接执行，非进入控制台执行
        @returns {CResult} - 命令执行结果，可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的print_str属性要求框架进行打印处理
        """
        # 获取字典参数, 并进行判断和处理
        _para_dict = self._cmd_para_to_dict(cmd_para, name_with_sign=False)
        if _para_dict.get('name', None) is None:
            prompt_obj.prompt_print(_('You must pass name'))
            return CResult(code='21006', i18n_msg_paras=('name'))

        # 进行创建
        self._nosql_db_tools.create_db(
            _para_dict['name'], *_para_dict.get('args', []), **_para_dict.get('kwargs', {})
        )

        # 返回结果
        prompt_obj.prompt_print(_('Create database [$1] success', _para_dict['name']))
        return CResult(code='00000')

    def _cmd_nosql_convert_init_file(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        NoSql初始化配置文件转换

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象，可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象
            shell_cmd {bool} - 如果传入参数有该key，且值为True，代表是命令行直接执行，非进入控制台执行
        @returns {CResult} - 命令执行结果，可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的print_str属性要求框架进行打印处理
        """
        # 获取字典参数, 并进行判断和处理
        _para_dict = self._cmd_para_to_dict(cmd_para, name_with_sign=False)
        _type = _para_dict.get('type', None)
        if _para_dict.get('type', None) not in ('init_collection', 'init_data'):
            prompt_obj.prompt_print(_('type para unsupport [$1]', _type))
            return CResult(code='21001')

        _src_excel = _para_dict.get('src_excel', None)
        if _src_excel is None:
            prompt_obj.prompt_print(_('You must pass src_excel'))
            return CResult(code='21006', i18n_msg_paras=('src_excel'))

        _src_excel = os.path.abspath(os.path.join(self._nosql_db_tools.app_base_path, _src_excel))
        if not os.path.exists(_src_excel) or not os.path.isfile(_src_excel):
            prompt_obj.prompt_print(_('src_excel not exists or is not a file: $1', _src_excel))
            return CResult(code='21001')

        _dest_yaml = _para_dict.get('dest_yaml', None)
        if _dest_yaml is None:
            _dest_yaml = os.path.abspath(os.path.join(
                self._nosql_db_tools.app_base_path, 'nosql_init',
                'init_data.yaml' if _type == 'init_data' else 'init_collection.yaml'
            ))
        else:
            _dest_yaml = os.path.abspath(os.path.join(self._nosql_db_tools.app_base_path, _dest_yaml))

        _db_name = _para_dict.get('db_name', None)
        if _db_name is not None and _db_name[0] == '[' and _db_name[-1] == ']':
            _db_name = json.loads(_db_name)

        _collection_name = _para_dict.get('collection_name', None)
        if _collection_name is not None and _collection_name[0] == '[' and _collection_name[-1] == ']':
            _collection_name = json.loads(_collection_name)

        _db_name_mapping = _para_dict.get('db_name_mapping', None)
        if _db_name_mapping is None:
            _db_name_mapping = {}
        else:
            _db_name_mapping = json.loads(_db_name_mapping)

        # 执行转换处理
        if _type == 'init_data':
            self._nosql_db_tools.init_data_excel_to_yaml(
                _src_excel, yaml_file=_dest_yaml,
                db_name=_db_name, collection_name=_collection_name, db_name_mapping=_db_name_mapping
            )
        else:
            self._nosql_db_tools.collection_excel_to_yaml(
                _src_excel, yaml_file=_dest_yaml, append=(_para_dict.get('append', 'y') == 'y'),
                index_only=(_para_dict.get('index_only', 'y') == 'y'),
                db_name=_db_name, collection_name=_collection_name, db_name_mapping=_db_name_mapping
            )

        # 返回结果
        prompt_obj.prompt_print(_('Converted initialize file to: [$1]', _dest_yaml))
        return CResult(code='00000')

    def _cmd_nosql_init_database(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        NoSql初始化数据库

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象，可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象
            shell_cmd {bool} - 如果传入参数有该key，且值为True，代表是命令行直接执行，非进入控制台执行
        @returns {CResult} - 命令执行结果，可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的print_str属性要求框架进行打印处理
        """
        # 获取字典参数, 并进行判断和处理
        _para_dict = self._cmd_para_to_dict(cmd_para, name_with_sign=False)

        # 执行初始化处理
        self._nosql_db_tools.init_database(
            collection_file=_para_dict.get('collection_file', None),
            db_option=_para_dict.get('db_option', None),
            collection_option=_para_dict.get('collection_option', None),
            driver_option=_para_dict.get('driver_option', None)
        )

        # 返回结果
        prompt_obj.prompt_print(_('Initialize database success'))
        return CResult(code='00000')

    def _cmd_nosql_init_data(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        NoSql初始化数据

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象，可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象
            shell_cmd {bool} - 如果传入参数有该key，且值为True，代表是命令行直接执行，非进入控制台执行
        @returns {CResult} - 命令执行结果，可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的print_str属性要求框架进行打印处理
        """
        # 获取字典参数, 并进行判断和处理
        _para_dict = self._cmd_para_to_dict(cmd_para, name_with_sign=False)

        self._nosql_db_tools.init_data(
            collection_file=_para_dict.get('collection_file', None),
            data_file=_para_dict.get('data_file', None),
        )

        # 返回结果
        prompt_obj.prompt_print(_('Initialize data success'))
        return CResult(code='00000')
