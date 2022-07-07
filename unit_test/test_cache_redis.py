#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试redis缓存服务

@module test_cache_redis
@file test_cache_redis.py
"""
import os
import sys
import time
import unittest
from HiveNetCore.utils.test_tool import TestTool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetMicro.plugins.extend.cache_redis import RedisCacheAdapter


#############################
# 缓存获取函数
#############################
def load_handler_base(cache_config, value):
    print('load_handler_base: %s' % str(cache_config))
    return value


def load_handler_list(cache_config, lis):
    print('load_handler_list: %s' % str(cache_config))
    return lis


def load_handler_dict(cache_config, dc):
    print('load_handler_dict: %s' % str(cache_config))
    return dc


#############################
# 检查函数
#############################
def check_handler(cache_config, is_ok):
    print('check_handler: %s' % str(cache_config))
    return is_ok


class TestRedisCacheAdapter(unittest.TestCase):
    """
    测试redis缓存服务
    """

    def test_common(self):
        # 测试通用缓存操作
        _adapter = RedisCacheAdapter(
            redis_para={
                'host': '127.0.0.1'
            }
        )

        _tips = '测试缓存改名'
        _group = 'common'
        _ret = _adapter.hset('d1', 'a', 'val_a', group=_group)
        self.assertTrue(_ret, '%s, 设置字典值失败: %s' % (_tips, str(_ret)))
        _ret = _adapter.hget('d1', 'a', group=_group)
        self.assertTrue(_ret == 'val_a', '%s, 获取字典值失败: %s' % (_tips, str(_ret)))

        _ret = _adapter.rename('d1', 'd2', group=_group)
        self.assertTrue(_ret, '%s, 改名操作失败: %s' % (_tips, str(_ret)))
        _ret = _adapter.hget('d1', 'a', group=_group)
        self.assertTrue(_ret is None, '%s, 获取旧缓存字典值失败: %s' % (_tips, str(_ret)))
        _ret = _adapter.hget('d2', 'a', group=_group)
        self.assertTrue(_ret == 'val_a', '%s, 检查改名后获取失败: %s' % (_tips, str(_ret)))

        _tips = '测试对不存在的缓存设置超时'
        _ret = _adapter.delete('d2', group=_group)
        self.assertTrue(_ret, '%s, 删除缓存失败: %s' % (_tips, str(_ret)))

        _ret = _adapter.set_expire('d2', 3, group=_group)
        self.assertTrue(not _ret, '%s, 不存在的缓存设置超时失败: %s' % (_tips, str(_ret)))

        _tips = '测试查找缓存key'
        _group = 'find'
        _ret = _adapter.delete_group(_group)

        _ret = _adapter.mset({'abc': 1, 'abcd': 2, 'abcdef': 3, 'abcefg': 4, 'add': 5}, group=_group)
        self.assertTrue(_ret, '%s, 批量添加缓存: %s' % (_tips, str(_ret)))

        _expect = ['abc', 'abcd', 'abcdef', 'abcefg']
        _ret = _adapter.keys('abc*', group=_group)
        self.assertTrue(
            TestTool.cmp_list(_ret, _expect, sorted=True), '%s, keys查询失败: %s' % (_tips, str(_ret))
        )

        _ret = _adapter.scan('abc*', group=_group, count=2)
        _list = []
        for _key in _ret:
            _list.append(_key)
        self.assertTrue(
            TestTool.cmp_list(_list, _expect, sorted=True), '%s, scan查询失败: %s' % (_tips, str(_ret))
        )

    def test_single_value(self):
        # 测试单值缓存处理
        _adapter = RedisCacheAdapter(
            redis_para={
                'host': '127.0.0.1'
            }
        )

        _tips = '测试python基础类型值的设置、获取和删除'
        _group = 'base_type'
        _ret = _adapter.set('int', 10, group=_group)
        self.assertTrue(_ret, '%s, 设置int失败' % _tips)
        _ret = _adapter.get('int', group=_group)
        self.assertTrue(_ret == 10, '%s, 获取int失败' % _tips)

        _ret = _adapter.set('int', 12, group=_group, nx=True)
        self.assertTrue(not _ret, '%s, nx不覆盖int失败' % _tips)
        _ret = _adapter.get('int', group=_group)
        self.assertTrue(_ret == 10, '%s, 检查nx不覆盖int失败' % _tips)

        _ret = _adapter.set('float', 10.1, group=_group)
        self.assertTrue(_ret, '%s, 设置float失败' % _tips)
        _ret = _adapter.get('float', group=_group)
        self.assertTrue(_ret == 10.1, '%s, 获取float失败' % _tips)

        _ret = _adapter.set('bool', False, group=_group)
        self.assertTrue(_ret, '%s, 设置bool失败' % _tips)
        _ret = _adapter.get('bool', group=_group)
        self.assertTrue(not _ret, '%s, 获取bool失败' % _tips)

        _ret = _adapter.set('str', '字符串', group=_group)
        self.assertTrue(_ret, '%s, 设置str失败' % _tips)
        _ret = _adapter.get('str', group=_group)
        self.assertTrue(_ret == '字符串', '%s, 获取str失败' % _tips)

        _expect_list = [1, 'str', 3, 4]
        _ret = _adapter.set('list', _expect_list, group=_group)
        self.assertTrue(_ret, '%s, 设置list失败' % _tips)
        _ret = _adapter.get('list', group=_group)
        self.assertTrue(TestTool.cmp_list(_ret, _expect_list), '%s, 获取list失败' % _tips)

        _expect_dict = {'a': 1, 'b': 'bval'}
        _ret = _adapter.set('dict', _expect_dict, group=_group)
        self.assertTrue(_ret, '%s, 设置dict失败' % _tips)
        _ret = _adapter.get('dict', group=_group)
        self.assertTrue(TestTool.cmp_dict(_ret, _expect_dict), '%s, 获取dict失败' % _tips)

        # 批量获取
        _ret = _adapter.mget(['int', 'float', 'str'], group=_group)
        self.assertTrue(
            TestTool.cmp_list(_ret, [10, 10.1, '字符串']), '%s, 批量获取失败' % _tips
        )

        _ret = _adapter.get_group(_group)
        self.assertTrue(
            TestTool.cmp_dict(_ret, {
                'int': 10, 'float': 10.1, 'bool': False, 'str': '字符串',
                'list': _expect_list, 'dict': _expect_dict
            }),
            '%s, 按分组获取失败' % _tips
        )

        # 删除
        _ret = _adapter.delete('int', group=_group)
        self.assertTrue(_ret, '%s, 删除int失败' % _tips)
        _ret = _adapter.get('int', group=_group)
        self.assertTrue(_ret is None, '%s, 已删除int获取检查失败' % _tips)

        _ret = _adapter.mdelete(['float', 'bool'], group=_group)
        self.assertTrue(_ret, '%s, 删除float, bool失败' % _tips)
        _ret = _adapter.get('bool', group=_group)
        self.assertTrue(_ret is None, '%s, 已删除float, bool获取检查失败' % _tips)

        _ret = _adapter.delete_group(_group)
        self.assertTrue(_ret, '%s, 删除分组失败' % _tips)
        _ret = _adapter.get('list', group=_group)
        self.assertTrue(_ret is None, '%s, 已删除分组获取检查失败' % _tips)

        _ret = _adapter.get_group(_group)
        self.assertTrue(_ret is None, '%s, 已删除分组获取检查2失败' % _tips)

        _tips = '测试mset和mget'
        _group = 'mset_mget'
        _expect = {'int': 10, 'float': 10.1, 'str': 'abc', 'list': [1, 3, 2, 4]}
        _ret = _adapter.mset(_expect, group=_group)
        self.assertTrue(_ret, '%s, 设置失败' % _tips)

        _ret = _adapter.mget(['int', 'float'], group=_group)
        self.assertTrue(
            TestTool.cmp_list(_ret, [10, 10.1]), '%s, 批量获取失败' % _tips
        )

        _ret = _adapter.get_group(_group)
        self.assertTrue(
            TestTool.cmp_dict(_ret, _expect), '%s, 分组获取失败' % _tips
        )

        _ret = _adapter.delete_group(_group)
        self.assertTrue(_ret, '%s, 分组删除失败' % _tips)

        _tips = '测试有效时间'
        _group = 'expire'
        _ret = _adapter.set('int', 10, group=_group, ex=3.0)
        self.assertTrue(_ret, '%s, 设置int失败' % _tips)
        _ret = _adapter.get('int', group=_group)
        self.assertTrue(_ret == 10, '%s, 获取int失败' % _tips)

        _expect = {'int': 10, 'float': 10.1, 'str': 'abc', 'list': [1, 3, 2, 4]}
        _ret = _adapter.mset(_expect, group=_group, ex=3.0)
        self.assertTrue(_ret, '%s, mset失败' % _tips)
        _ret = _adapter.get('float', group=_group)
        self.assertTrue(_ret == 10.1, '%s, 获取float失败' % _tips)

        _ret = _adapter.set('exval', 3, group=_group, ex=3.0)
        self.assertTrue(_ret, '%s, 设置exval失败' % _tips)
        _ret = _adapter.get('exval', group=_group)
        self.assertTrue(_ret == 3, '%s, 获取exval失败' % _tips)
        # 延长超时时间
        _ret = _adapter.set_expire('exval', 5.1, group=_group)
        self.assertTrue(_ret, '%s, 更改超时时间失败' % _tips)

        time.sleep(3.1)
        _ret = _adapter.get('int', group=_group)
        self.assertTrue(_ret is None, '%s, 超时后int检查失败' % _tips)
        _ret = _adapter.get('float', group=_group)
        self.assertTrue(_ret is None, '%s, 超时后float检查失败' % _tips)
        _ret = _adapter.get('exval', group=_group)
        self.assertTrue(_ret == 3, '%s, 3秒后获取exval失败' % _tips)

        time.sleep(3)
        _ret = _adapter.get('float', group=_group)
        self.assertTrue(_ret is None, '%s, 超时后exval检查失败' % _tips)

    def test_counter(self):
        # 测试计数器
        _adapter = RedisCacheAdapter(
            redis_para={
                'host': '127.0.0.1'
            }
        )

        _tips = "测试创建计数器和使用"
        _group = 'counter'
        _initial = 10
        _ret = _adapter.set_counter('c1', initial=_initial, group=_group, over_write=True)
        self.assertTrue(_ret, '%s, 设置计数器失败' % _tips)
        _ret = _adapter.get_counter('c1', group=_group)
        self.assertTrue(_ret == 10, '%s, 获取计数器当前值失败' % _tips)

        _ret = _adapter.incr_counter('c1', group=_group)
        self.assertTrue(_ret == 11, '%s, 增加计数器值1失败' % _tips)
        _ret = _adapter.incr_counter('c1', amount=3, group=_group)
        self.assertTrue(_ret == 14, '%s, 增加计数器值2失败' % _tips)

        _ret = _adapter.decr_counter('c1', group=_group)
        self.assertTrue(_ret == 13, '%s, 减少计数器值1失败' % _tips)
        _ret = _adapter.decr_counter('c1', amount=2, group=_group)
        self.assertTrue(_ret == 11, '%s, 减少计数器值2失败' % _tips)

        _ret = _adapter.set_counter('c1', initial=_initial, group=_group, over_write=False)
        self.assertTrue(
            _ret is None or not _ret, '%s, 已存在计数器重复创建失败' % _tips
        )

        _ret = _adapter.delete('c1', group=_group)
        self.assertTrue(_ret, '%s, 删除计数器失败' % _tips)
        _ret = _adapter.get('c1', group=_group)
        self.assertTrue(_ret is None, '%s, 删除计数器检查失败' % _tips)

        _tips = "查询自动创建计数器"
        _ret = _adapter.get_counter('c1', group=_group, auto_set=False)
        self.assertTrue(_ret is None, '%s, 不自动创建失败' % _tips)

        _ret = _adapter.get_counter('c1', group=_group, auto_set=True, initial=10)
        self.assertTrue(_ret == 10, '%s, 自动创建失败' % _tips)

        _ret = _adapter.incr_counter('c1', group=_group)
        self.assertTrue(_ret == 11, '%s, 增加计数器值1失败' % _tips)

        _ret = _adapter.delete('c1', group=_group)
        self.assertTrue(_ret, '%s, 删除计数器失败' % _tips)
        _ret = _adapter.get('c1', group=_group)
        self.assertTrue(_ret is None, '%s, 删除计数器检查失败' % _tips)

        _tips = "增加计数器值自动创建计数器"
        _ret = _adapter.incr_counter('c1', group=_group)
        self.assertTrue(_ret == 1, '%s, 自动创建失败' % _tips)

        _ret = _adapter.incr_counter('c1', group=_group)
        self.assertTrue(_ret == 2, '%s, 自动创建失败' % _tips)

        _ret = _adapter.delete('c1', group=_group)
        self.assertTrue(_ret, '%s, 删除计数器失败' % _tips)
        _ret = _adapter.get('c1', group=_group)
        self.assertTrue(_ret is None, '%s, 删除计数器检查失败' % _tips)

        _tips = "减少计数器值自动创建计数器"
        _ret = _adapter.decr_counter('c1', group=_group)
        self.assertTrue(_ret == -1, '%s, 自动创建失败' % _tips)

        _ret = _adapter.decr_counter('c1', group=_group)
        self.assertTrue(_ret == -2, '%s, 自动创建失败' % _tips)

        _ret = _adapter.delete('c1', group=_group)
        self.assertTrue(_ret, '%s, 删除计数器失败' % _tips)
        _ret = _adapter.get('c1', group=_group)
        self.assertTrue(_ret is None, '%s, 删除计数器检查失败' % _tips)

    def test_list(self):
        # 测试列表
        _adapter = RedisCacheAdapter(
            redis_para={
                'host': '127.0.0.1'
            }
        )

        _tips = '创建并使用列表'
        _group = 'list'
        _ret = _adapter.set_list('l1', group=_group, over_write=True)
        self.assertTrue(_ret, '%s, 创建列表失败' % _tips)

        _ret = _adapter.list_len('l1', group=_group)
        self.assertTrue(_ret == 0, '%s, 列表长度获取0失败: %s' % (_tips, str(_ret)))

        _ret = _adapter.lpush('l1', [1, 2, 3], group=_group)
        self.assertTrue(_ret, '%s, lpush添加列表失败' % _tips)
        _ret = _adapter.list_len('l1', group=_group)
        self.assertTrue(_ret == 3, '%s, 列表长度获取1失败: %s' % (_tips, str(_ret)))

        _ret = _adapter.rpush('l1', [4, 5, 6], group=_group)
        self.assertTrue(_ret, '%s, rpush添加列表失败' % _tips)
        _ret = _adapter.list_len('l1', group=_group)
        self.assertTrue(_ret == 6, '%s, 列表长度获取2失败: %s' % (_tips, str(_ret)))

        _ret = _adapter.list_range('l1', group=_group)
        self.assertTrue(
            TestTool.cmp_list(_ret, [3, 2, 1, 4, 5, 6]), '%s, 获取列表范围失败' % _tips
        )

        _ret = _adapter.lpop('l1', group=_group, count=2)
        self.assertTrue(
            TestTool.cmp_list(_ret, [3, 2]), '%s, 获取lpop失败' % _tips
        )

        _ret = _adapter.rpop('l1', group=_group, count=2)
        self.assertTrue(
            TestTool.cmp_list(_ret, [6, 5]), '%s, 获取rpop失败' % _tips
        )

        _ret = _adapter.list_clear('l1', group=_group)
        self.assertTrue(_ret, '%s, 清空列表失败' % _tips)
        _ret = _adapter.list_len('l1', group=_group)
        self.assertTrue(_ret == 0, '%s, 检查清空列表失败: %s' % (_tips, str(_ret)))

        _ret = _adapter.lpop('l1', group=_group, count=2)
        self.assertTrue(_ret is None, '%s, lpop从空清单取数据失败: %s' % (_tips, str(_ret)))
        _ret = _adapter.rpop('l1', group=_group, count=2)
        self.assertTrue(_ret is None, '%s, rpop从空清单取数据失败: %s' % (_tips, str(_ret)))

    def test_dict(self):
        # 测试字典
        _adapter = RedisCacheAdapter(
            redis_para={
                'host': '127.0.0.1'
            }
        )

        _tips = '测试字典缓存'
        _group = 'dict'
        _ret = _adapter.hset('d1', 'a', 'val_a', group=_group)
        self.assertTrue(_ret, '%s, 设置字典值失败: %s' % (_tips, str(_ret)))
        _ret = _adapter.hget('d1', 'a', group=_group)
        self.assertTrue(_ret == 'val_a', '%s, 获取字典值失败: %s' % (_tips, str(_ret)))

        _ret = _adapter.hset('d1', 'a', 'val_a_new', group=_group)
        self.assertTrue(_ret, '%s, 字典存在情况设置字典值失败: %s' % (_tips, str(_ret)))
        _ret = _adapter.hget('d1', 'a', group=_group)
        self.assertTrue(_ret == 'val_a_new', '%s, 获取新字典值失败: %s' % (_tips, str(_ret)))

        _expect = {'a': 'val_a_mset', 'b': 'btest', 'c': [1, 2, 3], 'd': 4}
        _ret = _adapter.hmset('d1', _expect, group=_group)
        self.assertTrue(_ret, '%s, 批量设置字典值失败: %s' % (_tips, str(_ret)))
        _ret = _adapter.hmget('d1', ['a', 'b', 'c', 'd'], group=_group)
        self.assertTrue(
            TestTool.cmp_dict(_ret, _expect), '%s, 检查批量设置字典值失败: %s' % (_tips, str(_ret))
        )

        _ret = _adapter.hexists('d1', 'b', group=_group)
        self.assertTrue(_ret, '%s, 检查key值存在失败: %s' % (_tips, str(_ret)))

        _ret = _adapter.hgetall('d1', group=_group)
        self.assertTrue(
            TestTool.cmp_dict(_ret, _expect), '%s, 获取所有字典值失败: %s' % (_tips, str(_ret))
        )

        _ret = _adapter.hdel('d1', ['b', 'c'], group=_group)
        self.assertTrue(_ret, '%s, 删除key值失败: %s' % (_tips, str(_ret)))

        _ret = _adapter.hkeys('d1', group=_group)
        self.assertTrue(
            TestTool.cmp_list(_ret, ['a', 'd']), '%s, 获取所有key列表失败: %s' % (_tips, str(_ret))
        )

        _ret = _adapter.delete('d1', group=_group)
        self.assertTrue(_ret, '%s, 删除name失败: %s' % (_tips, str(_ret)))

        _ret = _adapter.hkeys('d1', group=_group)
        self.assertTrue(
            TestTool.cmp_list(_ret, []), '%s, 检查删除name失败: %s' % (_tips, str(_ret))
        )

    def test_auto_cache(self):
        # 先清除数据
        _adapter_1 = RedisCacheAdapter(
            redis_para={
                'host': '127.0.0.1'
            }
        )
        _adapter_1.mdelete(['test_base', 'test_list'])
        _adapter_1.mdelete(
            ['test_dict', 'test_no_load', 'test_after_load', 'test_load_on_get'],
            group='test'
        )

        # 测试自动缓存配置
        _auto_cache_init_handlers = {
            'load_handlers': {
                'base': {
                    'handler': load_handler_base, 'args': ['base_default_val'], 'kwargs': {}
                },
                'list': {
                    'handler': load_handler_list, 'args': [['l1', 'l2', 'l3']], 'kwargs': {}
                },
                'dict': {
                    'handler': load_handler_dict, 'args': [{'d1': 'd1_val', 'd2': 'd2_val'}], 'kwargs': {}
                }
            },
            'check_handlers': {
                'com': {
                    'handler': check_handler, 'args': [True], 'kwargs': {}
                }
            }
        }
        _auto_cache = {
            None: {
                'test_base': {
                    'cache_type': 'base', 'load_handler': 'base', 'load_args': ['test_base_value'],
                    'load_on_init': True, 'reload_on_exists': True
                },
                'test_list': {
                    'cache_type': 'list', 'load_handler': 'list',
                    'load_on_init': True, 'reload_on_exists': True,
                    'check_handler': 'com'
                },
            },
            'test': {
                'test_dict': {
                    'cache_type': 'dict', 'load_handler': 'dict',
                    'load_on_init': True, 'reload_on_exists': True,
                    'check_handler': 'com'
                },
                'test_no_load': {
                    'cache_type': 'base', 'load_handler': 'base', 'load_args': ['test_base_value'],
                    'load_on_init': False, 'reload_on_exists': False,
                    'check_handler': 'com', 'check_args': [False]
                },
                'test_after_load': {
                    'cache_type': 'base', 'load_handler': 'base', 'load_args': ['test_base_value'],
                    'load_on_init': False, 'reload_on_exists': False,
                    'check_handler': 'com', 'check_args': [True]
                }
            }
        }
        _adapter = RedisCacheAdapter(
            auto_cache=_auto_cache,
            auto_cache_init_handlers=_auto_cache_init_handlers,
            redis_para={
                'host': '127.0.0.1'
            }
        )
        _tips = '自动缓存配置测试'
        _ret = _adapter.get('test_base')
        self.assertTrue(_ret == 'test_base_value', '%s, 初始化加载base失败: %s' % (_tips, _ret))

        _ret = _adapter.list_range('test_list')
        self.assertTrue(
            TestTool.cmp_list(_ret, ['l1', 'l2', 'l3']), '%s, 初始化加载list失败: %s' % (_tips, _ret)
        )

        _ret = _adapter.hgetall('test_dict', group='test')
        self.assertTrue(
            TestTool.cmp_dict(_ret, {'d1': 'd1_val', 'd2': 'd2_val'}), '%s, 初始化加载dict失败: %s' % (_tips, _ret)
        )

        _ret = _adapter.get('test_no_load', group='test')
        self.assertTrue(_ret is None, '%s, 初始化不加载失败1: %s' % (_tips, _ret))
        _ret = _adapter.get('test_after_load', group='test')
        self.assertTrue(_ret is None, '%s, 初始化不加载失败2: %s' % (_tips, _ret))

        _adapter.load_auto_cache('test_no_load', group='test')
        _ret = _adapter.get('test_no_load', group='test')
        self.assertTrue(_ret is None, '%s, 检查不通过不加载失败: %s' % (_tips, _ret))

        _adapter.load_auto_cache('test_after_load', group='test')
        _ret = _adapter.get('test_after_load', group='test')
        self.assertTrue(_ret == 'test_base_value', '%s, 初始化以后再加载失败: %s' % (_tips, _ret))

        _adapter.load_auto_cache('test_no_load', group='test', force=True)
        _ret = _adapter.get('test_no_load', group='test')
        self.assertTrue(_ret == 'test_base_value', '%s, 强制不检查加载数据失败: %s' % (_tips, _ret))

        _adapter.set_auto_cache(
            'test_load_on_get', load_handler_dict, group='test', cache_type='dict',
            load_args=[{'t1': 't1_val', 't2': 3}]
        )
        _ret = _adapter.hgetall('test_load_on_get', group='test')
        self.assertTrue(len(_ret) == 0, '%s, 未加载数据配置普通获取失败: %s' % (_tips, _ret))
        _ret = _adapter.hgetall_auto_cache('test_load_on_get', group='test')
        self.assertTrue(
            TestTool.cmp_dict(_ret, {'t1': 't1_val', 't2': 3}), '%s, 未加载数据配置获取时加载失败: %s' % (_tips, _ret)
        )


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
