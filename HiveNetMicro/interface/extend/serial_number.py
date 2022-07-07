#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
序列号获取适配器

@module serial_number
@file serial_number.py
"""
import os
import sys
import threading
from HiveNetCore.utils.run_tool import AsyncTools
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.adapter_base import AdapterBaseFw
from HiveNetMicro.core.global_manager import GlobalManager
from HiveNetMicro.core.logger_manager import LoggerManager


class SerialNumberAdapter(AdapterBaseFw):
    """
    序列号获取适配器
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
        return 'SerialNumber'

    #############################
    # 构造函数
    #############################
    def __init__(self, init_config: dict = {}, init_serial_infos: dict = {}, logger_id: str = None):
        """
        初始化适配器

        @param {dict} init_config={} - 适配器初始化参数
        @param {dict} init_serial_infos={} - 装载适配器时需初始化的序列号配置
            id {dict} - 序列号标识之下的配置字典
                current_num {int} - 当前序号, 默认为1
                start_num {int} - 默认为1
                max_num {int} - 最大序号, 默认为sys.maxsize
                repeat {bool} - 当获取序号超过最大序号时是否循环, 默认为True
                default_batch_size {int} - 批量获取序号时的默认批次大小, 默认为10
            注: 不存在序列号的情况才进行初始化
        @param {str} logger_id=None - 日志对象标识, 可以选择application.yaml配置中的其中一个日志对象
        """
        # 参数记录
        self.init_config = init_config
        self.init_serial_infos = init_serial_infos

        # 日志对象
        _logger_manager: LoggerManager = GlobalManager.GET_SYS_LOGGER_MANAGER()
        if _logger_manager is None:
            _logger_manager = LoggerManager('')
        self.logger = _logger_manager.get_logger(logger_id, none_with_default_logger=True)

        # 实现类自定义初始化函数
        self._self_init()

    #############################
    # 需实现类重载的公共函数
    #############################
    async def set_serial_info(self, id: str, current_num: int = 1, start_num: int = 1, max_num: int = sys.maxsize, repeat: bool = True,
            default_batch_size: int = 10):
        """
        设置或重置序列号基础数据

        @param {str} id - 序列号标识
        @param {int} current_num=1 - 当前序号
        @param {int} start_num=1 - 开始序号
        @param {int} max_num=sys.maxsize - 最大序号
            注意: 非循环情况下, 无法获取max_num值的序列号, 只能获取到max_num-1的位置
        @param {bool} repeat=True - 当获取序号超过最大序号时是否循环
        @param {int} default_batch_size=10 - 批量获取序号时的默认批次大小
        """
        raise NotImplementedError()

    async def set_current_num(self, id: str, current_num: int):
        """
        重置当前序号

        @param {str} id - 序列号标识
        @param {int} current_num - 要设置的当前序号
        """
        raise NotImplementedError()

    async def remove_serial_info(self, id: str):
        """
        删除指定序列号基础数据

        @param {str} id - 序列号标识
        """
        raise NotImplementedError()

    async def get_serial_info(self, id: str) -> dict:
        """
        获取序列号基础数据

        @param {str} id - 序列号标识

        @returns {dict} - 返回已设置的序列号基础数据
            {
                'id': '',  # 序列号标识
                'current_num': 1,  # 当前序号
                'start_num': 1,  # 开始序号
                'max_num': 999999999,  # 最大序号
                'repeat': True,  # 当获取序号超过最大序号时是否循环
                'default_batch_size': 10,  # 批量获取序号时的默认批次大小
            }
        """
        raise NotImplementedError()

    async def get_current_num(self, id: str) -> int:
        """
        获取当前序列号的序列值

        @param {str} id - 序列号标识

        @returns {int} - 当前序号
        """
        raise NotImplementedError()

    async def get_serial_num(self, id: str) -> int:
        """
        获取一个序列号

        @param {str} id - 序列号标识

        @returns {int} - 返回的可用序列号
        """
        raise NotImplementedError()

    async def get_serial_batch(self, id: str, batch_size: int = None) -> tuple:
        """
        获取一个序号区间批次

        @param {str} id - 序列号标识
        @param {int} batch_size=None - 要获取批次的大小, 如果不传则使用初始化的默认批次大小

        @returns {tuple} - 返回序号区间批次(开始序号, 结束序号)
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


class SerialNumberTool(object):
    """
    序列号处理工具
    """

    def __init__(self, adapter: SerialNumberAdapter):
        """
        构造函数

        @param {SerialNumberAdapter} adapter - 适配器对象实例
        """
        self.adapter = adapter

        # 缓存已获取到的序列号批次, key为序列号id,
        # value为字典{'lock': 访问锁对象, 'batch_size': 批次大小, 'start': 缓存开始序号, 'end': 缓存结束序号}
        self._cached_batch = {}

    #############################
    # 通用函数
    #############################
    async def cache_serial_batch(self, id: str, batch_size: int = None, cache_now: bool = False):
        """
        设定缓存指定id的序列号

        @param {str} id - 序列号id

        @param {int} batch_size=None - 缓存序列号的批次大小
        @param {bool} cache_now=False - 是否马上获取批次
        """
        if id not in self._cached_batch.keys():
            self._cached_batch[id] = {
                'lock': threading.RLock(),
                'batch_size': batch_size, 'start': 0, 'end': 0
            }

        if cache_now:
            # 立即获取序号缓存批次数据
            _cache_info = self._cached_batch[id]
            _cache_info['lock'].acquire()
            try:
                if _cache_info['start'] == _cache_info['end']:
                    # 获取批次数据
                    _cache_info['start'], _cache_info['end'] = await AsyncTools.async_run_coroutine(
                        self.adapter.get_serial_batch(id, batch_size=_cache_info['batch_size'])
                    )
            finally:
                _cache_info['lock'].release()

    async def get_serial_num(self, id: str) -> int:
        """
        获取一个序列号

        @param {str} id - 要获取的序列号id

        @returns {int} - 返回序列号
        """
        _cache_info = self._cached_batch.get(id, None)
        if _cache_info is None:
            # 没有缓存, 直接进行获取
            return await AsyncTools.async_run_coroutine(
                self.adapter.get_serial_num(id)
            )

        _cache_info['lock'].acquire()
        try:
            if _cache_info['start'] == _cache_info['end']:
                # 已经没有缓存数据了, 获取批次数据
                _cache_info['start'], _cache_info['end'] = await AsyncTools.async_run_coroutine(
                    self.adapter.get_serial_batch(id, batch_size=_cache_info['batch_size'])
                )

            # 返回结果
            _num = _cache_info['start']
            _cache_info['start'] += 1
            return _num
        finally:
            _cache_info['lock'].release()

    async def get_serial_num_fix_str(self, id: str, str_len: int) -> str:
        """
        获取固定长度字符串格式的序列号

        @param {str} id - 序列号id
        @param {int} str_len - 字符串长度

        @returns {str} - 字符串
        """
        _num = await self.get_serial_num(id)
        _fix_num = 10 ** str_len
        if _num >= _fix_num:
            # 已经超长, 直接返回
            return str(_num)
        else:
            # 返回合并以后去除1的数字
            return str(_fix_num + _num)[1:]
