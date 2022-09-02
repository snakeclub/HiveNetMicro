#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
微服务环境处理的的工具处理模块

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
    微服务环境处理的的工具处理模块
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
            'file_name': 'configCenter.yaml',  # 涉及的配置文件名
            'template_path': 'configs',  # 模版文件路径
            'template_id_as_name': '',  # 模版标识映射名(仅single可用), 如果不设置代表不映射
            'config_route': 'configs',  # 模版插入的yaml路径, 多级使用/分隔, 如果通过位置选择使用[位置]的方式表示
            'ref_para_route': 'base_config/center_type',  # 模版配置id对应的配置项yaml路径, 多级使用/分隔, 如果通过位置选择使用[位置]的方式表示
            'i18n_message': 'Select config center adapter: '  # 输入提示的i18n信息
        },
        # 集群适配器配置模版
        'clusters': {
            'type': 'single',
            'file_name': 'application.yaml',
            'template_path': 'clusters',
            'config_route': 'clusters',
            'ref_para_route': 'base_config/cluster_adapter',
            'i18n_message': 'Select cluster adapter: '
        },
        # 默认web服务器模版
        'web_servers': {
            'type': 'single',
            'file_name': 'application.yaml',
            'template_path': 'web_servers',
            'config_route': 'web_servers',
            'ref_para_route': 'base_config/default_web_server',
            'i18n_message': 'Select web server adapter: '
        },
        # 服务端报文格式转换插件模版
        'server_formaters': {
            'type': 'list',
            'file_name': 'application.yaml',
            'template_path': 'server_formaters',
            'config_route': 'server_formaters',
            'ref_para_route': 'web_servers[0]/server_formaters',
            'i18n_message': 'Select server formater adapters (multiple select): '
        },
        # 服务注册中心插件模版
        'namings': {
            'type': 'single',
            'file_name': 'application.yaml',
            'template_path': 'namings',
            'config_route': 'namings',
            'ref_para_route': 'base_config/naming',
            'i18n_message': 'Select naming adapter: '
        },
        # 链路追踪插件模版
        'opentracings': {
            'type': 'single',
            'file_name': 'application.yaml',
            'template_path': 'opentracings',
            'config_route': 'opentracings',
            'ref_para_route': 'base_config/tracer',
            'i18n_message': 'Select opentracing adapter: '
        },
        # 报文信息日志记录插件模版
        'inf_loggings': {
            'type': 'list',
            'file_name': 'application.yaml',
            'template_path': 'inf_loggings',
            'config_route': 'inf_loggings',
            'ref_para_route': '',
            'i18n_message': 'Select interface logging adapters (multiple select): '
        },
        # 请求报文信息检查插件模版
        'inf_checks': {
            'type': 'list',
            'file_name': 'application.yaml',
            'template_path': 'inf_checks',
            'config_route': 'inf_checks',
            'ref_para_route': '',
            'i18n_message': 'Select interface check adapters (multiple select): '
        },
        # 远程调用报文格式转换插件模版
        'caller_formaters': {
            'type': 'list',
            'file_name': 'application.yaml',
            'template_path': 'caller_formaters',
            'config_route': 'caller_formaters',
            'ref_para_route': 'base_config/caller_formaters',
            'i18n_message': 'Select caller formater adapters (multiple select): '
        },
        # NoSQL数据库插件
        'nosql_dbs': {
            'type': 'single',
            'file_name': 'adapters.yaml',
            'template_path': 'nosql_dbs',
            'template_id_as_name': 'nosql_db',
            'config_route': 'adapters',
            'ref_para_route': '',
            'i18n_message': 'Select NoSQL db adapter: '
        },
        # 自定义适配器
        'adapters': {
            'type': 'list',
            'file_name': 'adapters.yaml',
            'template_path': 'adapters',
            'config_route': 'adapters',
            'ref_para_route': '',
            'i18n_message': 'Select extend adapters (multiple select): '
        },
    }

    #############################
    # 构造函数
    #############################
    def __init__(self) -> None:
        """
        微服务环境处理的工具处理类
        """
        # 参数管理
        self.app_base_path = os.getcwd()  # 应用目录
        self.template_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.path.pardir, 'template')
        )

        # 创建公共的动态库管理模块
        _lib_plugins_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir, 'plugins')
        )
        self.lib_loader = DynamicLibManager(_lib_plugins_path)  # 系统动态库加载对象
        self.adapter_manager = AdapterManager(
            os.path.join(self.app_base_path, 'plugins'), self.app_base_path, lib_loader=self.lib_loader
        )

    #############################
    # 处理函数
    #############################
    def set_base_path(self, base_path: str):
        """
        设置应用目录

        @param {str} base_path - 应用目录
        """
        # 设置基础目录
        _base_path = os.path.abspath(os.path.join(os.getcwd(), base_path))
        if os.path.exists(_base_path):
            self.app_base_path = _base_path
        else:
            raise FileNotFoundError('path [%s] not exists!' % _base_path)

        # 重新设置适配器管理对象
        self.adapter_manager.remove_all()
        self.adapter_manager.plugins_path = os.path.join(self.app_base_path, 'plugins')
        self.adapter_manager.base_path = self.app_base_path

    def create_app(self, base_path: str = None, config: OrderedDict = {}):
        """
        创建应用配置

        @param {str} base_path=None - 指定要创建的路径
        @param {OrderedDict} config={} - 配置信息字典, 需注意按顺序传入以下值:
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
        """
        # 要处理的路径
        _base_path = base_path
        if _base_path is None:
            _base_path = self.app_base_path

        # 首先创建目录
        for _path in ['config', 'logs', 'plugins', 'services', 'tasks']:
            _real_path = os.path.abspath(os.path.join(_base_path, _path))
            FileTool.create_dir(_real_path, exist_ok=True)

        # 复制i18n文件
        _i18n_path = os.path.abspath(os.path.join(_base_path, 'i18n'))
        _i18n_template_path = os.path.abspath(os.path.join(self.template_path, 'i18n'))
        FileTool.copy_all_with_path(
            src_path=_i18n_template_path, dest_path=_i18n_path, regex_str=r'.*\.json$',
            exist_ok=True
        )

        # 复制基础配置文件
        _config_path = os.path.abspath(os.path.join(_base_path, 'config'))
        _config_template_path = os.path.abspath(os.path.join(self.template_path, 'config'))
        FileTool.copy_all_with_path(
            src_path=_config_template_path, dest_path=_config_path, regex_str=r'.*\.yaml$',
            exist_ok=True
        )

        # 支持处理的配置文件映射字典
        _yaml_configs = {}

        # 处理配置模版
        for _key, _val in config.items():
            _template_config = self.TEMPLATE_CONFIG.get(_key, None)
            if _template_config is None:
                raise ModuleNotFoundError('Template config not found')

            if _template_config['type'] in ('single', 'list'):
                # 单节点配置模版
                _yaml_config_obj = self._get_yaml_config_obj(
                    _yaml_configs, _template_config['file_name'], _config_path
                )

                if _template_config['type'] == 'list':
                    _template_list = _val
                else:
                    _template_list = [_val]

                for _template_id in _template_list:
                    # 映射名
                    _template_id_as_name = _template_id
                    if _template_config['type'] == 'single' and _template_config.get('template_id_as_name', '') != '':
                        _template_id_as_name = _template_config['template_id_as_name']

                    # 遍历进行设置
                    _template_yaml_config_obj = self._get_template_yaml_config_obj(
                        _template_id, _template_config['template_path'], _config_template_path
                    )
                    # 设置模版
                    _yaml_config_obj.set_value(
                        '%s/%s' % (_template_config['config_route'], _template_id_as_name),
                        _template_yaml_config_obj.yaml_config[_template_id],
                        auto_create=True
                    )

                # 设置关联配置值
                if _template_config.get('ref_para_route', '') != '':
                    _yaml_config_obj.set_value(
                        _template_config['ref_para_route'], _val
                    )
            else:
                raise ModuleNotFoundError('Template config type error: %s' % _template_config['type'])

        # 保存配置文件
        for _yaml_obj in _yaml_configs.values():
            _yaml_obj.save()

    #############################
    # 辅助函数
    #############################
    def get_template_config_info(self, name: str) -> dict:
        """
        获取模版配置的信息

        @param {str} name - 模版配置名

        @returns {dict} - 信息字典
        """
        _config = self.TEMPLATE_CONFIG.get(name, None)
        if _config is None:
            raise ModuleNotFoundError('Template config not found')

        _info = {
            'type': _config['type'],
            'i18n_message': _config['i18n_message']
        }

        # 获取可选信息
        _config_template_path = os.path.abspath(os.path.join(self.template_path, 'config'))
        _options = FileTool.get_filelist(
            path=os.path.join(_config_template_path, _config['template_path']),
            regex_str=r'.*\.yaml$', is_fullname=False
        )
        for _index in range(len(_options)):
            _options[_index] = _options[_index][0: -5]

        _info['options'] = _options

        return _info

    #############################
    # 内部函数
    #############################
    def _get_yaml_config_obj(self, yaml_configs: dict, file_name: str, config_path: str) -> SimpleYaml:
        """
        从配置对象字典获取已打开的配置对象

        @param {dict} yaml_configs - 已打开的配置字典
        @param {str} file_name - 配置文件名
        @param {str} config_path - 配置文件路径

        @returns {SimpleYaml} - yaml配置对象
        """
        _yaml_config_obj: SimpleYaml = yaml_configs.get(file_name, None)
        if _yaml_config_obj is None:
            _yaml_config_obj = SimpleYaml(
                os.path.join(config_path, file_name), obj_type=EnumYamlObjType.File,
                encoding='utf-8'
            )
            yaml_configs[file_name] = _yaml_config_obj

        return _yaml_config_obj

    def _get_template_yaml_config_obj(self, id: str, template_path: str, config_path: str) -> SimpleYaml:
        """
        获取模版的yaml配置对象

        @param {str} id - 模版id
        @param {str} template_path - 模版路径
        @param {str} config_path - 配置文件路径

        @returns {SimpleYaml} - yaml配置对象
        """
        return SimpleYaml(
            os.path.join(config_path, template_path, '%s.yaml' % id),
            obj_type=EnumYamlObjType.File, encoding='utf-8'
        )


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # _tool = EnvTools()
    # _tool.create_app(
    #     base_path='/Users/lhj/opensource/HiveNetMicro-Ser-User/HiveNetMicro-Ser-User/back',
    #     config={
    #         'configs': 'nacos',
    #         'clusters': 'redis_cluster',
    #         'web_servers': 'sanic',
    #         'server_formaters': ['SanicCommonFormater', 'SanicHiveNetStdIntfFormater'],
    #         'namings': 'nacos',
    #         'opentracings': 'jaeger',
    #         'inf_loggings': ['CommonInfLogging', 'ServiceRemoteCallInfLogging'],
    #         'caller_formaters': ['AioHttpCommonCallerFormater', 'AioHttpHiveNetStdIntfCallerFormater', 'HttpCommonCallerFormater'],
    #         'nosql_dbs': 'mongo'
    #     }
    # )
    pass
