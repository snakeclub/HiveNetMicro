#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
任务调度适配器
@module scheduler
@file scheduler.py
"""
import os
import sys
import traceback
from enum import Enum
from functools import wraps
from datetime import datetime
from HiveNetCore.generic import CResult
from HiveNetCore.utils.run_tool import AsyncTools
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.adapter_base import AdapterBaseFw
from HiveNetMicro.core.global_manager import GlobalManager
from HiveNetMicro.core.logger_manager import LoggerManager


class EnumSchedulerState(Enum):
    """
    调度服务状态

    @enum {int}

    """
    STATE_STOPPED = 0  # 停止
    STATE_RUNNING = 1  # 正在运行
    STATE_PAUSED = 2  # 暂停(已启动但job不执行)


class SchedulerAdapter(AdapterBaseFw):
    """
    任务调度适配器
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
        return 'Scheduler'

    #############################
    # 构造函数
    #############################
    def __init__(self, init_config: dict, logger_id: str = None, **kwargs):
        """
        构造函数

        @param {dict} init_config - 适配器实现类的初始化参数
        @param {str} logger_id=None - 日志对象标识, 可以选择application.yaml配置中的其中一个日志对象
        """
        # 参数处理
        self._init_config = init_config
        self._kwargs = kwargs

        # 日志对象
        _logger_manager: LoggerManager = GlobalManager.GET_SYS_LOGGER_MANAGER()
        if _logger_manager is None:
            _logger_manager = LoggerManager('')
        self.logger = _logger_manager.get_logger(
            self._kwargs.get('logger_id', None), none_with_default_logger=True
        )

        # 执行实现类的初始化函数
        self._self_init()

    #############################
    # 需要重载的属性
    #############################
    @property
    def state(self) -> EnumSchedulerState:
        """
        获取调度服务状态
        @property {EnumSchedulerState}
        """
        raise NotImplementedError()

    #############################
    # 需要重载的公共服务
    #############################
    def start(self) -> CResult:
        """
        启动调度服务

        @returns {CResult} - 启动结果
        """
        raise NotImplementedError()

    def stop(self) -> CResult:
        """
        停止调度服务
        注: 停止服务并不会删除任务

        @returns {CResult} - 停止结果
        """
        raise NotImplementedError()

    def pause(self) -> CResult:
        """
        暂停调度服务

        @returns {CResult} - 处理结果
        """
        raise NotImplementedError()

    def resume(self) -> CResult:
        """
        恢复调度服务

        @returns {CResult} - 处理结果
        """
        raise NotImplementedError()

    def add_job(self, job_id: str, func, args: list = None, kwargs: dict = None, job_type: str = 'date',
            run_date: datetime = None, interval_unit: str = 's', interval: float = 5, crontab: str = None,
            active_time: datetime = None, expire_time: datetime = None,
            replace_existing: bool = False, before_func=None, callback_func=None) -> CResult:
        """
        添加任务

        @param {str} job_id - 任务唯一标识
        @param {function} func - 任务函数对象
        @param {list} args=None - 任务函数对象的固定入参
        @param {dict} kwargs=None - 任务函数对象的kv入参
        @param {str} job_type='date' - 任务类型
            date - 指定时间点执行
            cron - 按crontab参数定时执行
            interval - 按固定时间间隔执行
        @param {str|datetime} run_date=None - 指定时间点运行的情况, 对应的时间点, 如果不传代表立即执行
            注: 如果为str, 格式为标准的日期时间格式, 例如: '2009-11-06 16:30:05'
        @param {str} interval_unit='s' - 固定时间间隔单位, s-秒, m-分钟, h-小时
        @param {float} interval=5 - 固定时间间隔时长
        @param {str} crontab=None - crontab参数, 标准6位或7位cron表达式
            '秒 分 时 日期 月 星期 年(可选)', 表达式取值支持:
                * 代表区域匹配每一个值, 例如在分这个域使用 *，即表示每分钟都会触发事件
                - 表示匹配起止范围, 例如在分这个域使用 5-20, 表示从 5 分到 20 分钟每分钟触发一次
                / 表示起始时间开始触发，然后每隔固定时间触发一次, 例如在分这个域使用 5/20, 表示在第 5 分钟触发一次，之后每 20 分钟触发一次，即 5、 25、45 等分别触发一次
                    注: 分领域的5-10/2 标识5-10这个区间内, 每2分钟触发一次
                , 列举多个表达式匹配, 例如分域 1-10,20-30,40 表示1分到10分, 20分到30分每分钟触发一次, 以及40分触发一次
                ? 只能在年和星期域使用, 表示不关心的值
                L 只能在日期域使用, 表示最后一天, 例如 L 表示最后一天; 和数字结合代表当月最后一个星期几, 例如6L代表当月最后一个星期五
            时分秒从数字0开始
            日期可以为数字1-31
            月可以用0-11 或用字符串  “JAN, FEB, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC” 表示
            星期可以用可以用数字1-7表示(1 = 星期日)或用字符串“SUN, MON, TUE, WED, THU, FRI, SAT”
        @param {str|datetime} active_time=None - 任务生效时间
            注: 如果为str, 格式为标准的日期时间格式, 例如: '2009-11-06 16:30:05'
        @param {str|datetime} expire_time=None - 任务失效时间
            注: 如果为str, 格式为标准的日期时间格式, 例如: '2009-11-06 16:30:05'
        @param {bool} replace_existing=Fasle - 如果任务已存在是否覆盖
        @parma {function} before_func=None - 任务执行前执行的函数
            函数定义为func(job_id, job_args, job_kwargs) -> bool, 其中job_args和job_kwargs为任务的入参
            函数如果返回False可以阻止当前任务的真实函数的执行
        @parma {function} callback_func=None - 执行完成后的结果回调函数
            函数定义为func(job_id, run_status, msg, func_ret, job_args, job_kwargs)
            其中run_status为任务状态(success-成功, excepton-异常), msg为任务状态的详细描述, func_ret为任务函数返回结果

        @returns {CResult} - 任务添加结果
        """
        raise NotImplementedError()

    def remove_job(self, job_id: str) -> CResult:
        """
        移除任务

        @param {str} job_id - 任务的唯一标识

        @returns {CResult} - 任务移除结果
        """
        raise NotImplementedError()

    def remove_all_jobs(self) -> CResult:
        """
        移除所有任务

        @returns {CResult} - 移除结果
        """
        raise NotImplementedError()

    def job_exists(self, job_id: str) -> bool:
        """
        检查job是否已存在

        @param {str} job_id - 任务唯一标识

        @returns {bool} - 是否存在
        """
        raise NotImplementedError()

    def pause_job(self, job_id: str) -> CResult:
        """
        暂停指定job

        @param {str} job_id - 任务唯一标识

        @returns {CResult} - 处理结果
        """
        raise NotImplementedError()

    def resume_job(self, job_id: str) -> CResult:
        """
        恢复暂停的job

        @param {str} job_id - 任务唯一标识

        @returns {CResult} - 处理结果
        """
        raise NotImplementedError()

    #############################
    # 需要实现类重载的内部函数
    #############################
    def _self_init(self):
        """
        实现类自定义的初始化函数
        """
        pass

    #############################
    # 内部工具函数
    #############################
    def std_job_func_wraps(self, job_id: str, before_func=None, callback_func=None):
        """
        标准化job执行函数的修饰符(前后增加处理函数)

        @param {str} job_id - 任务唯一标识
        @param {function} before_func=None - 任务执行前执行的函数
        @param {function} callback_func=None - 执行完成后的结果回调函数
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # 返回参数
                _run_status = 'success'
                _msg = ''
                _func_ret = None

                # 执行执行前函数
                if before_func is not None:
                    try:
                        _before_ret = AsyncTools.sync_run_coroutine(
                            before_func(job_id, args, kwargs)
                        )
                        if _before_ret is not None and not _before_ret:
                            # 返回False
                            _run_status = 'excepton'
                            _msg = 'before func return False'
                    except:
                        _run_status = 'excepton'
                        _msg = 'run before func error'
                        self.logger.error('%s: %s' % (_msg, traceback.format_exc()))

                # 执行job函数
                if _run_status == 'success':
                    try:
                        _func_ret = AsyncTools.sync_run_coroutine(
                            f(*args, **kwargs)
                        )
                    except:
                        _run_status = 'excepton'
                        _msg = 'run job func error'
                        self.logger.error('%s: %s' % (_msg, traceback.format_exc()))

                # 执行回调函数
                if callback_func is None:
                    # 没有回调函数
                    if _run_status == 'success':
                        return _func_ret
                    else:
                        raise RuntimeError(_msg)
                else:
                    AsyncTools.sync_run_coroutine(
                        callback_func(job_id, _run_status, _msg, _func_ret, args, kwargs)
                    )

            return decorated_function
        return decorator
