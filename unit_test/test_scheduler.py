#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
测试调度服务

@module test_scheduler
@file test_scheduler.py
"""

import os
import sys
import time
from datetime import datetime
import unittest
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetMicro.interface.extend.scheduler import SchedulerAdapter
from HiveNetMicro.plugins.extend.scheduler_standalone import StandaloneSchedulerAdapter


# 控制测试的字典
TEST_CONTROL = {
    'init': True,
    'normal': True,
    'exception': True
}


class SchedulerTestCaseFW(object):
    """
    通用的调度测试基础类
    """

    #############################
    # 构造函数和析构函数
    #############################
    def __init__(self):
        """
        构造函数, 初始化调度对象
        """
        self.is_stop = False  # 控制是否停止的标识

        # 设置任务执行次数的字典
        self.job_run_count = {}

        # 获取调度对象
        self.scheduler: SchedulerAdapter = self._init_scheduler()

        if TEST_CONTROL['init']:
            # 初始化任务
            _job_id = 'init_run_now'  # 注意, 如果间隔一段时间再启动, 因为时间偏差大, 任务不会执行
            _ret = self.scheduler.add_job(
                _job_id, self.job_common_func, args=[_job_id],
                kwargs={'kv_para': 'init_run_now para', 'ret_val': 'init_run_now ret'},
                before_func=self.job_common_before_func, callback_func=self.job_common_callback_func
            )
            if not _ret.is_success():
                raise RuntimeError('add job [%s] error' % _job_id)

            _job_id = 'init_run_interval'
            _ret = self.scheduler.add_job(
                _job_id, self.job_common_func, args=[_job_id],
                kwargs={'kv_para': 'init_run_interval para', 'ret_val': 'init_run_interval ret'},
                job_type='interval', interval_unit='s', interval=3,
                before_func=self.job_common_before_func, callback_func=self.job_common_callback_func
            )
            if not _ret.is_success():
                raise RuntimeError('add job [%s] error' % _job_id)

            _job_id = 'init_run_cron'
            _ret = self.scheduler.add_job(
                _job_id, self.job_common_func, args=[_job_id],
                kwargs={'kv_para': 'init_run_cron para', 'ret_val': 'init_run_cron ret'},
                job_type='cron', crontab='0,10,15,20,30,40,50 * * * * *',
                before_func=self.job_common_before_func, callback_func=self.job_common_callback_func
            )
            if not _ret.is_success():
                raise RuntimeError('add job [%s] error' % _job_id)

        # 启动调度任务
        print('start scheduler ...')
        self.scheduler.start()

        if TEST_CONTROL['init']:
            # 等待12秒执行
            time.sleep(12)

            # 删除任务
            _job_id = 'init_run_now'
            _ret = self.scheduler.remove_job(_job_id)
            if _ret.is_success():
                raise RuntimeError('remove job [%s] should error, but success: %s' % (_job_id, _ret))

            _job_id = 'init_run_interval'
            _ret = self.scheduler.remove_job(_job_id)
            if not _ret.is_success():
                raise RuntimeError('remove job [%s] error: %s' % (_job_id, _ret))

            _job_id = 'init_run_cron'
            _ret = self.scheduler.remove_job(_job_id)
            if not _ret.is_success():
                raise RuntimeError('remove job [%s] error: %s' % (_job_id, _ret))

            print('init jobs removed ...')

    def __del__(self):
        """
        析构函数
        """
        self.scheduler.stop()

    #############################
    # 测试案例函数
    #############################
    def test_normal(self, test_obj: unittest.TestCase):
        # 测试正常情况
        print('\n', 'test normal ...')
        _tips = 'test normal'
        _job_id = 'normal_run_now'  # 注意, 如果间隔一段时间再启动, 因为时间偏差大, 任务不会执行
        _ret = self.scheduler.add_job(
            _job_id, self.job_common_func, args=[_job_id],
            kwargs={'kv_para': '%s para' % _job_id, 'ret_val': '%s ret' % _job_id},
            before_func=self.job_common_before_func, callback_func=self.job_common_callback_func
        )
        test_obj.assertTrue(_ret.is_success(), '%s, add job [%s] error' % (_tips, _job_id))

        _job_id = 'normal_run_interval'
        _ret = self.scheduler.add_job(
            _job_id, self.job_common_func, args=[_job_id],
            kwargs={'kv_para': '%s para' % _job_id, 'ret_val': '%s ret' % _job_id},
            job_type='interval', interval_unit='s', interval=2,
            before_func=self.job_common_before_func, callback_func=self.job_common_callback_func
        )
        test_obj.assertTrue(_ret.is_success(), '%s, add job [%s] error' % (_tips, _job_id))

        _job_id = 'normal_run_cron'
        _ret = self.scheduler.add_job(
            _job_id, self.job_common_func, args=[_job_id],
            kwargs={'kv_para': '%s para' % _job_id, 'ret_val': '%s ret' % _job_id},
            job_type='cron', crontab='0-59/3 * * * * *',
            before_func=self.job_common_before_func, callback_func=self.job_common_callback_func
        )
        test_obj.assertTrue(_ret.is_success(), '%s, add job [%s] error' % (_tips, _job_id))

        # 等待6秒执行
        time.sleep(6)

        # 检查运行状态
        _job_id = 'normal_run_now'
        test_obj.assertTrue(
            self.job_run_count.get(_job_id, 0) > 0, '%s, job [%s] not run' % (_tips, _job_id)
        )
        _job_id = 'normal_run_interval'
        test_obj.assertTrue(
            self.job_run_count.get(_job_id, 0) > 0, '%s, job [%s] not run' % (_tips, _job_id)
        )
        _job_id = 'normal_run_cron'
        test_obj.assertTrue(
            self.job_run_count.get(_job_id, 0) > 0, '%s, job [%s] not run' % (_tips, _job_id)
        )

        # 暂停所有任务
        _ret = self.scheduler.pause()
        test_obj.assertTrue(_ret.is_success(), '%s, pause scheduler error' % _tips)
        print('\n', 'pause jobs ...')
        time.sleep(3)

        # 清空任务执行状态
        self.job_run_count.clear()

        print('\n', 'resume jobs ...')
        _ret = self.scheduler.resume()
        test_obj.assertTrue(_ret.is_success(), '%s, resume scheduler error' % _tips)
        time.sleep(3)

        # 检查运行状态
        _job_id = 'normal_run_interval'
        test_obj.assertTrue(
            self.job_run_count.get(_job_id, 0) > 0, '%s, job [%s] not run' % (_tips, _job_id)
        )
        _job_id = 'normal_run_cron'
        test_obj.assertTrue(
            self.job_run_count.get(_job_id, 0) > 0, '%s, job [%s] not run' % (_tips, _job_id)
        )

        # 暂停指定任务
        _job_id = 'normal_run_interval'
        _ret = self.scheduler.pause_job(_job_id)
        test_obj.assertTrue(
            _ret.is_success(), '%s, pause job [%s] error' % (_tips, _job_id)
        )
        _job_id = 'normal_run_cron'
        _ret = self.scheduler.pause_job(_job_id)
        test_obj.assertTrue(
            _ret.is_success(), '%s, pause job [%s] error' % (_tips, _job_id)
        )

        print('\n', 'pause interval and cron jobs ...')
        time.sleep(3)

        # 清空任务执行状态
        self.job_run_count.clear()

        # 恢复normal_run_interval
        _job_id = 'normal_run_interval'
        _ret = self.scheduler.resume_job(_job_id)
        test_obj.assertTrue(
            _ret.is_success(), '%s, resume job [%s] error' % (_tips, _job_id)
        )
        time.sleep(3)

        # 检查运行状态
        _job_id = 'normal_run_interval'
        test_obj.assertTrue(
            self.job_run_count.get(_job_id, 0) > 0, '%s, job [%s] not run' % (_tips, _job_id)
        )

        # 删除job
        _job_id = 'normal_run_interval'
        self.scheduler.remove_job(_job_id)
        test_obj.assertTrue(
            _ret.is_success(), '%s, remove job [%s] error' % (_tips, _job_id)
        )
        print('\n', 'remove interval job ...')
        time.sleep(3)

        _ret = self.scheduler.job_exists(_job_id)
        test_obj.assertTrue(
            not _ret, '%s, check job [%s] exists error' % (_tips, _job_id)
        )

        _job_id = 'normal_run_cron'
        _ret = self.scheduler.job_exists(_job_id)
        test_obj.assertTrue(
            _ret, '%s, check job [%s] exists error' % (_tips, _job_id)
        )

        # 删除所有job
        _ret = self.scheduler.remove_all_jobs()
        test_obj.assertTrue(
            _ret.is_success(), '%s, remove all jobs error' % (_tips)
        )
        _job_id = 'normal_run_cron'
        _ret = self.scheduler.job_exists(_job_id)
        test_obj.assertTrue(
            not _ret, '%s, check remove all jobs exists error' % (_tips)
        )

    def test_exception(self, test_obj: unittest.TestCase):
        # 测试异常情况
        print('\n', 'test exception ...')
        _tips = 'test exception'

        # 执行函数自行抛出异常
        _job_id = 'exception_run_now'
        _ret = self.scheduler.add_job(
            _job_id, self.job_raise_exception, args=[_job_id],
            before_func=self.job_common_before_func, callback_func=self.job_common_callback_func
        )
        test_obj.assertTrue(_ret.is_success(), '%s, [1] add job [%s] error' % (_tips, _job_id))

        print('\n', 'run exception 1 ...')
        time.sleep(0.1)

        # 传入执行函数不支持的参数
        _ret = self.scheduler.add_job(
            _job_id, self.job_raise_exception, args=[_job_id],
            kwargs={'no_exist_para': 'test'},
            before_func=self.job_common_before_func, callback_func=self.job_common_callback_func
        )
        test_obj.assertTrue(_ret.is_success(), '%s, [2] add job [%s] error' % (_tips, _job_id))

        print('\n', 'run exception 2 ...')
        time.sleep(0.1)

        # 没有回调函数情况下抛出异常
        _ret = self.scheduler.add_job(
            _job_id, self.job_raise_exception, args=[_job_id]
        )
        test_obj.assertTrue(_ret.is_success(), '%s, [3] add job [%s] error' % (_tips, _job_id))

        print('\n', 'run exception 3 ...')
        time.sleep(0.1)

        # 异常的周期任务
        self.job_run_count.clear()
        _job_id = 'exception_run_interval'
        _ret = self.scheduler.add_job(
            _job_id, self.job_raise_exception, args=[_job_id],
            job_type='interval', interval_unit='s', interval=1,
            before_func=self.job_common_before_func, callback_func=self.job_common_callback_func
        )
        test_obj.assertTrue(_ret.is_success(), '%s, interval[1] add job [%s] error' % (_tips, _job_id))

        print('\n', 'run interval exception 1 ...')
        time.sleep(3)

        # 检查执行次数
        test_obj.assertTrue(
            self.job_run_count[_job_id] > 1, '%s, interval[1] check job run [%s] error' % (_tips, _job_id)
        )

        _ret = self.scheduler.remove_all_jobs()
        test_obj.assertTrue(_ret.is_success(), '%s, interval[1] remove all jobs error' % (_tips))

        # 异常周期任务, 直接抛出异常的情况
        _job_id = 'exception_run_interval'
        _ret = self.scheduler.add_job(
            _job_id, self.job_raise_exception, args=[_job_id],
            job_type='interval', interval_unit='s', interval=1
        )
        test_obj.assertTrue(_ret.is_success(), '%s, interval[2] add job [%s] error' % (_tips, _job_id))

        print('\n', 'run interval exception 2 ...')
        time.sleep(3)

        # 检查执行次数
        test_obj.assertTrue(
            self.job_run_count[_job_id] > 1, '%s, interval[2] check job run [%s] error' % (_tips, _job_id)
        )

        _ret = self.scheduler.remove_all_jobs()
        test_obj.assertTrue(_ret.is_success(), '%s, interval[2] remove all jobs error' % (_tips))

    #############################
    # 开始和回调函数
    #############################
    def job_common_before_func(self, job_id, job_args, job_kwargs):
        """
        通用的开始函数
        """
        print('[%s]job_common_before_func: job_id[%s], job_args: %s, job_kwargs: %s' % (
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'), job_id, job_args, job_kwargs
        ))
        return True

    def job_common_callback_func(self, job_id, run_status, msg, func_ret, job_args, job_kwargs):
        """
        通用的回调函数
        """
        print('[%s]job_common_callback_func: job_id[%s], run_status[%s], func_ret[%s], msg[%s], job_args: %s, job_kwargs: %s' % (
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            job_id, run_status, func_ret, msg, job_args, job_kwargs
        ))

    #############################
    # 测试任务函数
    #############################
    def job_common_func(self, job_id: str, kv_para: str = 'no pass', ret_val: str = None) -> str:
        """
        通用任务执行函数
        """
        self.job_run_count[job_id] = self.job_run_count.get(job_id, 0) + 1
        print('[%s]job_common_func: job_id[%s], kv_para[%s]' % (
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'), job_id, kv_para
        ))
        return ret_val

    def job_raise_exception(self, job_id: str):
        """
        抛出异常的执行函数
        """
        self.job_run_count[job_id] = self.job_run_count.get(job_id, 0) + 1
        print('[%s]job_raise_exception: job_id[%s]' % (
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'), job_id
        ))
        return 1 / 0

    #############################
    # 需要实现类继承的函数
    #############################
    def _init_scheduler(self) -> SchedulerAdapter:
        """
        初始化并返回SchedulerAdapter
        """
        raise NotImplementedError()


class StandaloneSchedulerAdapterTestCase(SchedulerTestCaseFW):
    """
    单机版调度服务测试案例
    """
    #############################
    # 需要实现类继承的函数
    #############################
    def _init_scheduler(self) -> SchedulerAdapter:
        """
        初始化并返回SchedulerAdapter
        """
        return StandaloneSchedulerAdapter({
            'executor': 'thread', 'executor_pool_size': 20, 'default_job_max_instances': 1
        })


class TestStandaloneSchedulerAdapter(unittest.TestCase):
    """
    测试调度服务
    """

    def test(self):
        # 执行测试案例
        _case = StandaloneSchedulerAdapterTestCase()

        if TEST_CONTROL['init']:
            # 检查初始化任务执行情况
            _tips = 'check init job'
            _job_id = 'init_run_now'
            self.assertTrue(
                _case.job_run_count.get(_job_id, 0) > 0, '%s, job [%s] not run' % (_tips, _job_id)
            )
            _job_id = 'init_run_interval'
            self.assertTrue(
                _case.job_run_count.get(_job_id, 0) > 0, '%s, job [%s] not run' % (_tips, _job_id)
            )
            _job_id = 'init_run_cron'
            self.assertTrue(
                _case.job_run_count.get(_job_id, 0) > 0, '%s, job [%s] not run' % (_tips, _job_id)
            )

        # 执行正常测试案例
        if TEST_CONTROL['normal']:
            _case.test_normal(self)

        # 执行异常测试案例
        _case.test_exception(self)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
