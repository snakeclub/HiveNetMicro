#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
测试nacos配置中心适配器

@module test_config_nacos
@file test_config_nacos.py
"""

import os
import sys
import unittest
import time
from HiveNetCore.utils.run_tool import AsyncTools
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetMicro.plugins.config_nacos import NacosConfigAdapter
from HiveNetMicro.core.logger_manager import LoggerManager


class TestNacosConfig(unittest.TestCase):
    """
    测试nacos配置中心适配器
    """

    def test_nacos_config(self):
        # 初始化日志对象
        _logger_manager = LoggerManager(
            os.path.join(os.path.dirname(__file__), 'logs')
        )
        _logger = _logger_manager.create_logger(
            'nacos_test',
            {'config_json_str': None, 'logfile_path': 'test_nacos_config.log', 'logger_name': 'Console'}
        )

        # 初始化适配器
        _namespace = 'UNIT-TEST'
        _adapter = NacosConfigAdapter(
            init_config={
                'server_addresses': 'http://127.0.0.1:8848',
                'default_options': {
                    'TIMEOUT': 3.0
                }
            },
            namespace=_namespace
        )
        _adapter.set_logger(_logger)

        _data_id = 'test1.yaml'
        _group = 'test_group'
        _content = 'abcdefg'

        # 测试原生方法
        # _sync_res = _adapter.client.publish_config(_data_id, _group, _content, config_type='text')
        # print('publish_config: ', _sync_res)

        # _async_res = AsyncTools.sync_run_coroutine(
        #     _adapter.client.async_publish_config(_data_id, _group, _content, config_type='text')
        # )
        # print('async_publish_config: ', _async_res)

        # 查询配置
        _config = AsyncTools.sync_run_coroutine(
            _adapter.get_config(_data_id, group=_group)
        )
        if _config is None:
            _result = AsyncTools.sync_run_coroutine(
                _adapter.set_config(
                    _data_id, _content, group=_group
                )
            )
            print('Set config result: %s' % str(_result))
            time.sleep(0.5)  # 设置成功后, 如果马上获取会取不到, 所以需要等待一点时间
            _config = AsyncTools.sync_run_coroutine(_adapter.get_config(_data_id, group=_group))

        self.assertTrue(
            _config == _content, msg='get config error: %s' % _config
        )

        # 删除配置
        _result = AsyncTools.sync_run_coroutine(_adapter.remove_config(_data_id, group=_group))
        self.assertTrue(
            _result, msg='Remove config result error: %s' % str(_result)
        )

        # 删除命名空间
        _result = _adapter.client.remove_namespace(_namespace)
        self.assertTrue(
            _result, msg='Remove namespace result error: %s' % str(_result)
        )


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
