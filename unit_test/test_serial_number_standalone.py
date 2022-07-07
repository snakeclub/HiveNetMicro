#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试序列号适配器

@module test_serial_number_standalone
@file test_serial_number_standalone.py
"""
import os
import sys
import unittest
from HiveNetCore.utils.file_tool import FileTool
from HiveNetCore.utils.run_tool import AsyncTools
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetMicro.plugins.extend.serial_number_standalone import StandaloneSerialNumberAdapter


class TestStandaloneSerialNumber(unittest.TestCase):
    """
    测试序列号适配器
    """

    def test_serial(self):
        # 删除指定路径下的序列号文件
        _base_path = os.path.dirname(sys.argv[0])
        _store_path = 'serial_number_data'
        _file_path = os.path.join(_base_path, _store_path)
        if os.path.exists(_file_path):
            FileTool.remove_dir(_file_path)

        _adapter = StandaloneSerialNumberAdapter(
            init_config={
                'store_path': _store_path, 'overtime': 3.0, 'wait_delay': 0.1
            },
            init_serial_infos={
                'init_id_1': {
                    'current_num': 3, 'start_num': 2, 'max_num': 10, 'repeat': False,
                    'default_batch_size': 10
                },
                'init_id_2': {
                    'current_num': 1, 'start_num': 1, 'max_num': 100, 'repeat': True,
                    'default_batch_size': 100
                }
            }
        )

        # 正常处理
        _c_num = AsyncTools.sync_run_coroutine(_adapter.get_current_num('init_id_1'))
        self.assertTrue(_c_num == 3, msg='test get_current_num 1 error: %d' % _c_num)

        _s_num = AsyncTools.sync_run_coroutine(
            _adapter.get_serial_num('init_id_1')
        )
        _c_num = AsyncTools.sync_run_coroutine(_adapter.get_current_num('init_id_1'))
        self.assertTrue(_s_num == 3 and _c_num == 4, msg='test get_serial_num 1 error: %d %d' % (_s_num, _c_num))

        _batch_num = AsyncTools.sync_run_coroutine(
            _adapter.get_serial_batch('init_id_1', batch_size=3)
        )
        _c_num = AsyncTools.sync_run_coroutine(_adapter.get_current_num('init_id_1'))
        self.assertTrue(_batch_num[0] == 4 and _batch_num[1] == 6 and _c_num == 7, msg='test get_serial_batch 1 error: %d %d' % (_s_num, _c_num))

        # 批次超过不循环
        try:
            _batch_num = AsyncTools.sync_run_coroutine(
                _adapter.get_serial_batch('init_id_1', batch_size=4)
            )
        except AttributeError as e:
            print(e)
        except:
            raise

        _batch_num = AsyncTools.sync_run_coroutine(
            _adapter.get_serial_batch('init_id_1', batch_size=3)
        )
        _c_num = AsyncTools.sync_run_coroutine(_adapter.get_current_num('init_id_1'))
        self.assertTrue(_batch_num[0] == 7 and _batch_num[1] == 9 and _c_num == 10, msg='test get_serial_batch 2 error: %d %d' % (_s_num, _c_num))

        try:
            # 当前值达到最大值后, 非循环情况不能再获取新的值
            _s_num = AsyncTools.sync_run_coroutine(_adapter.get_serial_batch('init_id_1'))
        except AttributeError as e:
            print(e)
        except:
            raise

        # 测试重新打开适配器
        _s_num = AsyncTools.sync_run_coroutine(_adapter.get_serial_num('init_id_2'))
        _adapter1 = StandaloneSerialNumberAdapter(
            init_config={
                'store_path': _store_path, 'overtime': 3.0, 'wait_delay': 0.1
            },
            init_serial_infos={
                'init_id_1': {
                    'current_num': 3, 'start_num': 2, 'max_num': 10, 'repeat': False,
                    'default_batch_size': 10
                },
                'init_id_2': {
                    'current_num': 1, 'start_num': 1, 'max_num': 100, 'repeat': True,
                    'default_batch_size': 100
                }
            }
        )

        _c_num = AsyncTools.sync_run_coroutine(_adapter1.get_current_num('init_id_1'))
        self.assertTrue(_c_num == 10, msg='test get_current_num 2 error: %d' % _c_num)

        _c_num = AsyncTools.sync_run_coroutine(_adapter1.get_current_num('init_id_2'))
        self.assertTrue(_c_num == 2, msg='test get_current_num 3 error: %d' % _c_num)

        # 测试循环
        AsyncTools.sync_run_coroutine(
            _adapter1.set_current_num('init_id_2', 98)
        )
        _batch_num = AsyncTools.sync_run_coroutine(
            _adapter1.get_serial_batch('init_id_2', batch_size=4)
        )
        _c_num = AsyncTools.sync_run_coroutine(_adapter1.get_current_num('init_id_2'))
        self.assertTrue(_batch_num[0] == 98 and _batch_num[1] == 100 and _c_num == 1, msg='test get_serial_batch 3 error: %s %d' % (str(_batch_num), _c_num))

        AsyncTools.sync_run_coroutine(
            _adapter1.set_current_num('init_id_2', 99)
        )
        _s_num = AsyncTools.sync_run_coroutine(_adapter.get_serial_num('init_id_2'))
        _s_num = AsyncTools.sync_run_coroutine(_adapter.get_serial_num('init_id_2'))
        self.assertTrue(_s_num == 100, msg='test get_serial_num 5 error: %d' % _s_num)
        _s_num = AsyncTools.sync_run_coroutine(_adapter.get_serial_num('init_id_2'))
        self.assertTrue(_s_num == 1, msg='test get_serial_num 6 error: %d' % _s_num)

        # 删除测试数据
        if os.path.exists(_file_path):
            FileTool.remove_dir(_file_path)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()

