#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
配置中心标准模块

@module config_center
@file config_center.py
"""
import os
import sys
import json
import copy
from HiveNetCore.xml_hivenet import EnumXmlObjType, SimpleXml
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.import_tool import DynamicLibManager
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.utils.yaml import YamlConfig
from HiveNetMicro.interface.adapter.config import ConfigAdapter


class ConfigCenter(object):
    """
    配置中心
    """

    def __init__(self, config_path: str, plugins_path: str, sys_lib_loader: DynamicLibManager) -> None:
        """
        配置中心构造函数

        @param {str} config_path - 配置文件所在路径
        @param {str} plugins_path - 插件文件所在路径
        @param {DynamicLibLoader} sys_lib_loader - 系统动态库加载对象
        """
        # 参数设置
        self.config_path = config_path
        self.plugins_path = plugins_path
        self.config_file = os.path.join(self.config_path, 'configCenter.yaml')

        # 获取配置中心的配置
        _config = YamlConfig(file=self.config_file).yaml_config
        self.base_config: dict = _config['base_config']

        if self.base_config['env'] is not None and self.base_config['env'] != '':
            # 命名空间增加后缀处理
            self.base_config['namespace'] = '%s-%s' % (self.base_config['namespace'], self.base_config['env'])
        else:
            self.base_config['env'] = ''

        if self.base_config['prefix'] is None:
            self.base_config['prefix'] = ''

        self.data_file_mapping: dict = _config['data_file_mapping']
        self.centerConfig = None if self.base_config['center_type'] is None else _config['configs'][self.base_config['center_type']]

        # 缓存的配置信息, 以data_id作为唯一标识
        self._cache = {
            'text': {},  # 文本类型的配置
            'dict': {}  # 字典类型的配置
        }

        # 加载注册中心适配器
        self._adapter = None  # 注册中心适配器
        if self.centerConfig is not None:
            # 处理命名空间
            if self.centerConfig['plugin']['init_kwargs'].get('namespace', None) is None:
                self.centerConfig['plugin']['init_kwargs']['namespace'] = self.base_config['namespace']

            # 初始化插件
            self._adapter: ConfigAdapter = sys_lib_loader.load_by_config(
                self.centerConfig['plugin'], self.plugins_path
            )

    #############################
    # 属性
    #############################
    @property
    def env(self):
        """
        获取当前环境配置
        @property {str}
        """
        return self.base_config['env']

    @property
    def namespace(self):
        """
        获取当前环境的默认命名空间
        @property {str}
        """
        return self.base_config['namespace']

    @property
    def prefix(self):
        return self.base_config['prefix']

    #############################
    # 公共方法
    #############################
    async def get_config(self, data_id: str, group: str = None, timeout: int = None) -> str:
        """
        获取指定配置信息

        @param {str} data_id - 配置ID
        @param {str} group=None - 配置所属分组
        @param {int} timeout=None - 超时时间, 单位为毫秒

        @returns {str} - 返回配置信息的字符串
        """
        if self._adapter is None:
            # 从本地文件获取
            return self._read_file(data_id)
        else:
            # 通过配置中心获取
            _timeout = self.base_config['default_timeout'] if timeout is None else timeout
            _prefixed_data_id = self._get_prefixed_data_id(data_id)
            config_str = await AsyncTools.async_run_coroutine(
                self._adapter.get_config(
                    _prefixed_data_id, group, timeout=_timeout
                )
            )

            if config_str is None:
                if self.base_config['not_existed'] == 'create':
                    # 通过本地配置设置配置中心设置
                    config_str = self._read_file(data_id)
                    await AsyncTools.async_run_coroutine(
                        self.set_config(
                            data_id, config_str, group=group, content_type=self._get_config_type(data_id),
                            timeout=_timeout
                        )
                    )
                else:
                    # 直接抛出异常
                    raise FileNotFoundError('[dataid: %s] [group: %s] not found in config center' % (_prefixed_data_id, group))

            return config_str

    async def set_config(self, data_id: str, content: str, group: str = None, content_type: str = 'text',
                timeout: int = None):
        """
        设置指定的配置信息

        @param {str} data_id - 配置ID
        @param {str} content - 要设置的内容
        @param {str} group=None - 配置所属分组
        @param {str} content_type='text' - 内容类型, 支持:
            text - 文本
            xml - xml格式内容
            json - json格式的内容
            yaml - yaml格式
        @param {int} timeout=3000 - 超时时间, 单位为毫秒
        """
        if self._adapter is None:
            # 设置本地文件
            self._write_file(data_id, content)
        else:
            _timeout = self.base_config['default_timeout'] if timeout is None else timeout
            _prefixed_data_id = self._get_prefixed_data_id(data_id)
            await AsyncTools.async_run_coroutine(
                self._adapter.set_config(
                    _prefixed_data_id, content, group=group, content_type=content_type, timeout=_timeout
                )
            )

    async def get_config_cached(self, data_id: str, group: str = None, timeout: int = None,
            content_type: str = 'text'):
        """
        从管理的缓存中获取配置

        @param {str} data_id - 配置ID
        @param {str} group=None - 配置所属分组
        @param {int} timeout=None - 超时时间, 单位为毫秒
        @param {str} content_type='text' - 配置的数据类型
            text - 文本
            xml - xml格式内容
            json - json格式的内容
            yaml - yaml格式

        @returns {str|dict} - 如果数据类型为text, 则返回str；其他类型返回dict
        """
        _type = 'text' if content_type == 'text' else 'dict'
        config = self._cache[_type].get(data_id, None)
        if config is None:
            # 重新获取
            _timeout = self.base_config['default_timeout'] if timeout is None else timeout
            config_str = await AsyncTools.async_run_coroutine(
                self.get_config(data_id, group=group, timeout=_timeout)
            )
            if content_type == 'yaml':
                config = self.yaml_to_dict(config_str)
            elif content_type == 'json':
                config = self.json_to_dict(config_str)
            elif content_type == 'xml':
                config = self.xml_to_dict(config_str)
            else:
                # 文本格式
                config = config_str

            # 放入缓存
            self._cache[_type][data_id] = config

        # 返回复制对象, 避免修改影响到缓存的对象
        return copy.deepcopy(config)

    def set_logger(self, logger):
        """
        设置配置中心的日志对象

        @param {Logger} logger - 要设置的日志对象
        """
        if self._adapter is not None:
            self._adapter.set_logger(logger)

    #############################
    # 配置格式转换
    #############################
    def yaml_to_dict(self, config_str: str) -> dict:
        """
        将yaml配置转换为字典对象

        @param {str} config_str - 配置字符串

        @returns {dict} - 转换后的配置字典
        """
        return YamlConfig(yaml_str=config_str).yaml_config

    def dict_to_yaml(self, config_dict: dict) -> str:
        """
        将配置字典转换为yaml字符串

        @param {dict} config_dict - 配置字典

        @returns {str} - 转换后的yaml配置字符串
        """
        return YamlConfig.to_yaml_str(config_dict)

    def json_to_dict(self, config_str: str) -> dict:
        """
        将json配置转换为字典对象

        @param {str} config_str - 配置字符串

        @returns {dict} - 转换后的配置字典
        """
        return json.loads(config_str)

    def dict_to_json(self, config_dict: dict) -> str:
        """
        将配置字典转换为json字符串

        @param {dict} config_dict - 配置字典

        @returns {str} - 转换后的json配置字符串
        """
        return json.dumps(config_dict, ensure_ascii=False, indent=2)

    def xml_to_dict(self, config_str: str) -> dict:
        """
        将xml配置转换为字典对象
        注: 自动去掉根节点root

        @param {str} config_str - 配置字符串

        @returns {dict} - 转换后的配置字典
        """
        config_dict = SimpleXml(config_str, obj_type=EnumXmlObjType.String).to_dict()
        return next(iter(config_dict.values()))

    def dict_to_xml(self, config_dict: dict, root_name: str = 'root') -> str:
        """
        将配置字典转换为xml字符串

        @param {dict} config_dict - 配置字典
        @param {str} root_name='root' - 根节点名称设置

        @returns {str} - 转换后的json配置字符串
        """
        xml_doc = SimpleXml('<%s></%s>' % (root_name, root_name), obj_type=EnumXmlObjType.String)
        xml_doc.set_value_by_dict('', config_dict)
        return xml_doc.to_string(xml_declaration=True)

    #############################
    # 内部方法
    #############################
    def _get_config_type(self, data_id: str) -> str:
        """
        获取指定配置的类型

        @param {str} data_id - 配置ID

        @returns {str} - 返回配置类型, 如找不到设置返回text
        """
        _type = 'text'
        if data_id in self.data_file_mapping.keys():
            _type = self.data_file_mapping[data_id].get('type', None)
            if _type is None:
                _type = 'text'

        return _type

    def _get_prefixed_data_id(self, data_id: str) -> str:
        """
        获取添加了前缀的data_id

        @param {str} data_id - @param {str} data_id - 配置ID

        @returns {str} - 添加了前缀的data_id
        """
        if self.base_config['prefix'] != '':
            return '%s-%s' % (self.base_config['prefix'], data_id)
        else:
            return data_id

    def _get_loacl_file(self, data_id: str) -> str:
        """
        获取data_id对应的配置文件路径

        @param {str} data_id - 配置ID

        @returns {str} - 配置文件完整路径
        """
        # 通过映射获取真实文件名
        if data_id in self.data_file_mapping.keys():
            path = os.path.join(self.config_path, self.data_file_mapping[data_id]['local_file'])
        else:
            path = os.path.join(self.config_path, data_id)

        # 获取绝对路径
        path = os.path.abspath(path)

        # 判断是否要加上环境信息
        if self.env is not None and self.env != '':
            _path, _filename = os.path.split(path)
            _dot_index = _filename.rfind('.')
            if _dot_index == -1:
                _filename = '%s-%s' % (_filename, self.env)
            else:
                _filename = '%s-%s%s' % (_filename[0: _dot_index], self.env, _filename[_dot_index:])

            # 判断是否使用带环境信息的配置
            if not self.base_config.get('ignore_env_when_file_not_existed', False) or os.path.exists(os.path.join(_path, _filename)):
                path = os.path.join(_path, _filename)

        # 返回结果
        return path

    def _read_file(self, data_id: str) -> str:
        """
        读取本地配置文件配置字符串

        @param {str} data_id - 配置ID

        @returns {str} - 配置字符串
        """
        file = self._get_loacl_file(data_id)
        with open(file, 'r', encoding='utf-8') as fileio:
            file_str = fileio.read()

        return file_str

    def _write_file(self, data_id: str, content: str):
        """
        向文件写入配置文件字符串

        @param {str} data_id - 配置ID
        @param {str} content - 要写入的配置内容
        """
        file = self._get_loacl_file(data_id)
        with open(file, 'w', encoding='utf-8') as fileio:
            fileio.write(content)
