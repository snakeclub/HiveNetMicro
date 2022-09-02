#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
缓存服务适配器

@module cache
@file cache.py
"""
import os
import sys
import traceback
from typing import Any
from HiveNetCore.utils.run_tool import AsyncTools
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.adapter_base import AdapterBaseFw
from HiveNetMicro.core.global_manager import GlobalManager
from HiveNetMicro.core.logger_manager import LoggerManager


class CacheAdapter(AdapterBaseFw):
    """
    缓存服务适配器
    """

    #############################
    # 适配器基础属性
    #############################
    @property
    def adapter_type(self) -> str:
        """
        适配器类型

        @property {str} - 指定适配器类型
        """
        return 'Cache'

    #############################
    # 构造函数
    #############################
    def __init__(self, **kwargs):
        """
        构造函数

        @param {dict} auto_cache=None - 自动缓存管理参数
            [group] {dict} - 缓存所属分组, key为分组标识, 分组可以为None
                [name] {dict} - 缓存参数, key为缓存名
                    cache_type {str} - 缓存类型, base-基础类型缓存, list-列表类型缓存, dict-字典类型缓存
                    load_handler {function|str} - 缓存获取函数对象(或已加载的函数对象索引id)
                    load_args {list} - 缓存获取函数的固定入参列表
                    load_kwargs {dict} - 缓存获取函数的key-value入参字典
                    load_on_init {bool} - 插件初始化时加载数据, 默认为False
                    reload_on_exists {bool} - 当缓存已存在时是否重新加载(与load_on_init配套使用), 默认为False
                    check_handler {function|str} - 重新加载检查数据是否需更新的检查函数对象(或已加载的函数对象索引id)
                        注: 函数执行结果为True才会重新加载函数, 如果不设置该函数, 视为每次都重新加载数据
                    check_args {list} - 缓存更新检查函数的固定入参列表
                    check_kwargs {dict} - 缓存更新检查函数的key-value入参字典
        @param {dict} auto_cache_init_handlers=None - 自动缓存管理初始化的函数对象索引
            'load_handlers' {dict} - 缓存数据获取函数索引
                [id] {dict} - 函数对象索引id, key为索引id标识字符串
                    handler {function|str} - 缓存获取函数对象
                        注: 如果传入的是str代表获取统一加载的对象, 从SYS_ADAPTER_MANAGER中获取类型为DynamicObject的对应函数对象
                        函数定义为:
                        func(cache_config, *args, **kwargs)
                        cache_config为外部传入的缓存信息字典, 格式为:
                            {
                                'cache_adapter': object, # 缓存适配器实例对象, 可以通过该适配器查询缓存数据
                                'name': '',  # 缓存名
                                'group': '',  # 缓存所属数组
                                'cache_type': '',  # 缓存类型
                            }
                        函数返回值根据缓存类型采取不同的返回方式:  base类型直接返回单个缓存值, list类型返回缓存值的list清单, dict类型返回缓存字典
                    args {list} - 默认的缓存获取函数的固定入参列表(当自动缓存管理参数不设置时使用该值传入)
                    kwargs {dict} - 默认的缓存获取函数的key-value入参字典(当自动缓存管理参数不设置时使用该值传入)
            'check_handlers' {dict} - 检查缓存数据是否需更新的检查函数索引
                [id] {dict} - 函数对象索引id, key为索引id标识字符串
                    handler {function|str} - 检查缓存数据是否需要更新的函数对象
                        注: 如果传入的是str代表获取统一加载的对象, 从SYS_ADAPTER_MANAGER中获取类型为DynamicObject的对应函数对象
                        函数定义为:
                        func(cache_config, *args, **kwargs)
                        cache_config定义与load_handler一致
                        函数返回值为bool对象, 指示缓存数据是否需要更新
                    args {list} - 默认的缓存更新检查函数的固定入参列表(当自动缓存管理参数不设置时使用该值传入)
                    kwargs {dict} - 默认的缓存更新检查函数的key-value入参字典(当自动缓存管理参数不设置时使用该值传入)
        @param {str} logger_id=None - 日志对象标识, 可以选择application.yaml配置中的其中一个日志对象
        @param {kwargs} - 实现类的自定义参数
            ...
        """
        # 传入参数
        self._kwargs = kwargs

        # 日志对象
        _logger_manager: LoggerManager = GlobalManager.GET_SYS_LOGGER_MANAGER()
        if _logger_manager is None:
            _logger_manager = LoggerManager('')
        self.logger = _logger_manager.get_logger(
            self._kwargs.get('logger_id', None), none_with_default_logger=True
        )

        # 适配器管理模块
        self.sys_adapter_manager = GlobalManager.GET_SYS_ADAPTER_MANAGER()

        # 执行实现类的初始化函数
        self._self_init()

        # 自动缓存管理初始化的函数对象索引参数
        self._auto_cache_init_handlers = {
            'load_handlers': {}, 'check_handlers': {}
        }
        if self._kwargs.get('auto_cache_init_handlers', None) is not None:
            _load_handlers_config = self._kwargs['auto_cache_init_handlers'].get('load_handlers', {})
            for _id, _paras in _load_handlers_config.items():
                _load_handler = _paras['handler']
                if type(_load_handler) == str:
                    _load_handler = self.sys_adapter_manager.get_adapter(
                        'DynamicObject', _id
                    )

                self._auto_cache_init_handlers['load_handlers'][_id] = {
                    'handler': _load_handler,
                    'args': _paras.get('args', []),
                    'kwargs': _paras.get('kwargs', {})
                }

            _load_handlers_config = self._kwargs['auto_cache_init_handlers'].get('check_handlers', {})
            for _id, _paras in _load_handlers_config.items():
                _check_handler = _paras['handler']
                if type(_check_handler) == str:
                    _check_handler = self.sys_adapter_manager.get_adapter(
                        'DynamicObject', _id
                    )

                self._auto_cache_init_handlers['check_handlers'][_id] = {
                    'handler': _check_handler,
                    'args': _paras.get('args', []),
                    'kwargs': _paras.get('kwargs', {})
                }

        # 自动缓存管理参数
        self._auto_cache = {}
        if self._kwargs.get('auto_cache', None) is not None:
            for _group, _name_paras in self._kwargs['auto_cache'].items():
                self._auto_cache[_group] = {}
                for _name, _paras in _name_paras.items():
                    _load_handler = _paras.pop('load_handler')
                    self.set_auto_cache(_name, _load_handler, group=_group, **_paras)

    #############################
    # 缓存数据管理
    #############################
    def set_auto_cache(self, name: str, load_handler, group: str = None, **kwargs):
        """
        设置自动缓存配置

        @param {str} name - 缓存名
        @param {function|str} load_handler - 缓存获取函数对象(或已加载的函数对象索引id)
        @param {str} group=None - 缓存所属分组
        @param {str} cache_type='base' - 缓存类型, base-基础类型缓存, list-列表类型缓存, dict-字典类型缓存
        @param {list} load_args=None - 缓存获取函数的固定入参列表
        @param {dict} load_kwargs=None - 缓存获取函数的key-value入参字典
        @param {bool} load_on_init=False  - 插件初始化时加载数据
        @param {bool} reload_on_exists=False - 当缓存已存在时是否重新加载(与load_on_init配套使用)
        @param {function|str} check_handler=None - 重新加载检查数据是否需更新的检查函数对象(或已加载的函数对象索引id)
            注: 函数执行结果为True才会重新加载函数, 如果不设置该函数, 视为每次都重新加载数据
        @param {list} check_args=None - 缓存更新检查函数的固定入参列表
        @param {dict} check_kwargs=None - 缓存更新检查函数的key-value入参字典
        """
        # 校验参数
        if self._auto_cache.get(group, {}).get(name, None) is not None:
            raise RuntimeError('auto cache group[%s] name[%s] exists' % (str(group), name))

        # 处理分组
        _group_paras = self._auto_cache.get(group, None)
        if _group_paras is None:
            self._auto_cache[group] = {}
            _group_paras = self._auto_cache[group]

        # 处理部分参数
        _load_args = kwargs.get('load_args', None)
        _load_kwargs = kwargs.get('load_kwargs', None)
        if type(load_handler) == str:
            _handler_paras = self._auto_cache_init_handlers['load_handlers'].get(load_handler, None)
            _load_handler = _handler_paras['handler']
            _load_args = _handler_paras['args'] if _load_args is None else _load_args
            _load_kwargs = _handler_paras['kwargs'] if _load_kwargs is None else _load_kwargs
        else:
            _load_handler = load_handler
            _load_args = [] if _load_args is None else _load_args
            _load_kwargs = {} if _load_kwargs is None else _load_kwargs

        _check_handler = kwargs.get('check_handler', None)
        _check_args = kwargs.get('check_args', None)
        _check_kwargs = kwargs.get('check_kwargs', None)
        if type(_check_handler) == str:
            _handler_paras = self._auto_cache_init_handlers['check_handlers'].get(_check_handler, None)
            _check_handler = _handler_paras['handler']
            _check_args = _handler_paras['args'] if _check_args is None else _check_args
            _check_kwargs = _handler_paras['kwargs'] if _check_kwargs is None else _check_kwargs
        else:
            _check_args = [] if _check_args is None else _check_args
            _check_kwargs = {} if _check_kwargs is None else _check_kwargs

        # 设置参数
        _group_paras[name] = {
            'cache_type': kwargs.get('cache_type', 'base'),
            'load_handler': _load_handler,
            'load_args': _load_args,
            'load_kwargs': _load_kwargs,
            'load_on_init': kwargs.get('load_on_init', False),
            'reload_on_exists': kwargs.get('reload_on_exists', False),
            'check_handler': _check_handler,
            'check_args': _check_args,
            'check_kwargs': _check_kwargs
        }

        # 判断是否立即加载数据
        if _group_paras[name]['load_on_init']:
            if not self.exists(name, group=group) or _group_paras[name]['reload_on_exists']:
                self.load_auto_cache(name, group=group, force=True)

    def remove_auto_cache(self, name: str, group: str = None, delete_cache_data: bool = False):
        """
        移除设置自动缓存配置

        @param {str} name - 缓存名
        @param {str} group=None - 缓存所属分组
        @param {bool} delete_cache_data=False - 是否删除缓存数据
        """
        _paras = self._auto_cache.get(group, {}).get(name, None)
        if _paras is None:
            # 缓存配置不存在
            return

        # 删除配置
        self._auto_cache[group].pop(name)

        # 删除缓存数据
        if delete_cache_data:
            self.delete(name, group=group)

    def load_auto_cache(self, name: str, group: str = None, force: bool = False):
        """
        加载自动缓存数据

        @param {str} name - 缓存名
        @param {str} group=None - 缓存所属分组
        @param {bool} force=False - 是否忽略检查函数结果直接重新加载
        """
        _paras = self._auto_cache.get(group, {}).get(name, None)
        if _paras is None:
            raise RuntimeError('auto cache group[%s] name[%s] exists' % (str(group), name))

        # 准备更新参数
        _cache_config = {
            'cache_adapter': self,
            'name': name,  # 缓存名
            'group': group,  # 缓存所属数组
            'cache_type': _paras['cache_type']  # 缓存类型
        }

        # 检查是否需要更新
        _check_ok = True
        if not force and _paras['check_handler'] is not None:
            _check_ok = AsyncTools.sync_run_coroutine(
                _paras['check_handler'](
                    _cache_config, *_paras['check_args'], **_paras['check_kwargs']
                )
            )

        # 执行更新
        if not _check_ok:
            return

        _datas = AsyncTools.sync_run_coroutine(
            _paras['load_handler'](
                _cache_config, *_paras['load_args'], **_paras['load_kwargs']
            )
        )
        if _paras['cache_type'] == 'list':
            _temp_name = '{$load_auto_cache_temp$}_%s' % name
            _ret = self.set_list(_temp_name, initial=_datas, group=group, over_write=True)
            if _ret:
                # 删除原来的缓存数据并重命名
                self.delete(name, group=group)
                _ret = self.rename(_temp_name, name, group=group)
        elif _paras['cache_type'] == 'dict':
            _temp_name = '{$load_auto_cache_temp$}_%s' % name
            self.delete(_temp_name, group=group)
            _ret = self.hmset(_temp_name, _datas, group=group)
            if _ret:
                # 删除原来的缓存数据并重命名
                self.delete(name, group=group)
                _ret = self.rename(_temp_name, name, group=group)
        else:
            _ret = self.set(name, _datas, group=group)

        if not _ret:
            raise RuntimeError('set cache error')

    def get_auto_cache(self, name: str, group: str = None) -> Any:
        """
        获取auto_cache设置的缓存值(对应函数get)

        @param {str} name - 缓存名
        @param {str} group=None - 缓存所属分组标识

        @returns {Any} - 返回的缓存值
            注: 如果缓存不存在返回None
        """
        _val = self.get(name, group=group)
        if _val is None:
            # 查找不到数据, 尝试自动加载后重新获取
            try:
                self.load_auto_cache(name, group=group)
                _val = self.get(name, group=group)
            except:
                self.logger.warning(
                    'load_auto_cache name[%s] group[%s] error: %s' % (
                        name, group, traceback.format_exc()
                    )
                )

        return _val

    def hget_auto_cache(self, name: str, key: str, group: str = None) -> Any:
        """
        获取auto_cache设置的字典缓存的指定值(对应hget函数)

        @param {str} name - 字典名
        @param {str} key - 要获取的字典kv值的key
        @param {str} group=None - 缓存所在分组

        @returns {Any} - 字典kv值的value
        """
        _val = self.hget(name, key, group=group)
        if _val is None:
            # 查找不到数据, 尝试自动加载后重新获取
            try:
                self.load_auto_cache(name, group=group)
                _val = self.hget(name, key, group=group)
            except:
                self.logger.warning(
                    'load_auto_cache name[%s] group[%s] error: %s' % (
                        name, group, traceback.format_exc()
                    )
                )

        return _val

    def hmget_auto_cache(self, name: str, keys: list, group: str = None) -> dict:
        """
        获取auto_cache设置的字典中的多个值(对应hmget函数)

        @param {str} name - 字典名
        @param {list} keys - 要获取的key值清单
        @param {str} group=None - 缓存所在分组

        @returns {dict} - 相应清单的值
            注: 如果缓存不存在, 返回{}
        """
        _val = self.hmget(name, keys, group=group)
        if len(_val) == 0:
            # 查找不到数据, 尝试自动加载后重新获取
            try:
                self.load_auto_cache(name, group=group)
                _val = self.hmget(name, keys, group=group)
            except:
                self.logger.warning(
                    'load_auto_cache name[%s] group[%s] error: %s' % (
                        name, group, traceback.format_exc()
                    )
                )

        return _val

    def hgetall_auto_cache(self, name: str, group: str = None) -> dict:
        """
        获取auto_cache设置的字典的所有值(对应函数hgetall)

        @param {str} name - 字典名
        @param {str} group=None - 缓存所在分组

        @returns {dict} - 字典所有值
            注: 如果缓存不存在, 返回{}
        """
        _val = self.hgetall(name, group=group)
        if len(_val) == 0:
            # 查找不到数据, 尝试自动加载后重新获取
            try:
                self.load_auto_cache(name, group=group)
                _val = self.hgetall(name, group=group)
            except:
                self.logger.warning(
                    'load_auto_cache name[%s] group[%s] error: %s' % (
                        name, group, traceback.format_exc()
                    )
                )

        return _val

    #############################
    # 需要实现类重载的内部函数
    #############################
    def _self_init(self):
        """
        实现类自定义的初始化函数
        """
        pass

    #############################
    # 需重载的通用缓存操作
    #############################
    def delete(self, name: str, group: str = None) -> bool:
        """
        删除缓存值

        @param {str} name - 缓存名
        @param {str} group=None - 缓存所属分组标识

        @returns {bool} - 删除结果, 如果找不到name返回False
        """
        raise NotImplementedError()

    def mdelete(self, names: list, group: str = None) -> bool:
        """
        批量删除缓存

        @param {list} names - 缓存name列表
        @param {str} group=None - 缓存所属分组标识

        @returns {bool} - 处理结果
        """
        raise NotImplementedError()

    def delete_group(self, group: str) -> bool:
        """
        删除分组的所有缓存

        @param {str} group - 缓存所属分组标识

        @returns {bool} - 处理结果
        """
        raise NotImplementedError()

    def rename(self, src_name: str, dest_name: str, group: str = None) -> bool:
        """
        修改缓存名称

        @param {str} src_name - 源名称
        @param {str} dest_name - 目标名
        @param {str} group=None - 缓存所在分组

        @returns {bool} - 修改结果
        """
        raise NotImplementedError()

    def exists(self, name: str, group: str = None) -> bool:
        """
        判断缓存名是否存在

        @param {str} name - 缓存名
        @param {str} group=None - 缓存所在分组

        @returns {bool} - 是否存在
        """
        raise NotImplementedError()

    def keys(self, pattern: str, group: str = None) -> list:
        """
        获取指定key列表

        @param {str} pattern - 查询key的条件, 支持通配符如下:
            * - 代表匹配任意字符, 例如'abc_*'
            ? - 代表匹配一个字符, 例如'a?b'
            [] - 代表匹配部分字符, 例如[ab]代表匹配a或b, [1,3]代表匹配1和3, 而[1-10]代表匹配1到10的任意数字
            x - 转移字符，例如要匹配星号, 问号需要转义的字符, 例如'ax*b'
        @param {str} group=None - 缓存所属分组

        @returns {list} - 返回的缓存列表
        """
        raise NotImplementedError()

    def scan(self, pattern: str, group: str = None, count: int = 10):
        """
        通过迭代器方式查询key并返回

        @param {str} pattern - 查询key的条件, 支持通配符如下:
            * - 代表匹配任意字符, 例如'abc_*'
            ? - 代表匹配一个字符, 例如'a?b'
            [] - 代表匹配部分字符, 例如[ab]代表匹配a或b, [1,3]代表匹配1和3, 而[1-10]代表匹配1到10的任意数字
            x - 转移字符，例如要匹配星号, 问号需要转义的字符, 例如'ax*b'
        @param {str} group=None - 缓存所属分组
        @param {int} count=10 - 每次从服务器获取的数据批量大小(越大性能越好, 但内存占用越高)

        @retruns {iterator} - 返回key字符串的迭代器
        """
        raise NotImplementedError()

    #############################
    # 需重载的基础类型值缓存操作
    #############################
    def set(self, name: str, value: Any, group: str = None, ex: float = None, nx: bool = False) -> bool:
        """
        设置缓存值

        @param {str} name - 缓存名
        @param {Any} value - 要设置的缓存的值
        @param {str} group=None - 缓存所属分组标识, 分组内name应唯一
        @param {float} ex=None - 缓存过期时长, 单位为秒
        @param {bool} nx=False - 当缓存不存在时才进行设置, 默认为False, 代表直接覆盖

        @returns {bool} - 返回设置结果
        """
        raise NotImplementedError()

    def get(self, name: str, group: str = None) -> Any:
        """
        获取缓存值

        @param {str} name - 缓存名
        @param {str} group=None - 缓存所属分组标识

        @returns {Any} - 返回的缓存值
            注: 如果缓存不存在返回None
        """
        raise NotImplementedError()

    def mset(self, nvs: dict, group: str = None, ex: float = None) -> bool:
        """
        批量设置值

        @param {dict} nvs - 要设置的name-value字典
        @param {str} group=None - 缓存所属分组标识
        @param {float} ex=None - 缓存过期时长, 单位为秒

        @param {bool} - 返回结果(部分成功也是返回False)
        """
        raise NotImplementedError()

    def mget(self, names: list, group: str = None) -> list:
        """
        批量获取值

        @param {list} names - 要获取的name列表
        @param {str} group=None - 缓存所属分组标识

        @returns {list} - 以列表方式顺序返回对应name的值
            注: 如果获取不到返回None
        """
        raise NotImplementedError()

    def get_group(self, group: str) -> dict:
        """
        获取分组的所有值

        @param {str} group - 缓存所属分组标识
            注: 不支持分组为None的情况

        @returns {dict} - 获取到的name-value缓存字典
            注: 如果获取不到返回None
        """
        raise NotImplementedError()

    def set_expire(self, name: str, ex: float, group: str = None) -> bool:
        """
        更新缓存的过期时间

        @param {str} name - 缓存名
        @param {float} ex - 过期时间, 单位为秒
            注: 如果传None代表缓存不过期
        @param {str} group=None - 缓存所属分组标识

        @returns {bool} - 设置结果
        """
        raise NotImplementedError()

    #############################
    # 需重载的计数器缓存操作
    #############################
    def set_counter(self, name: str, initial: int = 0, group: str = None, over_write: bool = False) -> bool:
        """
        设置计数器
        注: counter实际上也是缓存, 可以直接通过get获取当前值, 以及delete删除

        @param {str} name - 计数器名
        @param {int} initial=0 - 设置初始值
        @param {str} group=None - 缓存所属分组
        @param {bool} over_write=False - 如果计数器已存在是否覆盖

        @returns {bool} - 设置结果
        """
        raise NotImplementedError()

    def get_counter(self, name: str, group: str = None, auto_set: bool = True, initial: int = 0) -> int:
        """
        获取计数器当前值

        @param {str} name - 计数器名
        @param {str} group=None - 缓存所属分组
        @param {bool} auto_set=True - 不存在是否自动设置计数器
        @param {int} initial=0 - 设置初始值

        @returns {int} - 返回当前计数器值, 不存在返回None
        """
        raise NotImplementedError()

    def incr_counter(self, name: str, amount: int = 1, group: str = None) -> int:
        """
        增加计数器值
        注: 如果计数器不存在, 将自动创建并设置初始值为0

        @param {str} name - 计数器名
        @param {int} amount=1 - 指定增加数
        @param {str} group=None - 缓存所属分组

        @returns {int} - 返回增长后的值
        """
        raise NotImplementedError()

    def decr_counter(self, name: str, amount: int = 1, group: str = None) -> int:
        """
        减少计数器值
        注: 如果计数器不存在, 将自动创建并设置初始值为0

        @param {str} name - 计数器名
        @param {int} amount=1 - 指定减少数
        @param {str} group=None - 缓存所属分组

        @returns {int} - 返回减少后的值
        """
        raise NotImplementedError()

    #############################
    # 需重载的列表类型缓存操作
    #############################
    def set_list(self, name: str, initial: list = [], group: str = None, over_write: bool = False) -> bool:
        """
        设置列表
        注: 列表可通过delete删除, 但不能通过get等其他基础类型函数处理

        @param {str} name - 列表名
        @param {list} initial=[] - 设置初始值
        @param {str} group=None - 缓存所属分组
        @param {bool} over_write=False - 如果列表已存在是否覆盖

        @returns {bool} - 设置结果
        """
        raise NotImplementedError()

    def list_len(self, name: str, group: str = None) -> int:
        """
        获取列表长度

        @param {str} name - 列表名
        @param {str} group=None - 缓存所在分组

        @returns {int} - 返回列表长度
            注: None代表name不存在
        """
        raise NotImplementedError()

    def list_clear(self, name: str, group: str = None) -> bool:
        """
        清空列表

        @param {str} name - 列表名
        @param {str} group=None - 缓存的分组

        @returns {bool} - 处理结果
        """
        raise NotImplementedError()

    def lpush(self, name: str, datas: list, group: str = None) -> bool:
        """
        在列表左边添加数据
        注: 如果列表不存在将自动创建列表

        @param {str} name - 列表名
        @param {list} datas - 要添加的数据列表
            注: 添加方式是逐个向左边添加, 因此添加完成后数据在列表中的顺序是相反的
        @param {str} group=None - 缓存所在分组

        @returns {bool} - 是否添加成功
        """
        raise NotImplementedError()

    def rpush(self, name: str, datas: list, group: str = None) -> bool:
        """
        在列表右边添加数据
        注: 如果列表不存在将自动创建列表

        @param {str} name - 列表名
        @param {list} datas - 要添加的数据列表
        @param {str} group=None - 缓存所在分组

        @returns {bool} - 是否添加成功
        """
        raise NotImplementedError()

    def list_range(self, name: str, start: int = 0, end: int = None, group: str = None) -> list:
        """
        获取列表指定区域范围的值列表

        @param {str} name - 列表名
        @param {int} start=0 - 开始位置, 从0开始
        @param {int} end=None - 结束为止, 如果为None代表获取到结尾
        @param {str} group=None - 缓存所在的组

        @returns {list} - 返回值列表
        """
        raise NotImplementedError()

    def lpop(self, name: str, group: str = None, count: int = 1) -> list:
        """
        从左边取出值并删除

        @param {str} name - 列表名
        @param {str} group=None - 缓存所在分组
        @param {int} count=1 - 要取出的数量

        @returns {list} - 取出数据的列表
            注: 如果没有值返回None
        """
        raise NotImplementedError()

    def rpop(self, name: str, group: str = None, count: int = 1) -> list:
        """
        从右边取出值并删除
        注: 如果取出多个, 结果列表中的排序是反序

        @param {str} name - 列表名
        @param {str} group=None - 缓存所在分组
        @param {int} count=1 - 要取出的数量

        @returns {list} - 取出数据的列表
            注: 如果没有值返回None
        """
        raise NotImplementedError()

    #############################
    # 需重载的字典类型缓存(hash set)操作
    #############################
    def hset(self, name: str, key: str, value: Any, group: str = None) -> bool:
        """
        设置字典的单个kv值

        @param {str} name - 字典名
        @param {str} key - 要设置的字典kv值的key
        @param {Any} value - 要设置的字典kv值的value
        @param {str} group=None - 缓存所在的分组

        @returns {bool} - 设置结果
        """
        raise NotImplementedError()

    def hmset(self, name: str, kvs: dict, group: str = None) -> bool:
        """
        批量设置字典的多个kv值

        @param {str} name - 字典名
        @param {dict} kvs - 要设置的key-value值
        @param {str} group=None - 缓存所在的分组

        @returns {bool} - 设置结果
        """
        raise NotImplementedError()

    def hget(self, name: str, key: str, group: str = None) -> Any:
        """
        获取字典缓存的指定值

        @param {str} name - 字典名
        @param {str} key - 要获取的字典kv值的key
        @param {str} group=None - 缓存所在分组

        @returns {Any} - 字典kv值的value
        """
        raise NotImplementedError()

    def hmget(self, name: str, keys: list, group: str = None) -> dict:
        """
        获取字典中的多个值

        @param {str} name - 字典名
        @param {list} keys - 要获取的key值清单
        @param {str} group=None - 缓存所在分组

        @returns {dict} - 相应清单的值
            注: 如果缓存不存在, 返回{}
        """
        raise NotImplementedError()

    def hgetall(self, name: str, group: str = None) -> dict:
        """
        获取字典的所有值

        @param {str} name - 字典名
        @param {str} group=None - 缓存所在分组

        @returns {dict} - 字典所有值
            注: 如果缓存不存在, 返回{}
        """
        raise NotImplementedError()

    def hdel(self, name: str, keys: list, group: str = None) -> bool:
        """
        删除字典中指定的key

        @param {str} name - 字典名
        @param {list} keys - 要删除的key列表
        @param {str} group=None - 缓存所在的分组

        @returns {bool} - 处理结果
        """
        raise NotImplementedError()

    def hexists(self, name: str, key: str, group: str = None) -> bool:
        """
        判断key是否在字典中

        @param {str} name - 字典名
        @param {str} key - key值
        @param {str} group=None - 缓存所在的分组

        @returns {bool} - 判断结果
        """
        raise NotImplementedError()

    def hkeys(self, name: str, group: str = None) -> list:
        """
        获取字典中的所有key清单

        @param {str} name - 字典名
        @param {str} group=None - 缓存所在的分组

        @returns {list} - key清单
        """
        raise NotImplementedError()
