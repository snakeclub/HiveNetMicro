#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
tracer适配器的jaeger实现
注1: 必须安装 jaeger 的python客户端包: pip install jaeger-client
注2: 建议在本地安装jaeger agent, 保证信息传输的可靠性
注2: 参考文档: https://github.com/jaegertracing/jaeger-client-python
注3: https://www.alibabacloud.com/help/zh/doc-detail/90506.htm

@module tracer_jaeger
@file tracer_jaeger.py
"""
import os
import sys
# 自动安装依赖库
from HiveNetCore.utils.pyenv_tool import PythonEnvTools
process_install_jaeger_client = False
while True:
    try:
        import jaeger_client.config
        from jaeger_client import Config
        from jaeger_client.metrics.prometheus import PrometheusMetricsFactory
        break
    except ImportError:
        if process_install_jaeger_client:
            break
        else:
            PythonEnvTools.install_package('jaeger-client')
            process_install_jaeger_client = True
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.interface.adapter.tracer import TracerAdapter


class JaegerTracerAdapter(TracerAdapter):
    """
    tracer适配器的jaeger实现
    """

    #############################
    # 需继承类实现的内部函数
    #############################
    def _generate_tracer(self):
        """
        生成opentracing的Tracer具体实现对象
        tracer_config支持的参数包括:
            config {dict} - jaeger-client的初始化配置
                logging {bool} - 是否启用日志, 默认为False
                local_agent {dict} - 指定JaegerAgent的配置
                    reporting_host {str} - JaegerAgent的访问ip地址, 建议装在本地, 为'127.0.0.1'
                    reporting_port {int} - JaegerAgent的访问端口, 例如6831
                    sampling_port: {int} - JaegerAgent的采用策略获取端口, 例如5778
                    注意: jaeger官方建议为了保证数据可靠性, JaegerClient和JaegerAgent运行在同一台主机内
                sampler {dict} - 客户端采样策略配置
                    type {str} - 采样类型, 默认为'const'
                    param {float} - 采样参数
                    注: 不同的采样类型及参数说明如下:
                    'const' - 常量, 始终对所有traces做出相同的决定, 采样所有跟踪(param=1), 全部不采样(sampler.param=0)
                    'probabilistic' - 概率, 按指定概率随机采样, 例如param=0.1的情况下, 将在10条迹线中大约采样1条
                    'ratelimiting' - 使用漏斗速率限制器来确保以一定的恒定速率对轨迹进行采样, 例如param=2.0时, 它将以每秒2条迹线的速率对请求进行采样
                    'remote' - 采样器会向Jaeger代理咨询有关在当前服务中使用的适当采样策略
                tags {dict} - 当前tracer固定添加到所有span的tags信息(在Process信息中查看)
                reporter_flush_interval {float} - tracer信息提交缓存的间隔时间, 单位为秒, 默认为1秒
                sampling_refresh_interval {float} - sampler为remote的情况下, 轮询jaeger agent以获取适当采样策略的频率, 单位为秒, 默认为60
                generate_128bit_trace_id {bool} - 生成128位的trace_id, 默认为False
                trace_id_header {str} - http头中定义的trace_id项名称, 默认为'uber-trace-id'
                baggage_header_prefix {str} - http头中记录baggage项的前缀字符串, 默认为'uberctx-'
                propagation {str} - Span传播上下文使用的标准格式, 默认为'jaeger', 也支持'b3', 'w3c'
                reporter_batch_size {int} - 报告批量打包发送的包大小, 默认为10
                reporter_queue_size {int} - 报告队列大小限制, 默认为100
            service_name {str} - 追踪日志应用名, 如果不传默认使用当前微服务app配置的应用名
            validate {bool} - 默认为true
            use_prometheus_metrics {bool} - 是否启用开源监控系统Prometheus的指标

        @returns {Tracer} - Tracer对象
        """
        # 准备Tracer的初始化参数
        _config = self._tracer_config.get('config', {})
        if _config.get('logging', False):
            # 启用日志
            if self.logger is not None:
                jaeger_client.config.logger = self.logger

        if _config.get('sampler', None) is None:
            _config['sampler'] = {
                'type': 'const', 'param': 1
            }

        _kwargs = {
            'service_name': self._tracer_config.get('service_name', None),
            'validate': self._tracer_config.get('validate', True)
        }
        if _kwargs['service_name'] is None:
            # 获取当前app的名称
            _kwargs['service_name'] = self.service_name

        # 是否加入开源监控系统Prometheus的性能指标
        if self._tracer_config.get('use_prometheus_metrics', False):
            _kwargs['metrics_factory'] = PrometheusMetricsFactory(
                namespace=_kwargs['service_name']
            )

        _jaeger_config = Config(_config, **_kwargs)
        return _jaeger_config.initialize_tracer()
