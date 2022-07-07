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
from HiveNetCore.utils.import_tool import DynamicLibManager
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.global_manager import GlobalManager


class AdapterManager(object):
    """
    通用的适配器管理模块
    """

    def __init__(self, plugins_path: str) -> None:
        """
        构造函数

        @param {str} plugins_path - 插件路径
        """
        self.plugins_path = plugins_path
        self.lib_loader: DynamicLibManager = GlobalManager.GET_SYS_LIB_LOADER()
        # 适配器实例缓存字典, 格式为 {'适配器类型': {'适配器id': 适配器实例对象}}
        self._adapters = {}

    def load_adapter(self, adapter_type: str, adapter_id: str, adapter_config: dict) -> Any:
        """
        装载适配器

        @param {str} adapter_type - 适配器类型
        @param {str} adapter_id - 适配器id
        @param {dict} adapter_config - 适配器配置

        @returns {Any} - 装载后的适配器实例对象
        """
        _adapter = self.get_adapter(adapter_type, adapter_id)
        if _adapter is None:
            # 需要重新装载
            _adapter = self.lib_loader.load_by_config(
                adapter_config, self.plugins_path
            )
            # 放入缓存字典
            if self._adapters.get(adapter_type, None) is None:
                self._adapters[adapter_type] = {}

            self._adapters[adapter_type][adapter_id] = _adapter

        return _adapter

    def get_adapter(self, adapter_type: str, adapter_id: str) -> Any:
        """
        获取报文转换适配器

        @param {str} adapter_type - 适配器类型
        @param {str} adapter_id - 适配器id

        @returns {Any} - 返回适配器实例, 如果获取不到返回None
        """
        return self._adapters.get(adapter_type, {}).get(adapter_id, None)
