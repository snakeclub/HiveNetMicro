#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
构建工具管道插件-文件夹处理

@module processer_dirs
@file processer_dirs.py
"""
import os
from HiveNetCore.utils.file_tool import FileTool
from HiveNetPipeline import PipelineProcesser


class ProcesserBuildDir(PipelineProcesser):
    """
    文件夹处理
    """

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称，唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'ProcesserBuildDir'

    @classmethod
    def execute(cls, input_data, context: dict, pipeline_obj, run_id: str):
        """
        执行处理

        @param {object} input_data - 处理器输入数据值，除第一个处理器外，该信息为上一个处理器的输出值
        @param {dict} context - 传递上下文，该字典信息将在整个管道处理过程中一直向下传递，可以在处理器中改变该上下文信息
        @param {Pipeline} pipeline_obj - 管道对象

        @returns {object} - 处理结果输出数据值, 供下一个处理器处理, 异步执行的情况返回None
        """
        # 获取当前要处理的标识
        _current_key = context.get('current_key', 'dirs')
        _config = context['build_config'].get(_current_key, None)

        # 获取不到配置, 不处理
        if _config is None:
            return input_data

        # 进行目录处理
        _source = context['build']['source']
        _output = context['build']['output']

        for _path, _para in _config.items():
            _path = os.path.abspath(os.path.join(_output, _path))
            if _para is None:
                # 仅创建目录
                FileTool.create_dir(_path, exist_ok=True)
                continue

            # 处理其他参数
            if _para.get('clear', False) and os.path.exists(_path):
                # 清空原来的目录
                FileTool.remove_dir(_path)

            # 创建目录
            FileTool.create_dir(_path, exist_ok=True)

            # 处理复制文件和目录
            if _para.get('copy', None) is not None:
                for _copy_para in _para['copy']:
                    if type(_copy_para) == str:
                        _src_file = os.path.join(_source, _copy_para)
                        _dest_file = os.path.join(_path, FileTool.get_file_name(_copy_para))
                    else:
                        _src_file = os.path.join(_source, _copy_para[0])
                        _dest_file = os.path.join(_path, _copy_para[1])

                    if os.path.isdir(_src_file):
                        FileTool.copy_all_with_path(
                            src_path=_src_file, dest_path=_dest_file
                        )
                    else:
                        FileTool.copy_file(_src_file, _dest_file)

            # 处理复制所有子文件夹
            if _para.get('copyAll', None) is not None:
                for _copy_para in _para['copyAll']:
                    if type(_copy_para) == str:
                        _src = os.path.join(_source, _copy_para)
                        _dest = _path
                    else:
                        _src = os.path.join(_source, _copy_para[0])
                        _dest = os.path.join(_path, _copy_para[1])

                    FileTool.copy_all_with_path(
                        src_path=_src, dest_path=_dest
                    )

        # 返回输出结果
        return input_data
