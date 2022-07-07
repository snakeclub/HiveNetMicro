#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
接口报文信息日志记录适配器

@module inf_logging
@file inf_logging.py
"""
import os
import sys
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.adapter_base import AdapterBaseFw
from HiveNetMicro.core.global_manager import GlobalManager
from HiveNetMicro.core.logger_manager import LoggerManager


class InfLoggingAdapter(AdapterBaseFw):
    """
    接口报文信息日志记录适配器
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
        return 'InfLogging'

    #############################
    # 构造函数
    #############################
    def __init__(self, init_config: dict = {}, logger_id: str = None):
        """
        构造函数

        @param {dict} init_config={} - 初始化参数, 根据不同的实现定义有所不同
        @param {str} logger_id=None - 日志对象标识, 可以选择application.yaml配置中的其中一个日志对象
        """
        self.init_config = init_config

        # 日志对象
        _logger_manager: LoggerManager = GlobalManager.GET_SYS_LOGGER_MANAGER()
        if _logger_manager is None:
            _logger_manager = LoggerManager('')
        self.logger = _logger_manager.get_logger(logger_id, none_with_default_logger=True)

        # 实现类自定义初始化函数
        self._self_init()

    #############################
    # 需实现类重载的公共函数
    #############################
    async def log(self, side: str, inf_type: str, std_inf: dict, service_config: dict = {}):
        """
        进行接口信息的日志登记
        注: 也可以支持定义为异步接口

        @param {str} side - 报文所在侧, S-服务端(Server), C-客户端(Client)
        @param {str} inf_type - 接口类型, R-请求报文(Request), B-响应报文(Back)
        @param {dict} std_inf - 标准请求/响应接口对象
        @param {dict} service_config={} - 接口对应的服务配置
        """
        raise NotImplementedError()

    #############################
    # 需要实现类继承的内部函数
    #############################
    def _self_init(self):
        """
        实现类继承实现的初始化函数
        """
        pass
