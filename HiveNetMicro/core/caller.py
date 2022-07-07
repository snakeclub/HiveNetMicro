#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
远程调用模块

@module caller
@file caller.py
"""
import os
import sys
import copy
from inspect import isawaitable
from typing import Any, Callable
from HiveNetCore.i18n import _, get_global_i18n, init_global_i18n
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.import_tool import DynamicLibManager
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.adapter_manager import AdapterManager
from HiveNetMicro.interface.adapter.naming import NamingAdapter
from HiveNetMicro.core.global_manager import GlobalManager


class RemoteCaller(object):
    """
    远程调用模块
    """

    def __init__(self, plugins_path: str, sys_lib_loader: DynamicLibManager, sys_adapter_manager: AdapterManager,
            global_config: dict = {}, namings_config: dict = {},
            default_naming_adapter: NamingAdapter = None):
        """
        远程调用模块

        @param {str} plugins_path - 插件路径
        @param {DynamicLibLoader} sys_lib_loader - 系统动态库加载对象
        @param {AdapterManager} sys_adapter_manager - 系统通用适配器管理对象
        @param {dict} global_config={} - 全局配置信息
            注: 当前类需要使用到的参数包括: namespace、cluster_name
        @param {dict} namings_config={} - 注册中心适配器配置清单
        @param {NamingAdapter} default_naming_adapter=None - 默认的注册中心适配器对象
        """
        # 兼容没有初始化i18n的情况
        if get_global_i18n() is None:
            init_global_i18n()

        # 获取公共对象
        self._sys_lib_loader = sys_lib_loader
        self._naming_config = namings_config
        self._plugins_path = plugins_path
        self._global_config = global_config

        # 通用适配器管理对象
        self.adapter_manager = sys_adapter_manager

        # 注册中心适配器
        self._default_naming = default_naming_adapter
        self._namings = dict()  # 自定义注册中心适配器的字典

        # 调用链适配器
        self._tracer = GlobalManager.GET_SYS_TRACER()

        # 可调用的远程服务登记, key为服务名, value为服务配置
        self._remote_services = dict()

        # 本地服务登记, key为服务名, value为服务配置
        self._local_services = dict()

    def add_remote_service(self, service_id: str, service_config: dict):
        """
        添加远程服务访问支持

        @param {str} service_id - 服务标识
        @param {dict} service_config - 服务配置信息, 固定信息如下:
            service_name {str} - 注册中心的服务名
            group_name {str} - 所属分组, 如不传则默认为'DEFAULT_GROUP'
            protocol {str} - 访问协议, 如果不传则自动从服务的metadata获取
            uri {str} - 访问服务的uri, 如果不传则自动从服务的metadata获取
            network {dict} - 默认网络协议参数字典, 如果不传则自动从服务的metadata获取
            headers {dict} - 默认的报文头设置字典, 如果不传则自动从服务的metadata获取
            local_call_first {bool} - 指定本地访问优先, 默认为True
            is_fixed_config {bool} - 是否固定参数(非本地实例, 但不从注册中心获取服务信息), 默认为False
            metadata {dict} - 服务元数据, is_fixed_config为True时可用
            ip {str} - 访问主机ip, is_fixed_config为True时应设置
            port {int} - 访问主机端口, is_fixed_config为True时应设置
            naming {str} - 注册中心适配器名(application.yaml中namings配置中的适配器), 不传代表使用系统默认的命名适配器
            formater {str} - 该服务使用的请求报文转换插件标识
            enable_tracer {bool} - 是否启用调用链, 默认为false
            tracer_inject_format {str} - 调用链上下文传递格式化类型, 默认为'http_headers'
        """
        if service_id in self._remote_services.keys():
            raise FileExistsError(_('Service id [$1] exists', service_id))

        # 添加服务信息到配置中
        self._remote_services[service_id] = {
            'service_name': None,
            'group_name': None,
            'protocol': None,
            'uri': None,
            'network': None,
            'headers': None,
            'local_call_first': True,
            'is_fixed_config': False,
            'metadata': {},
            'ip': None,
            'port': 80,
            'naming': None,
            'naming_subscribe_interval': 5.0,
            'formater': None,
            'enable_tracer': False
        }
        self._remote_services[service_id].update(
            copy.deepcopy(service_config)
        )

        # 处理注册中心适配器
        _naming_adapter = self._get_naming_adapter(self._remote_services[service_id]['naming'])

        # 设置服务订阅
        if _naming_adapter is not None:
            _naming_adapter.add_subscribe(
                self._remote_services[service_id]['service_name'],
                group_name=self._remote_services[service_id]['group_name'],
                interval=self._remote_services[service_id].get('naming_subscribe_interval', 5.0)
            )

    def remove_remote_service(self, service_id: str):
        """
        移除远程服务访问支持

        @param {str} service_id - 服务标识
        """
        _service_config = self._remote_services.pop(service_id, None)
        if _service_config is not None:
            _naming_adapter = self._get_naming_adapter(_service_config['naming'])

            # 移除订阅服务
            if _naming_adapter is not None:
                _naming_adapter.remove_subscribe(_service_config['service_name'])

    def add_local_service(self, service_id: str, handler: Callable, service_config: dict = {}):
        """
        添加本地服务访问支持

        @param {str} service_id - 服务标识
        @param {Callable} handler - 本地服务处理函数
        @param {dict} service_config - 本地服务配置
            service_name {str} - 注册中心的服务名
            group_name {str} - 所属分组, 如不传则默认为'DEFAULT_GROUP'
            protocol {str} - 访问协议, 如果不传则自动从服务的metadata获取
            uri {str} - 访问服务的uri, 如果不传则自动从服务的metadata获取
            metadata {dict} - 服务的metadata
        """
        self._local_services[service_id] = {
            'service_name': service_config.get('service_name', None),
            'group_name': service_config.get('group_name', None),
            'protocol': service_config.get('protocol', None),
            'uri': service_config.get('uri', None),
            'metadata': service_config.get('metadata', None),
            'handler': handler
        }

    def remove_local_service(self, service_id: str):
        """
        删除本地服务访问支持

        @param {str} service_id - 服务标识
        """
        self._local_services.pop(service_id, None)

    async def async_call_with_settings(self, service_id: str, self_settings: dict, request: dict, *args, **kwargs) -> Any:
        """
        请求远程调用(异步模式, 使用自定义配置覆盖配置文件)

        @param {str} service_id - 服务标识
        @param {dict} self_settings - 自定义的配置
        @param {dict} request - 请求信息字典
            {
                'network': {  # 请求的客户端标准信息支持传入以下参数
                    sysId: ''  # 指定请求发出的系统标识, 如果不传默认使用应用配置的系统参数
                    moduleId: ''  # 指定请求发出的模块标识, 如果不传默认使用应用配置的系统参数
                    method: ''  # 请求方法类型, 如果不传默认为GET
                    query_string: ''  # 请求的url参数字符串, 'aa=xx&bb=xx'这个形式的url参数
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 报文内容, 根据不同转换规则可能转换为不同的格式
            }
        @param {args} - 固定位置的参数, 如果路由存在变量, 自动按位置替换路由变量值
        @param {kwargs} - key-value形式的参数, 如果路由存在变量, 自动按变量名替换路由变量值

        @returns {dict} response - 返回对象, 格式定义如下:
            {
                'network': {
                    status: 200  # 协议状态码
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 响应报文内容, 任意格式
            }
        """
        # 获取服务实例信息
        _instance_info = await self._get_service_instance(service_id, self_settings=self_settings)

        # 获取客户端访问插件
        _formater = self.adapter_manager.get_adapter('formater_caller', _instance_info['formater'])
        if _formater is None:
            raise NotImplementedError(_('Caller formater [$1] is not found', _instance_info['formater']))

        # 获取报文信息日志记录插件
        _inf_logging = self.adapter_manager.get_adapter(
            'inf_logging', _instance_info.get('inf_logging', None)
        )

        # 处理默认报文头
        if _instance_info['headers'] is not None:
            _headers = copy.deepcopy(_instance_info['headers'])
            _headers.update(request.get('headers', {}))
            request['headers'] = _headers

        # 处理默认的客户端参数
        if _instance_info['network'] is not None:
            _network = copy.deepcopy(_instance_info['network'])
            _network.update(request.get('network', {}))
            request['network'] = _network

        # 处理调用链
        if _instance_info.get('enable_tracer', False) and self._tracer is not None:
            # 自身无需记录调用链, 实际上只需要处理上下文的传递即可
            self._tracer.inject_to_call(
                _instance_info.get('tracer_inject_format', 'http_headers'), request['headers']
            )

        if _instance_info['is_local']:
            # 本地调用
            _std_request = _formater.format_local_call_request(_instance_info, request, *args, **kwargs)
            if isawaitable(_std_request):
                _std_request = await _std_request

            if _inf_logging is not None:
                await AsyncTools.async_run_coroutine(
                    _inf_logging.log('C', 'R', _std_request, service_config=_instance_info)
                )

            try:
                _call_resp = _instance_info['handler'](_std_request, *args, **kwargs)
                if isawaitable(_call_resp):
                    _call_resp = await _call_resp

                _resp = _formater.format_local_call_response(
                    _call_resp, _std_request, _instance_info, request, *args, **kwargs
                )
                if isawaitable(_resp):
                    _resp = await _resp

            except Exception as _err:
                _resp = _formater.format_local_call_exception(
                    '21007',  None, _err, _std_request, _instance_info, request, *args, **kwargs
                )
                if isawaitable(_resp):
                    _resp = await _resp

            if _inf_logging is not None:
                await AsyncTools.async_run_coroutine(
                    _inf_logging.log('C', 'B', _resp, service_config=_instance_info)
                )
        else:
            # 通过客户端访问插件执行远程调用
            _std_request = _formater.format_remote_call_request(
                _instance_info, request, *args, **kwargs
            )
            if isawaitable(_std_request):
                _std_request = await _std_request

            if _inf_logging is not None:
                await AsyncTools.async_run_coroutine(
                    _inf_logging.log('C', 'R', _std_request, service_config=_instance_info)
                )

            _resp = _formater.call(_instance_info, _std_request, *args, **kwargs)
            if isawaitable(_resp):
                _resp = await _resp

            if _inf_logging is not None:
                await AsyncTools.async_run_coroutine(
                    _inf_logging.log('C', 'B', _resp, service_config=_instance_info)
                )

        return _resp

    def call_with_settings(self, service_id: str, self_settings: dict, request: dict, *args, **kwargs) -> Any:
        """
        请求远程调用(同步模式, 使用自定义配置覆盖配置文件)

        @param {str} service_id - 服务标识
        @param {dict} self_settings - 自定义的配置
        @param {dict} request - 请求信息字典
            {
                'network': {  # 请求的客户端标准信息支持传入以下参数
                    sysId: ''  # 指定请求发出的系统标识, 如果不传默认使用应用配置的系统参数
                    moduleId: ''  # 指定请求发出的模块标识, 如果不传默认使用应用配置的系统参数
                    method: ''  # 请求方法类型, 如果不传默认为GET
                    query_string: ''  # 请求的url参数字符串, 'aa=xx&bb=xx'这个形式的url参数
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 报文内容, 根据不同转换规则可能转换为不同的格式
            }
        @param {args} - 固定位置的参数, 如果路由存在变量, 自动按位置替换路由变量值
        @param {kwargs} - key-value形式的参数, 如果路由存在变量, 自动按变量名替换路由变量值

        @returns {dict} response - 返回对象, 格式定义如下:
            {
                'network': {
                    status: 200  # 协议状态码
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 响应报文内容, 任意格式
            }
        """
        return AsyncTools.sync_call(
            self.async_call_with_settings, service_id, self_settings, request, *args, **kwargs
        )

    async def async_call(self, service_id: str, request: dict, *args, **kwargs) -> Any:
        """
        请求远程调用(异步模式)

        @param {str} service_id - 服务标识
        @param {dict} request - 请求信息字典
            {
                'network': {  # 请求的客户端标准信息支持传入以下参数
                    sysId: ''  # 指定请求发出的系统标识, 如果不传默认使用应用配置的系统参数
                    moduleId: ''  # 指定请求发出的模块标识, 如果不传默认使用应用配置的系统参数
                    method: ''  # 请求方法类型, 如果不传默认为GET
                    query_string: ''  # 请求的url参数字符串, 'aa=xx&bb=xx'这个形式的url参数
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 报文内容, 根据不同转换规则可能转换为不同的格式
            }
        @param {args} - 固定位置的参数, 如果路由存在变量, 自动按位置替换路由变量值
        @param {kwargs} - key-value形式的参数, 如果路由存在变量, 自动按变量名替换路由变量值

        @returns {dict} response - 返回对象, 格式定义如下:
            {
                'network': {
                    status: 200  # 协议状态码
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 响应报文内容, 任意格式
            }
        """
        return await self.async_call_with_settings(
            service_id, {}, request, *args, **kwargs
        )

    def call(self, service_id: str, request: dict, *args, **kwargs) -> Any:
        """
        请求远程调用

        @param {str} service_id - 服务标识
        @param {dict} request - 请求信息字典
            {
                'network': {  # 请求的客户端标准信息支持传入以下参数
                    sysId: ''  # 指定请求发出的系统标识, 如果不传默认使用应用配置的系统参数
                    moduleId: ''  # 指定请求发出的模块标识, 如果不传默认使用应用配置的系统参数
                    method: ''  # 请求方法类型, 如果不传默认为GET
                    query_string: ''  # 请求的url参数字符串, 'aa=xx&bb=xx'这个形式的url参数
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 报文内容, 根据不同转换规则可能转换为不同的格式
            }
        @param {args} - 固定位置的参数, 如果路由存在变量, 自动按位置替换路由变量值
        @param {kwargs} - key-value形式的参数, 如果路由存在变量, 自动按变量名替换路由变量值

        @returns {dict} response - 返回对象, 格式定义如下:
            {
                'network': {
                    status: 200  # 协议状态码
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 响应报文内容, 任意格式
            }
        """
        return self.call_with_settings(
            service_id, {}, request, *args, **kwargs
        )

    #############################
    # 内部函数
    #############################
    async def _get_service_instance(self, service_id: str, self_settings: dict = {}) -> dict:
        """
        获取服务实例信息

        @param {str} service_id - 服务标识
        @param {dict} self_settings={} - 自定义的配置, 可覆盖配置文件信息

        @returns {dict} - 返回的实例信息字典
            {
                'is_fixed_config': False, # 是否固定参数(非本地实例, 但不从注册中心获取服务信息)
                'is_local': False,  # 是否本地实例
                'handler': None,  # 本地服务处理函数
                'protocol': 'http',  # 通讯协议
                'uri': '',  # 服务标识路径
                'network': {},  # 默认通讯协议参数
                'headers': {},  # 默认报文头设置
                'metadata': {}  # 服务元数据
                'ip': '',  # 访问主机ip, 如果是本地实例设置为None
                'port': 80,  # 访问主机端口, 如果是本地实例设置None
                'formater': None,  # 该服务使用的请求报文转换插件标识
                'enable_tracer': False  # 是否启用调用链, 默认为false
            }
        """
        # 获取远程配置信息
        _remote_config = self._remote_services.get(service_id, None)
        if _remote_config is None:
            raise ModuleNotFoundError(_('Remote service id [$1] is not found', service_id))

        # 处理自定义配置的情况
        _instance_info = copy.deepcopy(_remote_config)
        _instance_info.update(copy.deepcopy(self_settings))

        _instance_ok = False
        if _instance_info.get('local_call_first', True):
            # 先尝试从本地获取服务实例信息
            _service_info = self._local_services.get(service_id, None)
            if _service_info is not None:
                # 设置一些固定的参数
                _instance_info.update({
                    'is_local': True,
                    'handler': _service_info.get('handler', None),
                    'metadata': _service_info.get('metadata', None),
                    'ip': None,
                    'port': None,
                })
                _instance_ok = True

        if not _instance_ok and _instance_info.get('is_fixed_config', False):
            # 如果是固定参数, 直接从参数获取
            _instance_info.update({
                'is_local': False
            })
            _instance_ok = True

        if not _instance_ok:
            # 本地获取不到, 通过远程获取
            _naming_adapter = self._get_naming_adapter(_instance_info.get('naming', None))
            _service_info = await AsyncTools.async_run_coroutine(
                _naming_adapter.get_instance(
                    _instance_info.get('service_name', None),
                    group_name=_instance_info.get('group_name', None)
                )
            )

            if _service_info is None:
                raise ModuleNotFoundError(_(
                    'No enable instance [$1] of service name [$2] in the naming server',
                    service_id, _instance_info.get('service_name', None)
                ))

            _instance_info.update({
                'is_local': False,
                'metadata': _service_info.get('metadata', None),
                'ip': _service_info.get('ip', None),
                'port': _service_info.get('port', None)
            })

        # 处理uri和通讯协议
        if _instance_info['metadata'] is not None:
            if _instance_info['protocol'] is None:
                _instance_info['protocol'] = _instance_info['metadata'].get('protocol', None)
            if _instance_info['uri'] is None:
                _instance_info['uri'] = _instance_info['metadata'].get('uri', None)
            if _instance_info['headers'] is None:
                _instance_info['headers'] = _instance_info['metadata'].get('headers', None)
            if _instance_info['network'] is None:
                _instance_info['network'] = _instance_info['metadata'].get('network', None)

        return _instance_info

    def _add_naming_adapter(self, naming: str):
        """
        添加自定义注册中心适配器

        @param {str} naming - 注册中心适配器的标识

        @returns {object} - 返回适配器对象
        """
        _naming_config = self._naming_config.get(naming, {}).get('plugin', None)
        if _naming_config is None:
            raise ModuleNotFoundError(_('Naming config of [$1] not found', naming))

        # 处理命名空间和集群
        if _naming_config['init_config'].get('namespace', None) is None:
            _naming_config['init_config']['namespace'] = self._global_config['namespace']
        if _naming_config['init_config'].get('cluster_name', None) is None:
            _naming_config['init_config']['cluster_name'] = self._global_config['cluster_name']

        return self._sys_lib_loader.load_by_config(
            _naming_config, self._plugins_path
        )

    def _get_naming_adapter(self, naming: str):
        """
        根据注册中心适配器标识获取适配器对象

        @param {str} naming - 注册中心适配器的标识

        @returns {object} - 返回适配器对象
        """
        _naming_adapter = None
        if naming is not None and naming != '':
            # 指定自定义注册中心适配器
            _naming_adapter = self._namings.get(naming, None)
            if _naming_adapter is None:
                _naming_adapter = self._add_naming_adapter(naming)
        else:
            _naming_adapter = self._default_naming

        return _naming_adapter
