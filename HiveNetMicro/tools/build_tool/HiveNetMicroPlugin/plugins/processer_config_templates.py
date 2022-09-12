#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
构建工具管道插件-配置文件模版生成

@module processer_config_templates
@file processer_config_templates.py
"""
import os
from HiveNetCore.yaml import SimpleYaml, EnumYamlObjType
from HiveNetCore.utils.file_tool import FileTool
from HiveNetPipeline import PipelineProcesser


class ProcesserBuildConfigTemplates(PipelineProcesser):
    """
    配置文件模版生成
    """

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称，唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'ProcesserBuildConfigTemplates'

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
        _current_key = context.get('current_key', 'configTemplates')
        _config = context['build_config'].get(_current_key, None)

        # 获取不到配置, 不处理
        if _config is None:
            return input_data

        # 获取模版目录
        _template_path = context.get('build_type_config', {}).get('selfConfig', {}).get(
            'configTemplatesPath', ''
        )
        _template_path = os.path.abspath(
            os.path.join(context['base_path'], _template_path)
        )
        _output = context['build']['output']

        # 逐个配置进行处理
        for _yaml, _para in _config.items():
            # 复制配置文件模版
            _yaml_file = os.path.join(_template_path, '%s.yaml' % _yaml)
            _dest_file = os.path.join(_output, 'config', '%s.yaml' % _yaml)
            FileTool.copy_file(_yaml_file, _dest_file, overwrite=True)

            if _para is None:
                # 仅复制配置文件, 不增加子配置
                continue

            # 增加子模版
            _yaml_config = SimpleYaml(_dest_file, obj_type=EnumYamlObjType.File, encoding='utf-8')
            _set_list = []  # 要设置的配置列表
            cls._generate_set_list('', _para, _set_list)

            # 逐个配置进行设置
            for _set_item in _set_list:
                # 获取模版文件
                if _set_item['set_para'].get('remplate_path', None) is not None:
                    # 指定了路径
                    _sub_yaml_file = os.path.abspath(os.path.join(
                        _template_path, _set_item['set_para']['remplate_path'], '%s.yaml' % _set_item['set_para']['template']
                    ))
                else:
                    # 默认路径
                    _sub_yaml_file = os.path.abspath(os.path.join(
                        _template_path, _yaml, _set_item['set_path'], '%s.yaml' % _set_item['set_para']['template']
                    ))

                # 获取配置
                _sub_yaml_dict = SimpleYaml(_sub_yaml_file, obj_type=EnumYamlObjType.File, encoding='utf-8').yaml_dict
                if _set_item['set_para'].get('config_name', None) is not None:
                    _sub_yaml_dict = {
                        _set_item['set_para']['config_name']: list(_sub_yaml_dict.values())[0]
                    }

                # 设置参数值
                for _config_name, _config_val in _sub_yaml_dict.items():
                    _yaml_config.set_value(
                        '%s/%s' % (_set_item['set_path'], _config_name), _config_val, auto_create=True
                    )

            # 保存配置文件
            _yaml_config.save()

        # 返回输出结果
        return input_data

    #############################
    # 内部函数
    #############################
    @classmethod
    def _generate_set_list(cls, set_path: str, config_para, set_list: list):
        """
        初始化参数设置清单

        @param {str} set_path - 设置路径
        @param {Any} config_para - 要判断处理的参数, 当为list对象时才为要设置模版参数值
        @param {list} set_list - 要更新的参数列表
        """
        if isinstance(config_para, dict):
            # 仍为层级字典参数
            for _key, _para in config_para.items():
                _set_path = _key if set_path == '' else '%s/%s' % (set_path, _key)
                cls._generate_set_list(
                    _set_path, _para, set_list
                )
        else:
            # 为最终的参数
            for _item in config_para:
                set_list.append({
                    'set_path': set_path, 'set_para': _item
                })
