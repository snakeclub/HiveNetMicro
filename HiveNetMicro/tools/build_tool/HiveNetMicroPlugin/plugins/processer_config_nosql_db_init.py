#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
构建工具管道插件-NoSql数据库初始化

@module processer_config_nosql_db_init
@file processer_config_nosql_db_init.py
"""
import os
from HiveNetPipeline import PipelineProcesser
from HiveNetMicro.tools.utils.nosql import NoSqlTools


class ProcesserBuildNoSqlDbInit(PipelineProcesser):
    """
    配置文件模版生成
    """

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称，唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'ProcesserBuildNoSqlDbInit'

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
        _current_key = context.get('current_key', 'noSqlDbInit')
        _config = context['build_config'].get(_current_key, None)

        # 获取不到配置, 不处理
        if _config is None:
            return input_data

        # 获取目录信息
        _source = context['build']['source']
        _output = context['build']['output']
        _template_path = context.get('build_type_config', {}).get('selfConfig', {}).get(
            'noSqlDbInitScriptPath', ''
        )
        _template_path = os.path.abspath(
            os.path.join(context['base_path'], _template_path)
        )

        # 逐个配置进行处理
        for _adapter_id, _para in _config.items():
            for _op_id, _build_para in _para.items():
                # 保存的初始化yaml文件
                _init_filename = '%s_%s_%s' % (_adapter_id, _op_id, _build_para['type'])
                _init_yaml_file = os.path.abspath(os.path.join(
                    _output, 'nosql_init', '%s.yaml' % _init_filename
                ))

                # 脚本处理相关参数
                _py_file = os.path.abspath(os.path.join(
                    _output, 'nosql_init', '%s.py' % _init_filename
                ))
                _replaces = {
                    '{$=output_path$}': _output, '{$=adapter_id$}': _adapter_id,
                    '{$=init_filename$}': '%s.yaml' % _init_filename
                }

                if _build_para['type'] == 'db':
                    # 数据库初始化
                    NoSqlTools.build_db_para_to_yaml(_build_para, _init_yaml_file, append=False)
                    if _build_para.get('updateToDriverOpts', True):
                        NoSqlTools.update_dbs_to_driver_opts(
                            _output, _init_yaml_file, _adapter_id
                        )

                    # 生成初始化数据库的操作脚本
                    cls._generate_init_script(
                        os.path.join(_template_path, 'init_dbs.py'),
                        _py_file, replaces=_replaces
                    )
                elif _build_para['type'] == 'collection':
                    # 数据表初始化
                    NoSqlTools.build_collection_para_to_yaml(
                        _source, _build_para, _init_yaml_file, append=False
                    )
                    if _build_para.get('updateToDriverOpts', True):
                        NoSqlTools.update_collections_to_driver_opts(
                            _output, _init_yaml_file, _adapter_id
                        )

                    # 生成初始化数据库的操作脚本
                    cls._generate_init_script(
                        os.path.join(_template_path, 'init_collections.py'),
                        _py_file, replaces=_replaces
                    )
                elif _build_para['type'] == 'data':
                    # 数据初始化
                    NoSqlTools.build_data_para_to_yaml(_source, _build_para, _init_yaml_file, append=False)

                    # 生成初始化数据库的操作脚本
                    cls._generate_init_script(
                        os.path.join(_template_path, 'init_datas.py'),
                        _py_file, replaces=_replaces
                    )
                else:
                    raise AttributeError('noSqlDbInit type [%s] error' % _build_para['type'])

        # 返回输出结果
        return input_data

    #############################
    # 内部函数
    #############################
    @classmethod
    def _generate_init_script(cls, template_file: str, save_file: str, replaces: dict = {}):
        """
        生成初始化操作脚本

        @param {str} template_file - 脚本模版文件路径
        @param {str} save_file - 要生成的初始化脚本路径
        @param {dict} replaces={} - 要进行替换的内容
        """
        # 读取脚本内容
        with open(template_file, 'r', encoding='utf-8') as _f:
            _script_str = _f.read()

        # 进行内容替换
        for _key, _val in replaces.items():
            _script_str = _script_str.replace(_key, _val)

        # 保存脚本
        with open(save_file, 'w', encoding='utf-8') as _f:
            _f.write(_script_str)
