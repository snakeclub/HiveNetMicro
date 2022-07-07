#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
全局对象的管理模块

@module global_manager
@file global_manager.py
"""
import os
import sys
from typing import Any
from HiveNetCore.utils.run_tool import RunTool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))


class GlobalManager(object):
    """
    全局对象的管理模块
    """

    #############################
    # 环境信息
    #############################
    @classmethod
    def SET_ENV(cls, env: str):
        """
        设置环境信息

        @param {str} env - 环境信息
        """
        RunTool.set_global_var('SYS_ENV', env)

    @classmethod
    def GET_ENV(cls) -> Any:
        """
        获取环境信息

        @returns {str} - 获取到的环境信息
        """
        return RunTool.get_global_var('SYS_ENV', default='')

    @classmethod
    def SET_GLOBAL_CONFIG(cls, config: dict):
        """
        设置全局配置信息

        @param {dict} config - 全局配置信息
        """
        RunTool.set_global_var('SYS_GLOBAL_CONFIG', config)

    @classmethod
    def GET_GLOBAL_CONFIG(cls) -> Any:
        """
        获取全局配置信息

        @returns {dict} - 全局配置信息
        """
        return RunTool.get_global_var('SYS_GLOBAL_CONFIG', default={})

    #############################
    # 系统级别的全局对象
    #############################
    @classmethod
    def SET_SYS_LOGGER_MANAGER(cls, instance):
        """
        设置日志管理对象

        @param {any} instance - 要设置的对象
        """
        RunTool.set_global_var('SYS_LOGGER_MANAGER', instance)

    @classmethod
    def GET_SYS_LOGGER_MANAGER(cls) -> Any:
        """
        获取日志管理对象

        @returns {Any} - 获取到的对象, 如果获取不到返回None
        """
        return RunTool.get_global_var('SYS_LOGGER_MANAGER')

    @classmethod
    def SET_SYS_LOGGER(cls, instance):
        """
        设置系统日志对象

        @param {any} instance - 要设置的对象
        """
        RunTool.set_global_var('SYS_LOGGER', instance)

    @classmethod
    def GET_SYS_LOGGER(cls) -> Any:
        """
        获取系统日志对象

        @returns {Any} - 获取到的对象, 如果获取不到返回None
        """
        return RunTool.get_global_var('SYS_LOGGER')

    @classmethod
    def SET_SYS_LIB_LOADER(cls, instance):
        """
        设置系统动态库加载模块

        @param {any} instance - 要设置的对象
        """
        RunTool.set_global_var('SYS_LIB_LOADER', instance)

    @classmethod
    def GET_SYS_LIB_LOADER(cls) -> Any:
        """
        获取系统动态库加载模块

        @returns {Any} - 获取到的对象, 如果获取不到返回None
        """
        return RunTool.get_global_var('SYS_LIB_LOADER')

    @classmethod
    def SET_SYS_SERVICES_LOADER(cls, instance):
        """
        设置系统服务库加载模块

        @param {any} instance - 要设置的对象
        """
        RunTool.set_global_var('SYS_SERVICES_LOADER', instance)

    @classmethod
    def GET_SYS_SERVICES_LOADER(cls) -> Any:
        """
        获取系统服务库加载模块

        @returns {Any} - 获取到的对象, 如果获取不到返回None
        """
        return RunTool.get_global_var('SYS_SERVICES_LOADER')

    @classmethod
    def SET_SYS_CONFIG_CENTER(cls, instance):
        """
        设置配置中心对象

        @param {any} instance - 要设置的对象
        """
        RunTool.set_global_var('SYS_CONFIG_CENTER', instance)

    @classmethod
    def GET_SYS_CONFIG_CENTER(cls) -> Any:
        """
        获取配置中心对象

        @returns {Any} - 获取到的对象, 如果获取不到返回None
        """
        return RunTool.get_global_var('SYS_CONFIG_CENTER')

    @classmethod
    def SET_SYS_ADAPTER_MANAGER(cls, instance):
        """
        设置通用适配器管理模块

        @param {any} instance - 要设置的对象
        """
        RunTool.set_global_var('SYS_ADAPTER_MANAGER', instance)

    @classmethod
    def GET_SYS_ADAPTER_MANAGER(cls) -> Any:
        """
        获取通用适配器管理模块

        @returns {Any} - 获取到的对象, 如果获取不到返回None
        """
        return RunTool.get_global_var('SYS_ADAPTER_MANAGER')

    @classmethod
    def SET_SYS_NAMING(cls, instance):
        """
        设置服务注册中心对象

        @param {any} instance - 要设置的对象
        """
        RunTool.set_global_var('SYS_NAMING', instance)

    @classmethod
    def GET_SYS_NAMING(cls) -> Any:
        """
        获取服务注册中心对象

        @returns {Any} - 获取到的对象, 如果获取不到返回None
        """
        return RunTool.get_global_var('SYS_NAMING')

    @classmethod
    def SET_SYS_TRACER(cls, instance):
        """
        设置调用链对象

        @param {any} instance - 要设置的对象
        """
        RunTool.set_global_var('SYS_TRACER', instance)

    @classmethod
    def GET_SYS_TRACER(cls) -> Any:
        """
        获取调用链对象

        @returns {Any} - 获取到的对象, 如果获取不到返回None
        """
        return RunTool.get_global_var('SYS_TRACER')

    @classmethod
    def SET_SYS_REMOTE_CALLER(cls, instance):
        """
        设置远程调用对象

        @param {any} instance - 要设置的对象
        """
        RunTool.set_global_var('SYS_REMOTE_CALLER', instance)

    @classmethod
    def GET_SYS_REMOTE_CALLER(cls) -> Any:
        """
        获取远程调用对象

        @returns {Any} - 获取到的对象, 如果获取不到返回None
        """
        return RunTool.get_global_var('SYS_REMOTE_CALLER')

    @classmethod
    def SET_SYS_WEB_SERVER(cls, instance):
        """
        设置Web服务器对象

        @param {any} instance - 要设置的对象
        """
        RunTool.set_global_var('SYS_WEB_SERVER', instance)

    @classmethod
    def GET_SYS_WEB_SERVER(cls) -> Any:
        """
        获取Web服务器对象

        @returns {Any} - 获取到的对象, 如果获取不到返回None
        """
        return RunTool.get_global_var('SYS_WEB_SERVER')

    @classmethod
    def SET_SYS_CLUSTER(cls, instance):
        """
        设置集群适配器对象

        @param {any} instance - 要设置的对象
        """
        RunTool.set_global_var('SYS_CLUSTER', instance)

    @classmethod
    def GET_SYS_CLUSTER(cls) -> Any:
        """
        获取集群适配器对象

        @returns {Any} - 获取到的对象, 如果获取不到返回None
        """
        return RunTool.get_global_var('SYS_CLUSTER')

    #############################
    # 平台级别的全局对象
    #############################
    @classmethod
    def SET_PLATFORM_INSTANCE(cls, instance):
        """
        设置平台通用接口对象

        @param {DynamicLibLoader} instance - 平台通用接口对象
        """
        RunTool.set_global_var('PLATFORM_INSTANCE', instance)

    @classmethod
    def GET_PLATFORM_INSTANCE(cls) -> Any:
        """
        获取平台通用接口对象

        @returns {Any} - 获取到的对象, 如果获取不到返回None
        """
        return RunTool.get_global_var('PLATFORM_INSTANCE')

    @classmethod
    def SET_PLATFORM_LIB_LOADER(cls, instance):
        """
        设置公共的动态库加载对象

        @param {DynamicLibLoader} instance - 动态库加载对象
        """
        RunTool.set_global_var('PLATFORM_LIB_LOADER', instance)

    @classmethod
    def GET_PLATFORM_LIB_LOADER(cls) -> Any:
        """
        获取公共的动态库加载对象

        @returns {Any} - 获取到的对象, 如果获取不到返回None
        """
        return RunTool.get_global_var('PLATFORM_LIB_LOADER')

    @classmethod
    def SET_PLATFORM_LOGGER(cls, instance):
        """
        设置公共的平台服务日志对象

        @param {DynamicLibLoader} instance - 动态库加载对象
        """
        RunTool.set_global_var('PLATFORM_LOGGER', instance)

    @classmethod
    def GET_PLATFORM_LOGGER(cls) -> Any:
        """
        获取公共的平台服务日志对象

        @returns {Any} - 获取到的对象, 如果获取不到返回None
        """
        return RunTool.get_global_var('PLATFORM_LOGGER')
