#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
命令行构建应用相关命令

@module cmd_build
@file cmd_build.py
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
from HiveNetMicro.tools.build_tool.build import BuildPipeline
from HiveNetMicro.tools.utils.env import EnvTools


class CmdBuild(CmdBaseFW):
    """
    命令行构建应用相关命令
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
            'build': self._cmd_build,
            'create_build_file': self._cmd_create_build_file
        }

    #############################
    # 命令执行函数
    #############################
    def _cmd_build(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        通过构建配置生成应用

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
        _type = _para_dict.get('type', 'HiveNetMicro')
        _para_dict['type'] = _type

        _file = _para_dict.get('file', None)
        if _file is None:
            _build_file = os.path.abspath(os.path.join(os.getcwd(), 'build.yaml'))
        else:
            _build_file = os.path.abspath(os.path.join(os.getcwd(), _file))

        _base_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), os.path.pardir, os.path.pardir, 'build_tool'
        ))  # 编译器目录
        _config_file = os.path.join(_base_path, 'config.yaml')

        # 初始化构建管道对象
        _pipeline = BuildPipeline(_config_file, _build_file, _para_dict, _base_path)

        # 启动构建
        _pipeline.start_build()

        return CResult(code='00000')

    def _cmd_create_build_file(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        创建构建配置文件

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
        _type = _para_dict.get('type', 'HiveNetMicro')  # 构建类型
        _use_abspath = _para_dict.get('use_abspath', 'n')  # 使用绝对路径

        # 构建配置保存文件
        _file = _para_dict.get('file', 'build.yaml')
        _file = os.path.abspath(os.path.join(os.getcwd(), _file))
        _file_path, _filename = os.path.split(_file)
        if not os.path.exists(_file_path):
            # 如果目录不存在则创建目录
            FileTool.create_dir(_file_path, exist_ok=True)

        # 源文件目录
        _source = _para_dict.get('source', None)
        if _source is None:
            _source_path = _file_path
        else:
            _source_path = os.path.abspath(os.path.join(_file_path, _source))

        if _use_abspath == 'y':
            _source = _source_path

        # 输出目录
        _output = _para_dict.get('output', None)
        if _output is None:
            _output_path = _file_path
        else:
            _output_path = os.path.abspath(os.path.join(_file_path, _output))

        if _use_abspath == 'y':
            _output = _output_path
        elif _output is None:
            _output = 'build'

        try:
            # 判断配置是否已存在
            if os.path.exists(_file):
                _prompt_text = PromptPlus.simple_prompt(
                    message=_('The build config file already exists, this file will be overwritten, Continue? (y/n): '),
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
            _template_base_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), os.path.pardir, os.path.pardir, 'template'
            ))
            _create_config = OrderedDict()
            for _config_name in EnvTools.TEMPLATE_LIST:
                _info = EnvTools.get_template_config_info(_config_name, _template_base_path)
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

            # 执行构建文件处理
            _build_para = {
                'name': _para_dict.get('name', ''),
                'type': _type, 'source': _source, 'output': _output
            }
            EnvTools.create_build_config_file(
                _file, _build_para, _create_config, _template_base_path
            )

            # 提示处理成功
            prompt_obj.prompt_print(_('Create build config file success!'))
        except:
            print(traceback.format_exc())
            return CResult(code='29999')

        return CResult(code='00000')
