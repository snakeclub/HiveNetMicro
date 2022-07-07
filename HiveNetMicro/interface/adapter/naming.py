#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
服务注册中心适配器

@module naming
@file naming.py
"""
import os
import sys
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.adapter_base import AdapterBaseFw
from HiveNetMicro.core.global_manager import GlobalManager
from HiveNetMicro.core.logger_manager import LoggerManager


class NamingAdapter(AdapterBaseFw):
    """
    服务注册中心适配器
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
        return 'Naming'

    #############################
    # 构造函数
    #############################
    def __init__(self, init_config: dict = {}, namespace: str = None, cluster_name: str = None,
            logger_id: str = None) -> None:
        """
        构造函数

        @param {dict} init_config={} - 客户端连接配置(特定类型配置中心设置中的client配置, 由各个适配器自定义)
        @param {str} namespace=None - 指定当前连接要设置的命名空间
        @param {str} cluster_name=None - 当前应用所在的集群名
        @param {str} logger_id=None - 日志对象标识, 可以选择application.yaml配置中的其中一个日志对象
        """
        # 参数处理
        self.init_config = init_config
        self.namespace = namespace
        self.cluster_name = cluster_name

        # 日志对象
        _logger_manager: LoggerManager = GlobalManager.GET_SYS_LOGGER_MANAGER()
        if _logger_manager is None:
            _logger_manager = LoggerManager('')
        self.logger = _logger_manager.get_logger(logger_id, none_with_default_logger=True)

        # 实现类自定义初始化函数
        self._self_init()

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

        @returns {bool} - 是否注册成功(失败不抛出异常)
        """
        raise NotImplementedError()

    async def remove_instance(self, service_name: str, group_name: str = None, ip: str = None, port: int = None) -> bool:
        """
        取消实例注册信息

        @param {str} service_name - 服务名
        @param {str} group_name=None - 所属分组, 如不传则默认为'DEFAULT_GROUP'
        @param {str} ip=None - 服务实例IP, 如果不传代表删除'服务名+分组'下的所有服务配置
        @param {int} port=None - 服务实例port, 如果不传代表删除'服务名+分组'下的所有服务配置

        @returns {bool} - 是否取消注册成功(失败不抛出异常)
        """
        raise NotImplementedError()

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
        raise NotImplementedError()

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
                'healthy': True,  # 实例的健康状态
                # 不同适配器自身支持的参数
                'weight': 1.0  # 权重
                ...
            }
        """
        raise NotImplementedError()

    def add_subscribe(self, service_name: str, group_name: str = None, interval: float = 5):
        """
        添加远程服务信息订阅服务
        注: 订阅的服务信息自动更新本地缓存, 可以通过get_instance方法直接获取

        @param {str} service_name - 服务名
        @param {str} group_name=None - 所属分组, 如不传则默认为'DEFAULT_GROUP'
        @param {float} interval=5 - 服务信息变更检查时间间隔, 单位为秒
        """
        raise NotImplementedError()

    def remove_subscribe(self, service_name: str, group_name: str = None):
        """
        取消远程服务信息订阅服务

        @param {str} service_name - 服务名
        @param {str} group_name=None - 所属分组, 如不传则默认为'DEFAULT_GROUP'
        """
        raise NotImplementedError()

    #############################
    # 需要实现类继承的内部函数
    #############################
    def _self_init(self):
        """
        实现类继承实现的初始化函数
        """
        pass
