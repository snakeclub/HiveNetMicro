#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
构建工具管道插件-配置文件设置值

@module processer_config_config_set_values
@file processer_config_config_set_values.py
"""
import os
from HiveNetCore.yaml import SimpleYaml, EnumYamlObjType
from HiveNetCore.utils.value_tool import ValueTool
from HiveNetPipeline import PipelineProcesser


class ProcesserBuildConfigSetValues(PipelineProcesser):
    """
    配置文件设置值
    """

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称，唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'ProcesserBuildConfigSetValues'

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
        _current_key = context.get('current_key', 'configSetValues')
        _config = context['build_config'].get(_current_key, None)
        _output = context['build']['output']

        # 获取不到配置, 不处理
        if _config is None:
            return input_data

        # 逐个配置进行处理
        for _yaml, _para in _config.items():
            # 复制配置文件模版
            _yaml_file = os.path.join(_output, 'config', '%s.yaml' % _yaml)

            if _para is None:
                # 仅复制配置文件, 不增加子配置
                continue

            # 设置值
            _yaml_config = SimpleYaml(_yaml_file, obj_type=EnumYamlObjType.File, encoding='utf-8')
            ValueTool.merge_dict(_yaml_config.yaml_config, _para)

            # 保存配置文件
            _yaml_config.save()

        # 返回输出结果
        return input_data
