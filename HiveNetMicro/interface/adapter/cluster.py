#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
集群功能支持适配器

@module cluster
@file cluster.py
"""
import os
import sys
import time
import threading
import traceback
from HiveNetCore.generic import CResult
from HiveNetCore.parallel import Timer
from HiveNetCore.utils.exception_tool import ExceptionTool
from HiveNetCore.utils.run_tool import AsyncTools
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.adapter_base import AdapterBaseFw
from HiveNetMicro.core.global_manager import GlobalManager
from HiveNetMicro.core.logger_manager import LoggerManager


class ClusterAdapter(AdapterBaseFw):
    """
    集群功能支持适配器
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
        return 'Cluster'

    #############################
    # 构造函数
    #############################
    def __init__(self, init_config: dict = {}, logger_id: str = None, **kwargs):
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
        @param {str} logger_id=None - 日志对象标识, 可以选择application.yaml配置中的其中一个日志对象
        """
        # 参数处理
        self._init_config = init_config
        self._kwargs = kwargs
        self._expire = self._init_config.get('expire', 10)
        self._enable_event = self._init_config.get('enable_event', False)
        self._event_each_get = self._init_config.get('event_each_get', 10)
        self._after_register = self._init_config.get('after_register', None)
        self._after_deregister = self._init_config.get('after_deregister', None)
        self._after_own_master = self._init_config.get('after_own_master', None)
        self._after_lost_master = self._init_config.get('after_lost_master', None)

        # 日志对象
        _logger_manager: LoggerManager = GlobalManager.GET_SYS_LOGGER_MANAGER()
        if _logger_manager is None:
            _logger_manager = LoggerManager('')
        self.logger = _logger_manager.get_logger(
            self._kwargs.get('logger_id', None), none_with_default_logger=True
        )

        # 内部控制变量
        self._start_heart_beat = False  # 指示是否启动心跳处理
        self._registered = False  # 指示当前服务是否已注册集群
        self._registered_lock = threading.RLock()  # 变更注册状态的线程锁
        self._master = False  # 指示当前服务是否集群主服务
        self._master_lock = threading.RLock()  # 变更集群主服务状态的线程锁

        # 集群信息
        self._app_name = self._init_config.get('app_name')
        self._namespace = self._init_config.get('namespace')
        self._sys_id = self._init_config.get('sys_id')
        self._module_id = self._init_config.get('module_id')
        self._server_id = self._init_config.get('server_id')

        # 执行实现类的初始化函数
        self._self_init()

        # 启动续约心跳的定时器
        self._heart_timer = Timer(
            self._init_config.get('heart_beat', 4), self._heart_beat_timer_func
        )
        self._heart_timer.setDaemon(True)
        self._heart_timer.start()

        # 已注册的事件处理函数, key为事件, value为处理函数
        self._event_func = {}

        # 启动指令接收检查定时器
        self._event_timer = None
        if self._enable_event:
            self._event_timer = Timer(
                self._init_config.get('event_interval', 2), self._event_timer_func
            )
            self._event_timer.setDaemon(True)
            self._event_timer.start()

    def __del__(self):
        """
        析构函数
        """
        # 关闭守护线程
        if self._event_timer is not None:
            self._event_timer.cancel()

        if self._heart_timer is not None:
            self._heart_timer.cancel()

        # 如果已注册, 取消注册
        if self._registered:
            self.deregister_cluster()

    #############################
    # 需要实现类重载的内部函数
    #############################
    def _self_init(self):
        """
        实现类自定义的初始化函数
        """
        pass

    #############################
    # 公共属性
    #############################
    @property
    def registered(self) -> bool:
        """
        判断服务是否已注册集群

        @property {bool}
        """
        return self._registered

    @property
    def master(self) -> bool:
        """
        判断服务是否集群主服务

        @property {bool}
        """
        return self._master

    #############################
    # 公共函数
    #############################
    def register_cluster(self) -> CResult:
        """
        注册集群服务信息

        @returns {CResult} - 注册结果
        """
        _result = CResult()
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger, self_log_msg='register cluster error'
        ):
            if self._start_heart_beat:
                # 已经启动心跳, 代表曾经注册成功, 通过心跳重新注册即可
                raise RuntimeError('server is registered')

            # 进行集群信息注册处理
            if not self._register_cluster():
                raise RuntimeError('server register error')

            # 注册成功, 可以启动心跳处理
            self._start_heart_beat = True

            # 抢占集群主服务
            self._try_own_master()

        return _result

    def deregister_cluster(self) -> CResult:
        """
        取消集群服务注册信息

        @returns {CResult} - 取消注册结果
        """
        _result = CResult()
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger, self_log_msg='deregister cluster error'
        ):
            if not self._start_heart_beat:
                raise RuntimeError('server is not registered')

            # 先停止心跳处理
            self._start_heart_beat = False

            # 取消集群主服务占用
            self._try_lost_master()

            # 取消集群注册信息
            if not self._deregister_cluster():
                raise RuntimeError('deregistered server failure')

        return _result

    def register_event(self, event: str, func) -> CResult:
        """
        注册事件处理函数

        @param {str} event - 事件标识
        @param {function} func - 事件处理函数, 入参固定为(上下文信息, 事件字符串, 参数对象)
            其中上下文信息为字典, 定义如下:
            {
                adapter: obj, # 当前的适配器对象
                type: 'emit',  # 事件类型, emit-点对点发送, broadcast-广播
                from: {  # 事件发起方信息
                    'namespace': '',  # 服务注册所在的命名空间, 可以实现不同环境或项目的软隔离
                    'sys_id': '',  # 系统标识(标准为5位字符)
                    'module_id': '',  # 模块标识(标准为3位字符)
                    'server_id': '',  # 服务实例序号(标准为2个字符, 建议为数字)
                }
            }

        @returns {CResult} - 处理结果
        """
        _result = CResult()
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger, self_log_msg='register event error'
        ):
            if self._event_func.get(event, None) is not None:
                raise RuntimeError('event [%s] already exists' % event)

            self._event_func[event] = func

        return _result

    def deregister_event(self, event: str) -> CResult:
        """
        取消事件处理注册

        @param {str} event - 事件

        @returns {CResult} - 处理结果
        """
        _result = CResult()
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger, self_log_msg='deregister event error'
        ):
            self._event_func.pop(event)

        return _result

    #############################
    # 内部函数
    #############################
    def _register_cluster(self) -> bool:
        """
        注册集群信息函数

        @returns {bool} - 返回注册结果
        """
        _registered = False
        self._registered_lock.acquire()
        try:
            # 注册处理
            try:
                _registered = self._register_cluster_self()
            except:
                _registered = False
                self.logger.error('cluster register error: %s' % traceback.format_exc())

            if _registered:
                # 注册成功
                if not self._registered:
                    # 从原来不成功变成成功, 执行after_register触发器
                    self._registered = True
                    if self._after_register is not None:
                        try:
                            AsyncTools.sync_run_coroutine(self._after_register(self))
                        except:
                            self.logger.error(
                                'run after cluster register trigger func error: %s' % traceback.format_exc()
                            )
            else:
                # 注册失败
                if self._registered:
                    # 从原来成功变成不成功, 执行after_deregister触发器
                    self._registered = False
                    if self._after_deregister is not None:
                        try:
                            AsyncTools.sync_run_coroutine(self._after_deregister(self))
                        except:
                            self.logger.error(
                                'run after cluster deregister trigger func error: %s' % traceback.format_exc()
                            )
        finally:
            self._registered_lock.release()

        return _registered

    def _deregister_cluster(self) -> bool:
        """
        取消注册集群信息

        @returns {bool} - 处理结果
        """
        _ret = True
        self._registered_lock.acquire()
        try:
            if not self._registered:
                return True

            try:
                _ret = self._deregister_cluster_self()
            except:
                _ret = False
                self.logger.error('cluster deregister error: %s' % traceback.format_exc())

            # 设置状态
            self._registered = False

            # 执行取消注册触发器
            if self._after_deregister is not None:
                try:
                    AsyncTools.sync_run_coroutine(self._after_deregister(self))
                except:
                    self.logger.error(
                        'run after cluster deregister trigger func error: %s' % traceback.format_exc()
                    )
        finally:
            self._registered_lock.release()

        return _ret

    def _try_own_master(self):
        """
        尝试占用集群主服务
        """
        _master = False
        self._master_lock.acquire()
        try:
            try:
                _master = self._try_own_master_self()
            except:
                _master = False
                self.logger.error('try to own cluster master error: %s' % traceback.format_exc())

            if _master:
                # 抢占成功
                if not self._master:
                    # 从非主服务变为主服务
                    self._master = True
                    if self._after_own_master is not None:
                        try:
                            AsyncTools.sync_run_coroutine(self._after_own_master(self))
                        except:
                            self.logger.error(
                                'run after cluster own master trigger func error: %s' % traceback.format_exc()
                            )
            else:
                # 抢占失败
                if self._master:
                    # 从主服务变为非主服务
                    self._master = False
                    if self._after_lost_master is not None:
                        try:
                            AsyncTools.sync_run_coroutine(self._after_lost_master(self))
                        except:
                            self.logger.error(
                                'run after cluster lost master trigger func error: %s' % traceback.format_exc()
                            )
        finally:
            self._master_lock.release()

    def _try_lost_master(self):
        """
        尝试取消集群主服务占用
        """
        self._master_lock.acquire()
        try:
            if not self._master:
                return

            try:
                self._try_lost_master_self()
            except:
                self.logger.error('try to lost cluster master error: %s' % traceback.format_exc())

            self._master = False
            if self._after_lost_master is not None:
                try:
                    AsyncTools.sync_run_coroutine(self._after_lost_master(self))
                except:
                    self.logger.error(
                        'run after cluster lost master trigger func error: %s' % traceback.format_exc()
                    )
        finally:
            self._master_lock.release()

    def _heart_beat_timer_func(self):
        """
        心跳续约Timer的执行函数
        """
        if not self._start_heart_beat:
            # 没有注册, 不进行处理
            return

        # 先尝试注册集群信息
        _registered = self._register_cluster()

        # 注册成功, 尝试获取主服务
        if _registered:
            self._try_own_master()

    def _event_deal_func(self, context: dict, event: str, paras):
        """
        通用事件处理函数

        @param {dict} context - 上下文
        @param {str} event - 事件
        @param {Any} paras - 参数
        """
        _func = self._event_func.get(event, None)
        if _func is None:
            self.logger.warning('get event[%s] but not register deal func' % event)
        else:
            try:
                AsyncTools.sync_run_coroutine(_func(context, event, paras))
            except:
                self.logger.error('run event[%s] func error: ' % traceback.format_exc())

    def _event_timer_func(self):
        """
        事件接收检查定时器
        """
        _events = self._get_events_self()
        if _events is None:
            return

        for _item in _events:
            _item[0]['adapter'] = self
            self._event_deal_func(_item[0], _item[1], _item[2])

    #############################
    # 需实现类继承实现的公共函数
    #############################
    def get_cluster_master(self, namespace: str, sys_id: str, module_id: str) -> dict:
        """
        获取集群主服务信息

        @param {str} namespace - 服务注册所在的命名空间, 可以实现不同环境或项目的软隔离
        @param {str} sys_id - 系统标识(标准为5位字符)
        @param {str} module_id - 模块标识(标准为3位字符)

        @returns {dict} - 返回信息字典
            {
                'namespace': '',  # 服务注册所在的命名空间, 可以实现不同环境或项目的软隔离
                'sys_id': '',  # 系统标识(标准为5位字符)
                'module_id': '',  # 模块标识(标准为3位字符)
                'server_id': '',  # 服务实例序号(标准为2个字符, 建议为数字)
                'app_name': '',  # 当前服务的应用名称
                'master': True  # 指示是否主服务
            }
        """
        raise NotImplementedError()

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
        raise NotImplementedError()

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
        raise NotImplementedError()

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
        raise NotImplementedError()

    #############################
    # 需实现类继承的内部函数
    #############################
    def _register_cluster_self(self) -> bool:
        """
        注册集群信息
        注: 如果集群信息已存在, 则进行集群超时时间的延续

        @returns {bool} - 处理结果
        """
        raise NotImplementedError()

    def _deregister_cluster_self(self) -> bool:
        """
        取消注册集群信息

        @returns {bool} - 处理结果
        """
        raise NotImplementedError()

    def _try_own_master_self(self) -> bool:
        """
        尝试抢占集群主服务
        注: 如果本身已经是集群主服务, 则续约超时时间

        @returns {bool} - 抢占结果
        """
        raise NotImplementedError()

    def _try_lost_master_self(self) -> bool:
        """
        尝试取消集群主服务占用

        @returns {bool} - 处理结果
        """
        raise NotImplementedError()

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
        raise NotImplementedError()
