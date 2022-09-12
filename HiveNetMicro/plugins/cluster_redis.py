#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
基于Redis适配器实现的集群功能支持适配器

@module cluster_cache
@file cluster_cache.py
"""
import os
import sys
import json
import datetime
import json
from HiveNetCore.generic import CResult
from HiveNetCore.utils.exception_tool import ExceptionTool
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
from HiveNetMicro.interface.adapter.cluster import ClusterAdapter


class RedisClusterAdapter(ClusterAdapter):
    """
    基于Redis适配器实现的集群功能支持适配器
    """

    #############################
    # 继承类应重载实现的属性
    #############################
    @property
    def lib_dependencies(self) -> list:
        """
        当前适配器的依赖库清单
        注: 列出需要安装的特殊依赖库(HiveNetMicro未依赖的库)

        @property {list} - 依赖库清单, 可包含版本信息
            例如: ['redis', 'xxx==1.0.1']
        """
        return ['redis']

    #############################
    # 构造函数
    #############################
    def __init__(self, init_config: dict = {}, logger_id: str = None, is_manage: bool = False, **kwargs):
        """
        构造函数

        @param {dict} init_config={} - 适配器的初始化参数
            namespace {str} - 服务注册所在的命名空间, 可以实现不同环境或项目的软隔离
            sys_id {str} - 系统标识(标准为5位字符)
            module_id {str} - 模块标识(标准为3位字符)
            server_id {str} - 服务实例序号(标准为2个字符, 建议为数字)
            app_name {str} - 当前服务的应用名称
            expire {float} - 注册信息的超时时长(超过时长不续约自动从服务端下线), 单位为秒, 默认为10
            heart_beat {float} - 续约心跳间隔时长, 单位为秒, 默认为4
            enable_event {bool} - 服务是否开启集群事件接收处理, 默认为False
            event_interval {float} - 事件接收检查间隔, 单位为秒, 默认为2
            event_each_get {int} - 每次从服务器获取的事件数, 默认为10
            after_register {function} - 当注册集群成功后触发执行的函数, 函数入参为adapter对象(self)
            after_deregister {function}  - 当取消注册集群后触发执行的函数, 函数入参为adapter对象(self)
            after_own_master {function} - 当服务变为集群主服务后触发执行的函数, 函数入参为adapter对象(self)
            after_lost_master {function} - 当服务变为失去集群主服务后触发执行的函数, 函数入参为adapter对象(self)
            实现类定义的参数...
            redis_para {dict} - redis的连接参数字典, 具体参数见redis.Redis的初始化参数, 部分参数参考如下:
                max_connections {int} - 最大连接数, 默认为None
                host {str} - redis服务地址, 默认为'127.0.0.1'
                port {int} - redis服务端口, 默认为6379
                username {str} - 登录用户, 默认为None
                password {str} - 登录密码, 默认为None

        @param {str} logger_id=None - 日志对象标识, 可以选择application.yaml配置中的其中一个日志对象
        @param {bool} is_manage=False - 指定适配器是否以管理工具方式启动
            注: 管理工具方式启动不会进行集群注册和心跳同步
        """
        super().__init__(init_config, logger_id=logger_id, is_manage=is_manage)

    #############################
    # 需要实现类重载的内部函数
    #############################
    def _self_init(self):
        """
        实现类自定义的初始化函数
        """
        # redis缓存前缀
        self._cache_name = '{$group=cluster_info$}{$%s$}{$%s$}{$%s$}{$%s$}' % (
            self._namespace, self._sys_id, self._module_id, self._server_id
        )  # 当前服务器的集群唯一标识, 值为服务器的app_name
        self._cache_events_exists = '{$group=cluster_event_exists$}{$%s$}{$%s$}{$%s$}{$%s$}' % (
            self._namespace, self._sys_id, self._module_id, self._server_id
        )  # 用于判断列表是否存在, 有这个key就代表存在当前服务有集群消息列表, 值为1
        self._cache_events = '{$group=cluster_event$}{$%s$}{$%s$}{$%s$}{$%s$}' % (
            self._namespace, self._sys_id, self._module_id, self._server_id
        )  # 当前服务器的集群的消息列表队列, 值为待处理的消息列表
        self._cache_master = '{$group=cluster_master$}{$%s$}{$%s$}{$%s$}' % (
            self._namespace, self._sys_id, self._module_id
        ) # 当前集群模块的集群master服务器，值为服务器的server_id

        # 超时时间
        self._expire_timedelta = datetime.timedelta(seconds=self._expire)

        # Redis连接池和连接对象
        self._redis_para = self._init_config.get('redis_para', {})
        self._redis_para['decode_responses'] = True
        self._conn_pool = redis.ConnectionPool(**self._redis_para)
        self._redis = redis.Redis(connection_pool=self._conn_pool)

    #############################
    # 需实现类继承实现的公共函数
    #############################
    def get_cluster_master(self, namespace: str, sys_id: str, module_id: str) -> dict:
        """
        获取集群主服务信息

        @param {str} namespace - 服务注册所在的命名空间, 可以实现不同环境或项目的软隔离
        @param {str} sys_id - 系统标识(标准为5位字符)
        @param {str} module_id - 模块标识(标准为3位字符)

        @returns {dict} - 返回信息字典, 如果获取不到返回None
            {
                'namespace': '',  # 服务注册所在的命名空间, 可以实现不同环境或项目的软隔离
                'sys_id': '',  # 系统标识(标准为5位字符)
                'module_id': '',  # 模块标识(标准为3位字符)
                'server_id': '',  # 服务实例序号(标准为2个字符, 建议为数字)
                'app_name': '',  # 当前服务的应用名称
                'master': True  # 指示是否主服务
            }
        """
        # 获取实例id
        _cache_master = '{$group=cluster_master$}{$%s$}{$%s$}{$%s$}' % (
            namespace, sys_id, module_id
        )
        _server_id = self._redis.get(_cache_master)
        if _server_id is None:
            return None

        # 获取应用名
        _cache_name = '{$group=cluster_info$}{$%s$}{$%s$}{$%s$}{$%s$}' % (
            namespace, sys_id, module_id, _server_id
        )
        _app_name = self._redis.get(_cache_name)

        return {
            'namespace': namespace,
            'sys_id': sys_id,
            'module_id': module_id,
            'server_id': _server_id,
            'app_name': _app_name,
            'master': True
        }

    def get_cluster_list(self, namespace: str, sys_id: str = None, module_id: str = None) -> list:
        """
        获取集群信息清单

        @param {str} namespace - 服务注册所在的命名空间, 可以实现不同环境或项目的软隔离
        @param {str} sys_id=None - 系统标识(标准为5位字符), 不传代表获取上一级的所有信息
        @param {str} module_id=None - 模块标识(标准为3位字符), 不传代表获取上一级的所有信息

        @returns {list} - 返回集群服务清单
            [
                {
                    'namespace': '',  # 服务注册所在的命名空间, 可以实现不同环境或项目的软隔离
                    'sys_id': '',  # 系统标识(标准为5位字符)
                    'module_id': '',  # 模块标识(标准为3位字符)
                    'server_id': '',  # 服务实例序号(标准为2个字符, 建议为数字)
                    'app_name': '',  # 当前服务的应用名称
                    'master': True  # 指示是否主服务
                }, ...
            ]
        """
        # 匹配通配符
        _cache_name_pattern = '{$group=cluster_info$}{$%s$}{$%s$}{$%s$}{$*$}' % (
            namespace, '*' if sys_id is None else sys_id, '*' if sys_id is None or module_id is None else module_id
        )
        _cache_master_pattern = '{$group=cluster_master$}{$%s$}{$%s$}{$%s$}' % (
            namespace, '*' if sys_id is None else sys_id, '*' if sys_id is None or module_id is None else module_id
        )

        # 获取信息
        _name_keys = self._redis.keys(_cache_name_pattern)
        _app_names = self._redis.mget(_name_keys)
        _master_keys = self._redis.keys(_cache_master_pattern)
        _master_server_ids = self._redis.mget(_master_keys)

        # 生成结果
        _clusters = []
        for _i in range(len(_name_keys)):
            # 组装信息
            _splits = ('%s{$' % _name_keys[_i]).split('$}{$')
            _infos = {
                'namespace': namespace,
                'sys_id': _splits[2],
                'module_id': _splits[3],
                'server_id': _splits[4],
                'app_name': _app_names[_i],
                'master': False
            }

            # 检查是否主服务
            _cache_master = '{$group=cluster_master$}{$%s$}{$%s$}{$%s$}' % (
                namespace, _infos['sys_id'], _infos['module_id']
            )
            _master_index = -1
            if _cache_master in _master_keys:
                _master_index = _master_keys.index(_cache_master)
            if _master_index >= 0 and _master_server_ids[_master_index] == _infos['server_id']:
                _infos['master'] = True

            _clusters.append(_infos)

        return _clusters

    def emit(self, event: str, paras, namespace: str, sys_id: str, module_id: str, server_id: str) -> CResult:
        """
        向指定集群服务发送消息

        @param {str} event - 事件
        @param {Any} paras - 事件参数
        @param {str} namespace - 服务注册所在的命名空间, 可以实现不同环境或项目的软隔离
        @param {str} sys_id - 系统标识(标准为5位字符)
        @param {str} module_id - 模块标识(标准为3位字符)
        @param {str} server_id - 服务实例序号(标准为2个字符, 建议为数字)

        @returns {CResult} - 处理结果
        """
        _result = CResult()
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger, self_log_msg='emit cluster event error'
        ):
            _cache_events = '{$group=cluster_event$}{$%s$}{$%s$}{$%s$}{$%s$}' % (
                namespace, sys_id, module_id, server_id
            )
            _cache_events_exists = '{$group=cluster_event_exists$}{$%s$}{$%s$}{$%s$}{$%s$}' % (
                namespace, sys_id, module_id, server_id
            )
            _context = {
                'type': 'emit',
                'from': {
                    'namespace': self._namespace,
                    'sys_id': self._sys_id,
                    'module_id': self._module_id,
                    'server_id': self._server_id
                }
            }
            if self._redis.exists(_cache_events_exists) > 0:
                _event_str = json.dumps([_context, event, paras], ensure_ascii=False)
                _ret = self._redis.rpush(_cache_events, _event_str)
                if _ret <= 0:
                    raise RuntimeError('push cluster event error')
                elif _ret == 1:
                    # 重新创建, 设置超时时间
                    self._redis.expire(_cache_events, self._expire_timedelta)
            else:
                raise RuntimeError('cluster event not exists')

        return _result

    def broadcast(self, event: str, paras, namespace: str, sys_id: str = None, module_id: str = None) -> CResult:
        """
        向指定集群服务广播事件

        @param {str} event - 事件
        @param {Any} paras - 事件参数
        @param {str} namespace - 服务注册所在的命名空间, 可以实现不同环境或项目的软隔离
        @param {str} sys_id=None - 系统标识(标准为5位字符), 不传代表获取上一级的所有信息
        @param {str} module_id=None - 模块标识(标准为3位字符), 不传代表获取上一级的所有信息

        @returns {CResult} - 处理结果
        """
        _result = CResult()
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger, self_log_msg='broadcast cluster event error'
        ):
            _context = {
                'type': 'broadcast',
                'from': {
                    'namespace': self._namespace,
                    'sys_id': self._sys_id,
                    'module_id': self._module_id,
                    'server_id': self._server_id
                }
            }
            _event_str = json.dumps([_context, event, paras], ensure_ascii=False)

            _cache_events_pattern = '{$group=cluster_event_exists$}{$%s$}{$%s$}{$%s$}{$*$}' % (
                namespace, '*' if sys_id is None else sys_id,
                '*' if sys_id is None or module_id is None else module_id
            )

            _keys = self._redis.keys(_cache_events_pattern)
            for _key in _keys:
                _cache_name = _key.replace('{$group=cluster_event_exists$}', '{$group=cluster_event$}')
                _ret = self._redis.rpush(_cache_name, _event_str)
                if _ret == 1:
                    # 重新创建, 设置超时时间
                    self._redis.expire(_cache_name, self._expire_timedelta)

        return _result

    #############################
    # 需实现类继承的内部函数
    #############################
    def _register_cluster_self(self) -> bool:
        """
        注册集群信息
        注: 如果集群信息已存在, 则进行集群超时时间的延续

        @returns {bool} - 处理结果
        """
        _ret = True
        # 尝试直接延续超时, 如果缓存不存在会返回False
        if self._redis.expire(self._cache_name, self._expire_timedelta):
            # 缓存已存在, 延续事件超时时间
            if self._enable_event:
                self._redis.expire(self._cache_events_exists, self._expire_timedelta)
                self._redis.expire(self._cache_events, self._expire_timedelta)
        else:
            # 缓存不存在, 需要重新注册
            if self._enable_event:
                _ret = self._set_event()
            else:
                _ret = True

            if _ret:
                _ret = self._redis.set(
                    self._cache_name, self._app_name, ex=self._expire_timedelta
                )

        return _ret

    def _deregister_cluster_self(self) -> bool:
        """
        取消注册集群信息

        @returns {bool} - 处理结果
        """
        return self._redis.delete(self._cache_name, self._cache_events_exists, self._cache_events) > 0

    def _try_own_master_self(self) -> bool:
        """
        尝试抢占集群主服务
        注: 如果本身已经是集群主服务, 则续约超时时间

        @returns {bool} - 抢占结果
        """
        _ret = self._redis.set(
            self._cache_master, self._server_id, ex=self._expire_timedelta, nx=True
        )
        if _ret is None or not _ret:
            # 抢占失败, 看看是不是自己
            if self._redis.get(self._cache_master) == self._server_id:
                # 是自己，续约时长
                self._redis.expire(self._cache_master, self._expire_timedelta)
                return True
            else:
                return False
        else:
            # 抢占成功
            return True

    def _try_lost_master_self(self) -> bool:
        """
        尝试取消集群主服务占用

        @returns {bool} - 处理结果
        """
        if self._redis.get(self._cache_master) == self._server_id:
            # 当前主服务是自己, 删除
            _ret = self._redis.delete(self._cache_master)
            return _ret > 0
        else:
            # 主服务不是自己
            return False

    def _get_events_self(self):
        """
        获取当前服务的集群事件迭代数据

        @returns {iterator} - 当前收到的事件迭代数据, 每项为数组(上下文, 事件, 参数)
            注: 上下文为字典, 格式为
            {
                'type': 'emit',  # 事件类型, emit-点对点发送, broadcast-广播
                'from': {  # 事件发起方信息
                    'namespace': '',  # 服务注册所在的命名空间, 可以实现不同环境或项目的软隔离
                    'sys_id': '',  # 系统标识(标准为5位字符)
                    'module_id': '',  # 模块标识(标准为3位字符)
                    'server_id': '',  # 服务实例序号(标准为2个字符, 建议为数字)
                }
            }
        """
        while True:
            _ret = self._redis.lpop(self._cache_events, count=self._event_each_get)
            if _ret is None:
                # 没有消息了
                break

            for _item in _ret:
                yield json.loads(_item)

    def _clear_all_cluster(self, namespace: str, sys_id: str = None, module_id: str = None, server_id: str = None) -> bool:
        """
        清空所有集群信息(仅管理使用)

        @param {str} namespace - 服务注册所在的命名空间, 可以实现不同环境或项目的软隔离
        @param {str} sys_id=None - 系统标识(标准为5位字符), 不传代表获取上一级的所有信息
        @param {str} module_id=None - 模块标识(标准为3位字符), 不传代表获取上一级的所有信息
        @param {str} server_id=None - 服务实例序号(标准为2个字符, 建议为数字), 不传代表获取上一级的所有信息

        @returns {bool} - 处理结果
        """
        _clear_clusters = []
        if server_id is None:
            # 清除namespace下的所有集群信息
            _clusters = self.get_cluster_list(
                namespace, sys_id=sys_id, module_id=module_id
            )
            for _info in _clusters:
                _clear_clusters.append([
                    _info['namespace'], _info['sys_id'], _info['module_id'], _info['server_id'], _info['master']
                ])
        else:
            # 清除指定的服务器
            _master = self.get_cluster_master(namespace, sys_id, module_id)
            _clear_clusters.append([
                namespace, sys_id, module_id, server_id,
                False if _master is None else _master['server_id'] == server_id
            ])

        _clear_keys = []
        for _cluster in _clear_clusters:
            # 组装redis缓存前缀
            _cache_name = '{$group=cluster_info$}{$%s$}{$%s$}{$%s$}{$%s$}' % (
                _cluster[0], _cluster[1], _cluster[2], _cluster[3]
            )  # 当前服务器的集群唯一标识, 值为服务器的app_name
            _cache_events_exists = '{$group=cluster_event_exists$}{$%s$}{$%s$}{$%s$}{$%s$}' % (
                _cluster[0], _cluster[1], _cluster[2], _cluster[3]
            )  # 用于判断列表是否存在, 有这个key就代表存在当前服务有集群消息列表, 值为1
            _cache_events = '{$group=cluster_event$}{$%s$}{$%s$}{$%s$}{$%s$}' % (
                _cluster[0], _cluster[1], _cluster[2], _cluster[3]
            )  # 当前服务器的集群的消息列表队列, 值为待处理的消息列表

            _clear_keys.append(_cache_name)
            _clear_keys.append(_cache_events_exists)
            _clear_keys.append(_cache_events)
            if _cluster[4]:
                _cache_master = '{$group=cluster_master$}{$%s$}{$%s$}{$%s$}' % (
                    _cluster[0], _cluster[1], _cluster[2]
                ) # 当前集群模块的集群master服务器，值为服务器的server_id
                _clear_keys.append(_cache_master)

        # 清除对应的key
        if len(_clear_keys) == 0:
            return True
        else:
            return self._redis.delete(*_clear_keys) > 0

    #############################
    # 内部函数
    #############################
    def _set_event(self) -> bool:
        """
        设置事件列表缓存

        @returns {bool} - 设置结果
        """
        # 先删除旧的队列
        self._redis.delete(self._cache_events)

        # 不能创建空列表, 因此创建指示队列是否存在的缓存
        _ret = self._redis.set(
            self._cache_events_exists, '1', ex=self._expire_timedelta
        )

        return _ret is not None and _ret
