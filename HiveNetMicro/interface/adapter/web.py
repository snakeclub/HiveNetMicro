#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
web服务适配器

@module web
@file web.py
"""
import os
import sys
from functools import wraps
import traceback
from typing import Callable
from inspect import isawaitable
from HiveNetCore.utils.run_tool import AsyncTools
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.adapter_base import AdapterBaseFw
from HiveNetMicro.core.global_manager import GlobalManager
from HiveNetMicro.core.logger_manager import LoggerManager
from HiveNetMicro.interface.adapter.formater import RouterTools


class WebAdapter(AdapterBaseFw):
    """
    web服务适配器
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
        return 'Web'

    #############################
    # 构造函数
    #############################
    def __init__(
        self, web_server_id: str, app_name: str, host: str, port: int, init_config: dict,
        logger_id: str = None, formaters: list = [], after_server_start: Callable = None,
        before_server_stop: Callable = None
    ):
        """
        构造函数

        @param {str} web_server_id - 当前web服务器插件标识
        @param {str} app_name - web服务的app名
        @param {str} host - 绑定的主机地址
        @param {int} port - 服务监听的端口
        @param {dict} init_config - web服务的初始化参数, 不同的实现定义会有所不同
        @param {str} logger_id=None - 日志对象标识, 可以选择application.yaml配置中的其中一个日志对象
        @param {list} formaters=[] - web服务支持的报文转换插件清单(转换插件标识名清单)
        @param {callable} after_server_start=None - 服务启动完成后执行的函数, 无入参
        @param {callable} before_server_stop=None - 服务关闭前执行的函数, 无入参
            注意: after_server_start, before_server_stop均为异步函数, 如果服务不支持异步函数的情况需通过异步工具转化为同步函数进行处理
        """
        # 参数处理
        self.web_server_id = web_server_id
        self.app_name = app_name
        self.host = host
        self.port = port
        self.init_config = init_config
        self.formaters = formaters
        self.adapter_manager = GlobalManager.GET_SYS_ADAPTER_MANAGER()
        self.after_server_start = after_server_start
        self.before_server_stop = before_server_stop

        # 日志对象
        _logger_manager: LoggerManager = GlobalManager.GET_SYS_LOGGER_MANAGER()
        if _logger_manager is None:
            _logger_manager = LoggerManager('')
        self.logger = _logger_manager.get_logger(logger_id, none_with_default_logger=True)

        # 继承类的个性初始化函数
        self._self_init()

    #############################
    # 公共属性
    #############################
    @property
    def name(self):
        """
        获取服务应用名
        @property {str}
        """
        return self.app_name

    @property
    def native_app(self):
        """
        返回原生的服务app实例, 用于使用第三方容器启动
        @property {Any}
        """
        raise NotImplementedError()

    #############################
    # 公共函数
    #############################
    def start(self):
        """
        按同步方式启动服务(阻断线程)
        (可以为同步也可以为异步函数)
        """
        raise NotImplementedError()

    def add_service(self, handler: Callable, service_uri: str, service_config: dict = {}):
        """
        添加请求处理服务
        (可以为同步也可以为异步函数)

        @param {Callable} handler - 请求处理函数
            函数格式固定为: func(request: dict, *args, **kwargs) { return (resp_msg: dict, resp_headers: dict) }
            request的格式固定为: {network: dict, headers: dict, msg: dict}
            返回信息如果为数组, 则第一个为返回信息, 第二个返回为报文头设置对象；如果为单一对象, 则代表不设置报文头(None)
        @param {str} service_uri - 服务标识路径
            注: 对于Http服务则为路由uri, 建议遵循Sanic标准
        @param {dict} service_config={} - 服务配置字典
            注: 为services.yaml配置中services下服务配置标识的完整配置字典
        """
        raise NotImplementedError()

    #############################
    # 内部函数
    #############################
    def _self_init(self):
        """
        继承类的个性初始化函数
        注: 可在该函数中处理继承类的自定义处理逻辑
        """
        return

    def _wrap_request_handler(self, service_uri: str, service_config: dict):
        """
        通用的请求处理函数的修饰符
        注: 利用wrap处理通用的请求和响应标准化转换

        @param {str} service_uri - 服务标识路径
        @param {dict} service_config - 服务配置字典
            注: 为services.yaml配置中services下服务配置标识的完整配置字典
        """
        def decorator(f):
            @wraps(f)
            async def decorated_function(*args, **kwargs):
                # 获取请求对象, 请求数据标准化处理
                _real_args = list(args)
                _web_request = _real_args.pop(0)
                _formater = self.adapter_manager.get_adapter(
                    'formater_server', service_config.get('formater', None)
                )
                _inf_logging = self.adapter_manager.get_adapter(
                    'inf_logging', service_config.get('inf_logging', None)
                )
                try:
                    if _formater is None:
                        _std_request = _web_request
                        _query = RouterTools.get_query_dict(
                            _std_request.query_string,
                            value_trans_mapping=service_config.get('kv_type_trans_mapping', None)
                        )
                    else:
                        _std_request = _formater.format_request(
                            _web_request,
                            value_trans_mapping=service_config.get('kv_type_trans_mapping', None)
                        )
                        _query = _std_request.get('network', {}).get('query', None)

                    # 处理kv入参
                    if _query is not None and len(_query) > 0:
                        kwargs.update(_query)

                    # 记录收到请求的日志信息
                    if _inf_logging is not None:
                        await AsyncTools.async_run_coroutine(
                            _inf_logging.log('S', 'R', _std_request, service_config=service_config)
                        )

                    # 执行请求处理函数
                    _std_response = f(_std_request, *_real_args, **kwargs)
                    if isawaitable(_std_response):
                        _std_response = await _std_response

                    # 返回数据标准化处理
                    if _formater is None:
                        _web_response = _std_response
                    else:
                        _web_response = _formater.generate_web_response(_std_response)

                    # 记录响应的日志信息
                    if _inf_logging is not None:
                        await AsyncTools.async_run_coroutine(
                            _inf_logging.log('S', 'B', _std_response, service_config=service_config)
                        )

                    # 返回结果
                    return _web_response
                except Exception as e:
                    self.logger.error('service handler exception: %s' % traceback.format_exc())

                    if _formater is None:
                        raise
                    else:
                        _std_response = _formater.format_exception(
                            _web_request, e, service_config=service_config, is_std_request=False
                        )
                        _web_response = _formater.generate_web_response(_std_response)

                        # 记录异常情况响应的日志信息
                        if _inf_logging is not None:
                            await AsyncTools.async_run_coroutine(
                                _inf_logging.log('S', 'B', _std_response, service_config=service_config)
                            )

                        return _web_response

            return decorated_function
        return decorator
