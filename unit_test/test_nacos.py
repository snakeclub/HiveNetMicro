#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import os
import sys
import time
import unittest
from HiveNetCore.utils.run_tool import AsyncTools
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
import HiveNetMicro.core.nacos as nacos


class TestNacos(unittest.TestCase):
    """
    测试nacos
    """

    def test(self):
        _server_addresses = '127.0.0.1:8848'
        _namespace = 'UNIT-TEST-NAMING'
        self.client = nacos.NacosClient(
            _server_addresses, namespace=_namespace
        )

        # 创建命名空间
        if not self.client.is_namespace_exists(_namespace):
            self.client.add_namespace(
                _namespace, namespace=_namespace
            )

        # 删除实例
        _result = self.client.remove_naming_instance(
            'unit-test-service', '192.168.0.1', '8080', group_name='sys'
        )
        print('remove_naming_instance:', _result)
        return

        # 创建实例
        _result = self.client.add_naming_instance(
            'nacos-test-services', '192.168.0.1', '80', metadata={
                'preserved.heart.beat.interval': '3000',
                'preserved.heart.beat.timeout': '6000',
                'preserved.ip.delete.timeout': '9000'
            }
        )
        print('add_naming_instance:', _result)

        # 重复创建
        _result = self.client.add_naming_instance(
            'nacos-test-services', '192.168.0.1', '80', metadata={
                'preserved.heart.beat.interval': '3000',
                'preserved.heart.beat.timeout': '6000',
                'preserved.ip.delete.timeout': '9000'
            }
        )
        print('add_naming_instance:', _result)

        # 马上发送心跳
        _i = 0
        while _i < 2:
            _result = self.client.send_heartbeat(
                'nacos-test-services', '192.168.0.1', '80', metadata={
                    'preserved.heart.beat.interval': '3000',
                    'preserved.heart.beat.timeout': '6000',
                    'preserved.ip.delete.timeout': '9000'
                }
            )
            print('send_heartbeat:', _result)
            time.sleep(1)
            _i += 1

        # 异步模式发送心跳
        _result = AsyncTools.sync_call(
            self.client.async_send_heartbeat,
            'nacos-test-services', '192.168.0.1', '80', metadata={
                'preserved.heart.beat.interval': '3000',
                'preserved.heart.beat.timeout': '6000',
                'preserved.ip.delete.timeout': '9000'
            }
        )
        print('async_send_heartbeat:', _result)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
