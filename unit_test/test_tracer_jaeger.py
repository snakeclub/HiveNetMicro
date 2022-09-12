#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
测试jaeger调用链适配器

@module test_tracer_jaeger
@file test_tracer_jaeger.py
"""

import os
import sys
import time
import unittest
from HiveNetCore.utils.run_tool import AsyncTools
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetMicro.plugins.tracer_jaeger import JaegerTracerAdapter
from HiveNetMicro.core.global_manager import GlobalManager
from HiveNetMicro.core.logger_manager import LoggerManager


# 初始化适配器
logger_manager = LoggerManager(
    os.path.join(os.path.dirname(__file__), 'logs')
)
logger = logger_manager.create_logger(
    'jaeger_test',
    {'config_json_str': None, 'logfile_path': 'test_jaeger_tracer.log', 'logger_name': 'Console'}
)
GlobalManager.SET_SYS_LOGGER(logger)

GlobalManager.SET_GLOBAL_CONFIG({
    'app_config': {
        'app_name': 'test_app'
    }
})


class TestJaegerTracer(unittest.TestCase):
    """
    测试jaeger调用链适配器
    """

    def test_jaeger_tracer_method(self):
        # 测试对方法的修饰符功能
        adapter = JaegerTracerAdapter(
            tracer_config={
                'config': {
                    'logging': True,
                    'local_agent': {
                        'reporting_host': '127.0.0.1', 'reporting_port': 6831
                    },
                    'sampler': {
                        'type': 'const', 'param': 1
                    },
                    'tags': {
                        'test_tags1': 'tags1',
                        'test_tags2': 'tags2'
                    }
                },
                'validate': True,
                'use_prometheus_metrics': True
            },
            trace_options={
                'trace_all_exception': True
            },
            logger_id='jaeger_test'
        )

        # 测试开启新的Span
        # 开启一个新Span, 但不设置为当前激活Span
        with adapter.start_span('test_start_span') as _span:
            _active_span = adapter.get_active_span()
            self.assertTrue(_active_span is None and _span is not None, msg='start no active span error')

        # 开启一个新Span, 同时设置为当前激活Span
        with adapter.start_active_span('test_start_span') as _scope:
            _active_span = adapter.get_active_span()
            self.assertTrue(_active_span is not None and _scope.span == _active_span, msg='start active span error')

        # 默认开启的Span是当前激活Span的子Span
        with adapter.start_active_span('test_start_span') as _scope:
            with adapter.start_span('test_start_span') as _span:
                self.assertTrue(_span.parent_id == _scope.span.span_id, msg='test child of active span error')

        # 忽略激活的Span
        with adapter.start_active_span('test_start_span') as _scope:
            with adapter.start_span('test_start_span', ignore_active_span=True) as _span:
                self.assertTrue(_span.parent_id is None, msg='test ignore active span error')

        # 测试上下文传播
        with adapter.start_active_span('test_start_span') as _scope:
            # 注意仅支持字符串
            adapter.set_baggage('baggage_a', 'ba', span=_scope.span)
            adapter.set_baggage('baggage_int', 1, span=_scope.span)
            adapter.set_baggage('baggage_float', 0.1, span=_scope.span)
            adapter.set_baggage('baggage_dict', {}, span=_scope.span)

            headers = {}
            adapter.inject_to_call('http_headers', headers)
            self.assertTrue(
                headers.get('uber-trace-id', None) is not None and headers.get('uberctx-baggage_a', '') == 'ba',
                msg='test inject_to_call error'
            )
            _span_ctx = adapter.extract_from_call('http_headers', headers)
            self.assertTrue(
                _scope.span.trace_id == _span_ctx.trace_id and _span_ctx._baggage.get('baggage_a', '') == 'ba',
                msg='test extract_from_call error'
            )

        # 测试baggage的传播范围
        with adapter.start_active_span('test_start_span') as _scope:
            adapter.set_baggage('baggage_a', 'ba', span=_scope.span)
            adapter.set_baggage('baggage_int', 1, span=_scope.span)
            adapter.set_baggage('baggage_float', 0.1, span=_scope.span)
            adapter.set_baggage('baggage_dict', {}, span=_scope.span)

            with adapter.start_span('test_start_span', ignore_active_span=False) as _span:
                # 激活Span的子Span自动包含baggage
                self.assertTrue(
                    _span.context._baggage.get('baggage_a', '') == 'ba', msg='test active span baggage 1 error'
                )

            with adapter.start_span('test_start_span', child_of=_scope.span.context, ignore_active_span=True) as _span:
                # 非激活子Span自动包含baggage
                self.assertTrue(
                    _span.context._baggage.get('baggage_a', '') == 'ba', msg='test active span baggage 2 error'
                )

            # 通过信息载体传递
            headers = {}
            adapter.inject_to_call('http_headers', headers)
            _span_ctx = adapter.extract_from_call('http_headers', headers)
            with adapter.start_span('test_start_span', child_of=_span_ctx, ignore_active_span=True) as _span:
                # 非激活子Span自动包含baggage
                self.assertTrue(
                    _span.context._baggage.get('baggage_a', '') == 'ba', msg='test active span baggage 3 error'
                )

        # 测试函数修饰符
        @adapter.trace_method_async(
            operation_name_para='short_name:',
            tag_paras={'tag_paras_param1': 'args:0'}, resp_tag_paras={
                'resp_code': 'json: $.code',
                'resp_fun': 'json: $.fun'
            }
        )
        def test_wrap_method_inner(para1) -> dict:
            print('run test_wrap_method_inner: %s' % str(
                {
                    'para1': para1
                }
            ))

            # 获取当前激活的Span，获取到全局的baggage字典
            _active_span = adapter.get_active_span()
            print('span baggages: ', _active_span.context.baggage)

            return {'code': '00001', 'fun': 'test_wrap_method_inner'}

        @adapter.trace_method_async(
            operation_name_para='name:',
            tag_paras={
                'tag_paras_param1': 'args:0',
                'tag_paras_param2': 'args:1',
                'tag_paras_kwparam1': 'kwargs:kw1',
                'tag_paras_kwparam2': 'kwargs:kw2',
            },
            baggage_paras={
                'baggage_param1': 'args:0',
                'baggage_const': 'const: test'
            },
            resp_tag_paras={
                'resp_code': 'json: $.code',
                'resp_fun': 'json: $.fun'
            },
            trace_all_exception=None, trace_exceptions=None,
            get_return_error_func=None
        )
        def test_wrap_method_outer(para1, para2, kw1='kw1val', kw2='kw2val') -> dict:
            print('run test_wrap_method: %s' % str(
                {
                    'para1': para1, 'para2': para2, 'kw1': kw1, 'kw2': kw2
                }
            ))
            # 调用内部函数
            AsyncTools.sync_call(test_wrap_method_inner, 'callP1')
            return {'code': '00000', 'fun': 'test_wrap_method'}

        @adapter.trace_method_async(
            trace_all_exception=True
        )
        def test_wrap_method_exception(para1):
            raise RuntimeError('throw error')

        # 执行函数
        try:
            AsyncTools.sync_call(test_wrap_method_exception, 10)
        except:
            print('raise error')

        _ret = AsyncTools.sync_call(test_wrap_method_outer, 'p1', 'p2', kw1='kw1newval', kw2='kw2newval')
        print(_ret)

        # 等待打包推送
        time.sleep(2)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
