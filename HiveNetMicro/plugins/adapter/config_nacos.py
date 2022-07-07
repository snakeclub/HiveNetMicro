#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
配置中心适配器的nacos实现

@module config_nacos
@file config_nacos.py
"""
import os
import sys
import copy
import traceback
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.interface.adapter.config import ConfigAdapter
import HiveNetMicro.core.nacos as nacos


class NacosConfigAdapter(ConfigAdapter):
    """
    配置中心适配器的nacos实现
    """

    def __init__(self, init_config: dict = {}, namespace: str = None) -> None:
        """
        构造函数

        @param {dict} init_config={} - 客户端连接配置(configCenter.yaml中特定类型配置中心设置中的client配置, 由各个适配器自定义)
            nacos配置中心支持的初始化参数包括:
            server_addresses {str} - 必填, 服务端地址, 可以通过逗号分隔多个地址
                例如: "192.168.3.4:8848" or "https://192.168.3.4:443" or "http://192.168.3.4:8848,192.168.3.5:8848" or "https://192.168.3.4:443,https://192.168.3.5:443"
            endpoint {str} - 配置中心物理隔离参数, 可以不设置
            ak {str} - 阿里云MES的ak认证方案, 可以不设置
            sk {str} - 阿里云MES的sk认证方案, 可以不设置
            username {str} - 设置了登录认证的用户名
            password {str} - 设置了登录认证的密码
            auto_create_mamespace {bool} - 命名空间不存在时是否自动创建, 默认为True
            default_options {dict} - nacos默认参数值, 所支持的参数详见nacos的sdk
                TIMEOUT {float} - 默认超时时间, 单位为秒
                ...
        @param {str} namespace=None - 指定当前连接要设置的命名空间id
            注: 在Nacos上创建命名空间时, 命名空间的id必须为该值, 而不只是命名空间的名称
        """
        self.init_config = copy.deepcopy(init_config)
        self.init_config['namespace'] = namespace

        # 获取参数
        self.auto_create_namespace = self.init_config.pop('auto_create_mamespace', True)

        # 设置sdk的默认值
        self.default_options = self.init_config.pop('default_options', None)
        if self.default_options is not None:
            for _key, _val in self.default_options.items():
                nacos.DEFAULTS[_key] = _val

        # 设置日志对象
        self.logger = None

        # 连接服务器
        self.client = nacos.NacosClient(**self.init_config)

        # 不使用本地快照
        self.client.no_snapshot = True

        # 处理命名空间
        if self.auto_create_namespace and not self.client.is_namespace_exists(namespace):
            # 创建命名空间
            self.client.add_namespace(
                self.init_config['namespace'], namespace=self.init_config['namespace'],
                namespace_desc='Auto create by NacosConfigAdapter'
            )

    async def get_config(self, data_id: str, group: str = None, timeout: float = 3.0) -> str:
        """
        获取指定配置信息

        @param {str} data_id - 配置ID
        @param {str} group=None - 配置所属分组
        @param {float} timeout=3.0 - 超时时间, 单位为秒

        @returns {str} - 返回配置信息的字符串, 如果配置不存在返回None
            注: 如果获取失败应抛出异常
        """
        config_str = await self.client.async_get_config(
            data_id, 'DEFAULT_GROUP' if group is None else group,
            timeout=None if timeout is None else timeout
        )
        return config_str

    async def set_config(self, data_id: str, content: str, group: str = None, content_type: str = 'text',
                timeout: float = 3.0) -> bool:
        """
        设置指定的配置信息

        @param {str} data_id - 配置ID
        @param {str} content - 要设置的内容
        @param {str} group=None - 配置所属分组
        @param {str} content_type='text' - 内容类型, 应支持:
            text - 文本
            xml - xml格式内容
            json - json格式的内容
            yaml - yaml格式
        @param {float} timeout=3.0 - 超时时间, 单位为秒

        @returns {bool} - 设置是否成功
        """
        try:
            resp = await self.client.async_publish_config(
                data_id, 'DEFAULT_GROUP' if group is None else group, content, config_type=content_type,
                timeout=None if timeout is None else timeout
            )
            return resp
        except:
            if self.logger is not None:
                self.logger.error('set config error: %s' % traceback.format_exc())
            return False

    async def remove_config(self, data_id: str, group: str = None, timeout: float = 3.0) -> bool:
        """
        删除置顶配置信息

        @param {str} data_id - 配置ID
        @param {str} group=None - 配置所属分组
        @param {float} timeout=3.0 - 超时时间, 单位为秒

        @returns {bool} - 执行是否成功
        """
        try:
            resp = await self.client.async_remove_config(
                data_id, 'DEFAULT_GROUP' if group is None else group,
                timeout=None if timeout is None else timeout
            )
            return resp
        except:
            if self.logger is not None:
                self.logger.error('set config error: %s' % traceback.format_exc())
            return False

    def set_logger(self, logger):
        """
        设置适配器的日志对象
        注: 日志对象初始化后进行设置

        @param {Logger} logger - 要设置的日志对象
        """
        self.logger = logger
        if self.logger is not None:
            nacos.client.logger = self.logger
