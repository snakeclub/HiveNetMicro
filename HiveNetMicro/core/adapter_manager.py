#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
通用的适配器管理模块

@module adapter_manager
@file adapter_manager.py
"""
import os
import sys
from typing import Any
from HiveNetCore.utils.value_tool import ValueTool
from HiveNetCore.utils.import_tool import DynamicLibManager
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.global_manager import GlobalManager
from HiveNetMicro.core.logger_manager import LoggerManager


class AdapterManager(object):
    """
    通用的适配器管理模块
    """

    def __init__(self, plugins_path: str, base_path: str, lib_loader: DynamicLibManager = None) -> None:
        """
        构造函数

        @param {str} plugins_path - 插件路径(应用目录的插件路径)
            注: 框架自有插件目录在DynamicLibManager中已设置, 因此可以同时支持框架插件和自有插件的搜索
        @param {str} base_path - 应用基础路径, 用于替换装载配置中的文件路径
        @param {DynamicLibManager} lib_loader=None - 动态库管理对象, 如果不传则自动获取框架的系统动态库管理对象
        """
        self.plugins_path = plugins_path
        self.base_path = base_path

        # 动态库管理对象
        self.lib_loader = lib_loader
        if self.lib_loader is None:
            self.lib_loader: DynamicLibManager = GlobalManager.GET_SYS_LIB_LOADER()

        # 日志管理对象
        self.logger_manager: LoggerManager = GlobalManager.GET_SYS_LOGGER_MANAGER()

        # 适配器实例缓存字典, 格式为 {'适配器类型': {'适配器id': 适配器实例对象}}
        self._adapters = {}

    def load_adapter(self, adapter_id: str, **kwargs) -> Any:
        """
        装载适配器

        @param {str} adapter_id - 适配器id
        @param {str} adapter_type='unknown' - 适配器类型
        @param {dict} plugin={} - 适配器配置
        @param {list} convert_relative_paths=None - 需要转换为应用路径相对路径的配置项路径清单
            注: 路径从plugin下一级开始, 例如"init_args[1]"或"init_kwargs/para1/sub_para"
        @param {list} convert_logger_paths=None - 要替换的日志对象配置路径清单
            注: 路径从plugin下一级开始, 例如"init_args[1]"或"init_kwargs/para1/sub_para"

        @returns {Any} - 装载后的适配器实例对象
        """
        _adapter_type = kwargs.get('adapter_type', 'unknown')
        _adapter = self.get_adapter(_adapter_type, adapter_id)
        if _adapter is None:
            # 需要重新装载
            _plugin = kwargs.get('plugin')

            # 先判断是否有相对路径替换的情况
            _convert_relative_paths = kwargs.get('convert_relative_paths', None)
            if _convert_relative_paths is not None:
                for _path in _convert_relative_paths:
                    _src_path = ValueTool.get_dict_value_by_path(_path, _plugin)
                    if _src_path is not None:
                        ValueTool.set_dict_value_by_path(
                            _path, _plugin, os.path.abspath(os.path.join(
                                self.base_path, _src_path
                            ))
                        )

            # 判断是否有日志对象替换的情况
            _convert_logger_paths = kwargs.get('convert_logger_paths', None)
            if _convert_logger_paths is not None:
                for _path in _convert_logger_paths:
                    _src_logger = ValueTool.get_dict_value_by_path(_path, _plugin)
                    if _src_logger is not None:
                        _logger = None if self.logger_manager is None else self.logger_manager.get_logger(
                            _src_logger
                        )
                        ValueTool.set_dict_value_by_path(_path, _plugin, _logger)

            # 装载插件
            _adapter = self.lib_loader.load_by_config(
                _plugin, self.plugins_path
            )
            # 放入缓存字典
            if self._adapters.get(_adapter_type, None) is None:
                self._adapters[_adapter_type] = {}

            self._adapters[_adapter_type][adapter_id] = _adapter

        return _adapter

    def get_adapter(self, adapter_type: str, adapter_id: str) -> Any:
        """
        获取适配器

        @param {str} adapter_type - 适配器类型
        @param {str} adapter_id - 适配器id

        @returns {Any} - 返回适配器实例, 如果获取不到返回None
        """
        return self._adapters.get(adapter_type, {}).get(adapter_id, None)

    def remove_adapter(self, adapter_type: str, adapter_id: str):
        """
        移除适配器
        注: 只是从管理清单中移除, 对此前获取到的适配器对象无影响

        @param {str} adapter_type - 适配器类型
        @param {str} adapter_id - 适配器id
        """
        self._adapters.get(adapter_type, {}).pop(adapter_id, None)

    def remove_all(self):
        """
        移除所有适配器
        注: 只是从管理清单中移除, 对此前获取到的适配器对象无影响
        """
        self._adapters.clear()
