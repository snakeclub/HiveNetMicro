#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
命令行基础环境管理相关命令

@module cmd_env
@file cmd_env.py
"""
import os
import sys
import traceback
import copy
from collections import OrderedDict
from HiveNetCore.generic import CResult
from HiveNetCore.i18n import _
from HiveNetConsole.base_cmd import CmdBaseFW
from HiveNetConsole.server import ConsoleServer
from HiveNetCore.utils.file_tool import FileTool
from HiveNetPromptPlus import PromptPlus, SimpleCompleter
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.tools.utils.env import EnvTools
from HiveNetMicro.tools.utils.nosql_db import NoSqlDbTools


class CmdEnv(CmdBaseFW):
    """
    命令行基础环境管理相关命令
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
            'set_base_path': self._cmd_set_base_path,
            'show_base_path': self._cmd_show_base_path,
            'create_app': self._cmd_create_app,
        }

        # 初始化工具对象
        self._env_tools = EnvTools()
        self._console_global_para['env_tools'] = self._env_tools
        self._nosql_db_tools = NoSqlDbTools(self._env_tools.adapter_manager)
        self._console_global_para['nosql_db_tools'] = self._nosql_db_tools

    #############################
    # 命令执行函数
    #############################
    def _cmd_set_base_path(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        设置微服务应用基础目录

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象，可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象
            shell_cmd {bool} - 如果传入参数有该key，且值为True，代表是命令行直接执行，非进入控制台执行
        @returns {CResult} - 命令执行结果，可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的print_str属性要求框架进行打印处理
        """
        # 检查路径是否存在
        _base_path = os.path.abspath(cmd_para.strip())
        if not os.path.exists(_base_path):
            prompt_obj.prompt_print(
                _('Micro app base path not exists: $1', _base_path))
            return CResult(code='20801', i18n_msg_paras=(_base_path))

        # 设置基础路径
        self._env_tools.set_base_path(_base_path)
        self._nosql_db_tools.set_base_path(_base_path)
        # 设置set_nosql_driver命令的动态提示参数
        _set_nosql_driver_cmd_para = {'word_para': {}}
        for _word_para in self._nosql_db_tools.nosql_adapter_list:
            _set_nosql_driver_cmd_para['word_para'][_word_para] = ''
        ConsoleServer.change_cmd_para_config('set_nosql_driver', _set_nosql_driver_cmd_para)

        # 设置基础路径
        self._console_global_para['base_path'] = _base_path
        prompt_obj.prompt_print(
            _('Micro app base path is: $1', self._console_global_para['base_path']))

        return CResult(code='00000')

    def _cmd_show_base_path(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        显示微服务应用基础目录

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象，可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象
            shell_cmd {bool} - 如果传入参数有该key，且值为True，代表是命令行直接执行，非进入控制台执行
        @returns {CResult} - 命令执行结果，可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的print_str属性要求框架进行打印处理
        """
        prompt_obj.prompt_print(
            _('Micro app base path is: $1', self._console_global_para.get('base_path', '')))

        return CResult(code='00000')

    def _cmd_create_app(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        创建微服务应用

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象，可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象
            shell_cmd {bool} - 如果传入参数有该key，且值为True，代表是命令行直接执行，非进入控制台执行
        @returns {CResult} - 命令执行结果，可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的print_str属性要求框架进行打印处理
        """
        # 检查路径是否存在
        _para = cmd_para.strip()
        if _para == '':
            _para = self._console_global_para.get('base_path', '')

        if _para == '':
            prompt_obj.prompt_print(
                _('You must pass base path para or use set_base_path to set base path first'))
            return CResult(code='21399')
        else:
            _base_path = os.path.abspath(_para)

        try:
            # 创建目录
            if not os.path.exists(_base_path):
                # 目录不存在, 创建目录
                FileTool.create_dir(_base_path, exist_ok=True)
            else:
                _prompt_text = PromptPlus.simple_prompt(
                    message=_('The path already exists, the original configuration will be overwritten, Continue? (y/n): '),
                    completer=SimpleCompleter(['y', 'n'], ignore_case=True, select_mode=True, sentence=True)
                )
                if _prompt_text.strip().lower() != 'y':
                    prompt_obj.prompt_print(_('Cancle the operation'))
                    return CResult(code='29999')

            # 定义获取多选词的动态选项
            def _multiple_options_words(current_word, full_text, fun_arg) -> list:
                _words: list = copy.copy(fun_arg)
                _use_list = full_text.split(' ')
                if current_word != '':
                    _use_list = _use_list[0: -1]

                _new_words = []
                for _word in _words:
                    if _word not in _use_list:
                        _new_words.append(_word)

                return _new_words

            # 收集处理参数
            _create_config = OrderedDict()
            for _config_name in self._env_tools.TEMPLATE_LIST:
                _info = self._env_tools.get_template_config_info(_config_name)
                if _info['type'] == 'list':
                    # 支持多选
                    _prompt_text = PromptPlus.simple_prompt(
                        message=_(_info['i18n_message']),
                        completer=SimpleCompleter(
                            _multiple_options_words, ignore_case=False, select_mode=True,
                            sentence=False, words_fun_arg=_info['options']
                        )
                    )
                    _val = _prompt_text.strip()
                    if _val != '':
                        # 转为数组并去掉空值
                        _temp_val = _val.split(' ')
                        _val = []
                        for _id in _temp_val:
                            if _id != '':
                                _val.append(_id)
                else:
                    # 单选
                    _prompt_text = PromptPlus.simple_prompt(
                        message=_(_info['i18n_message']),
                        completer=SimpleCompleter(
                            _info['options'], ignore_case=False, select_mode=True, sentence=True
                        )
                    )
                    _val = _prompt_text.strip()

                # 设置参数
                if _val is not None and _val != '':
                    _create_config[_config_name] = _val

            # 执行处理
            self._env_tools.create_app(base_path=_base_path, config=_create_config)

            # 提示处理成功
            prompt_obj.prompt_print(_('Create app success!'))
        except:
            print(traceback.format_exc())
            return CResult(code='29999')

        return CResult(code='00000')
