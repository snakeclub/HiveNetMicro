#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
报文转换适配器的Sanic服务收发报文转换的实现

@module server_formater_sanic
@file server_formater_sanic.py
"""
import imp
import os
import sys
from typing import Union
from sanic.request import Request
from sanic.response import HTTPResponse, json
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.interface.adapter.formater import ServerFormaterAdapter, RouterTools


class SanicHiveNetStdIntfServerFormater(ServerFormaterAdapter):
    """
    HiveNet标准接口规范报文转换的Sanic服务端适配实现
    """

    #############################
    # 需实现类重载的公共函数
    #############################
    def format_request(self, request: Request, value_trans_mapping: dict = None) -> dict:
        """
        将web服务器的请求对象格式化为处理函数使用的标准字典

        @param {Request} request - web服务器的请求对象
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
                    query: {},  # 请求的url参数字典, 由'aa=xx&bb=xx'这个形式的url参数解析得到
                    url: '', # 当前请求的完整url
                },
                'headers': {
                    ...  # 字典形式的通讯协议头信息
                },
                'msg': ...  # 报文内容, 根据不同转换规则可能转换为不同的格式
            }
        """
        # 报文头的处理, key统一转换为小写格式
        _headers = {}
        for _key, _val in request.headers.items():
            _headers[_key.lower()] = _val

        # 连接信息和报文头处理
        _std_request = {
            'network': {
                'host': request.host, 'path': request.path, 'ip': request.ip, 'port': request.port,
                'method': request.method, 'url': request.url,
                'query': RouterTools.get_query_dict(
                    request.query_string, value_trans_mapping=value_trans_mapping
                )
            },
            'headers': _headers
        }
        # 报文内容处理
        if len(request.body) == 0:
            _std_request['msg'] = None
        else:
            _std_request['msg'] = request.json

        # 返回标准化后的结果
        return _std_request

    def format_response(self, request: Request, response: dict, is_std_request: bool = False) -> dict:
        """
        将处理函数返回的值转换为web服务器的标准形式

        @param {dict} request - web服务器的请求对象或格式化以后的标准请求对象
        @param {dict} response - 返回标准化对象, 格式为:
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
        if response is None:
            return None

        # 处理标准返回内容
        _response = {
            'network': {
                'status': 200
            },
            'headers': {
                'Content-Type': 'application/json;charset:utf-8;'
            },
            'msg': {
                'head': self.get_response_head(request, is_std_request)
            }
        }

        # 更新信息
        _response['network'].update(response.get('network', {}))
        _response['headers'].update(response.get('headers', {}))
        _response['msg']['head'].update(response.get('msg', {}).get('head', {}))
        if response.get('msg', {}).get('body', None) is not None:
            _response['msg']['body'] = response['msg']['body']

        return _response

    def format_exception(self, request: Union[Request, dict], exception: Exception, service_config: dict = {}, is_std_request: bool = False) -> dict:
        """
        执行处理过程出现异常情况时的返回值

        @param {Request|dict} request - 如果是在完成请求标准化前, 返回的是web请求对象; 如果是在完成请求标准化后
        @param {Exception} exception - 抛出的异常对象
        @param {dict} service_config={} - 服务配置信息
        @param {bool} is_std_request=False - 指示request对象是否标准请求对象

        @returns {dict} - 标准响应信息字典(对response对象进行标准化转换处理)
        """
        _response = {
            'network': {
                'status': 200
            },
            'headers': {
                'Content-Type': 'application/json;charset:utf-8;'
            },
            'msg': {
                'head': self.get_response_head(request, is_std_request)
            }
        }
        _response['msg']['head'].update({
            'errCode': '21599',
            'errMsg': 'other application failure',
            'errModule': '%s-%s' % (
                service_config.get('sys_id', ''), service_config.get('module_id', '')
            )
        })

        return _response

    def generate_web_response(self, std_response: dict) -> HTTPResponse:
        """
        基于标准返回对象生成适配web服务器的响应对象

        @param {dict} std_response - 标准响应报文字典

        @returns {HTTPResponse} - 适配web服务器的响应对象
        """
        return json(
            std_response.get('msg', None),
            status=std_response.get('network', {}).get('status', 200),
            headers=std_response.get('headers', None)
        )

    #############################
    # 辅助函数
    #############################

    def get_response_head(self, request: Request, is_std_request: bool) -> dict:
        """
        从请求对象中获取响应报文的标准报文头信息

        @param {Request} request - web服务器的请求对象
        @param {bool} is_std_request - 指示request对象是否标准请求对象

        @returns {dict} - 标准响应报文头信息
        """
        if is_std_request:
            if request is None:
                _req_head = {}
            else:
                _req_head = request.get('msg', {}).get('head', {})
        else:
            _req_head = request.json.get('head', {})

        return {
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


class SanicCommonServerFormater(ServerFormaterAdapter):
    """
    通用请求返回的Sanic服务端适配实现
    """

    #############################
    # 需实现类重载的公共函数
    #############################
    def format_request(self, request: Request, value_trans_mapping: dict = None) -> dict:
        """
        将web服务器的请求对象格式化为处理函数使用的标准字典

        @param {Request} request - web服务器的请求对象
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
        # 报文头的处理, key统一转换为小写格式
        _headers = {}
        for _key, _val in request.headers.items():
            _headers[_key.lower()] = _val

        # 连接信息和报文头处理
        _std_request = {
            'network': {
                'host': request.host, 'path': request.path, 'ip': request.ip, 'port': request.port,
                'method': request.method,
                'query': RouterTools.get_query_dict(
                    request.query_string, value_trans_mapping=value_trans_mapping
                )
            },
            'headers': _headers
        }
        # 报文内容处理
        if len(request.body) == 0:
            _std_request['msg'] = None
        elif _headers.get('content-type', '').startswith('application/json'):
            _std_request['msg'] = request.json
        else:
            _std_request['msg'] = request.body

        # 返回标准化后的结果
        return _std_request

    def format_response(self, request: Request, response: dict, is_std_request: bool = False) -> dict:
        """
        将处理函数返回的值转换为web服务器的标准形式

        @param {Request} request - web服务器的请求对象
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
        if response is None:
            return None

        # 标准返回内容
        _response = {
            'network': {
                'status': 200
            },
            'headers': None,
            'msg': None
        }
        _response.update(response)

        return _response

    def format_exception(self, request: Request, exception: Exception, service_config: dict = {}, is_std_request: bool = False) -> dict:
        """
        执行处理过程出现异常情况时的返回值

        @param {Request} request - web服务器的请求对象
        @param {Exception} exception - 抛出的异常对象
        @param {dict} service_config={} - 服务配置信息
        @param {bool} is_std_request=False - 指示request对象是否标准请求对象

        @returns {dict} - 标准响应信息字典(对response对象进行标准化转换处理)
        """
        _response = {
            'network': {
                'status': 500
            },
            'headers': {
                'Content-Type': 'application/json;charset:utf-8;'
            },
            'msg': {
                'errCode': '21599',
                'errMsg': 'other application failure'
            }
        }
        return _response

    def generate_web_response(self, std_response: dict) -> HTTPResponse:
        """
        基于标准返回对象生成适配web服务器的响应对象

        @param {dict} std_response - 标准响应报文字典

        @returns {HTTPResponse} - 适配web服务器的响应对象
        """
        return json(
            std_response.get('msg', None),
            status=std_response.get('network', {}).get('status', 200),
            headers=std_response.get('headers', None)
        )
