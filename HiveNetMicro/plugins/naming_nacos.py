#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
注册中心适配器的nacos实现
注: 需要安装nacos客户端: pip install nacos-sdk-python

@module register_nacos
@file register_nacos.py
"""
import os
from queue import Empty
from random import random
import sys
import copy
import asyncio
import traceback
from multiprocessing import Process, Queue
from HiveNetCore.utils.run_tool import AsyncTools
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.interface.adapter.naming import NamingAdapter
from HiveNetMicro.core.global_manager import GlobalManager
import HiveNetMicro.core.nacos as nacos
from HiveNetMicro.core.nacos.listener import SubscribeListener
from HiveNetMicro.core.logger_manager import LoggerManager


class HeartbeatProcess(Process):
    """
    进行心跳同步的子进程类
    """
    def __init__(self, nacos_server_addresses: str, nacos_init_client_config: dict,
            heartbeat_interval: float, instance_deal_queue: Queue, logger_config: dict,
            *args, **kwargs):
        """
        初始化类

        @param {str} nacos_server_addresses - nacos客户端的连接地址
        @param {dict} nacos_init_client_config - nacos客户端的初始化参数
        @param {float} heartbeat_interval - 循环发送心跳的间隔时间, 单位为秒
        @param {multiprocessing.Queue} instance_deal_queue - 从主进程传递过来要处理服务清单信息的队列
        @param {dict} logger_config - 日志配置字典, 格式如下:
            {
                'logger_id': '',  # 日志标识
                'config': '', # 日志配置
                'log_path': '',  # 日志所在路径
            }
        """
        super(HeartbeatProcess, self).__init__(*args, **kwargs)
        self._heartbeat_interval = heartbeat_interval

        # nacos客户端初始化参数
        self.nacos_server_addresses = nacos_server_addresses
        self.nacos_init_client_config = nacos_init_client_config
        self.instance_deal_queue = instance_deal_queue

        # 当前已注册的服务清单, key为'group_name@@service_name', value为{'ip:port': 服务创建参数}
        self._instances = dict()
        self._is_stop = False  # 通知心跳续约线程停止的变量

        # 日志配置
        self.logger_config = logger_config

    def run(self):
        """
        子进程的处理函数
        """
        # 设置日志对象
        _logger_manager = LoggerManager(self.logger_config['log_path'])
        _logger = _logger_manager.create_logger(
            self.logger_config['logger_id'], self.logger_config['config']
        )
        if _logger is not None:
            nacos.client.logger = _logger

        # 初始化nacos客户端
        _client = nacos.NacosClient(self.nacos_server_addresses, **self.nacos_init_client_config)
        while not self._is_stop:
            try:
                # 同步检查是不是要更新实例对象
                while True:
                    try:
                        _op = self.instance_deal_queue.get_nowait()
                        self.instance_deal(_op)
                    except Empty:
                        break
                    except:
                        if _logger is not None:
                            _logger.error('HiveNetMicro-Process-Heartbeat get instance deal from queue error: %s' % traceback.format_exc())
                        break

                # 生成协程任务
                _asyncio_gather_paras = []
                for _name, _instances in self._instances.items():
                    for _ip_key, _paras in _instances.items():
                        _asyncio_gather_paras.append(
                            _client.async_send_heartbeat(*_paras['args'], **_paras['kwargs'])
                        )

                # 并发执行协程
                AsyncTools.sync_call(asyncio.gather, *_asyncio_gather_paras)

                # 等待间隔时长
                AsyncTools.sync_call(asyncio.sleep, self._heartbeat_interval)
            except:
                if _logger is not None:
                    _logger.error('HiveNetMicro-Process-Heartbeat run error: %s' % traceback.format_exc())

    def instance_deal(self, op: dict):
        """
        处理实例清单的同步处理

        @param {dict} op - 同步操作字典

        """
        if op['op'] == 'overwrite':
            # 整个对象覆盖
            self._instances = op['value']
        elif op['op'] == 'update':
            # 更新
            self._instances[op['key']] = op['value']
        elif op['op'] == 'delete':
            # 删除
            self._instances.pop(op['key'], None)


class NacosNamingAdapter(NamingAdapter):
    """
    注册中心适配器的nacos实现
    """

    def __init__(self, init_config: dict = {}, namespace: str = None, cluster_name: str = None,
            logger_id: str = None) -> None:
        """
        构造函数

        @param {dict} init_config={} - 客户端连接配置(特定类型注册中心设置中的client配置, 由各个适配器自定义)
            nacos注册中心支持的初始化参数包括:
            server_addresses {str} - 必填, 服务端地址, 可以通过逗号分隔多个地址
                例如: "192.168.3.4:8848" or "https://192.168.3.4:443" or "http://192.168.3.4:8848,192.168.3.5:8848" or "https://192.168.3.4:443,https://192.168.3.5:443"
            endpoint {str} - 注册中心物理隔离参数, 可以不设置
            ak {str} - 阿里云MES的ak认证方案, 可以不设置
            sk {str} - 阿里云MES的sk认证方案, 可以不设置
            username {str} - 设置了登录认证的用户名
            password {str} - 设置了登录认证的密码
            auto_create_mamespace {bool} - 命名空间不存在是否自动创建命名空间, 默认为True
            default_options {dict} - nacos默认参数值, 所支持的参数详见nacos的sdk
                TIMEOUT {float} - 默认超时时间, 单位为秒
                ...
            default_instance_options {dict} - nacos默认的注册实例的参数, 所支持的参数见nacos的sdk
                weight {float} - 权重, 默认为1.0, 权重越大, 分配给该实例的流量越大
                ephemeral {bool} - 是否临时实例, 默认为True
            heartbeat_options {dict} - 心跳续约参数
                check_type {str} - 健康检测模式, server-服务端反向检测, client-客户端主动发送心跳包, 默认为server
                    注: server模式需在nacos服务端配置对应集群的主动检测功能; 如果只是用于寻找服务, 无需发布服务, 请设置为server
                interval {float} - 心跳续约的时间间隔, 单位为秒, 默认为3.0
                hb_timeout {float} - 设置心跳超时时间(超过这个时间收不到心跳则服务设置为不健康), 单位为秒, 默认为6.0
                ip_timeout {float} - 设置实例删除的超时时间(超过这个时间收不到心跳则实例下线), 单位为秒, 默认为9.0
        @param {str} namespace=None - 指定当前连接要设置的命名空间
        @param {str} cluster_name=None - 当前应用所在的集群名
        @param {str} logger_id=None - 日志对象标识, 可以选择application.yaml配置中的其中一个日志对象
        """
        # 执行基础类初始化函数
        super().__init__(
            init_config=init_config, namespace=namespace, cluster_name=cluster_name,
            logger_id=logger_id
        )

        self.global_config = GlobalManager.GET_GLOBAL_CONFIG()
        if self.global_config is None:
            self.global_config = {}

        self.init_config = copy.deepcopy(self.init_config)
        self.init_config['namespace'] = namespace

        # 获取参数
        self.auto_create_namespace = self.init_config.pop('auto_create_mamespace', True)

        # 设置sdk的默认值
        self.default_options = self.init_config.pop('default_options', None)
        if self.default_options is not None:
            for _key, _val in self.default_options.items():
                nacos.DEFAULTS[_key] = _val

        # 心跳续约参数
        self.heartbeat_options = self.init_config.pop('heartbeat_options', None)
        if self.heartbeat_options is None:
            self.heartbeat_options = {}

        # 健康检测模式
        self.heartbeat_mode = self.heartbeat_options.get('check_type', 'server')

        # 标准化心跳续约参数
        self.heartbeat_options['HEART_BEAT_INTERVAL'] = str(int(self.heartbeat_options.get(
            'interval', 3.0
        ) * 1000))
        self.heartbeat_options['HEART_BEAT_TIMEOUT'] = str(int(self.heartbeat_options.get(
            'hb_timeout', 6.0
        ) * 1000))
        self.heartbeat_options['IP_DELETE_TIMEOUT'] = str(int(self.heartbeat_options.get(
            'ip_timeout', 9.0
        ) * 1000))

        # 默认的实例注册参数
        self.default_instance_options = self.init_config.pop('default_instance_options', {})
        if self.default_instance_options is None:
            self.default_instance_options = {}
        self.default_instance_options['cluster_name'] = cluster_name

        # 连接服务器
        _server_addresses = self.init_config.pop('server_addresses')
        _init_client_config = {}
        _client_options = ['endpoint', 'namespace', 'ak', 'sk', 'username', 'password']
        for _key, _val in self.init_config.items():
            if _key in _client_options:
                _init_client_config[_key] = _val
            else:
                self.logger.info(
                    'unsupport nacos option [%s].[%s], ignored' % (_key, _val)
                )
        self.client = nacos.NacosClient(_server_addresses, **_init_client_config)

        # 设置nacos的日志对象
        nacos.client.logger = self.logger

        # 如果命名空间不存在, 创建命名空间
        if self.auto_create_namespace and not self.client.is_namespace_exists(namespace):
            # 创建命名空间
            self.client.add_namespace(
                self.init_config['namespace'], namespace=self.init_config['namespace'],
                namespace_desc='Auto create by NacosConfigAdapter'
            )

        # 远程实例订阅本地缓存
        # 格式为 { 'group_name@@service_name': {'instanceId': {...}, ...}}
        self._subscribe_cache = dict()

        # 心跳管理
        # 当前已注册的服务清单, key为'group_name@@service_name', value为{'ip:port': 服务创建参数}
        self._instances = dict()
        self._is_stop = False  # 通知心跳续约线程停止的变量
        self._heartbeat_interval = self.heartbeat_options.get('interval', 3.0)
        self._heartbeat_thread = None
        self._has_heartbeat_process = False
        self._instance_deal_queue = None
        if self.heartbeat_mode != 'server' and self.global_config.get('is_main_process', True):
            self._has_heartbeat_process = True
            self._instance_deal_queue = Queue()
            _logger_id = self.global_config.get('app_config', {}).get('sys_logger', 'sysLogger')
            _logger_config = {
                'logger_id': _logger_id,  # 日志标识
                'config': self.global_config.get('loggers_config', {}).get(_logger_id, None), # 日志配置
                'log_path': self.global_config.get('logs_path', '')  # 日志所在路径
            }
            self._heartbeat_process = HeartbeatProcess(
                _server_addresses, _init_client_config, self._heartbeat_interval,
                self._instance_deal_queue, _logger_config,
                name='HiveNetMicro-Process-Heartbeat'
            )
            self._heartbeat_process.daemon = True
            self._heartbeat_process.start()

    #############################
    # 需要实现类继承的公共函数
    #############################
    async def add_instance(self, service_name: str, ip: str, port: int, group_name: str = None, metadata: dict = None,
            **kwargs) -> bool:
        """
        注册服务实例

        @param {str} service_name - 服务名
        @param {str} ip - 服务实例IP
        @param {int} port - 服务实例port
        @param {str} group_name=None - 所属分组, 如不传则默认为'DEFAULT_GROUP'
        @param {dict} metadata=None - 服务元数据, 可不传
        @param {kwargs} - 其他参数, 根据自定义的注册中心适配器支持设置
            nacos支持的参数包括:
            cluster_name {str} - 集群名, 可不送
            weight {float} - 权重, 默认为1.0, 权重越大, 分配给该实例的流量越大
            enable {bool} - 是否启动服务, 默认为True
            healthy {bool} - 服务状态是否健康, 默认为True
            ephemeral {bool} - 是否临时实例, 默认为True, 如果是非临时实例, check_type应设置为server

        @returns {bool} - 是否注册成功(失败不抛出异常)
        """
        try:
            _group_name = group_name if group_name is not None else 'DEFAULT_GROUP'
            _args = (service_name, ip, port)
            # 处理 metadata 的心跳续约时间设置
            _metadata = {} if metadata is None else metadata
            _metadata['preserved.heart.beat.interval'] = self.heartbeat_options['HEART_BEAT_INTERVAL']
            _metadata['preserved.heart.beat.timeout'] = self.heartbeat_options['HEART_BEAT_TIMEOUT']
            _metadata['preserved.ip.delete.timeout'] = self.heartbeat_options['IP_DELETE_TIMEOUT']

            _kwargs = {
                'group_name': _group_name,
                'metadata': _metadata,
                'cluster_name': kwargs.get('cluster_name', self.default_instance_options.get('cluster_name', None)),
                'weight': kwargs.get('weight', self.default_instance_options.get('weight', 1.0)),
                'enable': kwargs.get('enable', self.default_instance_options.get('enable', True)),
                'healthy': kwargs.get('healthy', self.default_instance_options.get('healthy', True)),
                'ephemeral': kwargs.get('ephemeral', self.default_instance_options.get('ephemeral', True)),
            }
            _add_result = await self.client.async_add_naming_instance(
                *_args, **_kwargs
            )

            if _add_result:
                # 成功添加实例, 添加到实例清单
                _name_key = '%s@@%s' % (_group_name, service_name)
                _kwargs.pop('healthy', None)  # 心跳续约无需该参数
                _kwargs.pop('enable', None)
                if _name_key not in self._instances.keys():
                    self._instances[_name_key] = {}

                self._instances[_name_key]['%s:%d' % (ip, port)] = {
                    'args': _args, 'kwargs': _kwargs
                }

                # 更新操作送入子进程
                if self._has_heartbeat_process:
                    self._instance_deal_queue.put(
                        {'op': 'update', 'key': _name_key, 'value': self._instances[_name_key]}
                    )

                return True
            else:
                self.logger.error('add naming instance [%s@@%s] false, get return: %s' % (
                    _group_name, service_name, str(_add_result)
                ))
                return False
        except:
            self.logger.error('add naming instance [%s@@%s] error: %s' % (
                _group_name, service_name, traceback.format_exc()
            ))

    async def remove_instance(self, service_name: str, group_name: str = None, ip: str = None, port: int = None) -> bool:
        """
        取消实例注册信息

        @param {str} service_name - 服务名
        @param {str} group_name=None - 所属分组, 如不传则默认为'DEFAULT_GROUP'
        @param {str} ip=None - 服务实例IP, 如果不传代表删除'服务名+分组'下的所有服务配置
        @param {int} port=None - 服务实例port, 如果不传代表删除'服务名+分组'下的所有服务配置

        @returns {bool} - 是否取消注册成功(失败不抛出异常)
        """
        try:
            _group_name = group_name if group_name is not None else 'DEFAULT_GROUP'
            _key_name = '%s@@%s' % (_group_name, service_name)

            _instances = self._instances.get(_key_name, None)
            if _instances is None:
                raise ModuleNotFoundError('naming instance [%s] not found' % _key_name)

            if ip is not None and port is not None:
                # 删除指定服务
                _remove_list = ['%s:%d' % (ip, port)]
            else:
                _remove_list = list(_instances.keys())

            # 循环删除服务实例
            for _ip_key in _remove_list:
                _paras = _instances[_ip_key]
                _remove_result = await self.client.async_remove_naming_instance(
                    *_paras['args'], cluster_name=_paras['kwargs'].get('cluster_name'),
                    ephemeral=_paras['kwargs'].get('ephemeral'), group_name=_paras['kwargs'].get('group_name')
                )

                if _remove_result:
                    # 成功删除实例, 从实例清单清除
                    _instances.pop(_ip_key, None)
                else:
                    self.logger.error('remove naming instance [%s][%s] false, get return: %s' % (
                        _key_name, _ip_key, str(_remove_result)
                    ))
                    return False

            # 更新操作送入子进程
            if self._has_heartbeat_process:
                if self._instances.get(_key_name, None) is None:
                    # 完全删除
                    self._instance_deal_queue.put(
                        {'op': 'delete', 'key': _key_name}
                    )
                else:
                    self._instance_deal_queue.put(
                        {'op': 'update', 'key': _key_name, 'value': self._instances[_key_name]}
                    )

            # 返回成功
            return True
        except:
            self.logger.error('remove naming instance [%s] error: %s' % (
                _key_name, traceback.format_exc()
            ))

    async def list_instance(self, service_name: str, group_name: str = None, healthy_only: bool = True) -> list:
        """
        获取指定服务的实例清单
        注: 只包含可用的实例

        @param {str} service_name - 服务名
        @param {str} group_name=None - 所属分组, 如不传则默认为'DEFAULT_GROUP'
        @param {bool} healthy_only=True - 是否只列出健康的实例

        @returns {list} - 返回的服务列表, 格式如下:
            [
                {
                    # 标准信息
                    'instance_id': '',  # 实例id
                    'ip': '',  # ip地址
                    'port': 8888,  # 端口
                    'metadata': {},  # 元数据
                    'healthy': True,  # 实例的健康状态
                    # 不同适配器自身支持的参数
                    'weight': 1.0  # 权重
                    ...
                },
                ...
            ]
        """
        # 先尝试从本地缓存获取
        _group_name = group_name if group_name is not None else 'DEFAULT_GROUP'
        _resp = self._subscribe_cache.get('%s@@%s' % (_group_name, service_name), None)
        if _resp is not None:
            # 本地缓存获取
            _resp = list(_resp.values())

        if _resp is None or len(_resp) == 0:
            # 本地查找不到服务信息, 需要从服务器端获取
            _server_resp = await self.client.async_list_naming_instance(
                service_name, group_name=_group_name, healthy_only=healthy_only
            )
            _resp = _server_resp.get('hosts', [])

        _list = []
        for _host in _resp:
            if healthy_only and not _host.get('healthy', False):
                # 只获取健康的, 非健康的实例忽略掉
                continue

            _list.append({
                'instance_id': _host.get('instanceId'),
                'ip': _host.get('ip'),
                'port': _host.get('port'),
                'metadata': _host.get('metadata'),
                'healthy': _host.get('healthy'),
                'weight': _host.get('weight')
            })

        return _list

    async def get_instance(self, service_name: str, group_name: str = None, healthy_only: bool = True) -> dict:
        """
        获取一个可用的实例

        @param {str} service_name - 服务名
        @param {str} group_name=None - 所属分组, 如不传则默认为'DEFAULT_GROUP'
        @param {bool} healthy_only=True - 是否只列出健康的实例

        @returns {dict} - 实例信息, 如果找不到返回None, 实例信息格式如下
            {
                # 标准信息
                'instance_id': '',  # 实例id
                'ip': '',  # ip地址
                'port': 8888,  # 端口
                'metadata': {},  # 元数据
                'healthy': True,  # 该实例是否健康
                # 不同适配器自身支持的参数
                'weight': 1.0  # 权重
                ...
            }
        """
        _group_name = group_name if group_name is not None else 'DEFAULT_GROUP'
        _instance_list = await self.list_instance(service_name, group_name=_group_name, healthy_only=healthy_only)
        _len = len(_instance_list)
        if _len == 0:
            return None
        elif _len == 1:
            return _instance_list[0]

        if healthy_only:
            _healthy_list = _instance_list
            _unhealthy_list = []
        else:
            # 区分健康列表和非健康列表
            _healthy_list = []
            _unhealthy_list = []
            for _instance in _instance_list:
                if _instance['healthy']:
                    _healthy_list.append(_instance)
                else:
                    _unhealthy_list.append(_instance)

        _deal_list = _healthy_list
        while True:
            if len(_deal_list) > 0:
                # 通过负载均衡权重算法选择其中一个实例返回
                _total_weight = 0.0  # 权重加总数据
                _match_areas = []  # 匹配区间数组
                for _info in _instance_list:
                    _match_areas.append(_total_weight + _info['weight'])
                    _total_weight += _info['weight']
                _random = random() * _total_weight  # 用来匹配的随机数
                for _match_index in range(_len):
                    if _random < _match_areas[_match_index]:
                        return _instance_list[_match_index]

                # 可能算法存在问题匹配不到的情况, 返回第一个
                return _instance_list[0]
            else:
                # 健康列表没有, 从不健康列表获取
                _deal_list = _unhealthy_list
                continue

    def add_subscribe(self, service_name: str, group_name: str = None, interval: float = 5):
        """
        添加远程服务信息订阅服务
        注: 订阅的服务信息自动更新本地缓存, 可以通过get_instance方法直接获取

        @param {str} service_name - 服务名
        @param {str} group_name=None - 所属分组, 如不传则默认为'DEFAULT_GROUP'
        @param {float} interval=5 - 服务信息变更检查时间间隔, 单位为秒
        """
        _group_name = group_name if group_name is not None else 'DEFAULT_GROUP'
        # 创建缓存字典值
        _cached_key = '%s@@%s' % (_group_name, service_name)
        if _cached_key not in self._subscribe_cache.keys():
            self._subscribe_cache[_cached_key] = {}

        # 启动监听线程
        _listener = SubscribeListener(
            self._subscribe_update_fun, 'subscribe-%s@@%s' % (_group_name, service_name)
        )
        self.client.subscribe(
            _listener, listener_interval=interval, service_name=service_name,
            group_name=_group_name, healthy_only=False
        )

        # 从服务器获取当前服务清单放入缓存(线程只会监听变化)
        _server_resp = self.client.list_naming_instance(
            service_name, group_name=_group_name, healthy_only=False
        )
        for _host in _server_resp.get('hosts', []):
            self._subscribe_cache[_cached_key][_host['instanceId']] = {
                'instanceId': _host['instanceId'],
                'ip': _host['ip'],
                'port': _host['port'],
                'metadata': _host['metadata'],
                'healthy': _host['healthy'],
                'weight': _host['weight']
            }

    def remove_subscribe(self, service_name: str, group_name: str = None):
        """
        取消远程服务信息订阅服务

        @param {str} service_name - 服务名
        @param {str} group_name=None - 所属分组, 如不传则默认为'DEFAULT_GROUP'
        """
        _group_name = group_name if group_name is not None else 'DEFAULT_GROUP'
        self.client.unsubscribe(
            service_name, listener_name='subscribe-%s@@%s' % (_group_name, service_name)
        )
        # 从缓存中清除
        self._subscribe_cache.pop('%s@@%s' % (_group_name, service_name), None)

    #############################
    # 内部函数
    #############################

    def _subscribe_update_fun(self, *args, **kwargs):
        """
        订阅实例信息的更新函数
        """
        _event = args[0]
        _instance: nacos.client.SubscribedLocalInstance = args[1]
        _cached_key = _instance.instance['serviceName']
        if _event in ('ADDED', 'MODIFIED'):
            # 新增或修改
            if _cached_key not in self._subscribe_cache.keys():
                self._subscribe_cache[_cached_key] = {}

            # 添加需要缓存的字典
            self._subscribe_cache[_cached_key][_instance.instance_id] = {
                'instanceId': _instance.instance_id,
                'ip': _instance.instance.get('ip', None),
                'port': _instance.instance.get('port', None),
                'metadata': _instance.instance.get('metadata', None),
                'healthy': _instance.instance.get('healthy', True),
                'weight': _instance.instance.get('weight', 1)
            }
        else:
            # 删除
            if _cached_key in self._subscribe_cache.keys():
                self._subscribe_cache[_cached_key].pop(_instance.instance_id, None)
