#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
测试nacos注册中心适配器

@module test_naming_nacos
@file test_naming_nacos.py
"""

import os
import sys
import unittest
import time
import asyncio
from HiveNetCore.utils.test_tool import TestTool
from HiveNetCore.utils.run_tool import AsyncTools
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetMicro.plugins.adapter.naming_nacos import NacosNamingAdapter
from HiveNetMicro.core.logger_manager import LoggerManager
from HiveNetMicro.core.global_manager import GlobalManager


async def async_sleep(sleep_time: float):
    await asyncio.sleep(sleep_time)


class TestNacosNaming(unittest.TestCase):
    """
    测试nacos配置中心适配器
    """

    def test_nacos_naming(self):
        # 初始化日志对象
        _logger_manager = LoggerManager(
            os.path.join(os.path.dirname(__file__), 'logs')
        )
        _logger = _logger_manager.create_logger(
            'nacos_test',
            {'config_json_str': None, 'logfile_path': 'test_nacos_naming.log', 'logger_name': 'Console'}
        )
        GlobalManager.SET_SYS_LOGGER(_logger)

        GlobalManager.SET_GLOBAL_CONFIG({
            'app_config': {
                'sys_logger': 'sysLogger'
            },
            'loggers_config': {
                'sys_logger': {
                    'config_json_str': None, 'logfile_path': 'test_nacos_naming.log', 'logger_name': 'Console'
                }
            },
            'logs_path': ''
        })

        # 初始化适配器
        _namespace = 'UNIT-TEST-NAMING'
        _adapter = NacosNamingAdapter(
            init_config={
                'server_addresses': 'http://127.0.0.1:8848',
                'default_options': {
                    'TIMEOUT': 3.0
                },
                'heartbeat_options': {
                    'check_type': 'client',
                    'interval': 3,
                    'hb_timeout': 6,
                    'ip_timeout': 9
                }
            },
            namespace=_namespace, cluster_name=None, logger_id='nacos_test'
        )

        # 相关参数
        _service_name = 'unit-test-service'
        _ip = '196.168.0.1'
        _port = 8080
        _group_name = 'sys'
        _metadata = {
            'protocol': 'https', 'uri': 'unit/test/service/uri'
        }

        # 获取服务
        _instance_info = AsyncTools.sync_call(
            _adapter.get_instance, _service_name, group_name=_group_name
        )
        if _instance_info is None:
            # 创建微服务
            _result = AsyncTools.sync_call(
                _adapter.add_instance,
                _service_name, _ip, _port, group_name=_group_name, metadata=_metadata
            )
            self.assertTrue(
                _result, msg='Add namespace result error: %s' % str(_result)
            )

            time.sleep(1)  # 创建后不能马上获取到, 要等待一会

            _instance_info = AsyncTools.sync_call(
                _adapter.get_instance, _service_name, group_name=_group_name
            )

        # 获取到服务信息
        self.assertTrue(
            _instance_info['ip'] == _ip and _instance_info['port'] == _port and TestTool.cmp_dict(
                _instance_info['metadata'], _metadata
            ), msg='get instance info error: %s' % _instance_info
        )

        # AsyncTools.sync_call(async_sleep, 1000)

        # 监听服务, 每间隔1秒刷新一次
        _adapter.add_subscribe(_service_name, group_name=_group_name, interval=1)

        time.sleep(1)

        # 添加第2个实例
        _result = AsyncTools.sync_call(
            _adapter.add_instance,
            _service_name, '196.168.0.2', _port, group_name=_group_name, metadata=_metadata
        )
        self.assertTrue(
            _result, msg='Add namespace result error: %s' % str(_result)
        )

        time.sleep(3)  # 要等待超过同步刷新时间

        for _i in range(100):
            _instance_info = AsyncTools.sync_call(
                _adapter.get_instance, _service_name, group_name=_group_name
            )
            print(_instance_info)

        # 去除监听
        _adapter.remove_subscribe(_service_name, group_name=_group_name)

        # 取消注册服务
        _result = AsyncTools.sync_call(
            _adapter.remove_instance,
            _service_name, group_name=_group_name
        )
        self.assertTrue(
            _result, msg='remove namespace result error: %s' % str(_result)
        )

        # 删除命名空间
        _result = _adapter.client.remove_namespace(_namespace)
        print('Remove namespace result: %s' % str(_result))


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
