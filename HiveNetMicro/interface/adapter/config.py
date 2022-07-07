#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
接入配置中心的适配器

@module config_adapter
@file config_adapter.py
"""
import os
import sys
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.adapter_base import AdapterBaseFw


class ConfigAdapter(AdapterBaseFw):
    """
    接入配置中心的适配器接口
    """

    #############################
    # 适配器基础属性
    #############################
    @property
    def adapter_type(self) -> str:
        """
        适配器类型

        @property {str} - 指定适配器类型
        """
        return 'Config'

    #############################
    # 构造函数
    #############################
    def __init__(self, init_config: dict = {}, namespace: str = None) -> None:
        """
        构造函数

        @param {dict} init_config={} - 客户端连接配置(configCenter.yaml中特定类型配置中心设置中的client配置, 由各个适配器自定义)
        @param {str} namespace=None - 指定当前连接要设置的命名空间
        """
        raise NotImplementedError()

    #############################
    # 公共函数
    #############################
    async def get_config(self, data_id: str, group: str, timeout: float = 3.0) -> str:
        """
        获取指定配置信息

        @param {str} data_id - 配置ID
        @param {str} group - 配置所属分组
        @param {float} timeout=3.0 - 超时时间, 单位为秒

        @returns {str} - 返回配置信息的字符串, 如果配置不存在返回None
            注: 如果获取失败应抛出异常
        """
        raise NotImplementedError()

    async def set_config(self, data_id: str, content: str, group: str = None, content_type: str = 'text',
                timeout: float = 3.0) -> bool:
        """
        设置指定的配置信息

        @param {str} data_id - 配置ID
        @param {str} content - 要设置的内容
        @param {str} group=None - 配置所属分组
        @param {str} content_type='text' - 内容类型, 应支持:
            text - 文本
            xml - xml格式内容
            json - json格式的内容
            yaml - yaml格式
        @param {float} timeout=3.0 - 超时时间, 单位为秒

        @returns {bool} - 设置是否成功(失败不抛出异常)
        """
        raise NotImplementedError()

    async def remove_config(self, data_id: str, group: str = None, timeout: float = 3.0) -> bool:
        """
        删除置顶配置信息

        @param {str} data_id - 配置ID
        @param {str} group=None - 配置所属分组
        @param {float} timeout=3.0 - 超时时间, 单位为秒

        @returns {bool} - 执行是否成功(失败不抛出异常)
        """
        raise NotImplementedError()

    def set_logger(self, logger):
        """
        设置适配器的日志对象
        注: 日志对象初始化后进行设置

        @param {Logger} logger - 要设置的日志对象
        """
        return
