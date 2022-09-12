#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
独立服务器的序列号适配器

@module serial_number_standalone
@file serial_number_standalone.py
"""

import os
import sys
import time
import json
from HiveNetCore.utils.run_tool import AsyncTools
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.interface.extend.serial_number import SerialNumberAdapter
from HiveNetMicro.core.global_manager import GlobalManager


class FileLockException(Exception):
    pass


class SerialInfoNotExists(Exception):
    pass


class CurrentSerialNumberUidError(Exception):
    pass


class StandaloneSerialNumberAdapter(SerialNumberAdapter):
    """
    独立服务器的序列号适配器
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, init_config: dict = {}, init_serial_infos: dict = {}, logger_id: str = None):
        """
        初始化适配器

        @param {dict} init_config={} - 适配器初始化参数
            store_path {str} - 持久化存储文件目录, 为应用启动目录的相对路径
            overtime {float} - 存储文件锁等待的超时时间, 单位为秒, 默认为3.0
            wait_delay {float} - 存储文件锁等待的循环时间间隔, 单位为秒, 默认为0.1
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
        # 执行基础类初始化函数
        super().__init__(
            init_config=init_config, init_serial_infos=init_serial_infos, logger_id=logger_id
        )

        # 参数处理
        self._global_config = GlobalManager.GET_GLOBAL_CONFIG()
        if self._global_config is None:
            self._global_config = {}
        self.store_path = os.path.join(
            self._global_config.get('base_path', os.path.dirname(sys.argv[0])),
            init_config.get('store_path', 'serial_number_data')
        )
        self.info_file = os.path.join(
            self.store_path, 'info.json'
        )
        self.overtime = init_config.get('overtime', 3.0)
        self.wait_delay = init_config.get('wait_delay', 0.1)

        # 当前已存储的序列号配置字典, 如果发现有变更将自动进行更新
        self.info = {}

        # 初始化数据
        if not os.path.exists(self.store_path):
            os.makedirs(self.store_path, exist_ok=True)

        if not os.path.exists(self.info_file):
            self._save_info_file()

        # 读取基本配置
        self._get_info_from_file()

        # 初始化序列号
        if init_serial_infos is not None:
            for _id, _info in init_serial_infos.items():
                if _id in self.info.keys():
                    continue

                # 创建序列号
                AsyncTools.sync_run_coroutine(
                    self.set_serial_info(
                        _id, current_num=_info.get('current_num', 1),
                        start_num=_info.get('start_num', 1), max_num=_info.get('max_num', sys.maxsize),
                        repeat=_info.get('repeat', True),
                        default_batch_size=_info.get('default_batch_size', 10)
                    )
                )

    #############################
    # 通用函数
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
        # 进行有效性检查
        if current_num < start_num and current_num > max_num:
            raise AttributeError('current_num is not in the area')

        self._upd_serial_info(
            id, {
                'id': id,
                'current_num': current_num,
                'start_num': 1,
                'max_num': max_num,
                'repeat': repeat,
                'default_batch_size': default_batch_size
            }
        )

    async def set_current_num(self, id: str, current_num: int):
        """
        重置当前序号

        @param {str} id - 序列号标识
        @param {int} current_num - 要设置的当前序号
        """
        self._set_current_num(id, new_num=current_num)

    async def remove_serial_info(self, id: str):
        """
        删除指定序列号基础数据

        @param {str} id - 序列号标识
        """
        self._del_serial_info(id)

    async def get_serial_info(self, id: str) -> dict:
        """
        获取序列号基础数据

        @param {str} id - 序列号标识

        @returns {dict} - 返回已设置的序列号基础数据, 如果没有配置返回None
            {
                'id': '',  # 序列号标识
                'current_num': 1,  # 当前序号
                'start_num': 1,  # 开始序号
                'max_num': 999999999,  # 最大序号
                'repeat': True,  # 当获取序号超过最大序号时是否循环
                'default_batch_size': 10,  # 批量获取序号时的默认批次大小
            }
        """
        # 获取最新的信息
        self._get_info_from_file()
        return self.info.pop(id, None)

    async def get_current_num(self, id: str) -> int:
        """
        获取当前序列号的序列值

        @param {str} id - 序列号标识

        @returns {int} - 当前序号
        """
        return self._set_current_num(id)[0]

    async def get_serial_num(self, id: str) -> int:
        """
        获取一个序列号

        @param {str} id - 序列号标识

        @returns {int} - 返回的可用序列号
        """
        return self._set_current_num(id, batch_size=1, is_batch=True)[0]

    async def get_serial_batch(self, id: str, batch_size: int = None) -> tuple:
        """
        获取一个序号区间批次

        @param {str} id - 序列号标识
        @param {int} batch_size=None - 要获取批次的大小, 如果不传则使用初始化的默认批次大小

        @returns {tuple} - 返回序号区间批次(开始序号, 结束序号)
        """
        _current_num, _new_num, _max_num = self._set_current_num(id, batch_size=batch_size, is_batch=True)
        if _new_num > _current_num:
            return (_current_num, _new_num - 1)
        else:
            # 出现了循环
            return (_current_num, _max_num)

    #############################
    # 内部函数
    #############################
    def _lock_file(self, lock_file: str) -> int:
        """
        获取锁文件

        @param {str} lock_file - 锁文件

        @returns {int} - 返回锁文件的句柄
        """
        start_time = time.time()
        while True:
            try:
                _fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            except OSError:
                # 无法获取到锁文件
                if (time.time() - start_time) >= self.overtime:
                    # 超时
                    raise FileLockException("Timeout occured")

                # 继续尝试获取
                time.sleep(self.wait_delay)
                continue

            return _fd

    def _unlock_file(self, lock_file: str, fd: int):
        """
        释放锁

        @param {str} lock_file - 锁文件
        @param {int} fd - 锁文件句柄
        """
        os.close(fd)
        os.unlink(lock_file)

    def _save_info_file(self):
        """
        将当前配置信息写入存储文件
        """
        _lock_file = '%s.lock' % self.info_file
        _fd = self._lock_file(_lock_file)  # 获取锁
        try:
            # 写文件
            with open(self.info_file, 'wb') as _f:
                _f.write(json.dumps(self.info, ensure_ascii=False).encode(encoding='utf-8'))
        finally:
            # 释放锁
            self._unlock_file(_lock_file, _fd)

    def _upd_serial_info(self, id: str, info: dict):
        """
        更新序列号配置信息

        @param {str} id - 序列号标识
        @param {dict} info - 序列号配置字典
            {
                'id': '',  # 序列号标识
                'current_num': 1,  # 当前序号
                'start_num': 1,  # 开始序号
                'max_num': 999999999,  # 最大序号
                'repeat': True,  # 当获取序号超过最大序号时是否循环
                'default_batch_size': 10,  # 批量获取序号时的默认批次大小
            }
        """
        _lock_file = '%s.lock' % self.info_file
        _fd = self._lock_file(_lock_file)  # 获取锁
        try:
            _current_file = os.path.join(self.store_path, 'current_num_%s.json' % info['id'])
            _current_lock_file = '%s.lock' % _current_file
            _cfd = self._lock_file(_current_lock_file)  # 获取锁
            try:
                # 获取当前序列号文件信息
                if os.path.exists(_current_file):
                    with open(_current_file, 'rb') as _f:
                        _current_info = json.loads(
                            _f.read().decode(encoding='utf-8')
                        )
                    # 自增更新id
                    if _current_info['uid'] >= sys.maxsize:
                        _current_info['uid'] = info['start_num']
                    else:
                        _current_info['uid'] += 1

                    _current_info['current_num'] = info['current_num']
                else:
                    _current_info = {'uid': 1, 'num': info['current_num']}

                # 写入当前序列号文件信息
                with open(_current_file, 'wb') as _f:
                    _f.write(json.dumps(_current_info, ensure_ascii=False).encode(encoding='utf-8'))

                # info中的uid信息设置为一致, 通过_current_file中的uid通知其他进程更新信息
                info['uid'] = _current_info['uid']

                # 获取最新信息
                with open(self.info_file, 'rb') as _f:
                    self.info = json.loads(
                        _f.read().decode(encoding='utf-8')
                    )

                # 更新配置信息项
                self.info[id] = info

                # 写入存储文件
                with open(self.info_file, 'wb') as _f:
                    _f.write(json.dumps(self.info, ensure_ascii=False).encode(encoding='utf-8'))
            finally:
                self._unlock_file(_current_lock_file, _cfd)
        finally:
            # 释放锁
            self._unlock_file(_lock_file, _fd)

    def _del_serial_info(self, id: str):
        """
        删除指定配置

        @param {str} id - 序列号标识
        """
        _lock_file = '%s.lock' % self.info_file
        _fd = self._lock_file(_lock_file)  # 获取锁
        try:
            _current_file = os.path.join(self.store_path, 'current_num_%s.json' % id)
            _current_lock_file = '%s.lock' % _current_file
            _cfd = self._lock_file(_current_lock_file)  # 获取锁
            try:
                # 删除当前序列号文件
                if os.path.exists(_current_file):
                    os.unlink(_current_file)

                # 获取最新信息
                with open(self.info_file, 'rb') as _f:
                    self.info = json.loads(
                        _f.read().decode(encoding='utf-8')
                    )

                self.info.pop(id, None)

                # 写入存储文件
                with open(self.info_file, 'wb') as _f:
                    _f.write(json.dumps(self.info, ensure_ascii=False).encode(encoding='utf-8'))
            finally:
                self._unlock_file(_current_lock_file, _cfd)
        finally:
            # 释放锁
            self._unlock_file(_lock_file, _fd)

    def _get_info_from_file(self):
        """
        从配置文件中获取配置信息
        """
        _lock_file = '%s.lock' % self.info_file
        _fd = self._lock_file(_lock_file)  # 获取锁
        try:
            # 读文件
            with open(self.info_file, 'rb') as _f:
                self.info = json.loads(
                    _f.read().decode(encoding='utf-8')
                )
        finally:
            # 释放锁
            self._unlock_file(_lock_file, _fd)

    def _set_current_num(self, id: str, new_num: int = None, batch_size: int = None, is_batch: bool = False) -> tuple:
        """
        设置当前序列值

        @param {str} id - 要设置的序列号id
        @param {int} new_num=None - 要设置的新序列值, 如果不传代表不处理或使用加减方式修改
        @param {int} batch_size=None - 要设置的批次大小
        @param {bool} is_batch=False - 是否批次获取

        @returns {tuple} - 返回(原值, 当前值, 序列最大值)
        """
        # 如果找不到配置, 重新获取一次最新的数据
        if self.info.get(id, None) is None:
            _need_refresh = True
        else:
            _need_refresh = False

        _current_file = os.path.join(self.store_path, 'current_num_%s.json' % id)
        _current_lock_file = '%s.lock' % _current_file
        while True:
            if _need_refresh:
                self._get_info_from_file()

            _info = self.info.get(id, None)
            if _info is None:
                raise SerialInfoNotExists('Serial number info not exists')

            _cfd = self._lock_file(_current_lock_file)  # 获取锁
            try:
                with open(_current_file, 'rb') as _f:
                    _current_info = json.loads(
                        _f.read().decode(encoding='utf-8')
                    )

                if _current_info['uid'] != _info['uid']:
                    if _need_refresh:
                        # 已经刷新过一次, 直接抛出异常
                        raise CurrentSerialNumberUidError('%s uid error' % _current_file)
                    else:
                        # 需要刷新, 重新循环
                        _need_refresh = True
                        continue

                # 通过检查, 进行序列号的处理
                if not is_batch and new_num is None:
                    # 没有设置参数, 直接返回当前值
                    return (_current_info['num'], _current_info['num'], _info['max_num'])

                if not is_batch:
                    # 直接设置新值
                    if new_num > _info['max_num'] or new_num < _info['start_num']:
                        raise AttributeError('current_num is out of the area')
                    _new_num = new_num
                else:
                    # 批次获取
                    _batch_size = _info['default_batch_size'] if batch_size is None else batch_size
                    _new_num = _current_info['num'] + _batch_size
                    if _new_num > _info['max_num']:
                        if _info['repeat']:
                            _new_num = _info['start_num']
                        else:
                            # 超过了最大区间, 并且没有设置循环
                            raise AttributeError('current_num is out of the area')

                # 设置返回值
                _ret = (_current_info['num'], _new_num, _info['max_num'])
                _current_info['num'] = _new_num

                # 写入当前序列号文件信息
                with open(_current_file, 'wb') as _f:
                    _f.write(json.dumps(_current_info, ensure_ascii=False).encode(encoding='utf-8'))

                return _ret
            finally:
                self._unlock_file(_current_lock_file, _cfd)
