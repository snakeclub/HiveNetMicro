#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
接口报文信息日志记录适配器的通用实现

@module inf_logging_common
@file inf_logging_common.py
"""

import os
import sys
import json
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.interface.adapter.inf_logging import InfLoggingAdapter
from HiveNetMicro.core.global_manager import GlobalManager


class CommonInfLoggingAdapter(InfLoggingAdapter):
    """
    接口报文信息日志记录适配器的通用实现
    """

    #############################
    # 需实现类重载的公共函数
    #############################
    async def log(self, side: str, inf_type: str, std_inf: dict, service_config: dict = {}):
        """
        进行接口信息的日志登记

        @param {str} side - 报文所在侧, S-服务端(Server), C-客户端(Client)
        @param {str} inf_type - 接口类型, R-请求报文(Request), B-响应报文(Back)
        @param {dict} std_inf - 标准请求/响应接口对象
        @param {dict} service_config={} - 接口对应的服务配置
        """
        if side == 'S':
            # 服务端日志
            _log_msg = '[service:%s]%s:\n' % (
                service_config.get('service_name', ''),
                'get request' if inf_type == 'R' else 'back response'
            )
        else:
            # 客户端日志
            _log_msg = '[call service:%s]%s:\n' % (
                service_config.get('service_name', ''),
                'send request' if inf_type == 'R' else 'get response'
            )

        # 简单记录日志
        self.logger.info(
            '%s%s' % (_log_msg, json.dumps(std_inf, ensure_ascii=False, indent=2))
        )
