#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
基于Redis实现的缓存服务适配器

@module cache_redis
@file cache_redis.py
"""
import os
import sys
import math
import datetime
import json
from typing import Any
# 自动安装依赖库
from HiveNetCore.utils.pyenv_tool import PythonEnvTools
try:
    import redis
except ImportError:
    PythonEnvTools.install_package('redis')
    import redis
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.interface.extend.cache import CacheAdapter


class RedisCacheAdapter(CacheAdapter):
    """
    基于Redis实现的缓存服务适配器
    """

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
            redis_para {dict} - redis的连接参数字典, 具体参数见redis.Redis的初始化参数, 部分参数参考如下:
                max_connections {int} - 最大连接数, 默认为None
                host {str} - redis服务地址, 默认为'127.0.0.1'
                port {int} - redis服务端口, 默认为6379
                username {str} - 登录用户, 默认为None
                password {str} - 登录密码, 默认为None
            json {object} - 用于进行缓存值json转换的对象, 必须实现兼容原生json的dumps和loads函数, 默认使用原生json
        """
        super().__init__(**kwargs)

    def __del__(self):
        """
        析构函数
        """
        # 关闭连接
        self._redis.close()

    #############################
    # 需要实现类重载的内部函数
    #############################
    def _self_init(self):
        """
        实现类自定义的初始化函数
        """
        # 处理连接处理
        self._redis_para = self._kwargs.get('redis_para', {})
        self._redis_para['decode_responses'] = True
        self._json = self._kwargs.get('json', json)

        # 连接池和连接对象
        self._conn_pool = redis.ConnectionPool(**self._redis_para)
        self._redis = redis.Redis(connection_pool=self._conn_pool)

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
        return self._redis.delete(self._get_real_name(name, group)) == 1

    def mdelete(self, names: list, group: str = None) -> bool:
        """
        批量删除缓存

        @param {list} names - 缓存name列表
        @param {str} group=None - 缓存所属分组标识

        @returns {bool} - 处理结果
        """
        return self._redis.delete(*self._get_real_name_list(names, group)) == len(names)

    def delete_group(self, group: str) -> bool:
        """
        删除分组的所有缓存

        @param {str} group - 缓存所属分组标识

        @returns {bool} - 处理结果
        """
        _names = self._redis.keys('{$group=%s$}_*' % group)
        if _names is None or len(_names) == 0:
            return None

        return self._redis.delete(*_names) == len(_names)

    def rename(self, src_name: str, dest_name: str, group: str = None) -> bool:
        """
        修改缓存名称

        @param {str} src_name - 源名称
        @param {str} dest_name - 目标名
        @param {str} group=None - 缓存所在分组

        @returns {bool} - 修改结果
        """
        _src_real_name = self._get_real_name(src_name, group)
        _dest_real_name = self._get_real_name(dest_name, group)
        return self._redis.rename(_src_real_name, _dest_real_name)

    def exists(self, name: str, group: str = None) -> bool:
        """
        判断缓存名是否存在

        @param {str} name - 缓存名
        @param {str} group=None - 缓存所在分组

        @returns {bool} - 是否存在
        """
        _real_name = self._get_real_name(name, group)
        return self._redis.exists(_real_name) > 0

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
        # 生成真正的查询条件
        if group is None:
            _group = ''
        else:
            _group_len = len('{$group=%s$}_' % group)
            _group = group.replace('*', 'x*').replace('?', 'x?').replace('[', 'x[').replace(']', 'x]')
            _group = '{$group=%s$}_' % _group

        _pattern = '%s%s' % (_group, pattern)

        _keys = self._redis.keys(_pattern)
        if group is None:
            return _keys
        else:
            return [_key[_group_len:] for _key in _keys]

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
        # 生成真正的查询条件
        if group is None:
            _group = ''
        else:
            _group_len = len('{$group=%s$}_' % group)
            _group = group.replace('*', 'x*').replace('?', 'x?').replace('[', 'x[').replace(']', 'x]')
            _group = '{$group=%s$}_' % _group

        _pattern = '%s%s' % (_group, pattern)

        for _key in self._redis.scan_iter(_pattern, count=count):
            if group is None:
                yield _key
            else:
                yield _key[_group_len:]

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
        _px = None if ex is None else math.floor(ex * 1000)
        if type(value) == str:
            # 无需进行转换, 直接存储
            _value = value
        else:
            # 转换为json格式存储
            _value = '{$json$}%s' % self._json.dumps(value, ensure_ascii=False)

        _ret = self._redis.set(
            self._get_real_name(name, group), _value, px=_px, nx=nx
        )
        return False if _ret is None else _ret

    def get(self, name: str, group: str = None) -> Any:
        """
        获取缓存值

        @param {str} name - 缓存名
        @param {str} group=None - 缓存所属分组标识

        @returns {Any} - 返回的缓存值
            注: 如果缓存不存在返回None
        """
        _value = self._redis.get(self._get_real_name(name, group))
        return self._get_real_value(_value)

    def mset(self, nvs: dict, group: str = None, ex: float = None) -> bool:
        """
        批量设置值

        @param {dict} nvs - 要设置的name-value字典
        @param {str} group=None - 缓存所属分组标识
        @param {float} ex=None - 缓存过期时长, 单位为秒

        @param {bool} - 返回结果(部分成功也是返回False)
        """
        _real_nvs = self._get_mset_nvs(nvs, group)
        _ret = self._redis.mset(_real_nvs)
        if ex is None:
            # 不设置超时
            return _ret
        else:
            # 遍历设置超时
            _result = True
            for _name in _real_nvs.keys():
                if not self.set_expire(_name, ex, group=None):
                    _result = False

            return _result

    def mget(self, names: list, group: str = None) -> list:
        """
        批量获取值

        @param {list} names - 要获取的name列表
        @param {str} group=None - 缓存所属分组标识

        @returns {list} - 以列表方式顺序返回对应name的值
            注: 如果获取不到返回None
        """
        _names = self._get_real_name_list(names, group)
        _ret = self._redis.mget(_names)
        if _ret is None:
            return _ret
        else:
            return [self._get_real_value(_val) for _val in _ret]

    def get_group(self, group: str) -> dict:
        """
        获取分组的所有值

        @param {str} group - 缓存所属分组标识
            注: 不支持分组为None的情况

        @returns {dict} - 获取到的name-value缓存字典
            注: 如果获取不到返回None
        """
        # 获取分组的key清单
        _names = self._redis.keys('{$group=%s$}_*' % group)
        if _names is None or len(_names) == 0:
            return None

        # 获取值
        _values = self.mget(_names, group=None)
        if _values is None:
            return None
        else:
            # 对应回key字典
            _ret = {}
            for _i in range(len(_names)):
                _name = _names[_i][_names[_i].find('$}_') + 3:]
                _ret[_name] = _values[_i]

            return _ret

    def set_expire(self, name: str, ex: float, group: str = None) -> bool:
        """
        更新缓存的过期时间

        @param {str} name - 缓存名
        @param {float} ex - 过期时间, 单位为秒
            注: 如果传None代表缓存不过期
        @param {str} group=None - 缓存所属分组标识

        @returns {bool} - 设置结果
        """
        return self._redis.expire(
            self._get_real_name(name, group), datetime.timedelta(seconds=ex)
        )

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
        _real_name = self._get_real_name(name, group)
        return self._redis.set(
            _real_name, initial, nx=(not over_write)
        )

    def get_counter(self, name: str, group: str = None, auto_set: bool = True, initial: int = 0) -> int:
        """
        获取计数器当前值

        @param {str} name - 计数器名
        @param {str} group=None - 缓存所属分组
        @param {bool} auto_set=True - 不存在是否自动设置计数器
        @param {int} initial=0 - 设置初始值

        @returns {int} - 返回当前计数器值, 不存在返回None
        """
        _real_name = self._get_real_name(name, group)
        _ret = self._redis.get(_real_name)
        if _ret is None:
            if auto_set:
                self._redis.set(_real_name, initial, nx=True)
                _ret = self._redis.get(_real_name)
            else:
                return None

        if _ret is not None:
            _ret = int(_ret)

        return _ret

    def incr_counter(self, name: str, amount: int = 1, group: str = None) -> int:
        """
        增加计数器值
        注: 如果计数器不存在, 将自动创建并设置初始值为0

        @param {str} name - 计数器名
        @param {int} amount=1 - 指定增加数
        @param {str} group=None - 缓存所属分组

        @returns {int} - 返回增长后的值
        """
        _real_name = self._get_real_name(name, group)
        return self._redis.incr(_real_name, amount=amount)

    def decr_counter(self, name: str, amount: int = 1, group: str = None) -> int:
        """
        减少计数器值
        注: 如果计数器不存在, 将自动创建并设置初始值为0

        @param {str} name - 计数器名
        @param {int} amount=1 - 指定减少数
        @param {str} group=None - 缓存所属分组

        @returns {int} - 返回减少后的值
        """
        _real_name = self._get_real_name(name, group)
        return self._redis.decr(_real_name, amount=amount)

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
        _real_name = self._get_real_name(name, group)
        if self._redis.exists(_real_name) > 0:
            # 列表已存在
            if over_write:
                self._redis.delete(_real_name)
            else:
                # 不覆盖, 返回失败
                return False

        # 创建列表
        if len(initial) > 0:
            # 处理列表值
            _initial = [self._get_save_value_str(_val) for _val in initial]
            return self._redis.rpush(_real_name, *_initial) > 0
        else:
            # 不能创建空列表, 直接返回成功即可
            return True

    def list_len(self, name: str, group: str = None) -> int:
        """
        获取列表长度

        @param {str} name - 列表名
        @param {str} group=None - 缓存所在分组

        @returns {int} - 返回列表长度
            注: None代表name不存在
        """
        _real_name = self._get_real_name(name, group)
        return self._redis.llen(_real_name)

    def list_clear(self, name: str, group: str = None) -> bool:
        """
        清空列表

        @param {str} name - 列表名
        @param {str} group=None - 缓存的分组

        @returns {bool} - 处理结果
        """
        _real_name = self._get_real_name(name, group)
        _len = self._redis.llen(_real_name)
        if _len > 0:
            self._redis.ltrim(_real_name, _len, _len)

        return True

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
        _real_name = self._get_real_name(name, group)

        # 修改值
        _datas = [self._get_save_value_str(_val) for _val in datas]

        # 添加到列表左边
        return self._redis.lpush(_real_name, *_datas) > 0

    def rpush(self, name: str, datas: list, group: str = None) -> bool:
        """
        在列表右边添加数据
        注: 如果列表不存在将自动创建列表

        @param {str} name - 列表名
        @param {list} datas - 要添加的数据列表
        @param {str} group=None - 缓存所在分组

        @returns {bool} - 是否添加成功
        """
        _real_name = self._get_real_name(name, group)

        # 修改值
        _datas = [self._get_save_value_str(_val) for _val in datas]

        # 添加到列表左边
        return self._redis.rpush(_real_name, *_datas) > 0

    def list_range(self, name: str, start: int = 0, end: int = None, group: str = None) -> list:
        """
        获取列表指定区域范围的值列表

        @param {str} name - 列表名
        @param {int} start=0 - 开始位置, 从0开始
        @param {int} end=None - 结束为止, 如果为None代表获取到结尾
        @param {str} group=None - 缓存所在的组

        @returns {list} - 返回值列表
        """
        _real_name = self._get_real_name(name, group)
        _end = end if end is not None else self._redis.llen(_real_name)
        _values = self._redis.lrange(_real_name, start, _end)

        return [self._get_real_value(_val) for _val in _values]

    def lpop(self, name: str, group: str = None, count: int = 1) -> list:
        """
        从左边取出值并删除

        @param {str} name - 列表名
        @param {str} group=None - 缓存所在分组
        @param {int} count=1 - 要取出的数量

        @returns {list} - 取出数据的列表
            注: 如果没有值返回None
        """
        _real_name = self._get_real_name(name, group)
        _values = self._redis.lpop(_real_name, count)
        if _values is None:
            return None

        return [self._get_real_value(_val) for _val in _values]

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
        _real_name = self._get_real_name(name, group)
        _values = self._redis.rpop(_real_name, count)
        if _values is None:
            return None

        return [self._get_real_value(_val) for _val in _values]

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
        _real_name = self._get_real_name(name, group)
        _ret = self._redis.hset(_real_name, key, self._get_save_value_str(value))
        return False if _ret is None else True

    def hmset(self, name: str, kvs: dict, group: str = None) -> bool:
        """
        批量设置字典的多个kv值

        @param {str} name - 字典名
        @param {dict} kvs - 要设置的key-value值
        @param {str} group=None - 缓存所在的分组

        @returns {bool} - 设置结果
        """
        _real_name = self._get_real_name(name, group)
        _kvs = self._get_mset_nvs(kvs, None)
        _ret = self._redis.hset(_real_name, None, None, _kvs)
        return False if _ret is None else True

    def hget(self, name: str, key: str, group: str = None) -> Any:
        """
        获取字典缓存的指定值

        @param {str} name - 字典名
        @param {str} key - 要获取的字典kv值的key
        @param {str} group=None - 缓存所在分组

        @returns {Any} - 字典kv值的value
        """
        _real_name = self._get_real_name(name, group)
        return self._get_real_value(self._redis.hget(_real_name, key))

    def hmget(self, name: str, keys: list, group: str = None) -> dict:
        """
        获取字典中的多个值

        @param {str} name - 字典名
        @param {list} keys - 要获取的key值清单
        @param {str} group=None - 缓存所在分组

        @returns {dict} - 相应清单的值
            注: 如果缓存不存在, 返回{}
        """
        _real_name = self._get_real_name(name, group)
        _values = self._redis.hmget(_real_name, keys)
        if _values is None:
            return None

        _ret = {}
        for _i in range(len(keys)):
            _ret[keys[_i]] = self._get_real_value(_values[_i])

        return _ret

    def hgetall(self, name: str, group: str = None) -> dict:
        """
        获取字典的所有值

        @param {str} name - 字典名
        @param {str} group=None - 缓存所在分组

        @returns {dict} - 字典所有值
            注: 如果缓存不存在, 返回{}
        """
        _real_name = self._get_real_name(name, group)
        _kvs = self._redis.hgetall(_real_name)
        if _kvs is None:
            return None

        _ret = {}
        for _key, _value in _kvs.items():
            _ret[_key] = self._get_real_value(_value)

        return _ret

    def hdel(self, name: str, keys: list, group: str = None) -> bool:
        """
        删除字典中指定的key

        @param {str} name - 字典名
        @param {list} keys - 要删除的key列表
        @param {str} group=None - 缓存所在的分组

        @returns {bool} - 处理结果
        """
        _real_name = self._get_real_name(name, group)
        _ret = self._redis.hdel(_real_name, *keys)
        return False if _ret is None else True

    def hexists(self, name: str, key: str, group: str = None) -> bool:
        """
        判断key是否在字典中

        @param {str} name - 字典名
        @param {str} key - key值
        @param {str} group=None - 缓存所在的分组

        @returns {bool} - 判断结果
        """
        _real_name = self._get_real_name(name, group)
        return self._redis.hexists(_real_name, key)

    def hkeys(self, name: str, group: str = None) -> list:
        """
        获取字典中的所有key清单

        @param {str} name - 字典名
        @param {str} group=None - 缓存所在的分组

        @returns {list} - key清单
        """
        _real_name = self._get_real_name(name, group)
        return self._redis.hkeys(_real_name)

    #############################
    # 内部函数
    #############################
    def _get_real_name(self, name: str, group: str) -> str:
        """
        获取真正存储的name值

        @param {str} name - 缓存名
        @param {str} group - 缓存所属分组标识

        @returns {str} - redis真正保存的name
        """
        return name if group is None else '{$group=%s$}_%s' % (group, name)

    def _get_mset_nvs(self, nvs: dict, group: str) -> dict:
        """
        获取mset设置的真正nvs字典

        @param {dict} nvs - 要设置的name-value字典
        @param {str} group=None - 缓存所属分组标识

        @returns {dict} - 返回标准的设置字典
        """
        _real_nvs = {}
        for _name, _val in nvs.items():
            _val = self._get_save_value_str(_val)

            if group is None:
                _real_nvs[_name] = _val
            else:
                _real_nvs[self._get_real_name(_name, group)] = _val

        return _real_nvs

    def _get_real_name_list(self, names: list, group: str) -> list:
        """
        获取真正存储的name值列表

        @param {list} names - 缓存name列表
        @param {str} group - 缓存所属分组标识

        @returns {list} - 处理后的key列表
        """
        if group is None:
            return names
        else:
            return [self._get_real_name(_name, group) for _name in names]

    def _get_save_value_str(self, value: Any) -> str:
        """
        获取值的保存字符串格式

        @param {Any} value - 要保存的值

        @returns {str} - 转换后的字符串
        """
        if type(value) != str:
            # 转换为json格式存储
            return '{$json$}%s' % self._json.dumps(value, ensure_ascii=False)
        else:
            return value

    def _get_real_value(self, value: str) -> Any:
        """
        获取真实类型的缓存值

        @param {str} value - 存储的String格式数据

        @returns {Any} - 转换为真实类型的值
        """
        if type(value) == str and value.startswith('{$json$}'):
            return self._json.loads(value[8:])
        else:
            return value
