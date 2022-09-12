#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
环境处理相关工具

@module env
@file env.py
"""
import os
import sys
from collections import OrderedDict
from HiveNetCore.yaml import SimpleYaml, EnumYamlObjType
from HiveNetCore.utils.file_tool import FileTool
from HiveNetCore.utils.import_tool import DynamicLibManager
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.adapter_manager import AdapterManager


class EnvTools(object):
    """
    环境工具
    """

    #############################
    # 模版配置参数字典
    #############################
    # 模版清单
    TEMPLATE_LIST = [
        'configs', 'clusters', 'web_servers', 'server_formaters', 'namings', 'opentracings', 'inf_loggings',
        'inf_checks', 'caller_formaters', 'nosql_dbs', 'adapters'
    ]

    TEMPLATE_CONFIG = {
        # 配置中心模版
        'configs': {
            'type': 'single',  # 配置模版类型, single-单模版配置, list-列表模版配置
            'yaml_file': 'configCenter',  # 涉及的yaml配置文件名
            'std_template_mode': True,  # 是否标准模版形式, 即模版路径和配置路径的层级保持一致, 默认为True
            'template_path': 'configCenter/configs',  # 模版文件路径
            'template_filter': '',  # 模版文件的过滤正则表达式, 如果不设置代表不过滤
            'template_config_name': '',  # 模版标识映射名(仅single可用), 如果不设置代表不映射
            'config_path': 'configs',  # 模版插入的yaml路径, 多级使用/分隔, 如果通过位置选择使用[位置]的方式表示
            'ref_para_path': 'base_config/center_type',  # 模版配置id对应的配置项yaml路径, 多级使用/分隔, 如果通过位置选择使用[位置]的方式表示
            'i18n_message': 'Select config center adapter: '  # 输入提示的i18n信息
        },
        # 集群适配器配置模版
        'clusters': {
            'type': 'single',
            'yaml_file': 'application',
            'template_path': 'application/clusters',
            'config_path': 'clusters',
            'ref_para_path': 'base_config/cluster_adapter',
            'i18n_message': 'Select cluster adapter: '
        },
        # 默认web服务器模版
        'web_servers': {
            'type': 'single',
            'yaml_file': 'application',
            'template_path': 'application/web_servers',
            'config_path': 'web_servers',
            'ref_para_path': 'base_config/default_web_server',
            'i18n_message': 'Select web server adapter: '
        },
        # 服务端报文格式转换插件模版
        'server_formaters': {
            'type': 'list',
            'yaml_file': 'application',
            'template_path': 'application/server_formaters',
            'config_path': 'server_formaters',
            'ref_para_path': 'web_servers/{$=web_server_id$}/server_formaters',  # 需特殊处理web服务器的替换
            'i18n_message': 'Select server formater adapters (multiple select): '
        },
        # 服务注册中心插件模版
        'namings': {
            'type': 'single',
            'yaml_file': 'application',
            'template_path': 'application/namings',
            'config_path': 'namings',
            'ref_para_path': 'base_config/naming',
            'i18n_message': 'Select naming adapter: '
        },
        # 链路追踪插件模版
        'opentracings': {
            'type': 'single',
            'yaml_file': 'application',
            'template_path': 'application/opentracings',
            'config_path': 'opentracings',
            'ref_para_path': 'base_config/tracer',
            'i18n_message': 'Select opentracing adapter: '
        },
        # 报文信息日志记录插件模版
        'inf_loggings': {
            'type': 'list',
            'yaml_file': 'application',
            'template_path': 'application/inf_loggings',
            'config_path': 'inf_loggings',
            'ref_para_path': '',
            'i18n_message': 'Select interface logging adapters (multiple select): '
        },
        # 请求报文信息检查插件模版
        'inf_checks': {
            'type': 'list',
            'yaml_file': 'application',
            'template_path': 'application/inf_checks',
            'config_path': 'inf_checks',
            'ref_para_path': '',
            'i18n_message': 'Select interface check adapters (multiple select): '
        },
        # 远程调用报文格式转换插件模版
        'caller_formaters': {
            'type': 'list',
            'yaml_file': 'application',
            'template_path': 'application/caller_formaters',
            'config_path': 'caller_formaters',
            'ref_para_path': 'base_config/caller_formaters',
            'i18n_message': 'Select caller formater adapters (multiple select): '
        },
        # NoSQL数据库插件
        'nosql_dbs': {
            'type': 'single',
            'yaml_file': 'adapters',
            'template_path': 'adapters/adapters',
            'template_filter': r'^nosql.*\.yaml$',
            'template_id_as_name': 'nosql_db',
            'config_path': 'adapters',
            'ref_para_path': '',
            'i18n_message': 'Select NoSQL db adapter: '
        },
        # 自定义适配器
        'adapters': {
            'type': 'list',
            'yaml_file': 'adapters',
            'template_path': 'adapters/adapters',
            'config_path': 'adapters',
            'template_filter': r'^(?!nosql).*\.yaml$',
            'ref_para_path': '',
            'i18n_message': 'Select extend adapters (multiple select): '
        },
    }

    #############################
    # 公共函数
    #############################
    @classmethod
    def get_adapter_manager(cls, base_path: str) -> AdapterManager:
        """
        获取初始化后的插件管理对象

        @param {str} base_path - 应用所在目录

        @returns {AdapterManager} - 插件管理对象
        """
        # 公共
        _lib_plugins_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir, 'plugins')
        )
        _lib_loader = DynamicLibManager(_lib_plugins_path)  # 系统动态库加载对象

        return AdapterManager(
            os.path.join(base_path, 'plugins'), base_path, lib_loader=_lib_loader
        )

    @classmethod
    def get_template_config_info(cls, name: str, template_base_path: str) -> dict:
        """
        获取模版配置的信息

        @param {str} name - 模版配置名
        @param {str} template_base_path - 模版所在基础目录

        @returns {dict} - 信息字典
        """
        _config = cls.TEMPLATE_CONFIG.get(name, None)
        if _config is None:
            raise ModuleNotFoundError('Template config not found')

        _info = {
            'type': _config['type'],
            'i18n_message': _config['i18n_message']
        }

        # 获取可选信息
        _config_template_path = os.path.abspath(os.path.join(
            template_base_path, 'configTemplates'
        ))
        _options = FileTool.get_filelist(
            path=os.path.join(_config_template_path, _config['template_path']),
            regex_str=r'.*\.yaml$' if _config.get('template_filter', '') == '' else _config['template_filter'],
            is_fullname=False
        )
        for _index in range(len(_options)):
            _options[_index] = _options[_index][0: -5]

        _info['options'] = _options

        return _info

    @classmethod
    def create_build_config_file(cls, file: str, build_para: dict, config: OrderedDict, template_base_path: str):
        """
        创建构建配置文件

        @param {str} file - 要保存的构建文件
        @param {dict} build_para - 构建参数字典
        @param {OrderedDict} config - 要构建的配置信息字典, 需注意按顺序传入以下值:
            {
                'configs': '配置中心类型id, 例如nacos',
                'clusters': '集群适配器id, 例如redis_cluster',
                'web_servers': '默认web服务类型id, 例如sanic',
                'server_formaters': ['web服务支持的报文转换适配器id', ...],
                'namings': '注册中心适配器id, 例如nacos',
                'inf_loggings': ['报文信息日志记录插件id', ...],
                'inf_checks': ['请求报文信息检查插件id', ...],
                'caller_formaters': ['远程调用报文格式转换插件id', ...]
            }
        @param {str} template_base_path - 模版所在基础目录
        """
        # 如果文件已存在, 删除文件
        if os.path.exists(file):
            FileTool.remove_file(file)

        # 装载模版
        _yaml = SimpleYaml(
            os.path.join(template_base_path, 'buildTemplates/build.yaml'),
            obj_type=EnumYamlObjType.File, encoding='utf-8'
        )

        # 处理构建参数
        for _key, _val in build_para.items():
            _yaml.set_value('build/%s' % _key, _val, auto_create=True)

        # 处理配置模版
        for _key, _val in config.items():
            _template_config = cls.TEMPLATE_CONFIG.get(_key, None)
            if _template_config is None:
                raise ModuleNotFoundError('Template config not found')

            if _template_config['type'] in ('single', 'list'):
                # 处理基础配置
                _std_template_mode = _template_config.get('std_template_mode', True)

                if _template_config['type'] == 'list':
                    _template_list = _val
                else:
                    _template_list = [_val]

                # 处理模版生成的设置参数
                if _std_template_mode:
                    # 标准模版路径层级
                    _set_path = 'configTemplates/%s/%s' % (
                        _template_config['yaml_file'], _template_config['config_path']
                    )
                    _set_vals = []
                    for _template_id in _template_list:
                        _template_val = {
                            'template': _template_id  # 模版文件名
                        }
                        if _template_config['type'] == 'single':
                            # 单一节点, 可能涉及调整模版key名
                            if _template_config.get('template_id_as_name', None) is not None:
                                _template_val['config_name'] = _template_config['template_id_as_name']
                        _set_vals.append(_template_val)
                else:
                    # 非标准的模版路径层级
                    _set_path = 'configTemplates/%s' % _template_config['yaml_file']
                    _vals = []
                    for _template_id in _template_list:
                        _template_val = {
                            'template': _template_id,  # 模版文件名
                            'remplate_path': _template_config['template_path']  # 模版路径
                        }
                        if _template_config['type'] == 'single':
                            # 单一节点, 可能涉及调整模版key名
                            if _template_config.get('template_id_as_name', None) is not None:
                                _template_val['config_name'] = _template_config['template_id_as_name']

                    _set_vals = {
                        _template_config['config_path']: _vals
                    }

                # 设置模版参数
                _yaml.set_value(_set_path, _set_vals, auto_create=True)

                # 处理关联参数设置
                if _template_config.get('ref_para_path', '') != '':
                    _set_path = 'configSetValues/%s/%s' % (
                        _template_config['yaml_file'], _template_config['ref_para_path']
                    )
                    if _key == 'server_formaters':
                        # 服务器格式化适配器部分需要特殊处理
                        if config.get('web_servers', None) is None:
                            raise AttributeError('You must set web server if use server formaters')

                        _set_path = _set_path.replace('{$=web_server_id$}', config['web_servers'])

                    if _template_config['type'] == 'list':
                        # 列表形式, 更新为列表值
                        _set_vals = _val
                    else:
                        # 单值模式, 设置为key标识
                        if _template_config.get('template_id_as_name', None) is not None:
                            _set_vals = _template_config['template_id_as_name']
                        else:
                            _set_vals = _val

                # 设置配置值参数
                _yaml.set_value(_set_path, _set_vals, auto_create=True)
            else:
                raise ModuleNotFoundError('Template config type error: %s' % _template_config['type'])

        # 保存配置
        _yaml.save(file=file, encoding='utf-8')

        # 复制模版的build.py文件
        with open(os.path.join(template_base_path, 'buildTemplates/build.py'), 'r', encoding='utf-8') as _f:
            _py_str = _f.read()

        _build_path, _build_file = os.path.split(file)
        _py_str = _py_str.replace('{$=build.yaml$}', _build_file)
        _py_file = FileTool.get_file_name_no_ext(_build_file)
        with open(os.path.join(_build_path, '%s.py' % _py_file), 'w', encoding='utf-8') as _f:
            _f.write(_py_str)
