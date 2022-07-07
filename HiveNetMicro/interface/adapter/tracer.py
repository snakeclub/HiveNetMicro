#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
调用链适配器

@module tracer
@file tracer.py
"""
import os
import sys
import copy
import inspect
import json
import time
from functools import wraps
from inspect import isawaitable
import traceback
from typing import List, Callable, Any, Union
from pyjsonpath import JsonPath
import opentracing
from opentracing.ext import tags
from HiveNetCore.utils.run_tool import RunTool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.adapter_base import AdapterBaseFw
from HiveNetMicro.core.global_manager import GlobalManager
from HiveNetMicro.core.logger_manager import LoggerManager


class TracerAdapter(AdapterBaseFw):
    """
    调用链适配器
    """
    #############################
    # 参数表达式说明
    # 在TracerAdapter的很多配置上都可以通过参数表达式来动态获取指定的参数值
    # 表达式的格式固定为 "参数类型:取值字符串", 以下为所有支持的参数类型和说明:
    #   const - 固定字符串, 例如: "const:MyName"所取到的值为"MyName"
    #   name - 获取函数完整名称, 名称中包括模块、类名, 例如"name:"所取到的值为"test_moudle.MyClass.func"
    #   short_name - 获取函数短名称(只有函数名本身), 例如"short_name:"所取到的值为"func"
    #   args - 获取函数入参的固定位置的传值, 例如"args:0"获取函数固定入参的第1个参数(注意对于请求函数第0个参数固定为请求对象)
    #   kwargs - 获取函数入参的kv参数的传值, 例如"kwargs:kvname"获取key值为kvname的传值
    #   network - 获取标准请求/响应对象的network字典的指定值(网络连接信息), 例如"network:key"获取network字典中的key对应的值
    #   head - 获取标准请求/响应对象的协议报文头字典的指定值, 例如"head:key"获取协议报文头字典中的key对应的值
    #   json - 获取标准请求/响应对象的报文体(JSON格式)的指定值, 取值字符串为JsonPath查找字符串, 根目录固定为对象的msg字典
    #          例如: "json:$.key1.key2"获取请求/响应对象obj['msg'][key1][key2]的节点信息
    #############################

    #############################
    # 适配器基础属性
    #############################
    @property
    def adapter_type(self) -> str:
        """
        适配器类型

        @property {str} - 指定适配器类型
        """
        return 'Tracer'

    #############################
    # 静态工具函数
    #############################
    @classmethod
    def get_object_class_name(cls, obj) -> str:
        """
        获取对象的类名

        @param {Any} obj - 要获取类名的对象

        @returns {str} - 返回类名字符串
        """
        _module_name = inspect.getmodule(obj.__class__).__name__
        if _module_name == 'builtins':
            _module_name = ''
        else:
            _module_name = _module_name + '.'

        return '%s%s' % (_module_name, obj.__class__.__name__)

    @classmethod
    def get_func_by_config(cls, plugin_config: dict):
        """
        通过插件配置获取函数对象

        @param {dict} plugin_config - 插件配置
        """
        if plugin_config is None:
            # 没有配置
            return None

        _lib_loader = RunTool.get_global_var('SYS_LIB_LOADER')
        _plugins_path = RunTool.get_global_var('SYS_BASE_CONFIG')['plugins_path']
        return _lib_loader.load_by_config(plugin_config, _plugins_path)

    #############################
    # 构造函数
    #############################
    def __init__(self, tracer_config: dict = {}, trace_options: dict = {}, logger_id: str = None):
        """
        初始化适配器

        @param {dict} tracer_config={} - 具体的Tracer实现对象的初始化参数, 根据不同的适配器自定义
        @param {dict} trace_options={} - 调用链追踪参数
            request_tag_paras {dict} - 需要从请求对象获取并放入Tags的参数字典
                每个参数的key为要送入Tags的标识名, value为参数表达式
            request_baggage_paras {dict} - 需要从请求对象获取并放入SpanContext中Baggage传递到后续调用的参数字典
                key为要送入Baggage的标识名, value为参数表达式
            response_tag_paras {dict} - 需要从需处理函数的返回对象获取并放入Tags的的参数字典
                每个参数的key为要送入Tags的标识名, value为参数表达式
            trace_all_exception {bool} - 是否记录所有异常错误(默认为True), 如果为False则按照trace_exceptions所设定的异常类型进行记录
            trace_exceptions {List[str]} - 要记录的异常错误清单, 字符格式, 包含模块名
            get_response_error_func {Callable|dict} - 判断请求函数返回值是否错误的自定义函数, 或插件加载配置
                函数格式为 func(response_obj) -> None|Exception|str
                注: 如果检查通过返回None, 检查不通过返回特定的Exception对象或错误描述字符串
            tracer_close_wait_time {float} - tracer对象关闭后等待剩余调用链信息推送的等待时间, 单位为秒, 默认2.0
        @param {str} logger_id=None - 日志对象标识, 可以选择application.yaml配置中的其中一个日志对象
        """
        # 处理参数
        self._tracer_config = tracer_config
        self._trace_options = trace_options

        self._request_tag_paras = self._trace_options.get('request_tag_paras', {})
        if self._request_tag_paras is None:
            self._request_tag_paras = {}
        self._request_baggage_paras = self._trace_options.get('request_baggage_paras', {})
        if self._request_baggage_paras is None:
            self._request_baggage_paras = {}
        self._response_tag_paras = self._trace_options.get('response_tag_paras', {})
        if self._response_tag_paras is None:
            self._response_tag_paras = {}

        self._trace_all_exception = self._trace_options.get('trace_all_exception', True)
        self._trace_exceptions = self._trace_options.get('trace_exceptions', [])
        if self._trace_exceptions is None:
            self._trace_exceptions = []

        self._get_response_error_func = self._trace_options.get('get_response_error_func', None)
        if type(self._get_response_error_func) == dict:
            # 支持配置方式处理
            self._get_response_error_func = self.get_func_by_config(self._get_response_error_func)

        # 通用的参数
        _global_config = GlobalManager.GET_GLOBAL_CONFIG()
        if _global_config is None:
            _global_config = {}

        self.service_name = _global_config.get('app_config', {}).get('app_name', 'noAppName')

        # 日志对象
        _logger_manager: LoggerManager = GlobalManager.GET_SYS_LOGGER_MANAGER()
        if _logger_manager is None:
            _logger_manager = LoggerManager('')
        self.logger = _logger_manager.get_logger(logger_id, none_with_default_logger=True)

        # 初始化Tracer
        self.tracer = self._generate_tracer()

        # 存储Span对象的字典, 用于切换不同执行函数范围的Span
        # key为Span对应的request对象的string格式, value为包含Span的Scope对象
        self._current_scopes = {}

    def __del__(self):
        """
        删除对象时需要执行的函数
        """
        # 将缓存的调用链信息推送到服务端
        self.tracer.close()

        # 等待
        time.sleep(self._trace_options.get('tracer_close_wait_time', 2))

    #############################
    # 属性
    #############################
    @property
    def native_tracer(self):
        """
        获取原生的Tracer实例对象
        @property {opentracing.Tracer}
        """
        return self.tracer

    #############################
    # 公共函数
    #############################
    def get_active_span(self) -> opentracing.Span:
        """
        获取当前激活的Span对象

        @returns {opentracing.Span} - 当前激活的Span对象
            注: 如果当前没有Span返回None
        """
        return self.tracer.active_span

    def start_span(self, operation_name: str, child_of: Union[opentracing.Span, opentracing.SpanContext] = None,
            ignore_active_span: bool = False) -> opentracing.Span:
        """
        生成一个新的Span对象(不设置为当前进程激活的Span)

        @param {str} operation_name - 操作名
        @param {opentracing.Span | opentracing.SpanContext} child_of=None - 指定父Span或父Span的上下文对象
            注: 如果无父Span可以不传该值
        @param {bool} ignore_active_span=False - 是否忽略当前进程激活Span
            注: 默认新打开的Span是当前进程激活Span的子Span, 但将该参数设置为True, 则开启一个新的根Span

        @returns {opentracing.Span} - 返回打开的Span对象
        """
        return self.tracer.start_span(
            operation_name=operation_name, child_of=child_of, ignore_active_span=ignore_active_span
        )

    def start_active_span(self, operation_name: str, child_of: Union[opentracing.Span, opentracing.SpanContext] = None,
            ignore_active_span: bool = False) -> opentracing.Scope:
        """
        生成一个新的Span对象(设置为当前进程激活的Span)

        @param {str} operation_name - 操作名
        @param {opentracing.Span | opentracing.SpanContext} child_of=None - 指定父Span或父Span的上下文对象
            注: 如果无父Span可以不传该值
        @param {bool} ignore_active_span=False - 是否忽略当前进程激活Span
            注: 默认新打开的Span是当前进程激活Span的子Span, 但将该参数设置为True, 则开启一个新的根Span

        @returns {opentracing.Scope} - 返回该Span所在的Scope(作用范围)对象
            注: 如果要获取Span对象, 可以从Scope对象的span属性获取
        """
        return self.tracer.start_active_span(
            operation_name=operation_name, child_of=child_of, ignore_active_span=ignore_active_span
        )

    def set_tag(self, tag_name: str, tag_val: Union[str, bool, int, float], span: opentracing.Span = None) -> opentracing.Span:
        """
        在当前激活的Span上设置Tags

        @param {str} tag_name - 要设置的tag标识
        @param {str|bool|int|float} tag_val - 要设置的值
        @param {opentracing.Span} span=None - 指定要设置tag的Span对象
            注: 如果传None, 代表自动尝试获取当前激活Span

        @returns {opentracing.Span} - 当前激活的Span对象
        """
        _span = span
        if span is None:
            _span = self.tracer.active_span

        if _span is not None:
            _tag_val = tag_val
            _type = type(tag_val)
            if _type in (dict, tuple, list):
                # 转换为json字符串
                _tag_val = json.dumps(
                    tag_val, ensure_ascii=False
                )
            return _span.set_tag(tag_name, _tag_val)

    def set_baggage(self, itme_name: str, itme_val: str, span: opentracing.Span = None) -> opentracing.Span:
        """
        在当前激活的Span上设置Baggage(传递到下一次调用)

        @param {str} itme_name - 要设置的Baggage Item标识
        @param {str} itme_val - 要设置的Baggage Item的值
            注: 仅支持字符串
        @param {opentracing.Span} span=None - 指定要设置tag的Span对象
            注: 如果传None, 代表自动尝试获取当前激活Span

        @returns {opentracing.Span} - 当前激活的Span对象
        """
        _span = span
        if span is None:
            _span = self.tracer.active_span

        if _span is not None:
            _itme_val = itme_val
            _type = type(itme_val)
            if _type in (dict, tuple, list):
                # 转换为json字符串
                _itme_val = json.dumps(
                    itme_val, ensure_ascii=False
                )
            elif type(itme_val) != str:
                _itme_val = str(itme_val)

            return _span.set_baggage_item(itme_name, _itme_val)

    def get_baggage(self) -> dict:
        """
        获取Span上的Baggage(上下文)字典

        @returns {dict} - 返回的Baggage(上下文)字典
        """
        span = self.tracer.active_span
        _baggage = None
        if span is not None:
            _baggage = span.context.baggage

        if _baggage is None:
            _baggage = {}

        return _baggage

    def get_baggage_item(self, itme_name: str, default: str = None) -> str:
        """
        获取Span上的Baggage(上下文)指定项的值

        @param {str} itme_name - 指定项的名称
        @param {str} default=None - 如果获取不到的默认值

        @returns {str} - 返回值
        """
        span = self.tracer.active_span
        _val = None
        if span is not None:
            _val = span.get_baggage_item(itme_name)

        if _val is None:
            _val = default

        return _val

    def log_kv(self, key_values: dict) -> opentracing.Span:
        """
        在当前激活的Span上记录key_value日志事件

        @param {dict} key_values - 要设置的key_values事件字典

        @returns {opentracing.Span} - 当前激活的Span对象
        """
        span = self.tracer.active_span
        if span is not None:
            return span.log_kv(key_values)

    def inject_to_call(self, format: str, carrier: Any) -> Any:
        """
        注入SpanContext(上下文)到请求载体

        @param {str} format - 格式化类型, 例如 opentracing.Format.HTTP_HEADERS
        @param {Any} carrier - 要注入上下文的载体对象
        """
        span = self.tracer.active_span
        if span is not None:
            return self.tracer.inject(span.context, format, carrier)

    def extract_from_call(self, format: str, carrier: Any) -> opentracing.SpanContext:
        """
        从请求载体中获取注入的SpanContext(上下文)

        @param {str} format - 格式化类型, 例如 opentracing.Format.HTTP_HEADERS
        @param {Any} carrier - 注入上下文的载体对象

        @returns {opentracing.SpanContext} - 上下文对象
        """
        return self.tracer.extract(format, carrier)

    def get_wrapped_request_func_async(self, func, trace_options: dict):
        """
        获取包裹了请求调用链处理修饰符的函数对象
        注: 支持修饰同步及异步函数, 但修饰后函数需按异步函数执行

        @param {function} func - 需要处理的函数对象
        @param {dict} trace_options - 调用链参数

        @returns {function} - 包裹调用链处理修饰符后的函数对象
        """
        # 处理调用链参数
        _trace_options = {} if trace_options is None else copy.deepcopy(trace_options)
        if _trace_options.get('operation_name_para', None) is None:
            _trace_options['operation_name_para'] = 'name:'

        if _trace_options.get('get_response_error_func', None) is not None:
            _trace_options['get_response_error_func'] = self.get_func_by_config(
                _trace_options.get('get_response_error_func', None)
            )

        # 因为进行了封装, 所以要将函数取名的情况换成固定值
        if _trace_options['operation_name_para'] in ('name:', 'short_name:'):
            _name = RunTool.get_function_name(func, is_with_class=True, is_with_module=True)
            if _trace_options['operation_name_para'] == 'name:':
                _trace_options['operation_name_para'] = 'const:%s' % _name
            else:
                _last_index = _name.rfind('.')
                if _last_index >= 0:
                    _short_name = _name[_last_index + 1:]
                else:
                    _short_name = _name
                _trace_options['operation_name_para'] = 'const:%s' % _short_name

        # 包裹修饰函数
        @self.trace_request_async(**_trace_options)
        async def wraped_func(*args, **kwargs):
            _resp = func(*args, **kwargs)
            if isawaitable(_resp):
                _resp = await _resp
            return _resp

        return wraped_func

    #############################
    # 修饰符
    #############################
    def trace_request_async(
        self, operation_name_para: str = 'name:', self_tag_paras: dict = None,
        self_baggage_paras: dict = None, self_resp_tag_paras: dict = None,
        trace_all_exception: bool = None, trace_exceptions: List[str] = None,
        get_response_error_func: Callable = None
    ):
        """
        请求处理函数的trace追踪修饰符
        注: 支持修饰同步及异步函数, 但修饰后需按异步函数执行

        @param {str} operation_name_para=None - 要获取的操作名称的参数, 格式为参数表达式
        @param {dict} self_tag_paras=None - 当前函数自有的放入Tags的参数字典, 将覆盖实例公共的参数字典
            每个参数的key为要送入Tags的标识名, value为参数表达式
        @param {dict} self_baggage_paras=None - 当前函数自有的放入SpanContext中Baggage传递到后续调用的参数字典,
            将覆盖实例公共的参数字典, key为要送入Baggage的标识名, value为参数表达式
        @param {dict} self_resp_tag_paras=None - 当前函数自有的需放入Tags的response信息的参数字典, 将覆盖实例公共的参数字典
            每个参数的key为要送入Tags的标识名, value为参数表达式
        @param {bool} trace_all_exception=None - 是否记录所有异常错误, 如果为False则按照trace_exceptions所设定的异常类型进行记录
            注: 如果为None代表根据实例初始化时定义的参数处理
        @param {List[str]} trace_exceptions=[] - 要记录的异常错误清单, 字符格式, 包含模块名
        @param {Callable} get_response_error_func=None - 判断请求返回值是否错误的自定义函数
            函数格式为 func(response_obj) -> None|Exception|str
            注: 如果检查通过返回None, 检查不通过返回特定的Exception对象或错误描述字符串
        """
        def decorator(f):
            @wraps(f)
            async def decorated_function(*args, **kwargs):
                # 获取函数信息, 执行执行调用前的trace处理
                method_info_obj = self._get_method_info_obj(f, args, kwargs)
                self._before_request_fn(
                    method_info_obj, operation_name_para=operation_name_para,
                    tag_paras=self_tag_paras,
                    baggage_paras=self_baggage_paras,
                    is_request=True
                )

                try:
                    # 执行请求处理函数
                    _response = f(*args, **kwargs)
                    if isawaitable(_response):
                        _response = await _response

                    # 判断返回值是否错误
                    _error = None
                    _get_response_error_func = get_response_error_func if get_response_error_func is not None else self._get_response_error_func
                    if _get_response_error_func is not None:
                        _error = _get_response_error_func(_response)

                    # 处理返回值的trace处理
                    self._after_request_fn(
                        method_info_obj, _response, tag_paras=self_resp_tag_paras, error=_error,
                        is_request=True
                    )

                    # 返回处理结果
                    return _response
                except Exception as e:
                    _trace_all_exception = self._trace_all_exception if trace_all_exception is None else trace_all_exception
                    _trace_exceptions = self._trace_exceptions if trace_exceptions is None else trace_exceptions
                    if _trace_all_exception or (_trace_exceptions and self.get_object_class_name(e) in trace_exceptions):
                        # 遇到需要追踪的特定错误时, 需要记录问题
                        self._after_request_fn(
                            method_info_obj, None, error=e, is_request=True
                        )
                    raise

            return decorated_function

        return decorator

    def trace_method_async(
        self, operation_name_para: str = 'name:', tag_paras: dict = None,
        baggage_paras: dict = None, resp_tag_paras: dict = None,
        trace_all_exception: bool = None, trace_exceptions: List[str] = None,
        get_return_error_func: Callable = None
    ):
        """
        普通函数的trace追踪修饰符
        注: 支持修饰同步及异步函数, 但修饰后需按异步函数执行

        @param {str} operation_name_para=None - 要获取的操作名称的参数, 格式为参数表达式
        @param {dict} tag_paras=None - 需放入Tags的参数字典
            每个参数的key为要送入Tags的标识名, value为参数表达式
        @param {dict} baggage_paras=None - 需放入SpanContext中Baggage传递到后续调用的参数字典,
            key为要送入Baggage的标识名, value为参数表达式
        @param {dict} resp_tag_paras=None - 当前函数自有的需放入Tags的response信息的参数字典
            每个参数的key为要送入Tags的标识名, value为参数表达式
        @param {bool} trace_all_exception=None - 是否记录所有异常错误, 如果为False则按照trace_exceptions所设定的异常类型进行记录
        @param {List[str]} trace_exceptions=None - 要记录的异常错误清单, 字符格式, 包含模块名
        @param {Callable} get_return_error_func=None - 判断请求返回值是否错误的自定义函数
            函数格式为 func(return_obj) -> None|Exception|str
            注: 如果检查通过返回None, 检查不通过返回特定的Exception对象或错误描述字符串
        """
        def decorator(f):
            @wraps(f)
            async def decorated_function(*args, **kwargs):
                # 获取函数信息, 执行执行调用前的trace处理
                method_info_obj = self._get_method_info_obj(f, args, kwargs)
                self._before_request_fn(
                    method_info_obj, operation_name_para=operation_name_para,
                    tag_paras=tag_paras,
                    baggage_paras=baggage_paras,
                    is_request=False
                )

                try:
                    # 执行请求处理函数
                    _response = f(*args, **kwargs)
                    if isawaitable(_response):
                        _response = await _response

                    # 判断返回值是否错误
                    _error = None
                    if get_return_error_func is not None:
                        _error = get_return_error_func(_response)

                    # 处理返回值的trace处理
                    self._after_request_fn(
                        method_info_obj, _response, tag_paras=resp_tag_paras, error=_error, is_request=False
                    )

                    # 返回处理结果
                    return _response
                except Exception as e:
                    if trace_all_exception or (trace_exceptions and self.get_object_class_name(e) in trace_exceptions):
                        # 遇到需要追踪的特定错误时, 需要记录问题
                        self._after_request_fn(
                            method_info_obj, None, error=e, is_request=False
                        )
                    raise

            return decorated_function

        return decorator

    #############################
    # 内部函数
    #############################
    def _before_request_fn(
        self,
        method_info_obj: dict,
        operation_name_para: str = 'name:',
        tag_paras: dict = None,
        baggage_paras: dict = None,
        is_request: bool = True
    ):
        """
        请求处理前要执行的trace处理函数

        @param {dict} method_info_obj - 要处理的函数信息字典
        @param {str} operation_name_para=None - 要获取的操作名称的参数, 格式为参数表达式
        @param {dict} tag_paras=None - 需放入Tags的参数字典
            每个参数的key为要送入Tags的标识名, value为参数表达式
        @param {dict} baggage_paras=None - 需放入SpanContext中Baggage传递到后续调用的参数字典,
            key为要送入Baggage的标识名, value为参数表达式
        @param {bool} is_request=True - 是否请求处理函数, 如果为False代表是普通函数处理
        """
        obj_type = 'req' if is_request else 'para'
        operation_name = self._get_obj_info(
            obj_type, method_info_obj, operation_name_para, default='getNameError'
        )

        # 创建包含Span的Scope对象
        if is_request:
            # 网络请求, 每次都是开启一个新的Span
            try:
                span_ctx = self.tracer.extract(
                    *self._get_extract_para(method_info_obj['parameters'].get('_P0', {}))
                )
                scope = self.tracer.start_active_span(
                    operation_name, child_of=span_ctx, ignore_active_span=True
                )
            except (
                opentracing.InvalidCarrierException,
                opentracing.SpanContextCorruptedException,
            ):
                # 无法获取到SpanContext的情况, 创建一个包含新Span的Scope对象
                scope = self.tracer.start_active_span(
                    operation_name, ignore_active_span=True
                )
        else:
            # 获取当前进程的激活Span
            scope = self.tracer.start_active_span(operation_name, child_of=self.tracer.active_span)

        self._current_scopes[id(method_info_obj)] = scope

        span = scope.span
        # 设置Tags
        if is_request:
            # 覆盖实例默认要设置的参数
            _tag_paras = copy.deepcopy(self._request_tag_paras)
            _tag_paras.update(
                {} if tag_paras is None else tag_paras
            )
        else:
            _tag_paras = {} if tag_paras is None else tag_paras

        for _tag_name, _tag_para in _tag_paras.items():
            _tag_value = self._get_obj_info(obj_type, method_info_obj, _tag_para)
            if _tag_value is not None:
                self.set_tag(_tag_name, _tag_value, span=span)

        # 设置Baggage
        if is_request:
            # 覆盖实例默认要设置的参数
            _baggage_paras = copy.deepcopy(self._request_baggage_paras)
            _baggage_paras.update(
                {} if baggage_paras is None else baggage_paras
            )
        else:
            _baggage_paras = {} if baggage_paras is None else baggage_paras

        for _baggage_name, _baggage_para in _baggage_paras.items():
            _baggage_value = self._get_obj_info(obj_type, method_info_obj, _baggage_para)
            if _baggage_value is not None:
                self.set_baggage(_baggage_name, _baggage_value, span=span)

    def _after_request_fn(
        self, method_info_obj: dict, response_obj: Any, tag_paras: dict = None,
        error: Union[Exception, str] = None, is_request: bool = True
    ):
        """
        请求处理后要执行的trace处理函数

        @param {dict} method_info_obj - 要处理的函数信息字典
        @param {Any} response_obj - 返回信息对象
        @param {dict} tag_paras=None - 当前函数自有的需放入Tags的response信息的参数字典
            每个参数的key为要送入Tags的标识名, value为参数表达式
        @param {Union[Exception, str]} error=None - 错误信息, 如果有传值进来代表响应为失败的情况
        @param {bool} is_request=True - 是否请求处理函数, 如果为False代表是普通函数处理
        """
        # 执行Span的关闭处理
        scope = self._current_scopes.pop(id(method_info_obj), None)
        if scope is None:
            return

        if response_obj is not None:
            span = scope.span
            # 设置Tags, 覆盖实例默认要设置的参数
            if is_request:
                _tag_paras = copy.deepcopy(self._response_tag_paras)
                _tag_paras.update(
                    {} if tag_paras is None else tag_paras
                )
            else:
                _tag_paras = {} if tag_paras is None else tag_paras

            obj_type = 'resp' if is_request else 'return'
            for _tag_name, _tag_para in _tag_paras.items():
                _tag_value = self._get_obj_info(
                    obj_type, response_obj, _tag_para
                )
                if _tag_value is not None:
                    self.set_tag(_tag_name, _tag_value, span=span)

        # 如果有异常, 按照OpenTracing标准设置错误并记录日志
        if error is not None:
            scope.span.set_tag(tags.ERROR, True)
            _stack = traceback.format_exc()
            if type(error) == str:
                scope.span.lo_kv({{"message": error, 'stack': _stack}})
            else:
                scope.span.log_kv({"event": tags.ERROR, "error.object": error, 'stack': _stack})

        # 关闭span
        scope.close()

    def _get_method_info_obj(self, func: Callable, args: tuple, kwargs: dict) -> dict:
        """
        获取函数对象的信息

        @param {Callable} func - 函数对象
        @param {tuple} args - 固定位置入参
        @param {dict} kwargs - key-value形式的入参

        @returns {dict} - 返回的函数对象信息, 格式为:
            {
                'name': '函数名',
                'short_name': '不含模块和类信息的函数名',
                # 函数入参取值索引
                'parameters': {
                    '入参名': 参数值,
                    '_P1': 第2个位置的参数值(从0开始),
                    ...
                }
            }
        """
        parameters = {}
        parameter_defines = RunTool.get_function_parameter_defines(func)
        index = 0  # 当前参数的位置
        args_len = len(args)
        for parameter in parameter_defines:
            name = parameter['name']
            para_type = parameter['type']
            if para_type == 'KEYWORD_ONLY':
                parameters[name] = kwargs.get(
                    name, parameter['default'] if parameter['has_default'] else None
                )
            elif para_type == 'POSITIONAL_OR_KEYWORD':
                if index < args_len:
                    val = args[index]
                else:
                    val = kwargs.get(
                        name, parameter['default'] if parameter['has_default'] else None
                    )
                # 同时具有位置和名字检索
                parameters['_P%d' % index] = val
                if name is not None and name != '':
                    parameters[name] = val
            elif para_type == 'VAR_POSITIONAL':
                # *args位置变量, 增加可变的位置检索
                for var_index in range(index, args_len):
                    parameters['_P%d' % var_index] = args[var_index]
            elif para_type == 'VAR_KEYWORD':
                # **kwargs可变数量的kv形式参数, 将所有key-value的值添加到索引
                for key, val in kwargs.items():
                    if parameters.get(key, None) is None:
                        parameters[key] = val

            # 继续下一个循环
            index += 1

        _name = RunTool.get_function_name(func, is_with_class=True, is_with_module=True)
        _last_index = _name.rfind('.')
        if _last_index >= 0:
            _short_name = _name[_last_index + 1:]
        else:
            _short_name = _name
        method_info_obj = {
            'name': _name,
            'short_name': _short_name,
            'parameters': parameters
        }
        return method_info_obj

    def _get_obj_info(self, obj_type: str, obj: Any, para_str: str, default: Any = None) -> Any:
        """
        从请求或响应对象获取指定参数值的通用函数

        @param {str} obj_type - 对象类型, req-请求对象, resp-请求响应对象, para-函数入参, return-函数返回值
        @param {Any} obj - 如果对象类型为req和para, 送入method_info_obj对象
        @param {str} para_str - 获取参数
        @param {Any} default=None - 如果获取不到所返回的默认值

        @returns {Any} - 返回获取到的结果
        """
        # 解析参数
        get_type = 'const'
        get_para = ''
        index = para_str.find(':')
        if index < 0:
            get_para = para_str.strip()
        elif index == 0:
            get_para = para_str[1:].strip()
        else:
            get_type = para_str[0:index].strip()
            get_para = para_str[index+1:].strip()

        # 获取信息
        if get_type == 'const':
            return get_para
        elif obj_type in ('req', 'para'):
            # 请求对象和函数入参的处理方式一样
            return self._get_obj_info_from_method(
                obj, get_type, get_para, default=default
            )
        elif obj_type == 'resp':
            # 请求返回对象的信息获取
            return self._get_obj_info_from_resp(
                obj, get_type, get_para, default=default
            )
        elif obj_type == 'return':
            return self._get_obj_info_from_return(
                obj, get_type, get_para, default=default
            )
        else:
            # 不支持的类型
            return default

    def _get_obj_info_from_method(self, method_info_obj: dict, get_type: str, get_para: str, default: Any = None) -> Any:
        """
        从函数信息字典中获取指定参数的信息

        @param {dict} method_info_obj - 要处理的函数信息字典
        @param {str} get_type - 获取类型, 支持:
            network - 从第一个参数对象(request对象)中的network下获取指定key信息的值
            head - 从一个参数对象(request对象)中的header下获取指定key信息的值
            json - 从一个参数对象(request对象)中的msg中按json格式获取值, 参数为JsonPath查找字符串
                例如: $.key1.key2 获取obj['msg'][key1][key2]的节点信息
            name - 获取函数名
            args - 获取函数入参指定位置参数值
            kwargs - 获取函数入参指定key值的参数值
        @param {str} get_para - 获取参数
        @param {Any} default=None - 如果获取不到信息, 返回的默认值

        @returns {Any} - 返回获取到的信息值
        """
        try:
            if get_type == 'network':
                return method_info_obj['parameters'].get('_P0', {}).get('network', {}).get(get_para, default)
            elif get_type == 'head':
                return method_info_obj['parameters'].get('_P0', {}).get('headers', {}).get(get_para, default)
            elif get_type == 'name':
                return method_info_obj['name']
            elif get_type == 'short_name':
                return method_info_obj['short_name']
            elif get_type == 'args':
                return method_info_obj['parameters'].get('_P%s' % get_para, default)
            elif get_type == 'kwargs':
                return method_info_obj['parameters'].get(get_para, default)
            elif get_type == 'json':
                # 将消息转为json方式进行处理
                _msg = method_info_obj['parameters'].get('_P0', {}).get('msg', None)
                if _msg is None:
                    return default

                elif type(_msg) == str:
                    _msg = json.loads(_msg)

                # 通过jsonpath方式获取值
                _vals = JsonPath(_msg, get_para).load()
                if len(_vals) == 0:
                    return default
                else:
                    return _vals[0]
            else:
                # 不支持的类型
                return default
        except:
            return default

    def _get_obj_info_from_resp(self, resp_obj: dict, get_type: str, get_para: str, default: Any = None) -> Any:
        """
        从请求返回对象中获取指定参数的信息

        @param {dict} resp_obj - 请求返回对象
        @param {str} get_type - 获取类型, 支持:
            network - 从返回对象中获取服务器信息的值
            head - 从返回对象中获取指定报文头中获取指定key的值
            json - 从返回对象中按json格式获取值, 参数为JsonPath查找字符串
                例如: $.key1.key2 获取obj['msg'][key1][key2]的节点信息
        @param {str} get_para - 获取参数
        @param {Any} default=None - 如果获取不到信息, 返回的默认值

        @returns {Any} - 返回获取到的信息值
        """
        try:
            if get_type == 'network':
                return resp_obj.get('network', {}).get(get_para, default)
            if get_type == 'head':
                return resp_obj.get('head', {}).get(get_para, default)
            elif get_type == 'json':
                # 将消息转为json方式进行处理
                _msg = resp_obj.get('msg', None)
                if _msg is None:
                    return default

                elif type(_msg) == str:
                    _msg = json.loads(_msg)

                # 通过jsonpath方式获取值
                _vals = JsonPath(_msg, get_para).load()
                if len(_vals) == 0:
                    return default
                else:
                    return _vals[0]
            else:
                # 不支持的类型
                return default
        except:
            return default

    def _get_obj_info_from_return(self, ret_obj: Any, get_type: str, get_para: str, default: Any = None) -> Any:
        """
        从函数返回对象中获取指定参数的信息

        @param {Any} ret_obj - 函数返回对象
        @param {str} get_type - 获取类型, 支持:
            json - 从返回对象中按json格式获取值, 参数为JsonPath查找字符串
                例如: $.key1.key2 获取obj['msg'][key1][key2]的节点信息
        @param {str} get_para - 获取参数
        @param {Any} default=None - 如果获取不到信息, 返回的默认值

        @returns {Any} - 返回获取到的信息值
        """
        try:
            if get_type == 'json':
                _json = ret_obj
                if type(ret_obj) == str:
                    _json = json.loads(ret_obj)

                # 通过jsonpath方式获取值
                _vals = JsonPath(_json, get_para).load()
                if len(_vals) == 0:
                    return default
                else:
                    return _vals[0]
            else:
                return default
        except:
            return default

    #############################
    # 需继承类实现的内部函数
    #############################
    def _generate_tracer(self) -> opentracing.Tracer:
        """
        生成opentracing的Tracer具体实现对象

        @returns {Tracer} - Tracer对象
        """
        return opentracing.Tracer()

    def _get_extract_para(self, request: dict) -> tuple:
        """
        获取从请求对象提取SpanContext的参数

        @param {dict} request_obj - 请求对象

        @returns {tuple} - 返回(format, carrier)的字典
            例如: return opentracing.Format.HTTP_HEADERS, headers
        """
        headers = {}
        for k, v in request.get('headers', {}).items():
            headers[k.lower()] = v
        return opentracing.Format.HTTP_HEADERS, headers
