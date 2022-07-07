#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
不同通讯接口格式转换适配器

@module formater
@file formater.py
"""
import os
import sys
from typing import Any
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.adapter_base import AdapterBaseFw
from HiveNetMicro.core.global_manager import GlobalManager
from HiveNetMicro.core.logger_manager import LoggerManager


class ServerFormaterAdapter(AdapterBaseFw):
    """
    针对服务器请求的接口格式转换适配器
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
        return 'ServerFormater'

    #############################
    # 构造函数
    #############################

    def __init__(self, init_config: dict = {}, logger_id: str = None) -> None:
        """
        不同web服务器的接口格式转换适配器

        @param {dict} init_config={} - 初始化参数
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
    def format_request(self, request: Any, value_trans_mapping: dict = None) -> dict:
        """
        将服务器的收到的请求对象格式化为处理函数使用的标准字典

        @param {Any} request - web服务器的请求对象
        @param {dict} value_trans_mapping=None - 参数值类型转换映射字典
            注: key为参数名, value为强制转换的函数字符串, 例如'int'

        @returns {dict} - 请求处理函数使用的标准字典
            {
                'network': {  # 请求中的网络通讯信息, 以下为几个标准信息
                    method: ''  # 请求方法类型
                    host: '',  # 当前请求访问主机(如果不是默认的80端口, 则应为'hostname:port')
                    path: '',  # 当前请求的url路径
                    ip: '',  # 请求连接的客户端ip
                    port: '',  # 请求连接的端口
                    query: {}  # 请求的url参数字典, 由'aa=xx&bb=xx'这个形式的url参数解析得到
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 报文内容, 根据不同转换规则可能转换为不同的格式
            }
        """
        raise NotImplementedError()

    def format_response(self, request: Any, response: dict, is_std_request: bool = False) -> dict:
        """
        将处理函数返回的值转换为服务器所需的对象形式

        @param {Any} request - web服务器的请求对象或格式化以后的标准请求对象
        @param {dict} response - 返回对象, 格式为:
            {
                'network': {
                    status: 200  # 协议状态码
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 响应报文内容, 任意格式
            }
        @param {bool} is_std_request=False - 指示request对象是否标准请求对象

        @returns {dict} - 标准响应信息字典(对response对象进行标准化转换处理)
        """
        raise NotImplementedError()

    def format_exception(self, request: Any, exception: Exception, service_config: dict = {}, is_std_request: bool = False) -> dict:
        """
        执行处理过程出现异常情况时的返回值

        @param {Any} request - web服务器的请求对象或格式化以后的标准请求对象
        @param {Exception} exception - 抛出的异常对象
        @param {dict} service_config={} - 服务配置信息
        @param {bool} is_std_request=False - 指示request对象是否标准请求对象

        @returns {dict} - 标准响应信息字典(对response对象进行标准化转换处理)
        """
        raise NotImplementedError()

    def generate_web_response(self, std_response: dict):
        """
        基于标准返回对象生成适配web服务器的响应对象

        @param {dict} std_response - 标准响应报文字典

        @returns {object} - 适配web服务器的响应对象
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


class CallerFormaterAdapter(AdapterBaseFw):
    """
    针对远程调用请求的接口格式转换适配器
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
        return 'CallerFormater'

    #############################
    # 构造函数
    #############################
    def __init__(self, init_config: dict = {}, logger_id: str = None) -> None:
        """
        不同远程调用请求的接口格式转换适配器

        @param {dict} init_config={} - 初始化参数
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

    async def format_remote_call_request(self, instance_info: dict, request: dict, *args, **kwargs) -> dict:
        """
        格式化远程调用时的请求对象

        @param {dict} instance_info - 请求实例信息字典
            {
                'protocol': 'http',  # 通讯协议, 支持http, https
                'uri': '',  # 服务标识路径
                'headers': {},  # 报文头
                'metadata': {}  # 服务元数据
                'ip': '',  # 访问主机ip, 如果是本地实例设置为None
                'port': 80  # 访问主机端口, 如果是本地实例设置None
            }
        @param {dict} request - 远程调用标准请求对象
            {
                'network': {  # 请求的客户端标准信息支持传入以下参数
                    method: ''  # 请求方法类型, 如果不传默认为GET
                    query: {}  # 请求的url参数字典, 最终会组成'aa=xx&bb=xx'这个形式的url参数
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 报文内容, 根据不同转换规则可能转换为不同的格式
            }

        @returns {dict} - 返回格式化后的请求字典
        """
        raise NotImplementedError()

    async def call(self, instance_info: dict, std_request: dict, *args, **kwargs) -> dict:
        """
        远程调用请求标准适配函数

        @param {dict} instance_info - 请求实例信息字典
            {
                'protocol': 'http',  # 通讯协议
                'uri': '',  # 服务标识路径
                'headers': {},  # 报文头
                'metadata': {}  # 服务元数据
                'ip': '',  # 访问主机ip, 如果是本地实例设置为None
                'port': 80  # 访问主机端口, 如果是本地实例设置None
            }
        @param {dict} std_request - 远程调用标准请求对象
            {
                'network': {  # 请求的客户端标准信息支持传入以下参数
                    method: ''  # 请求方法类型, 如果不传默认为GET
                    query: {}  # 请求的url参数字典, 最终会组成'aa=xx&bb=xx'这个形式的url参数
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 报文内容, 根据不同转换规则可能转换为不同的格式
            }

        @returns {dict} - 标准返回对象
            {
                'host': {
                    status: 200  # 协议状态码
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 响应报文内容, 任意格式
            }
        """
        raise NotImplementedError()

    async def format_local_call_request(self, instance_info: dict, request: dict, *args, **kwargs) -> dict:
        """
        格式化本地调用时的请求对象

        @param {dict} instance_info - 请求实例信息字典
            {
                'protocol': 'http',  # 通讯协议, 支持http, https
                'uri': '',  # 服务标识路径
                'headers': {},  # 报文头
                'metadata': {}  # 服务元数据
                'ip': '',  # 访问主机ip, 如果是本地实例设置为None
                'port': 80  # 访问主机端口, 如果是本地实例设置None
            }
        @param {dict} request - 远程调用标准请求对象
            {
                'network': {  # 请求的客户端标准信息支持传入以下参数
                    method: ''  # 请求方法类型, 如果不传默认为GET
                    query: {}  # 请求的url参数字典, 最终会组成'aa=xx&bb=xx'这个形式的url参数
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 报文内容, 根据不同转换规则可能转换为不同的格式
            }

        @returns {dict} - 返回格式化后的请求字典
        """
        raise NotImplementedError()

    async def format_local_call_response(self, response: dict, std_request: dict, instance_info: dict, request: dict, *args, **kwargs) -> dict:
        """
        格式化本地调用时的返回字典

        @param {dict} response - 返回对象, 格式为:
            {
                'host': {
                    status: 200  # 协议状态码
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 响应报文内容, 任意格式
            }
        @param {dict} std_request - 标准化后的请求字典
        @param {dict} instance_info - 请求实例信息字典
            {
                'protocol': 'http',  # 通讯协议, 支持http, https
                'uri': '',  # 服务标识路径
                'headers': {},  # 报文头
                'metadata': {}  # 服务元数据
                'ip': '',  # 访问主机ip, 如果是本地实例设置为None
                'port': 80  # 访问主机端口, 如果是本地实例设置None
            }
        @param {dict} request - 远程调用标准请求对象
            {
                'network': {  # 请求的客户端标准信息支持传入以下参数
                    method: ''  # 请求方法类型, 如果不传默认为GET
                    query: {}  # 请求的url参数字典, 最终会组成'aa=xx&bb=xx'这个形式的url参数
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 报文内容, 根据不同转换规则可能转换为不同的格式
            }

        @returns {dict} - 返回格式化后的响应字典
        """
        raise NotImplementedError()

    async def format_local_call_exception(self, err_code: str, err_msg: str, exception: Exception,
            std_request: dict, instance_info: dict, request: dict, *args, **kwargs) -> dict:
        """
        格式化本地调用异常情况下返回的字典

        @param {str} err_code - 错误码
        @param {str} err_msg - 错误信息, 可以传None
        @param {Exception} exception - 抛出的异常对象
        @param {dict} std_request - 标准化后的请求字典
        @param {dict} instance_info - 请求实例信息字典
            {
                'protocol': 'http',  # 通讯协议, 支持http, https
                'uri': '',  # 服务标识路径
                'headers': {},  # 报文头
                'metadata': {}  # 服务元数据
                'ip': '',  # 访问主机ip, 如果是本地实例设置为None
                'port': 80  # 访问主机端口, 如果是本地实例设置None
            }
        @param {dict} request - 远程调用标准请求对象
            {
                'network': {  # 请求的客户端标准信息支持传入以下参数
                    method: ''  # 请求方法类型, 如果不传默认为GET
                    query: {}  # 请求的url参数字典, 最终会组成'aa=xx&bb=xx'这个形式的url参数
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 报文内容, 根据不同转换规则可能转换为不同的格式
            }

        @returns {dict} - 异常情况下返回的字典
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


class RouterTools(object):
    """
    路由处理工具函数
    """

    @classmethod
    def get_query_dict(cls, query_string: str, value_trans_mapping: dict = None) -> dict:
        """
        获取url请求中的query参数字典

        @param {str} query_string - url请求中的query参数字符串
        @param {dict} value_trans_mapping=None - 参数值类型转换映射字典
            注: key为参数名, value为强制转换的函数字符串, 例如'int'

        @returns {dict} - 解析后的参数字典
        """
        _query_dict = {}
        if query_string is None or query_string == '':
            return _query_dict

        # 进行解析处理
        _query_list = query_string.split('&')
        for _param in _query_list:
            if _param == '':
                continue

            _index = _param.find('=')
            if _index > 0:
                _name = _param[0: _index]
                _value = _param[_index + 1:]
                # 进行类型转换处理
                if value_trans_mapping is not None:
                    _tran_fun = value_trans_mapping.get(_name, None)
                    if _tran_fun is not None:
                        _value = eval('%s(_value)' % _tran_fun)
                _query_dict[_name] = _value
            else:
                # 没有参数名
                continue

        return _query_dict

    @classmethod
    def format_uri(cls, uri: str, fun_args: tuple = None, fun_kwargs: dict = None) -> str:
        """
        格式化uri生成真正访问的url串

        @param {str} uri - uri字符串, 支持以下格式:
            <name:type> - 占位形式的路由参数, 将按位置顺序将fun_args中的参数替换过去
                type为类型, 支持以下几种类型:
                    string - 字符串, 不设置默认为字符串
                    int - 整形
                    number - 数字
        @param {tuple} fun_args=None - 函数固定位置入参, 替换占位形式的参数
        @param {dict} fun_kwargs=None - 函数key-value方式入参, 组成'?aa=xx&bb=xx'这个形式的url参数

        @returns {str} - 格式化后的请求url字符串
        """
        # _regex = re.compile(r'<.*?>')
        # _result = _regex.finditer(uri)
        _url = uri
        if fun_args is not None and len(fun_args) > 0:
            _path_list = uri.split('/')
            _args_pos = 0
            for _i in range(len(_path_list)):
                if _path_list[_i].startswith('<') and _path_list[_i].endswith('>'):
                    # 需要进行uri替换
                    _path_list[_i] = str(fun_args[_args_pos])
                    _args_pos += 1

            # 重新组合回来
            _url = '/'.join(_path_list)

        if fun_kwargs is not None and len(fun_kwargs) > 0:
            # 组成query字符串
            _query_list = []
            for _key, _val in fun_kwargs.items():
                _query_list.append('%s=%s' % (_key, _val))

            _url = '%s?%s' % (_url, '&'.join(_query_list))

        return _url
