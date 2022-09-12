#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
单服务器支持的任务调度适配器
注: 基于apscheduler实现支持

@module scheduler_standalone
@file scheduler_standalone.py
"""
import os
import sys
from datetime import datetime
from HiveNetCore.generic import CResult
from HiveNetCore.utils.exception_tool import ExceptionTool
# 自动安装依赖库
from HiveNetCore.utils.pyenv_tool import PythonEnvTools
try:
    from pytz import utc
except ImportError:
    PythonEnvTools.install_package('pytz')
    from pytz import utc
process_install_apscheduler = False
while True:
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.jobstores.memory import MemoryJobStore
        from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
        break
    except ImportError:
        if process_install_apscheduler:
            break
        else:
            PythonEnvTools.install_package('apscheduler')
            process_install_apscheduler = True
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.interface.extend.scheduler import SchedulerAdapter, EnumSchedulerState


class StandaloneSchedulerAdapter(SchedulerAdapter):
    """
    单服务器支持的任务调度适配器
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, init_config: dict, logger_id: str = None, **kwargs):
        """
        构造函数

        @param {dict} init_config - 适配器实现类的初始化参数
            executor {str} - 执行器类型, 支持: thread-线程模式执行器, process-进程模式执行器
            executor_pool_size {int} - 执行器池大小(支持并行任务数量), 默认为20
            default_job_max_instances {int} - 默认job的最大实例数量(同一个任务可以并行多少个实例执行), 默认为1
        @param {str} logger_id=None - 日志对象标识, 可以选择application.yaml配置中的其中一个日志对象
        """
        # 执行基类的初始化函数
        super().__init__(init_config, logger_id=logger_id)

    #############################
    # 需要实现类重载的内部函数
    #############################
    def _self_init(self):
        """
        实现类自定义的初始化函数
        """
        # 内存存储, 调度任务不基于控件的持久化
        _jobstores = {
            'default': MemoryJobStore()
        }

        # 执行器的线程/进程池设置
        _executor_pool_size = self._init_config.get('executor_pool_size', 20)
        if self._init_config.get('executor', 'thread') == 'process':
            _executor = ProcessPoolExecutor(_executor_pool_size)
        else:
            _executor = ThreadPoolExecutor(_executor_pool_size)

        _executors = {
            'default': _executor
        }

        # 默认任务配置
        _job_defaults = {
            'coalesce': False,
            'max_instances': self._init_config.get('default_job_max_instances', 1)  # 任务最大实例数
        }

        self._scheduler = BackgroundScheduler(
            jobstores=_jobstores, executors=_executors, job_defaults=_job_defaults, timezone=utc
        )

    #############################
    # 需要重载的属性
    #############################
    @property
    def state(self) -> EnumSchedulerState:
        """
        获取调度服务状态
        @property {EnumSchedulerState}
        """
        return self._scheduler.state

    #############################
    # 需要重载的公共服务
    #############################
    def start(self) -> CResult:
        """
        启动调度服务

        @returns {CResult} - 启动结果
        """
        _result = CResult()
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger, self_log_msg='start scheduler error'
        ):
            self._scheduler.start()

        return _result

    def stop(self) -> CResult:
        """
        停止调度服务
        注: 停止服务并不会删除任务

        @returns {CResult} - 停止结果
        """
        _result = CResult()
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger, self_log_msg='stop scheduler error'
        ):
            self._scheduler.shutdown()

        return _result

    def pause(self) -> CResult:
        """
        暂停调度服务

        @returns {CResult} - 处理结果
        """
        _result = CResult()
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger, self_log_msg='pause scheduler error'
        ):
            self._scheduler.pause()

        return _result

    def resume(self) -> CResult:
        """
        恢复调度服务

        @returns {CResult} - 处理结果
        """
        _result = CResult()
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger, self_log_msg='resume scheduler error'
        ):
            self._scheduler.resume()

        return _result

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
        _result = CResult()
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger, self_log_msg='add scheduler job'
        ):
            # 标准执行函数对象
            @self.std_job_func_wraps(job_id, before_func=before_func, callback_func=callback_func)
            def std_job_func(*job_args, **job_kwargs):
                return func(*job_args, **job_kwargs)

            # 处理入参
            _job_args = [] if args is None else args
            _job_kwargs = {} if kwargs is None else kwargs

            # 处理job参数
            _kwargs = {
                'replace_existing': replace_existing
            }
            if active_time is not None:
                if type(active_time) == str:
                    _kwargs['start_date'] = active_time
                else:
                    _kwargs['start_date'] = active_time.strftime('%Y-%m-%d %H:%M:%S')
            if expire_time is not None:
                if type(expire_time) == str:
                    _kwargs['end_date'] = expire_time
                else:
                    _kwargs['end_date'] = expire_time.strftime('%Y-%m-%d %H:%M:%S')

            if job_type == 'cron':
                # 按crontab参数定时执行
                _values = crontab.split()
                if len(_values) not in (6, 7):
                    raise ValueError('Wrong number of fields; got {}, expected 6 or 7'.format(len(_values)))

                # 进行cron表达式的标准化处理
                if _values[0] != '?':
                    _kwargs['second'] = _values[0]
                if _values[1] != '?':
                    _kwargs['minute'] = _values[1]
                if _values[2] != '?':
                    _kwargs['hour'] = _values[2]
                if _values[3] != '?':
                    _kwargs['day'] = _values[3].lower()
                    if _kwargs['day'] == 'l':
                        _kwargs['day'] = 'last'
                    elif _kwargs['day'][-1:] == 'l':
                        _kwargs['day'] = 'last %s' % _kwargs['day'][:-1]
                if _values[4] != '?':
                    _kwargs['month'] = _values[4].lower()
                if _values[5] != '?':
                    _kwargs['day_of_week'] = _values[5].lower()
                if len(_values) == 7 and _values[6] != '?':
                    _kwargs['year'] = _values[6]

                self._scheduler.add_job(
                    std_job_func, trigger='cron', args=_job_args, kwargs=_job_kwargs, id=job_id,
                    **_kwargs
                )
                self.logger.info('Added job to scheduler: id: %s, crontab: %s' % (
                    job_id, crontab
                ))
            elif job_type == 'interval':
                # 间隔时间发起的情况
                if interval_unit == 'h':
                    _kwargs['hours'] = interval
                elif interval_unit == 'm':
                    _kwargs['minutes'] = interval
                else:
                    _kwargs['seconds'] = interval

                self._scheduler.add_job(
                    std_job_func, trigger='interval', args=_job_args, kwargs=_job_kwargs, id=job_id,
                    **_kwargs
                )
                self.logger.info('Added job to scheduler: id: %s, interval: %d%s' % (
                    job_id, interval, interval_unit
                ))
            else:
                # 指定时间点执行
                if run_date is not None:
                    _kwargs['run_date'] = run_date
                self._scheduler.add_job(
                    std_job_func, trigger='date', args=_job_args, kwargs=_job_kwargs, id=job_id,
                    **_kwargs
                )
                self.logger.info('Added job to scheduler: id: %s, run on %s' % (job_id, str(run_date)))

        return _result

    def remove_job(self, job_id: str) -> CResult:
        """
        移除任务

        @param {str} job_id - 任务的唯一标识

        @returns {CResult} - 任务移除结果
        """
        _result = CResult()
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger, self_log_msg='remove scheduler job'
        ):
            self._scheduler.remove_job(job_id)

        return _result

    def remove_all_jobs(self) -> CResult:
        """
        移除所有任务

        @returns {CResult} - 移除结果
        """
        _result = CResult()
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger, self_log_msg='remove all scheduler jobs'
        ):
            self._scheduler.remove_all_jobs()

        return _result

    def job_exists(self, job_id: str) -> bool:
        """
        检查job是否已存在

        @param {str} job_id - 任务唯一标识

        @returns {bool} - 是否存在
        """
        _job = self._scheduler.get_job(job_id)
        return False if _job is None else True

    def pause_job(self, job_id: str) -> CResult:
        """
        暂停指定job

        @param {str} job_id - 任务唯一标识

        @returns {CResult} - 处理结果
        """
        _result = CResult()
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger, self_log_msg='pause scheduler job [%s] error' % job_id
        ):
            self._scheduler.pause_job(job_id)

        return _result

    def resume_job(self, job_id: str) -> CResult:
        """
        恢复暂停的job

        @param {str} job_id - 任务唯一标识

        @returns {CResult} - 处理结果
        """
        _result = CResult()
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger, self_log_msg='resume scheduler job [%s] error' % job_id
        ):
            self._scheduler.resume_job(job_id)

        return _result
