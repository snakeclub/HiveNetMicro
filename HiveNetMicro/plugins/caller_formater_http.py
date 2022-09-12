#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
http协议的远程调用请求的接口格式转换适配器

@module caller_formater_http
@file caller_formater_http.py
"""
import os
import sys
import datetime
import copy
import json
import ssl
import traceback
import urllib.request
import urllib.error
import aiohttp
from HiveNetCore.utils.run_tool import AsyncTools
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.interface.adapter.formater import CallerFormaterAdapter, RouterTools
from HiveNetMicro.core.global_manager import GlobalManager
from HiveNetMicro.interface.extend.serial_number import SerialNumberTool
from HiveNetMicro.core.logger_manager import LoggerManager


class HttpCommonCallerFormater(CallerFormaterAdapter):
    """
    http协议的远程调用请求的通用格式转换适配器实现
    """

    def __init__(self, init_config: dict = {}, logger_id: str = None) -> None:
        """
        构造函数

        @param {dict} init_config={} - 初始化参数
            json_ensure_ascii {bool} - 转换json字符串是严格为ascii编码, 默认为False
            timeout {float} - 请求超时时间, 单位为秒, 默认为60
            headers {dict} - 默认附带的请求头字典, 默认为{}
            origin_req_host {str} - 指定请求方的主机地址或IP, 默认为None
            protocol_mapping {dict} - 协议映射字典, key为url中的协议(http/https), value为平台协议标识清单
                例如: {
                    'https': ['https_with_ssl', 'https'],
                    'http': []
                }
            cafile {str} - 证书文件名称, 例如'ca.pem'
            capath {str} - 证书文件路径
            ssl_context {str} - ssl的验证上下文:
                ''或None - 不使用上下文
                'unverified' - 不验证ssl
                'default' - 默认ssl上下文: ssl._create_default_https_context
            ssl_context_check_hostname {bool} - 设置ssl上下文是否验证主机名
            ssl_context_verify_mode {str} - 设置ssl上下文的验证模式
                ''或None - 不设置
                'CERT_NONE' - 不验证
                'CERT_REQUIRED' - 必须验证
                'CERT_OPTIONAL' - 可选验证
        @param {str} logger_id=None - 日志对象标识, 可以选择application.yaml配置中的其中一个日志对象
        """
        # 执行基础类初始化函数
        super().__init__(
            init_config=init_config, logger_id=logger_id
        )

        self.init_config = {
            'json_ensure_ascii': init_config.get('json_ensure_ascii', False),
            'timeout': init_config.get('timeout', 60.0),
            'headers': init_config.get('init_config', {}),
            'origin_req_host': init_config.get('origin_req_host', None),
            'protocol_mapping': copy.deepcopy(init_config.get('protocol_mapping', {'https': ['https']})),
            'cafile': init_config.get('cafile', None),
            'capath': init_config.get('capath', None),
        }

        # ssl上下文
        _ssl_context = init_config.get('ssl_context', '')
        if _ssl_context == 'unverified':
            self.init_config['ssl_context'] = ssl._create_unverified_context()
        elif _ssl_context == 'default':
            self.init_config['ssl_context'] = ssl.create_default_context()
        else:
            self.init_config['ssl_context'] = None
            self.init_config['ssl_context_check_hostname'] = None
            self.init_config['ssl_context_verify_mode'] = None

        # ssl上下文配置
        if self.init_config['ssl_context'] is not None:
            self.init_config['ssl_context_check_hostname'] = init_config.get('ssl_context_check_hostname', None)
            _verify_mode = init_config.get('ssl_context_verify_mode', '')
            if _verify_mode == 'CERT_NONE':
                self.init_config['ssl_context_verify_mode'] = ssl.VerifyMode.CERT_NONE
            elif _verify_mode == 'CERT_REQUIRED':
                self.init_config['ssl_context_verify_mode'] = ssl.VerifyMode.CERT_REQUIRED
            elif _verify_mode == 'CERT_OPTIONAL':
                self.init_config['ssl_context_verify_mode'] = ssl.VerifyMode.CERT_OPTIONAL
            else:
                self.init_config['ssl_context_verify_mode'] = None

            # 进行设置
            if self.init_config['ssl_context_check_hostname'] is not None:
                self.init_config['ssl_context'].check_hostname = self.init_config['ssl_context_check_hostname']
            if self.init_config['ssl_context_verify_mode'] is not None:
                self.init_config['ssl_context'].verify_mode = self.init_config['ssl_context_verify_mode']

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
        _std_request = {
            'network': copy.deepcopy(request.get('network', {})),
            'headers': await self._get_call_headers(instance_info, request, *args, **kwargs),
            'msg': await self._format_call_msg(request.get('msg', None), instance_info, request, *args, **kwargs)
        }

        return _std_request

    async def call(self, instance_info: dict, std_request: dict, *args, **kwargs) -> dict:
        """
        远程调用请求标准适配函数

        @param {dict} instance_info - 请求实例信息字典
            {
                'protocol': 'http',  # 通讯协议, 支持http, https
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
                'network': {
                    status: 200  # 协议状态码
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 响应报文内容, 任意格式
            }
        """
        # 处理url
        _url = await self._get_call_url(instance_info, std_request, *args, **kwargs)

        # 处理msg
        _msg = await self._get_call_msg(instance_info, std_request, *args, **kwargs)

        try:
            # 处理请求
            _request = urllib.request.Request(
                _url, _msg, headers=std_request.get('headers', None),
                origin_req_host=self.init_config['origin_req_host']
            )
            # 设置请求方法
            _request.get_method = lambda: std_request.get('network', {}).get('method', 'GET')

            # 真正执行请求调用
            try:
                _response = urllib.request.urlopen(
                    _request, timeout=self.init_config['timeout'],
                    cafile=self.init_config['cafile'], capath=self.init_config['capath'],
                    context=self.init_config['ssl_context']
                )

                # 返回标准响应信息
                _resp_status = _response.status
                _resp_header = {}
                for _item in _response.getheaders():
                    _resp_header[_item[0].lower()] = _item[1]

                _resp_msg = _response.read()
                if _resp_status == 200:
                    if _resp_msg == '':
                        _resp_msg = None

                # 判断是否进行格式处理
                if _resp_msg is not None:
                    _msg_type = type(_resp_msg)
                    if _resp_header.get('content-type', '').startswith('application/json') and _msg_type in (bytes, str):
                        _resp_msg = json.loads(_resp_msg)

                # 组成返回对象
                _resp_obj = {
                    'network': {
                        'status': _resp_status
                    },
                    'headers': _resp_header,
                    'msg': _resp_msg
                }
            except Exception as _err:
                # 已经发起远程调用, 如果出现异常都视为未知类的异常
                _resp_obj = await self._format_on_exception(
                    '31007', None, _err, _url, instance_info, std_request, *args, **kwargs
                )
        except Exception as _err:
            # 未发起远程调用, 异常视为失败
            _resp_obj = await self._format_on_exception(
                '21007', None, _err, _url, instance_info, std_request, *args, **kwargs
            )

        # 处理标准返回对象
        _resp_obj = await self._format_resp_obj(
            _resp_obj, instance_info, std_request, std_request, *args, **kwargs
        )
        return _resp_obj

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
        # uri参数设置
        _uri = RouterTools.format_uri(
            instance_info['uri'], fun_args=args, fun_kwargs=None
        )

        # 客户端链接信息
        _std_network = {
            'method': 'GET',
            'host': 'local',
            'path': _uri,  # 当前请求的url路径
            'ip': '127.0.0.1',
            'port': 0
        }
        if request.get('network', None) is None:
            request['network'] = _std_network
        else:
            _std_network.update(request['network'])
            request['network'] = _std_network

        # 报文头信息
        if len(self.init_config['headers']) > 0:
            _header = copy.deepcopy(self.init_config['headers'])
            _header.update(request.get('headers', {}))
            request['headers'] = _header

        # 处理报文内容
        _msg = request.pop('msg', None)
        _msg = await self._format_call_msg(_msg, instance_info, request, *args, **kwargs)
        if _msg is not None:
            request['msg'] = _msg

        return request

    async def format_local_call_response(self, response: dict, std_request: dict, instance_info: dict, request: dict, *args, **kwargs) -> dict:
        """
        格式化本地调用时的返回字典

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
        if response.get('network', None) is None:
            response['network'] = {'status': 200}

        if response['network'].get('status', None) is None:
            response['network']['status'] = 200

        _resp_obj = await self._format_resp_obj(
            response, std_request, instance_info, request, *args, **kwargs
        )
        return _resp_obj

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
        _resp_obj = await self._format_on_exception(
            err_code, err_msg, exception, instance_info.get('uri', ''), instance_info, request, *args, **kwargs
        )
        _resp_obj = await self._format_resp_obj(_resp_obj, std_request, instance_info, request, *args, **kwargs)
        return _resp_obj

    #############################
    # 内部辅助函数
    #############################
    async def _get_call_url(self, instance_info: dict, request: dict, *args, **kwargs) -> str:
        """
        生成远程调用的url

        @param {dict} instance_info - 请求实例信息字典
        @param {dict} request - 远程调用标准请求对象

        @returns {str} - 要远程访问的url
        """
        # 判断协议
        _protocol = instance_info.get('protocol', 'http')
        if _protocol in self.init_config['protocol_mapping']['https']:
            _protocol = 'https'
        else:
            _protocol = 'http'

        # uri参数设置
        _query = {} if instance_info.get('query', None) is None else instance_info['query']
        _kwargs = {} if kwargs is None else kwargs
        _query.update(_kwargs)
        _uri = RouterTools.format_uri(
            instance_info['uri'], fun_args=args, fun_kwargs=_query
        )

        # 拼接url
        _url = '%s://%s%s/%s' % (
            _protocol, instance_info['ip'],
            '' if instance_info.get('port', None) is None else ':%d' % instance_info['port'],
            _uri
        )
        return _url

    async def _get_call_headers(self, instance_info: dict, request: dict, *args, **kwargs) -> dict:
        """
        生成远程调用的请求报文头

        @param {dict} instance_info - 请求实例信息字典
        @param {dict} request - 远程调用标准请求对象

        @returns {dict} - 远程访问的请求报文头
        """
        _header = copy.deepcopy(self.init_config['headers'])
        _header.update(request.get('headers', {}))
        return _header

    async def _get_call_msg(self, instance_info: dict, std_request: dict, *args, **kwargs) -> bytes:
        """
        生成远程调用的数据

        @param {dict} instance_info - 请求实例信息字典
        @param {dict} std_request - 远程调用标准请求对象

        @returns {bytes} - 远程访问的消息数据
        """
        # 处理消息内容转换
        _msg = std_request.get('msg', None)

        # 处理消息格式转换
        if _msg is not None:
            _msg_type = type(_msg)
            if _msg_type in (dict, list, tuple):
                _msg = json.dumps(_msg, ensure_ascii=self.init_config['json_ensure_ascii'])
            elif _msg_type != bytes:
                _msg = str(_msg)

            if type(_msg) == str:
                _msg = _msg.encode('utf-8')

        return _msg

    async def _format_call_msg(self, msg, instance_info: dict, request: dict, *args, **kwargs):
        """
        转换消息内容

        @param {Any} - 要处理的消息对象
        @param {dict} instance_info - 请求实例信息字典
        @param {dict} request - 远程调用标准请求对象

        @returns {dict} - 转换后的消息内容对象
        """
        return msg

    async def _format_on_exception(self, err_code: str, err_msg: str, err_obj,
            url: str, instance_info: dict, request: dict, *args, **kwargs) -> dict:
        """
        转换异常处理

        @param {str} err_code - 错误码
        @param {str} err_msg - 错误信息, 可以传None
        @param {Exception} err_obj - 异常对象
        @param {str} url - 访问的网页地址
        @param {dict} instance_info - 请求实例信息字典
        @param {dict} request - 远程调用标准请求对象

        @returns {dict} - 转换后的标准返回对象
        """
        _err_type = type(err_obj)
        _status = 500 if _err_type != urllib.error.HTTPError else err_obj.status
        return {
            'network': {
                'status': _status
            },
            'headers': {},
            'msg': {
                'errCode': err_code,
                'errMsg': str(err_obj) if err_msg is None else err_msg,
                'errType': _err_type.__name__,
                'url': url,
                'traceback': traceback.format_exc()
            }
        }

    async def _format_resp_obj(self, resp_obj, std_request: dict, instance_info: dict, request: dict, *args, **kwargs):
        """
        转换返回的对象

        @param {dict} resp_obj - 标准返回对象
        @param {dict} std_request - 标准请求报文对象
        @param {dict} instance_info - 请求实例信息字典
        @param {dict} request - 远程调用标准请求对象

        @returns {Any} - 转换后的标准返回对象
        """
        return resp_obj


class AioHttpCommonCallerFormater(HttpCommonCallerFormater):
    """
    http协议的远程调用请求的通用格式转换适配器实现
    (基于aiohttp的异步模式)
    """

    def __init__(self, init_config: dict = {}, logger_id: str = None) -> None:
        """
        构造函数

        @param {dict} init_config={} - 初始化参数
            json_ensure_ascii {bool} - 转换json字符串是严格为ascii编码, 默认为False
            timeout {float} - 请求超时时间, 单位为秒, 默认为60
            headers {dict} - 默认附带的请求头字典, 默认为{}
            protocol_mapping {dict} - 协议映射字典, key为url中的协议(http/https), value为平台协议标识清单
                例如: {
                    'https': ['https_with_ssl', 'https'],
                    'http': []
                }
            cafile {str} - 证书文件名称, 例如'ca.crt'
            capath {str} - 证书文件路径
            certfile {str} - cert证书文件路径, 例如'xxx/xxx.pem'
            keyfile {str} - 证书key文件路径, 例如'xxx/xxx.key'
        @param {str} logger_id=None - 日志对象标识, 可以选择application.yaml配置中的其中一个日志对象
        """
        self.init_config = {
            'json_ensure_ascii': init_config.get('json_ensure_ascii', False),
            'timeout': init_config.get('timeout', 60.0),
            'headers': init_config.get('init_config', {}),
            'protocol_mapping': copy.deepcopy(init_config.get('protocol_mapping', {'https': ['https']})),
            'cafile': init_config.get('cafile', None),
            'capath': init_config.get('capath', None),
        }

        # 日志对象
        _logger_manager: LoggerManager = GlobalManager.GET_SYS_LOGGER_MANAGER()
        if _logger_manager is None:
            _logger_manager = LoggerManager('')
        self.logger = _logger_manager.get_logger(logger_id, none_with_default_logger=True)

        # ssl上下文
        if self.init_config['cafile'] is None:
            self.init_config['ssl'] = False
        else:
            self.init_config['ssl'] = ssl.create_default_context(
                cafile=self.init_config['cafile'], capath=self.init_config['capath']
            )
            if init_config.get('certfile', None) is not None:
                self.init_config['ssl'].load_cert_chain(
                    init_config['certfile'], init_config['keyfile']
                )

    async def call(self, instance_info: dict, std_request: dict, *args, **kwargs) -> dict:
        """
        远程调用请求标准适配函数(异步模式)

        @param {dict} instance_info - 请求实例信息字典
            {
                'protocol': 'http',  # 通讯协议, 支持http, https
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
                'network': {
                    status: 200  # 协议状态码
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 响应报文内容, 任意格式
            }
        """
        # 处理url
        _url = await self._get_call_url(instance_info, std_request, *args, **kwargs)

        # 处理msg
        _msg = await self._get_call_msg(instance_info, std_request, *args, **kwargs)

        try:
            async with aiohttp.ClientSession(
                headers=std_request.get('headers', None),
                timeout=aiohttp.ClientTimeout(total=self.init_config['timeout']),
                connector=aiohttp.TCPConnector(enable_cleanup_closed=True),
            ) as _session:
                # 真正进行调用
                try:
                    async with _session.request(
                        std_request.get('network', {}).get('method', 'GET'), _url,
                        data=_msg, ssl=self.init_config['ssl']
                    ) as _response:
                        # 返回标准响应信息
                        _resp_status = _response.status
                        _resp_header = {}
                        for _item in _response.headers.items():
                            _resp_header[_item[0].lower()] = _item[1]

                        _resp_msg = await _response.read()
                        if _resp_status == 200:
                            if _resp_msg == '':
                                _resp_msg = None

                        # 判断是否进行格式处理
                        if _resp_msg is not None:
                            _msg_type = type(_resp_msg)
                            if _resp_header.get('content-type', '').startswith('application/json') and _msg_type in (bytes, str):
                                _resp_msg = json.loads(_resp_msg)

                        # 返回标准对象
                        _resp_obj = {
                            'network': {
                                'status': _resp_status
                            },
                            'headers': _resp_header,
                            'msg': _resp_msg
                        }
                except Exception as _err:
                    # 已经发起远程调用, 如果出现异常都视为未知类的异常
                    _resp_obj = await self._format_on_exception(
                        '31007', None, _err, _url, instance_info, std_request, *args, **kwargs
                    )
        except Exception as _err:
            # 未发起远程调用, 异常视为失败
            _resp_obj = await self._format_on_exception(
                '21007', None, _err, _url, instance_info, std_request, *args, **kwargs
            )

        # 处理标准返回对象
        _resp_obj = await self._format_resp_obj(
            _resp_obj, std_request, instance_info, std_request, *args, **kwargs
        )
        return _resp_obj


class AioHttpHiveNetStdIntfCallerFormater(AioHttpCommonCallerFormater):
    """
    http协议的远程调用请求的HiveNet标准报文格式转换适配器实现
    (基于aiohttp的异步模式)
    注意: 该适配器依赖于动态适配器获取序号: id: serial_number, adapter_type: SerialNumber
    """

    #############################
    # 适配器基础属性
    #############################
    @property
    def adapter_dependencies(self):
        """
        当前适配器的依赖适配器清单
        注: 列出动态加载的适配器清单中应装载的适配器信息清单

        @property {list} - 依赖适配器清单, 每个值为适配器信息字典, 格式如下:
            [
                {
                    'adapter_type': '',  # 必须, 依赖适配器类型
                    'base_class': '',  # 可选, 依赖适配器的基类名
                    'adapter_id': ''  # 可选, 依赖适配器的id
                },
                ...
            ]
        """
        return [
            {
                'adapter_type': 'SerialNumber',
                'base_class': 'HiveNetMicro.interface.extend.serial_number.SerialNumberAdapter',
                'adapter_id': 'serial_number'
            }
        ]

    #############################
    # 构造函数
    #############################
    def __init__(self, init_config: dict = {}, logger_id: str = None):
        """
        构造函数

        @param {dict} init_config={} - 初始化参数
            json_ensure_ascii {bool} - 转换json字符串是严格为ascii编码, 默认为False
            timeout {float} - 请求超时时间, 单位为秒, 默认为60
            headers {dict} - 默认附带的请求头字典, 默认为{}
            protocol_mapping {dict} - 协议映射字典, key为url中的协议(http/https), value为平台协议标识清单
                例如: {
                    'https': ['https_with_ssl', 'https'],
                    'http': []
                }
            cafile {str} - 证书文件名称, 例如'ca.crt'
            capath {str} - 证书文件路径
            certfile {str} - cert证书文件路径, 例如'xxx/xxx.pem'
            keyfile {str} - 证书key文件路径, 例如'xxx/xxx.key'
            serial_number_adapter_id {str} - 序列号适配器标识, 默认为'serial_number'
            serial_number_adapter_type {str} - 序列号适配器类型, 默认为'SerialNumber'
            global_serial_number_id {str} - 全局流水号的序列号id, 默认为'globSeqNum'
            sys_serial_number_id {str} - 系统流水号的序列号id, 默认为'sysSeqNum'
            inf_serial_number_id {str} - 接口流水号的序列号id, 默认为'infSeqNum'
            global_serial_number_batch_size {int} - 全局流水号的序列号缓存批次大小, 0代表不缓存, 默认为0
            sys_serial_number_batch_size {int} - 全局流水号的序列号缓存批次大小, 0代表不缓存, 默认为0
            inf_serial_number_batch_size {int} - 全局流水号的序列号缓存批次大小, 0代表不缓存, 默认为0
        @param {str} logger_id=None - 日志对象标识, 可以选择application.yaml配置中的其中一个日志对象
        """
        super().__init__(init_config=init_config, logger_id=logger_id)

        # 序列号适配器
        self.adapter_manager = GlobalManager.GET_SYS_ADAPTER_MANAGER()
        self.serial_number_adapter = self.adapter_manager.get_adapter(
            init_config.get('serial_number_adapter_type', 'SerialNumber'),
            init_config.get('serial_number_adapter_id', 'serial_number')
        )
        self.serial_tool = SerialNumberTool(self.serial_number_adapter)

        # 序列号获取参数
        self.global_serial_number_id = init_config.get('global_serial_number_id', 'globSeqNum')
        self.sys_serial_number_id = init_config.get('sys_serial_number_id', 'sysSeqNum')
        self.inf_serial_number_id = init_config.get('inf_serial_number_id', 'infSeqNum')

        # 处理缓存设置
        if init_config.get('global_serial_number_batch_size', 0) > 0:
            AsyncTools.sync_run_coroutine(
                self.serial_tool.cache_serial_batch(
                    self.global_serial_number_id, batch_size=init_config['global_serial_number_batch_size']
                )
            )

        if init_config.get('sys_serial_number_batch_size', 0) > 0:
            AsyncTools.sync_run_coroutine(
                self.serial_tool.cache_serial_batch(
                    self.sys_serial_number_id, batch_size=init_config['sys_serial_number_batch_size']
                )
            )

        if init_config.get('inf_serial_number_batch_size', 0) > 0:
            AsyncTools.sync_run_coroutine(
                self.serial_tool.cache_serial_batch(
                    self.inf_serial_number_id, batch_size=init_config['inf_serial_number_batch_size']
                )
            )

    #############################
    # 内部辅助函数
    #############################
    async def _format_call_msg(self, msg, instance_info: dict, request: dict, *args, **kwargs):
        """
        转换消息内容

        @param {Any} - 要处理的消息对象
        @param {dict} instance_info - 请求实例信息字典
        @param {dict} request - 远程调用标准请求对象

        @returns {dict} - 转换后的消息内容对象
        """
        if msg is None:
            return msg

        # 处理报文头
        _global_config = GlobalManager.GET_GLOBAL_CONFIG()
        _ctime = datetime.datetime.now()

        _head = msg.pop('head', {})
        # 请求系统标识
        if _head.get('sysId', '') == '':
            _sysId = request.get('network', {}).get(
                'sysId', _global_config['app_config'].get('sys_id', '')
            )
            _moduleId = request.get('network', {}).get(
                'moduleId', _global_config['app_config'].get('module_id', '')
            )
            _head['sysId'] = '%s-%s' % (_sysId, _moduleId)

        # 源系统标识
        if _head.get('originSysId', '') == '':
            _head['originSysId'] = _head['sysId']

        # 接口类型
        if _head.get('infType', '') == '':
            _head['infType'] = '01'

        # 统一流水号
        if _head.get('globSeqNum', '') == '':
            _head['globSeqNum'] = '%s%s%s%s%s' % (
                _global_config['app_config'].get('sys_id', ''),
                _global_config['app_config'].get('module_id', ''),
                _global_config['app_config'].get('server_id', ''),
                _ctime.strftime('%Y%m%d'),
                await AsyncTools.async_run_coroutine(self.serial_tool.get_serial_num_fix_str(
                    self.global_serial_number_id, 10
                )) # 10位序号
            )

        # 系统流水号
        if _head.get('sysSeqNum', '') == '':
            _head['sysSeqNum'] = '%s%s%s%s%s' % (
                _global_config['app_config'].get('sys_id', ''),
                _global_config['app_config'].get('module_id', ''),
                _global_config['app_config'].get('server_id', ''),
                _ctime.strftime('%Y%m%d'),
                await AsyncTools.async_run_coroutine(self.serial_tool.get_serial_num_fix_str(
                    self.sys_serial_number_id, 10
                )) # 12位序号
            )

        # 接口流水号
        if _head.get('infSeqNum', '') == '':
            _head['infSeqNum'] = '%s%s%s%s%s' % (
                _global_config['app_config'].get('sys_id', ''),
                _global_config['app_config'].get('module_id', ''),
                _global_config['app_config'].get('server_id', ''),
                _ctime.strftime('%Y%m%d%H%M%S'),
                await AsyncTools.async_run_coroutine(self.serial_tool.get_serial_num_fix_str(
                    self.inf_serial_number_id, 10
                )) # 10位序号
            )

        # 放回消息对象
        msg['head'] = _head

        return msg

    async def _format_on_exception(self, err_code: str, err_msg: str, err_obj, url: str,
            instance_info: dict, request: dict, *args, **kwargs) -> dict:
        """
        转换异常处理

        @param {str} err_code - 错误码
        @param {str} err_msg - 错误信息, 可以传None
        @param {Exception} err_obj - 异常对象
        @param {str} url - 访问的网页地址
        @param {dict} instance_info - 请求实例信息字典
        @param {dict} request - 远程调用标准请求对象

        @returns {dict} - 转换后的标准返回对象
        """
        _err_type = type(err_obj)
        _errModule = request.get('msg', {}).get('head', {}).get('', None)
        if _errModule is None:
            _global_config = GlobalManager.GET_GLOBAL_CONFIG()
            _sysId = request.get('network', {}).get(
                'sysId', _global_config['app_config'].get('sys_id', '')
            )
            _moduleId = request.get('network', {}).get(
                'moduleId', _global_config['app_config'].get('module_id', '')
            )
            _errModule = '%s-%s' % (_sysId, _moduleId)
        return {
            'network': {
                'status': 200
            },
            'headers': {},
            'msg': {
                'head': {
                    'errCode': err_code,
                    'errMsg': str(err_obj) if err_msg is None else err_msg,
                    'errModule': _errModule
                },
                'body': {
                    'errType': _err_type.__name__,
                    'url': url,
                    'traceback': traceback.format_exc(),
                    'realStatus': 500 if _err_type != urllib.error.HTTPError else err_obj.status
                }
            }
        }

    async def _format_resp_obj(self, resp_obj, std_request: dict, instance_info: dict, request: dict, *args, **kwargs):
        """
        转换返回的对象

        @param {dict} resp_obj - 标准返回对象
        @param {dict} std_request - 标准请求报文对象
        @param {dict} instance_info - 请求实例信息字典
        @param {dict} request - 远程调用标准请求对象

        @returns {Any} - 转换后的标准返回对象
        """
        if resp_obj is None:
            return None

        _req_head = std_request.get('msg', {}).get('head', {})
        _head = {
            'prdCode': _req_head.get('prdCode', ''),
            'tranCode': _req_head.get('tranCode', ''),
            'originSysId': _req_head.get('originSysId', ''),
            'infType': '02',
            'tranMode': _req_head.get('tranMode', 'ONLINE'),
            'userId': _req_head.get('userId', ''),
            'globSeqNum': _req_head.get('globSeqNum', ''),
            'sysSeqNum': _req_head.get('sysSeqNum', ''),
            'infSeqNum': _req_head.get('infSeqNum', ''),
            'errCode': '00000',
            'errMsg': 'Success'
        }

        _status = resp_obj.get('network', {}).get('status', 200)
        if _status < 200 or _status >= 300 and resp_obj.get('msg', {}).get('head', None) is None:
            # 访问远端服务异常, 并且返回的内容不是标准格式
            _head['errCode'] = '31007'
            _head['errMsg'] = 'Http status error [%d]' % _status
            resp_obj['network']['status'] = 200
            resp_obj['msg'] = {
                'body': resp_obj['msg']
            }

        # 处理响应字典
        if resp_obj.get('msg', None) is None:
            resp_obj['msg'] = {'head': {}}

        if resp_obj['msg'].get('head', None) is None:
            resp_obj['msg']['head'] = {}

        _head.update(resp_obj['msg']['head'])
        resp_obj['msg']['head'] = _head
        return resp_obj
