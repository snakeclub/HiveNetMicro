#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试Redis集群功能支持适配器

@module test_cluster_redis
@file test_cluster_redis.py
"""
import os
import sys
import time
import copy
import unittest
from HiveNetCore.utils.test_tool import TestTool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetMicro.plugins.cluster_redis import RedisClusterAdapter


# 控制测试的字典
TEST_CONTROL = {
    'single': True,
    'mutiple': True,
    'event': True
}


def after_register(obj: RedisClusterAdapter):
    print('run after_register: %s' % obj._server_id)


def after_deregister(obj: RedisClusterAdapter):
    print('run after_deregister: %s' % obj._server_id)


def after_own_master(obj: RedisClusterAdapter):
    print('run after_own_master: %s' % obj._server_id)


def after_lost_master(obj: RedisClusterAdapter):
    print('run after_lost_master: %s' % obj._server_id)


def common_event(context: dict, event: str, para):
    print('run event [%s] on [%s], para [%s], from [%s]' % (
        event, context['adapter']._app_name, str(para), str(context['from'])
    ))


INIT_CONFIG = {
    'namespace': 'test_namespace', 'sys_id': 'SYSID', 'module_id': 'WEB',
    'server_id': '01', 'app_name': 'app_01',
    'expire': 5.0, 'heart_beat': 2.0,
    'enable_event': True,
    'after_register': after_register,
    'after_deregister': after_deregister,
    'after_own_master': after_own_master,
    'after_lost_master': after_lost_master,
    'redis_para': {'host': '127.0.0.1'}
}


class TestRedisClusterAdapter(unittest.TestCase):
    """
    测试Redis集群功能支持适配器
    """

    def test_single(self):
        if not TEST_CONTROL['single']:
            return

        _tips = '测试单个服务集群'
        print(_tips)

        # 清理无效服务
        _init_config = copy.deepcopy(INIT_CONFIG)
        _adapter_manager = RedisClusterAdapter(init_config=_init_config, is_manage=True)
        _ret = _adapter_manager.clear_all_cluster(
            _init_config['namespace']
        )
        self.assertTrue(_ret, '%s, clear all cluster error: %s' % (_tips, str(_ret)))
        _clusters = _adapter_manager.get_cluster_list(_init_config['namespace'])
        self.assertTrue(
            len(_clusters) == 0, '%s, clear all cluster error: %s' % (_tips, str(_clusters))
        )

        _init_config = copy.deepcopy(INIT_CONFIG)
        _adapter1 = RedisClusterAdapter(init_config=_init_config)
        _ret = _adapter1.register_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, register_cluster error %s' % (_tips, _adapter1.registered)
        )
        self.assertTrue(_adapter1.registered, '%s, registered error %s' % (_tips, _adapter1.registered))
        self.assertTrue(_adapter1.master, '%s, master error %s' % (_tips, _adapter1.master))

        # 等待6秒
        time.sleep(6)
        self.assertTrue(_adapter1.registered, '%s, registered 2 error %s' % (_tips, _adapter1.registered))
        self.assertTrue(_adapter1.master, '%s, master 2 error %s' % (_tips, _adapter1.master))

        # 检查集群列表
        _expect = {'namespace': 'test_namespace', 'sys_id': 'SYSID', 'module_id': 'WEB', 'server_id': '01', 'app_name': 'app_01', 'master': True}
        _ret = _adapter1.get_cluster_list(_init_config['namespace'])
        self.assertTrue(
            TestTool.cmp_dict(_ret[0], _expect),
            '%s, get_cluster_list error %s' % (_tips, str(_ret))
        )
        _ret = _adapter1.get_cluster_master(
            _init_config['namespace'], _init_config['sys_id'], _init_config['module_id']
        )
        self.assertTrue(
            TestTool.cmp_dict(_ret, _expect),
            '%s, get_cluster_master error %s' % (_tips, str(_ret))
        )

        # 删除集群服务
        _ret = _adapter1.deregister_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, deregister_cluster error %s' % (_tips, _ret)
        )

        _ret = _adapter1.get_cluster_list(_init_config['namespace'])
        self.assertTrue(len(_ret) == 0, '%s, get_cluster_list none error %s' % (_tips, _ret))

        _ret = _adapter1.get_cluster_master(
            _init_config['namespace'], _init_config['sys_id'], _init_config['module_id']
        )
        self.assertTrue(_ret is None, '%s, get_cluster_master none error %s' % (_tips, _ret))

        _tips = '测试单个服务集群超时后无效'
        print(_tips)
        _init_config = copy.deepcopy(INIT_CONFIG)
        _init_config['expire'] = 2.0
        _init_config['heart_beat'] = 5.0
        _adapter1 = RedisClusterAdapter(init_config=_init_config)
        _ret = _adapter1.register_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, register_cluster error %s' % (_tips, _adapter1.registered)
        )
        self.assertTrue(_adapter1.registered, '%s, registered overtime error %s' % (_tips, _adapter1.registered))
        self.assertTrue(_adapter1.master, '%s, master overtime error %s' % (_tips, _adapter1.master))

        # 等待超时
        time.sleep(2)
        _ret = _adapter1.get_cluster_list(_init_config['namespace'])
        self.assertTrue(len(_ret) == 0, '%s, get_cluster_list overtime error %s' % (_tips, _ret))
        _ret = _adapter1.get_cluster_master(
            _init_config['namespace'], _init_config['sys_id'], _init_config['module_id']
        )
        self.assertTrue(_ret is None, '%s, get_cluster_master overtime error %s' % (_tips, _ret))

        # 等待心跳重新注册
        time.sleep(3)
        # 检查集群列表
        _expect = {'namespace': 'test_namespace', 'sys_id': 'SYSID', 'module_id': 'WEB', 'server_id': '01', 'app_name': 'app_01', 'master': True}
        _ret = _adapter1.get_cluster_list(_init_config['namespace'])
        self.assertTrue(
            TestTool.cmp_dict(_ret[0], _expect),
            '%s, get_cluster_list overtime 1 error %s' % (_tips, str(_ret))
        )
        _ret = _adapter1.get_cluster_master(
            _init_config['namespace'], _init_config['sys_id'], _init_config['module_id']
        )
        self.assertTrue(
            TestTool.cmp_dict(_ret, _expect),
            '%s, get_cluster_master overtime 1 error %s' % (_tips, str(_ret))
        )

        # 删除集群服务
        print('before deregister', _adapter1._redis.exists(_adapter1._cache_name), _adapter1._redis.exists(_adapter1._cache_name),)

        _ret = _adapter1.deregister_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, deregister_cluster error %s' % (_tips, _ret)
        )

        _ret = _adapter1.get_cluster_list(_init_config['namespace'])
        self.assertTrue(len(_ret) == 0, '%s, get_cluster_list overtime 2 error %s' % (_tips, _ret))
        _ret = _adapter1.get_cluster_master(
            _init_config['namespace'], _init_config['sys_id'], _init_config['module_id']
        )
        self.assertTrue(_ret is None, '%s, get_cluster_master overtime 2 error %s' % (_tips, _ret))

    def test_mutiple(self):
        if not TEST_CONTROL['mutiple']:
            return

        _tips = '测试多个服务集群'
        print(_tips)

        # 清理无效服务
        _init_config = copy.deepcopy(INIT_CONFIG)
        _adapter_manager = RedisClusterAdapter(init_config=_init_config, is_manage=True)
        _ret = _adapter_manager.clear_all_cluster(
            _init_config['namespace']
        )
        self.assertTrue(_ret, '%s, clear all cluster error: %s' % (_tips, str(_ret)))
        _clusters = _adapter_manager.get_cluster_list(_init_config['namespace'])
        self.assertTrue(
            len(_clusters) == 0, '%s, clear all cluster error: %s' % (_tips, str(_clusters))
        )

        _init_config = copy.deepcopy(INIT_CONFIG)
        _init_config['expire'] = 3.0
        _init_config['heart_beat'] = 1.0

        _adapter1 = RedisClusterAdapter(init_config=_init_config)
        _ret = _adapter1.register_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, register_cluster adapter1 error %s' % (_tips, _adapter1.registered)
        )
        self.assertTrue(_adapter1.registered, '%s, registered adapter1 error %s' % (_tips, _adapter1.registered))
        self.assertTrue(_adapter1.master, '%s, master adapter1 error %s' % (_tips, _adapter1.master))

        _init_config['server_id'] = '02'
        _init_config['app_name'] = 'app_02'
        _adapter2 = RedisClusterAdapter(init_config=_init_config)
        _ret = _adapter2.register_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, register_cluster adapter2 error %s' % (_tips, _adapter2.registered)
        )
        self.assertTrue(_adapter2.registered, '%s, registered adapter2 error %s' % (_tips, _adapter2.registered))
        self.assertTrue(not _adapter2.master, '%s, master adapter2 error %s' % (_tips, _adapter2.master))

        _init_config['server_id'] = '03'
        _init_config['app_name'] = 'app_03'
        _adapter3 = RedisClusterAdapter(init_config=_init_config)
        _ret = _adapter3.register_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, register_cluster adapter3 error %s' % (_tips, _adapter3.registered)
        )
        self.assertTrue(_adapter3.registered, '%s, registered adapter3 error %s' % (_tips, _adapter3.registered))
        self.assertTrue(not _adapter3.master, '%s, master adapter3 error %s' % (_tips, _adapter3.master))

        # 获取集群列表信息
        _expect = {
            '01': {'namespace': 'test_namespace', 'sys_id': 'SYSID', 'module_id': 'WEB', 'server_id': '01', 'app_name': 'app_01', 'master': True},
            '02': {'namespace': 'test_namespace', 'sys_id': 'SYSID', 'module_id': 'WEB', 'server_id': '02', 'app_name': 'app_02', 'master': False},
            '03': {'namespace': 'test_namespace', 'sys_id': 'SYSID', 'module_id': 'WEB', 'server_id': '03', 'app_name': 'app_03', 'master': False}
        }
        _ret = _adapter1.get_cluster_list(_init_config['namespace'])
        self.assertTrue(len(_ret) == len(_expect), '%s, get_cluster_list 1 error: len %s' % (_tips, str(_ret)))
        for _cluster in _ret:
            self.assertTrue(
                TestTool.cmp_dict(_cluster, _expect[_cluster['server_id']]),
                '%s, get_cluster_list 1 error: cluster cmp %s' % (_tips, str(_cluster))
            )

        _ret = _adapter1.get_cluster_master(
            _init_config['namespace'], _init_config['sys_id'], _init_config['module_id']
        )
        self.assertTrue(
            TestTool.cmp_dict(_ret, _expect['01']),
            '%s, get_cluster_master 1 error %s' % (_tips, str(_ret))
        )

        # 等待超时时间
        time.sleep(3.1)
        _ret = _adapter1.get_cluster_master(
            _init_config['namespace'], _init_config['sys_id'], _init_config['module_id']
        )
        self.assertTrue(
            TestTool.cmp_dict(_ret, _expect['01']),
            '%s, get_cluster_master 2 error %s' % (_tips, str(_ret))
        )

        # 取消注册
        _ret = _adapter1.deregister_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, deregister_cluster adapter1 error %s' % (_tips, _ret)
        )

        # 等待2秒被其他集群抢占
        time.sleep(2)
        _ret = _adapter3.get_cluster_master(
            _init_config['namespace'], _init_config['sys_id'], _init_config['module_id']
        )
        self.assertTrue(
            _ret['server_id'] != '01'
            '%s, get_cluster_master 3 error %s' % (_tips, str(_ret))
        )

        # 重新注册适配器1
        _ret = _adapter1.register_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, redo register_cluster adapter1 error %s' % (_tips, _adapter1.registered)
        )
        self.assertTrue(_adapter1.registered, '%s, redo registered adapter1 error %s' % (_tips, _adapter1.registered))
        self.assertTrue(not _adapter1.master, '%s, redo master adapter1 error %s' % (_tips, _adapter1.master))

        # 从后往前逐个取消注册
        _ret = _adapter3.deregister_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, deregister_cluster adapter3 error %s' % (_tips, _ret)
        )
        time.sleep(1.1)  # 等待其他抢占
        _ret = _adapter3.get_cluster_master(
            _init_config['namespace'], _init_config['sys_id'], _init_config['module_id']
        )
        self.assertTrue(
            _ret['server_id'] != '03' and not _adapter3.master and not _adapter3.registered,
            '%s, get_cluster_master 4 error %s' % (_tips, str(_ret))
        )

        _ret = _adapter2.deregister_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, deregister_cluster adapter2 error %s' % (_tips, _ret)
        )
        time.sleep(1.1)  # 等待其他抢占
        _ret = _adapter2.get_cluster_master(
            _init_config['namespace'], _init_config['sys_id'], _init_config['module_id']
        )
        self.assertTrue(
            _ret['server_id'] != '02' and not _adapter2.master and not _adapter2.registered,
            '%s, get_cluster_master 5 error %s' % (_tips, str(_ret))
        )

        _ret = _adapter1.deregister_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, deregister_cluster adapter1 error %s' % (_tips, _ret)
        )
        time.sleep(1.1)  # 等待其他抢占
        _ret = _adapter1.get_cluster_master(
            _init_config['namespace'], _init_config['sys_id'], _init_config['module_id']
        )
        self.assertTrue(
            _ret is None and not _adapter1.master and not _adapter1.registered,
            '%s, get_cluster_master 6 error %s' % (_tips, str(_ret))
        )

    def test_event(self):
        if not TEST_CONTROL['event']:
            return

        _tips = '测试事件'
        print(_tips)

        # 清理无效服务
        _init_config = copy.deepcopy(INIT_CONFIG)
        _adapter_manager = RedisClusterAdapter(init_config=_init_config, is_manage=True)
        _ret = _adapter_manager.clear_all_cluster(
            _init_config['namespace']
        )
        self.assertTrue(_ret, '%s, clear all cluster error: %s' % (_tips, str(_ret)))
        _clusters = _adapter_manager.get_cluster_list(_init_config['namespace'])
        self.assertTrue(
            len(_clusters) == 0, '%s, clear all cluster error: %s' % (_tips, str(_clusters))
        )

        _init_config = copy.deepcopy(INIT_CONFIG)
        _init_config['event_interval'] = 1.0

        _adapter1 = RedisClusterAdapter(init_config=_init_config)
        _ret = _adapter1.register_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, register_cluster adapter1 error %s' % (_tips, _adapter1.registered)
        )
        # 注册事件处理函数
        _ret = _adapter1.register_event('emit_event', common_event)
        self.assertTrue(
            _ret.is_success(), '%s, register_event emit_event adapter1 error %s' % (_tips, _ret)
        )
        _ret = _adapter1.register_event('broadcast_event', common_event)
        self.assertTrue(
            _ret.is_success(), '%s, register_event broadcast_event adapter1 error %s' % (_tips, _ret)
        )

        _init_config['server_id'] = '02'
        _init_config['app_name'] = 'app_02'
        _adapter2 = RedisClusterAdapter(init_config=_init_config)
        _ret = _adapter2.register_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, register_cluster adapter2 error %s' % (_tips, _adapter2.registered)
        )
        # 注册事件处理函数
        _ret = _adapter2.register_event('emit_event', common_event)
        self.assertTrue(
            _ret.is_success(), '%s, register_event emit_event adapter1 error %s' % (_tips, _ret)
        )
        _ret = _adapter2.register_event('broadcast_event', common_event)
        self.assertTrue(
            _ret.is_success(), '%s, register_event broadcast_event adapter1 error %s' % (_tips, _ret)
        )

        _init_config['server_id'] = '03'
        _init_config['app_name'] = 'app_03'
        _adapter3 = RedisClusterAdapter(init_config=_init_config)
        _ret = _adapter3.register_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, register_cluster adapter3 error %s' % (_tips, _adapter3.registered)
        )
        # 注册事件处理函数
        _ret = _adapter3.register_event('emit_event', common_event)
        self.assertTrue(
            _ret.is_success(), '%s, register_event emit_event adapter1 error %s' % (_tips, _ret)
        )
        _ret = _adapter3.register_event('broadcast_event', common_event)
        self.assertTrue(
            _ret.is_success(), '%s, register_event broadcast_event adapter1 error %s' % (_tips, _ret)
        )

        # 发送点对点事件
        _ret = _adapter1.emit(
            'emit_event', {'para1': 'val_para1'}, _init_config['namespace'],
            _init_config['sys_id'], _init_config['module_id'], '02'
        )
        self.assertTrue(
            _ret.is_success(), '%s, adapter1 emit to adapter2 error %s' % (_tips, _ret)
        )

        _ret = _adapter2.emit(
            'emit_event', {'para1': 'val_para1'}, _init_config['namespace'],
            _init_config['sys_id'], _init_config['module_id'], '03'
        )
        self.assertTrue(
            _ret.is_success(), '%s, adapter2 emit to adapter3 error %s' % (_tips, _ret)
        )

        time.sleep(2)

        # 发送广播
        _ret = _adapter1.broadcast(
            'broadcast_event',  {'para1': 'val_para1'}, _init_config['namespace']
        )
        self.assertTrue(
            _ret.is_success(), '%s, adapter1 broadcast to namespace error %s' % (_tips, _ret)
        )
        time.sleep(2)

        # 取消注册
        _ret = _adapter1.deregister_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, deregister_cluster adapter1 error %s' % (_tips, _ret)
        )

        _ret = _adapter2.deregister_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, deregister_cluster adapter2 error %s' % (_tips, _ret)
        )

        _ret = _adapter3.deregister_cluster()
        self.assertTrue(
            _ret.is_success(), '%s, deregister_cluster adapter3 error %s' % (_tips, _ret)
        )


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
