#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
NacosDemo测试
注意: 如果修改了配置, 测试前必须删除nacos上的配置文件

@module test_service
@file test_service.py
"""
import os
import sys
import time
import threading
import traceback
import unittest
from HiveNetCore.utils.run_tool import RunTool
from HiveNetCore.utils.test_tool import TestTool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.server import ServerStarter
from HiveNetMicro.plugins.adapter.config_nacos import NacosConfigAdapter


__MOUDLE__ = 'test_service'  # 模块名
__DESCRIPT__ = u'NacosDemo测试'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2022.3.20'  # 发布日期


def start_server_thread_fun():
    """
    启动服务的线程函数
    """
    _kv_opts = RunTool.get_kv_opts()
    _start_config = dict()
    _start_config.update(_kv_opts)
    if 'visit_port' in _start_config.keys():
        _start_config['visit_port'] = int(_start_config['visit_port'])
    if 'port' in _start_config.keys():
        _start_config['port'] = int(_start_config['port'])

    # 测试所需参数
    _start_config['base_path'] = os.path.abspath(os.path.dirname(__file__))

    # 初始化服务启动器
    starter = ServerStarter(_start_config)
    RunTool.set_global_var('TEST_STARTER', starter)

    # 启动服务
    starter.start_sever()


def setUpModule():
    print("test module start >>>>>>>>>>>>>>")

    # 删除服务端的配置, 避免本地配置修改后不生效
    try:
        _adapter = NacosConfigAdapter(
            init_config={
                'server_addresses': '127.0.0.1:8848',
                'default_options': {
                    'TIMEOUT': 3.0
                }
            },
            namespace='HiveNetMicroConfig-dev'
        )
        _adapter.remove_config('server01-application.yaml', group='sys')
        _adapter.remove_config('server01-remoteServices.yaml', group='sys')
        _adapter.remove_config('server01-services.yaml', group='sys')
    except:
        print('remove server config error: %s' % traceback.format_exc())

    # 启动服务线程
    _thread = threading.Thread(
        target=start_server_thread_fun, name='Thread-LocalDemo-Server',
        daemon=True
    )

    # 启动线程
    _thread.start()

    # 等待服务启动成果
    while RunTool.get_global_var('TEST_STARTER') is None:
        time.sleep(1)

    # 再等待2秒
    time.sleep(2)


def tearDownModule():
    print("test module end >>>>>>>>>>>>>>")


class Test(unittest.TestCase):
    """
    测试LocalDemo
    """

    def test_main_func_Common(self):
        print("test main func Common")
        starter: ServerStarter = RunTool.get_global_var('TEST_STARTER')
        # 无入参
        _tips = 'test local call localDemoMainFuncNoPara'
        _resp = starter.remote_caller.call(
            'localDemoMainFuncNoPara', {
                'msg': {'msg_body': 'test localDemoMainFuncNoPara with local'}
            }
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'], {'code': '00000', 'fun': 'main_func_no_para'}, print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        _tips = 'test net call localDemoMainFuncNoPara'
        _resp = starter.remote_caller.call_with_settings(
            'localDemoMainFuncNoPara',
            {
                'local_call_first': False
            },
            {
                'msg': {'msg_body': 'test localDemoMainFuncNoPara with service'}
            }
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'], {'code': '00000', 'fun': 'main_func_no_para'}, print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        # 固定位置参数
        _tips = 'test local call localDemoMainFuncWithArgs'
        _para1 = 'p1'
        _para2 = 10
        _resp = starter.remote_caller.call(
            'localDemoMainFuncWithArgs', {
                'msg': {'msg_body': 'test localDemoMainFuncWithArgs with local'}
            }, _para1, _para2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'], {'code': '00000', 'fun': 'main_func_with_args', 'args': [_para1, _para2]},
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        _tips = 'test net call localDemoMainFuncWithArgs'
        _para1 = 'p11'
        _para2 = 101
        _resp = starter.remote_caller.call_with_settings(
            'localDemoMainFuncWithArgs',
            {
                'local_call_first': False
            },
            {
                'msg': {'msg_body': 'test localDemoMainFuncWithArgs with service'}
            }, _para1, _para2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'], {'code': '00000', 'fun': 'main_func_with_args', 'args': [_para1, _para2]},
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        # key-value参数
        _tips = 'test local call localDemoMainFuncWithKwargs'
        _kwpara1 = 'abcd'
        _kwpara2 = 10
        _resp = starter.remote_caller.call(
            'localDemoMainFuncWithKwargs', {
                'msg': {'msg_body': 'test localDemoMainFuncWithKwargs with local'}
            }, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'],
                {'code': '00000', 'fun': 'main_func_with_kwargs', 'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}},
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        _tips = 'test net call localDemoMainFuncWithKwargs'
        _kwpara1 = 'abcde'
        _kwpara2 = 101
        _resp = starter.remote_caller.call_with_settings(
            'localDemoMainFuncWithKwargs',
            {
                'local_call_first': False
            },
            {
                'msg': {'msg_body': 'test localDemoMainFuncWithKwargs with service'}
            }, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'],
                {'code': '00000', 'fun': 'main_func_with_kwargs', 'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}},
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        # 混合参数
        _tips = 'test local call localDemoMainFuncWithParas'
        _para1 = 'mp1'
        _para2 = 20
        _kwpara1 = 'mabcd'
        _kwpara2 = 30
        _resp = starter.remote_caller.call(
            'localDemoMainFuncWithParas', {
                'msg': {'msg_body': 'test localDemoMainFuncWithParas with local'}
            }, _para1, _para2, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'],
                {
                    'code': '00000', 'fun': 'main_func_with_paras',
                    'args': [_para1, _para2],
                    'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}
                },
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        _tips = 'test net call localDemoMainFuncWithParas'
        _para1 = 'mp2'
        _para2 = 21
        _kwpara1 = 'mabcde'
        _kwpara2 = 31
        _resp = starter.remote_caller.call_with_settings(
            'localDemoMainFuncWithParas',
            {
                'local_call_first': False
            },
            {
                'msg': {'msg_body': 'test localDemoMainFuncWithParas with service'}
            }, _para1, _para2, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'],
                {
                    'code': '00000', 'fun': 'main_func_with_paras',
                    'args': [_para1, _para2],
                    'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}
                },
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        # 抛出异常
        _tips = 'test local call localDemoMainFuncWithException'
        _resp = starter.remote_caller.call(
            'localDemoMainFuncWithException', {
                'msg': {'msg_body': 'test localDemoMainFuncWithException with local'}
            }
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 500 and _resp['msg']['errCode'] == '21007',
            msg='%s error: %s' % (_tips, _resp)
        )

        _tips = 'test net call localDemoMainFuncWithException'
        _resp = starter.remote_caller.call_with_settings(
            'localDemoMainFuncWithException',
            {
                'local_call_first': False
            },
            {
                'msg': {'msg_body': 'test localDemoMainFuncWithException with service'}
            }
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 500 and _resp['msg']['errCode'] == '31007',
            msg='%s error: %s' % (_tips, _resp)
        )

        # 服务中的远程调用
        # 注意: web服务是单线程的情况，如果使用的是非异步模式（阻塞）的情况，如果在服务端函数再调用自己，则会出现等待锁死的情况,
        #     因此建议直接使用本地调用，如果一定要远程调用自身, 则应使用异步模式, 以确保不会出现锁死的情况
        _tips = 'test net call localDemoMainFuncRemoteCall'
        _para1 = 'Sp2'
        _resp = starter.remote_caller.call_with_settings(
            'localDemoMainFuncRemoteCall',
            {
                'local_call_first': False
            },
            {
                'msg': {'msg_body': 'test localDemoMainFuncRemoteCall with service'}
            }, _para1
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'], {'code': '00000', 'fun': 'main_func_remote_call', 'args': [_para1]},
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        # 等待tracer刷新
        time.sleep(2)

    def test_main_func_Common_std(self):
        print("test main func Common STd")
        starter: ServerStarter = RunTool.get_global_var('TEST_STARTER')

        # 无入参
        _tips = 'test local call stdLocalDemoMainFuncNoPara'
        _resp = starter.remote_caller.call(
            'stdLocalDemoMainFuncNoPara', {
                'msg': {'body': {'info': 'test stdLocalDemoMainFuncNoPara with local'}}
            }
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and _resp['msg']['head']['errCode'] == '00000' and
            TestTool.cmp_dict(
                _resp['msg']['body'], {'fun': 'std.main_func_no_para'}, print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        _tips = 'test net call stdLocalDemoMainFuncNoPara'
        _resp = starter.remote_caller.call_with_settings(
            'stdLocalDemoMainFuncNoPara',
            {
                'local_call_first': False
            },
            {
                'msg': {'body': 'test stdLocalDemoMainFuncNoPara with service'}
            }
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and _resp['msg']['head']['errCode'] == '00000' and
            TestTool.cmp_dict(
                _resp['msg']['body'], {'fun': 'std.main_func_no_para'}, print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        # 固定位置参数
        _tips = 'test local call stdLocalDemoMainFuncWithArgs'
        _para1 = 'p1'
        _para2 = 10
        _resp = starter.remote_caller.call(
            'stdLocalDemoMainFuncWithArgs', {
                'msg': {'body': 'test stdLocalDemoMainFuncWithArgs with local'}
            }, _para1, _para2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and _resp['msg']['head']['errCode'] == '00000' and
            TestTool.cmp_dict(
                _resp['msg']['body'], {'fun': 'std.main_func_with_args', 'args': [_para1, _para2]},
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        _tips = 'test net call stdLocalDemoMainFuncWithArgs'
        _para1 = 'p11'
        _para2 = 101
        _resp = starter.remote_caller.call_with_settings(
            'stdLocalDemoMainFuncWithArgs',
            {
                'local_call_first': False
            },
            {
                'msg': {'body': 'test stdLocalDemoMainFuncWithArgs with service'}
            }, _para1, _para2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and _resp['msg']['head']['errCode'] == '00000' and
            TestTool.cmp_dict(
                _resp['msg']['body'], {'fun': 'std.main_func_with_args', 'args': [_para1, _para2]},
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        # key-value参数
        _tips = 'test local call stdLocalDemoMainFuncWithKwargs'
        _kwpara1 = 'abcd'
        _kwpara2 = 10
        _resp = starter.remote_caller.call(
            'stdLocalDemoMainFuncWithKwargs', {
                'msg': {'body': 'test stdLocalDemoMainFuncWithKwargs with local'}
            }, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and _resp['msg']['head']['errCode'] == '00000' and
            TestTool.cmp_dict(
                _resp['msg']['body'],
                {'fun': 'std.main_func_with_kwargs', 'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}},
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        _tips = 'test net call stdLocalDemoMainFuncWithKwargs'
        _kwpara1 = 'abcde'
        _kwpara2 = 101
        _resp = starter.remote_caller.call_with_settings(
            'stdLocalDemoMainFuncWithKwargs',
            {
                'local_call_first': False
            },
            {
                'msg': {'body': 'test stdLocalDemoMainFuncWithKwargs with service'}
            }, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and _resp['msg']['head']['errCode'] == '00000' and
            TestTool.cmp_dict(
                _resp['msg']['body'],
                {'fun': 'std.main_func_with_kwargs', 'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}},
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        # 混合参数
        _tips = 'test local call stdLocalDemoMainFuncWithParas'
        _para1 = 'mp1'
        _para2 = 20
        _kwpara1 = 'mabcd'
        _kwpara2 = 30
        _resp = starter.remote_caller.call(
            'stdLocalDemoMainFuncWithParas', {
                'msg': {'body': 'test stdLocalDemoMainFuncWithParas with local'}
            }, _para1, _para2, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and _resp['msg']['head']['errCode'] == '00000' and
            TestTool.cmp_dict(
                _resp['msg']['body'],
                {
                    'fun': 'std.main_func_with_paras',
                    'args': [_para1, _para2],
                    'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}
                },
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        _tips = 'test net call stdLocalDemoMainFuncWithParas'
        _para1 = 'mp2'
        _para2 = 21
        _kwpara1 = 'mabcde'
        _kwpara2 = 31
        _resp = starter.remote_caller.call_with_settings(
            'stdLocalDemoMainFuncWithParas',
            {
                'local_call_first': False
            },
            {
                'msg': {'body': 'test stdLocalDemoMainFuncWithParas with service'}
            }, _para1, _para2, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and _resp['msg']['head']['errCode'] == '00000' and
            TestTool.cmp_dict(
                _resp['msg']['body'],
                {
                    'fun': 'std.main_func_with_paras',
                    'args': [_para1, _para2],
                    'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}
                },
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        # 抛出异常
        _tips = 'test local call stdLocalDemoMainFuncWithException'
        _resp = starter.remote_caller.call(
            'stdLocalDemoMainFuncWithException', {
                'msg': {'msg_body': 'test stdLocalDemoMainFuncWithException with local'}
            }
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and _resp['msg']['head']['errCode'] == '21007',
            msg='%s error: %s' % (_tips, _resp)
        )

        _tips = 'test net call stdLocalDemoMainFuncWithException'
        _resp = starter.remote_caller.call_with_settings(
            'stdLocalDemoMainFuncWithException',
            {
                'local_call_first': False
            },
            {
                'msg': {'msg_body': 'test stdLocalDemoMainFuncWithException with service'}
            }
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and _resp['msg']['head']['errCode'] == '21599',
            msg='%s error: %s' % (_tips, _resp)
        )

        # 服务中的远程调用
        # 注意: web服务是单线程的情况，如果使用的是非异步模式（阻塞）的情况，如果在服务端函数再调用自己，则会出现等待锁死的情况,
        #     因此建议直接使用本地调用，如果一定要远程调用自身, 则应使用异步模式, 以确保不会出现锁死的情况
        _tips = 'test net call stdLocalDemoMainFuncRemoteCall'
        _para1 = 'Sp2'
        _resp = starter.remote_caller.call_with_settings(
            'stdLocalDemoMainFuncRemoteCall',
            {
                'local_call_first': False
            },
            {
                'msg': {'body': 'test stdLocalDemoMainFuncRemoteCall with service'}
            }, _para1
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg']['body'], {'fun': 'std.main_func_remote_call', 'args': [_para1]},
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        # 等待tracer刷新
        time.sleep(2)

    def test_static_class_func_Common(self):
        print("test static class func Common")
        starter: ServerStarter = RunTool.get_global_var('TEST_STARTER')

        # 静态函数
        _tips = 'test local call localDemoStaticClassSFuncWithParas'
        _para1 = 'mp1'
        _para2 = 20
        _kwpara1 = 'mabcd'
        _kwpara2 = 30
        _resp = starter.remote_caller.call(
            'localDemoStaticClassSFuncWithParas', {
                'msg': {'msg_body': 'test localDemoStaticClassSFuncWithParas with local'}
            }, _para1, _para2, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'],
                {
                    'code': '00000', 'fun': 'static_func_with_paras',
                    'args': [_para1, _para2],
                    'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}
                },
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        _tips = 'test net call localDemoStaticClassSFuncWithParas'
        _para1 = 'mp2'
        _para2 = 21
        _kwpara1 = 'mabcde'
        _kwpara2 = 31
        _resp = starter.remote_caller.call_with_settings(
            'localDemoStaticClassSFuncWithParas',
            {
                'local_call_first': False
            },
            {
                'msg': {'msg_body': 'test localDemoStaticClassSFuncWithParas with service'}
            }, _para1, _para2, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'],
                {
                    'code': '00000', 'fun': 'static_func_with_paras',
                    'args': [_para1, _para2],
                    'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}
                },
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        # 类函数
        _tips = 'test local call localDemoStaticClassCFuncWithParas'
        _para1 = 'mp1'
        _para2 = 20
        _kwpara1 = 'mabcd'
        _kwpara2 = 30
        _resp = starter.remote_caller.call(
            'localDemoStaticClassCFuncWithParas', {
                'msg': {'msg_body': 'test localDemoStaticClassCFuncWithParas with local'}
            }, _para1, _para2, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'],
                {
                    'code': '00000', 'fun': 'class_func_with_paras',
                    'args': [_para1, _para2],
                    'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}
                },
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        _tips = 'test net call localDemoStaticClassCFuncWithParas'
        _para1 = 'mp2'
        _para2 = 21
        _kwpara1 = 'mabcde'
        _kwpara2 = 31
        _resp = starter.remote_caller.call_with_settings(
            'localDemoStaticClassCFuncWithParas',
            {
                'local_call_first': False
            },
            {
                'msg': {'msg_body': 'test localDemoStaticClassCFuncWithParas with service'}
            }, _para1, _para2, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'],
                {
                    'code': '00000', 'fun': 'class_func_with_paras',
                    'args': [_para1, _para2],
                    'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}
                },
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        # 等待tracer刷新
        time.sleep(2)

    def test_object_class_func_Common(self):
        print("test object class func Common")
        starter: ServerStarter = RunTool.get_global_var('TEST_STARTER')

        # 静态函数
        _tips = 'test local call localDemoObjectClassSFuncWithParas'
        _para1 = 'mp1'
        _para2 = 20
        _kwpara1 = 'mabcd'
        _kwpara2 = 30
        _resp = starter.remote_caller.call(
            'localDemoObjectClassSFuncWithParas', {
                'msg': {'msg_body': 'test localDemoObjectClassSFuncWithParas with local'}
            }, _para1, _para2, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'],
                {
                    'code': '00000', 'fun': 'obj.static_func_with_paras',
                    'args': [_para1, _para2],
                    'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}
                },
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        _tips = 'test net call localDemoObjectClassSFuncWithParas'
        _para1 = 'mp2'
        _para2 = 21
        _kwpara1 = 'mabcde'
        _kwpara2 = 31
        _resp = starter.remote_caller.call_with_settings(
            'localDemoObjectClassSFuncWithParas',
            {
                'local_call_first': False
            },
            {
                'msg': {'msg_body': 'test localDemoObjectClassSFuncWithParas with service'}
            }, _para1, _para2, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'],
                {
                    'code': '00000', 'fun': 'obj.static_func_with_paras',
                    'args': [_para1, _para2],
                    'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}
                },
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        # 类函数
        _tips = 'test local call localDemoObjectClassCFuncWithParas'
        _para1 = 'mp1'
        _para2 = 20
        _kwpara1 = 'mabcd'
        _kwpara2 = 30
        _resp = starter.remote_caller.call(
            'localDemoObjectClassCFuncWithParas', {
                'msg': {'msg_body': 'test localDemoObjectClassCFuncWithParas with local'}
            }, _para1, _para2, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'],
                {
                    'code': '00000', 'fun': 'obj.class_func_with_paras',
                    'args': [_para1, _para2],
                    'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}
                },
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        _tips = 'test net call localDemoObjectClassCFuncWithParas'
        _para1 = 'mp2'
        _para2 = 21
        _kwpara1 = 'mabcde'
        _kwpara2 = 31
        _resp = starter.remote_caller.call_with_settings(
            'localDemoObjectClassCFuncWithParas',
            {
                'local_call_first': False
            },
            {
                'msg': {'msg_body': 'test localDemoObjectClassCFuncWithParas with service'}
            }, _para1, _para2, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'],
                {
                    'code': '00000', 'fun': 'obj.class_func_with_paras',
                    'args': [_para1, _para2],
                    'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2}
                },
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        # 实例函数
        _tips = 'test local call localDemoObjectClassMFuncWithParas'
        _para1 = 'mp1'
        _para2 = 20
        _kwpara1 = 'mabcd'
        _kwpara2 = 30
        _resp = starter.remote_caller.call(
            'localDemoObjectClassMFuncWithParas', {
                'msg': {'msg_body': 'test localDemoObjectClassMFuncWithParas with local'}
            }, _para1, _para2, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'],
                {
                    'code': '00000', 'fun': 'obj.member_func_with_paras',
                    'args': [_para1, _para2],
                    'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2},
                    'self.tips': 'ObjectClassService'
                },
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        _tips = 'test net call localDemoObjectClassMFuncWithParas'
        _para1 = 'mp2'
        _para2 = 21
        _kwpara1 = 'mabcde'
        _kwpara2 = 31
        _resp = starter.remote_caller.call_with_settings(
            'localDemoObjectClassMFuncWithParas',
            {
                'local_call_first': False
            },
            {
                'msg': {'msg_body': 'test localDemoObjectClassMFuncWithParas with service'}
            }, _para1, _para2, kwpara1=_kwpara1, kwpara2=_kwpara2
        )
        self.assertTrue(
            _resp.get('network', {}).get('status', None) == 200 and TestTool.cmp_dict(
                _resp['msg'],
                {
                    'code': '00000', 'fun': 'obj.member_func_with_paras',
                    'args': [_para1, _para2],
                    'kwargs': {'kwpara1': _kwpara1, 'kwpara2': _kwpara2},
                    'self.tips': 'ObjectClassService'
                },
                print_if_diff=True
            ),
            msg='%s error: %s' % (_tips, _resp)
        )

        # 等待tracer刷新
        time.sleep(2)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
