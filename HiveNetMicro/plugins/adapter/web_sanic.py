#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
web服务适配器的Sanic实现

@module web_sanic
@file web_sanic.py
"""
import os
import sys
from typing import Callable
from inspect import isawaitable
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetSimpleSanic.server import SanicServer
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.interface.adapter.web import WebAdapter


class SanicWebAdapter(WebAdapter):
    """
    web服务适配器的Sanic实现
    """

    #############################
    # 公共属性
    #############################
    @property
    def native_app(self):
        """
        返回原生的服务app实例, 用于使用第三方容器启动
        @property {Any}
        """
        return self._sanic_server.native_app

    #############################
    # 公共函数
    #############################
    async def start(self):
        """
        按同步方式启动服务(阻断线程)
        """
        try:
            # 直接启动阻断线程
            await AsyncTools.async_run_coroutine(
                self._sanic_server.start(is_asyn=False)
            )
        except:
            # 捕获到异常终止, 执行 before_server_stop 函数
            await AsyncTools.async_run_coroutine(self.before_server_stop())
            raise

    async def add_service(self, handler: Callable, service_uri: str, service_config: dict = {}):
        """
        添加请求处理服务

        @param {Callable} handler - 请求处理函数
            函数格式固定为: func(request: dict, *args, **kwargs) { return (resp_msg: dict, resp_headers: dict) }
            request的格式固定为: {network: dict, headers: dict, msg: dict}
            返回信息如果为数组, 则第一个为返回信息, 第二个返回为报文头设置对象；如果为单一对象, 则代表不设置报文头(None)
        @param {str} service_uri - 服务标识路径
            注: 对于Sanic服务则为路由uri
        @param {dict} service_config={} - 服务配置字典
            注1: 为services.yaml配置中services下服务配置标识的完整配置字典
            注2: web_server中支持的Web服务器自有配置参数如下:
                methods {list[str]} - 服务支持的http方法清单, 默认为['GET']
        """
        # 新定义增加了修饰符的处理函数
        @self._wrap_request_handler(service_uri, service_config)
        async def wraped_handler(*args, **kwargs):
            _resp = handler(*args, **kwargs)
            if isawaitable(_resp):
                _resp = await _resp
            return _resp

        await AsyncTools.async_run_coroutine(
            self._sanic_server.add_service(
                service_uri, wraped_handler,
                methods=service_config.get('web_server', {}).get(self.web_server_id, {}).get('methods', ['GET'])
            )
        )

    #############################
    # 内部函数
    #############################
    def _self_init(self):
        """
        继承类的个性初始化函数
        注: 可在该函数中处理继承类的自定义处理逻辑
        """
        # 修改参数
        if self.init_config.get('run_config', None) is None:
            self.init_config['run_config'] = {}
        self.init_config['run_config']['host'] = self.host
        self.init_config['run_config']['port'] = self.port

        # 创建真正的服务
        self._sanic_server = SanicServer(
            self.app_name, server_config=self.init_config,
            after_server_start=self.after_server_start, before_server_stop=self.before_server_stop,
            logger=self.logger
        )
