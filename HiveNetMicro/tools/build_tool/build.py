#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
应用构建工具

@module build
@file build.py
"""
import os
import copy
from HiveNetCore.utils.run_tool import RunTool
from HiveNetCore.utils.file_tool import FileTool
from HiveNetCore.yaml import SimpleYaml, EnumYamlObjType
from HiveNetPipeline import Pipeline


class BuildPipeline(object):
    """
    构建管道对象
    """

    def __init__(self, config_file: str, build_file: str, cmd_opts: dict, base_path: str):
        """
        初始化对象

        @param {str} config_file - 配置文件
        @param {str} build_file - 构建文件
        @param {dict} cmd_opts - 命令行参数
            file: str, 构建配置文件(build.yaml)
            source: str, 指定构建源码目录
            output: str, 构建结果输出目录
            type: str, 构建类型
        @param {str} base_path - 编译器目录
        """
        # 基础参数
        self._base_path = base_path
        if base_path is None:
            self._base_path = os.path.abspath(os.path.dirname(__file__))  # 编译器目录

        self._config_file = config_file
        if config_file is None:
            self._config_file = os.path.join(self._base_path, 'config.yaml') # 配置文件

        self._cmd_opts = cmd_opts
        self._build_file = build_file
        self._build_file_path = os.path.dirname(build_file)

        # 加载构建配置文件
        self._build_config = SimpleYaml(
            build_file, obj_type=EnumYamlObjType.File, encoding='utf-8'
        ).yaml_dict

        # 处理构建文件的路径
        if cmd_opts.get('source', None) is not None:
            self._source = os.path.abspath(os.path.join(os.getcwd(), cmd_opts['source']))
        else:
            if self._build_config['build'].get('source', None) is None:
                self._source = self._build_file_path
            else:
                self._source = os.path.join(self._build_file_path, self._build_config['build']['source'])

        if cmd_opts.get('output', None) is not None:
            self._output = os.path.abspath(os.path.join(os.getcwd(), cmd_opts['output']))
        else:
            if self._build_config['build'].get('output', None) is None:
                self._output = self._build_file_path
            else:
                self._output = os.path.join(self._build_file_path, self._build_config['build']['output'])

        # 加载构建工具配置文件
        self._config = SimpleYaml(
            self._config_file, obj_type=EnumYamlObjType.File, encoding='utf-8'
        ).yaml_dict

        # 当前构建类型参数
        if cmd_opts.get('type', None) is None:
            self._type = self._build_config['build']['type']
        else:
            self._type = cmd_opts['type']

        self._type_config = self._config[self._type]

        # 装载管道通用插件和当前构建类型管道插件
        Pipeline.load_plugins_by_path(os.path.join(self._base_path, 'plugins'))
        if self._type_config.get('plugins', None) is not None:
            Pipeline.load_plugins_by_path(
                os.path.join(self._base_path, self._type_config['plugins'])
            )

        # 获取管道运行参数
        self._pipeline_config = SimpleYaml(
            os.path.join(self._base_path, self._type_config['pipeline']),
            obj_type=EnumYamlObjType.File, encoding='utf-8'
        ).yaml_dict
        self._pipeline = Pipeline(
            'build', self._pipeline_config, running_notify_fun=self._running_notify_fun,
            end_running_notify_fun=self._end_running_notify_fun
        )

    def start_build(self):
        """
        启动构建处理
        """
        # 初始化上下文
        _context = {
            'build_type_config': copy.deepcopy(self._type_config),
            'base_path': self._base_path,
            'cmd_opts': self._cmd_opts,
            'build': copy.deepcopy(self._build_config['build']),
            'build_config': copy.deepcopy(self._build_config)
        }

        # 处理构建参数的路径
        _context['build']['type'] = self._type
        _context['build']['source'] = self._source
        _context['build']['output'] = self._output

        # 创建输出目录
        FileTool.create_dir(self._output, exist_ok=True)

        # 运行构建管道
        _run_id, _status, _output = self._pipeline.start(
            context=_context
        )

        # 返回结果
        if _status == 'S':
            print('\n构建成功\n')
            # 提示信息
            if self._build_config['build'].get('successTips', None) is not None:
                for _line in self._build_config['build']['successTips']:
                    print(_line)
                print('\n')
        else:
            print('\n构建失败\n')
            exit(1)

    #############################
    # 内部函数
    #############################
    def _running_notify_fun(self, name, run_id, node_id, node_name, pipeline_obj):
        """
        节点运行通知函数
        """
        print('[%s] 开始执行构建步骤[%s: %s]' % (
            name, node_id, node_name
        ))

    def _end_running_notify_fun(self, name, run_id, node_id, node_name, status, status_msg, pipeline_obj):
        """
        结束节点运行通知
        """
        print('[%s] 结束执行构建步骤[%s: %s] [状态: %s]: %s' % (
            name, node_id, node_name,
            'S-成功' if status == 'S' else '%s-失败' % status,
            status_msg
        ))


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    _opts = RunTool.get_kv_opts()  # 获取命令行参数

    # 处理配置信息
    _base_path = os.path.abspath(os.path.dirname(__file__))  # 编译器目录
    _config_file = os.path.join(_base_path, 'config.yaml') # 配置文件
    if _opts.get('file', None) is None:
        _build_file = os.path.abspath(os.path.join(os.getcwd(), 'build.yaml'))
    else:
        _build_file = os.path.abspath(os.path.join(os.getcwd(), _opts['file']))

    # 测试
    # _build_file = os.path.abspath(
    #     os.path.join(_base_path, os.path.pardir, os.path.pardir, 'demo/local_no_db/build.yaml')
    # )

    # 初始化构建管道对象
    _pipeline = BuildPipeline(_config_file, _build_file, _opts, _base_path)

    # 启动构建
    _pipeline.start_build()
