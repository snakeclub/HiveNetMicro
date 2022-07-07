#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
服务器启动模块

@module init_server
@file init_server.py
"""
from copy import copy
import os
import sys
import copy
import traceback
from functools import wraps
from inspect import isawaitable
from HiveNetCore.i18n import SimpleI18N, set_global_i18n, _
from HiveNetCore.logging_hivenet import Logger
from HiveNetCore.utils.value_tool import ValueTool
from HiveNetCore.utils.run_tool import RunTool, AsyncTools
from HiveNetCore.utils.import_tool import DynamicLibManager
from async_timeout import asyncio
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.config_center import ConfigCenter
from HiveNetMicro.core.global_manager import GlobalManager
from HiveNetMicro.core.logger_manager import LoggerManager
from HiveNetMicro.interface.adapter.tracer import TracerAdapter
from HiveNetMicro.core.caller import RemoteCaller
from HiveNetMicro.core.adapter_manager import AdapterManager


class ServerStarter(object):
    """
    服务器启动模块
    """

    def __init__(self, start_config: dict):
        """
        服务器启动模块构造函数

        @param {dict} start_config - 启动参数
            base_path {str} - 应用的启动目录
            logs_path {str} - 日志文件路径, 如果传入将覆盖application.yaml的base_config.logs_path配置
            web_server {str} - 指定要启动的web服务标识, 如果传入None代表启动无Web Server的后台服务器
            visit_host {str} - 外部访问的主机地址(针对设置了代理的情况), 如果传入将覆盖application.yaml的base_config.host配置
            visit_port {int} - 外部访问的主机端口(针对设置了代理的情况), 如果传入将覆盖application.yaml的base_config.port配置
            host {str} - 服务监听的ip地址, 如果传入将覆盖web服务器的监听ip
            port {int} - 服务监听的端口, 如果传入将覆盖web服务器的监听端口
            server_id {str} - 服务实例序号(标准为2个字符, 建议为数字)
        """
        print('Server initialize ...')
        self.pid = os.getpid()  # 获取进程信息
        self.started = False  # 指示服务是否已完成启动
        self.sys_logger = None
        self.start_config = start_config  # 传入的启动参数
        # 全局的基础配置, 配置项包括
        #   base_path: 应用的启动目录
        #   config_path: 配置文件所在路径
        #   plugins_path: 自有插件文件所在路径
        #   services_path: 要装载的服务模块文件所在路径
        #   running_data_path: 运行过程中的临时数据
        #   logs_path: 日志文件所在路径
        #   is_main_process: 当前进程是否主进程
        #   env: 当前应用环境标识
        #   cluster_name: 应用所在集群名
        #   configNamespace: 配置中心的默认命名空间
        #   serviceNamespace: 注册中心的默认命名空间
        #   app_config: 应用配置信息(application.yaml的base_config配置)
        #   loggers_config: 日志配置信息(application.yaml的loggers配置)
        self.global_config = {}

        # 参数处理
        self.lib_base_path = os.path.join(os.path.dirname(__file__), os.path.pardir)  # 默认库安装目录
        self.base_path = os.path.abspath(
            start_config.get('base_path', self.lib_base_path)
        )

        # 路径处理
        self.config_path = os.path.join(self.base_path, 'config')  # 配置文件路径
        self.plugins_path = os.path.join(self.base_path, 'plugins')  # 自有插件文件路径
        self.tasks_path = os.path.join(self.base_path, 'tasks')  # 要装载的后台任务的路径
        self.services_path = os.path.join(self.base_path, 'services')  # 要装载的服务的路径
        self.running_data_path = os.path.join(self.base_path, 'running_data')  # 运行过程中的临时数据
        os.makedirs(self.running_data_path, exist_ok=True)  # 创建该临时目录
        self.global_config['base_path'] = self.base_path
        self.global_config['config_path'] = self.config_path
        self.global_config['plugins_path'] = self.plugins_path
        self.global_config['services_path'] = self.services_path
        self.global_config['running_data_path'] = self.running_data_path

        # 处理单进程控制, 获取是否主进程
        self.is_main_process = RunTool.single_process_enter(
            process_name='HiveNetMicroMainProcess', base_path=self.running_data_path,
            is_try_del_lockfile=True
        )
        self.global_config['is_main_process'] = self.is_main_process

        # 基础配置信息
        GlobalManager.SET_GLOBAL_CONFIG(self.global_config)

        # 初始化动态加载对象
        self._init_lib_loader()

        # 加载配置中心对象
        self._init_config_center()

        # 获取应用配置
        print('get application config ...')
        self.app_config = AsyncTools.sync_call(
            self.config_center.get_config_cached,
            'application.yaml', group='sys', content_type='yaml'
        )  # 应用的配置信息

        # 初始化i18n对象
        self._init_i18n()

        # 全局基础配置
        self.global_config['env'] = self.config_center.env
        self.global_config['configNamespace'] = self.config_center.namespace
        self.global_config['cluster_name'] = self.app_config['base_config'].get('cluster_name', None)
        self.global_config['app_config'] = self.app_config['base_config']  # 将应用配置放入基础配置共享字典中
        self.global_config['loggers_config'] = self.app_config['loggers']  # 将日志配置放入基础配置共享字典中

        # 端口配置的初始化
        if self.start_config.get('visit_host', None) is not None:
            self.app_config['base_config']['host'] = self.start_config['visit_host']
        if self.start_config.get('visit_port', None) is not None:
            self.app_config['base_config']['port'] = self.start_config['visit_port']
        if self.start_config.get('host', None) is not None:
            self.app_config['base_config']['host'] = self.start_config['host']
        if self.start_config.get('port', None) is not None:
            self.app_config['base_config']['port'] = self.start_config['port']
        if self.start_config.get('server_id', None) is not None:
            self.app_config['base_config']['server_id'] = self.start_config['server_id']

        # 日志路径配置
        self.logs_path = self.start_config.get(
            'logs_path', self.app_config['base_config'].get('logs_path', 'logs')
        )
        self.logs_path = os.path.join(self.base_path, self.logs_path)
        self.global_config['logs_path'] = self.logs_path

        # 加载日志对象
        self._init_logger()

        # 设置配置中心的日志对象
        self.config_center.set_logger(self.sys_logger)

        self.sys_logger.info(_('Start logging server initialize ...'))
        try:
            # 初始化插件管理模块
            self.adapter_manager = AdapterManager(self.plugins_path)
            GlobalManager.SET_SYS_ADAPTER_MANAGER(self.adapter_manager)

            # 初始化动态适配器
            self._init_dynamic_adapter()

            # 初始化注册中心
            self._init_naming()

            # 初始化opentracing
            self._init_tracer()

            # 初始化报文日志记录适配器
            self._init_inf_logging_adapters()

            # 初始化请求报文检查适配器
            self._init_inf_check_adapters()

            # 初始化远程调用对象
            self._init_remote_caller()

            # 初始化集群适配器
            self._init_cluster()

            # 初始化web服务器
            self._init_web()

            # 装载服务清单
            self._init_services()

        except:
            # 出现异常情况, 记录日志并抛出异常
            self.sys_logger.error(traceback.format_exc())
            raise

    def start_sever(self):
        """
        启动服务
        """
        if self.web_server is not None:
            # 启动Web服务
            AsyncTools.sync_run_coroutine(self.web_server.start())
        else:
            # 启动不带Web Server的后台服务
            AsyncTools.sync_run_coroutine(self._no_web_server_start())

    #############################
    # 内部函数(初始化)
    #############################
    def _init_lib_loader(self):
        """
        初始化动态库加载对象
        """
        if self.sys_logger is None:
            print('import dynamic lib loader ...')
        else:
            self.sys_logger.info('import dynamic lib loader ...')

        # 默认支持插件所在目录
        _lib_plugins_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.path.pardir, 'plugins')
        )

        # 创建公共的动态库管理模块
        self.lib_loader = DynamicLibManager(_lib_plugins_path)  # 系统动态库加载对象
        GlobalManager.SET_SYS_LIB_LOADER(self.lib_loader)
        self.services_loader = DynamicLibManager(_lib_plugins_path)  # 系统服务库加载对象
        GlobalManager.SET_SYS_SERVICES_LOADER(self.services_loader)
        self.platform_lib_loader = DynamicLibManager(_lib_plugins_path)  # 平台提供给业务逻辑模块使用的动态库加载对象
        GlobalManager.SET_PLATFORM_LIB_LOADER(self.platform_lib_loader)

    def _init_config_center(self):
        """
        初始化配置中心对象
        """
        if self.sys_logger is None:
            print('import config center ...')
        else:
            self.sys_logger.info('import config center ...')

        self.config_center = ConfigCenter(self.config_path, self.plugins_path, self.lib_loader)
        GlobalManager.SET_SYS_CONFIG_CENTER(self.config_center)
        GlobalManager.SET_ENV(self.config_center.env)

    def _init_i18n(self):
        """
        初始化全局的i18n对象
        """
        # 加载默认的多国语言文件
        _i18n_config = self.app_config['base_config'].get('i18n', {})
        self.i18n = SimpleI18N(
            lang=_i18n_config.get('lang', 'en'),
            trans_file_path=os.path.join(self.lib_base_path, 'i18n'),
            trans_file_prefix='sys', auto_loads=True
        )

        # 加载启动目录的多国语言文件
        _base_i18n_path = os.path.join(self.base_path, 'i18n')
        if os.path.exists(_base_i18n_path):
            self.i18n.load_trans_from_dir(
                _base_i18n_path, _i18n_config.get('file_prefix', 'sys'),
                append=True
            )

        # 设置为全局i18n语言
        set_global_i18n(self.i18n)

    def _init_logger(self):
        """
        初始化日志对象
        """
        print('import loggers ...')
        self.logger_manager = LoggerManager(self.logs_path)
        GlobalManager.SET_SYS_LOGGER_MANAGER(self.logger_manager)

        for _logger_id, _config in self.app_config['loggers'].items():
            if not _config.get('enable', False):
                # 不启用日志对象
                continue

            # 加载日志对象
            self.logger_manager.create_logger(
                _logger_id, _config
            )

        # 处理系统日志和服务公共日志对象
        self.sys_logger: Logger = self.logger_manager.get_logger(
            self.app_config['base_config']['sys_logger'], none_with_default_logger=True
        )
        GlobalManager.SET_SYS_LOGGER(self.sys_logger)  # 系统日志对象

        GlobalManager.SET_PLATFORM_LOGGER(
            self.logger_manager.get_logger(
                self.app_config['base_config']['service_logger'], none_with_default_logger=True
            )
        )  # 服务公共日志对象

    def _init_dynamic_adapter(self):
        """
        初始化动态适配器
        """
        self.sys_logger.info(_('Get adapters config ...'))
        self.adapters_config = AsyncTools.sync_call(
            self.config_center.get_config_cached,
            'adapters.yaml', group='sys', content_type='yaml'
        )

        # 遍历进行加载处理
        if self.adapters_config['adapters'] is None:
            # 没有动态适配器
            return

        for _name, _config in self.adapters_config['adapters'].items():
            self.sys_logger.info(_('Initialize dynamic adapter [$1] ...', _name))
            self.adapter_manager.load_adapter(
                _config['adapter_type'], _name, _config['plugin']
            )

    def _init_naming(self):
        """
        初始化注册中心
        """
        self.naming_adapter = None
        self.naming_id = self.app_config['base_config']['naming']
        if self.naming_id is not None:
            self.sys_logger.info(_('Initialize naming adapter [$1] ...', self.naming_id))

            # 处理参数, 设置命名空间和集群名
            _naming_config = self.app_config['namings'][self.naming_id]['plugin']
            if _naming_config['init_kwargs'].get('namespace', None) is None:
                self.global_config['serviceNamespace'] = '%s%s' % (
                    self.app_config['base_config'].get('namespace', 'HiveNetMicroService'),
                    '' if self.config_center.env == '' else '-%s' % self.config_center.env
                )
                _naming_config['init_kwargs']['namespace'] = self.global_config['serviceNamespace']
            else:
                self.global_config['serviceNamespace'] = _naming_config['init_kwargs']['namespace']

            if _naming_config['init_kwargs'].get('cluster_name', None) is None:
                _naming_config['init_kwargs']['cluster_name'] = self.global_config['cluster_name']

            self.naming_adapter = self.lib_loader.load_by_config(
                _naming_config, self.plugins_path
            )

        GlobalManager.SET_SYS_NAMING(self.naming_adapter)

    def _init_tracer(self):
        """
        初始化opentracing
        """
        self.tracer = None
        if self.app_config['base_config']['tracer'] is None:
            # 默认的调用链对象, 不实际处理
            self.sys_logger.info(_('Initialize tracer adapter [$1] ...', 'default'))
            self.tracer = TracerAdapter({})
        else:
            # 适配器支持的调用链对象
            self.sys_logger.info(_('Initialize tracer adapter [$1] ...', self.app_config['base_config']['tracer']))
            _tracer_config = self.app_config['opentracings'][self.app_config['base_config']['tracer']]
            self.tracer = self.lib_loader.load_by_config(
                _tracer_config['plugin'], self.plugins_path
            )

        GlobalManager.SET_SYS_TRACER(self.tracer)

    def _init_inf_logging_adapters(self):
        """
        初始化报文日志记录适配器
        """
        self.sys_logger.info(_('Initialize interface logging adapters ...'))
        _inf_loggings = self.app_config.get('inf_loggings', None)
        if _inf_loggings is not None:
            for _adapter_id, _config in _inf_loggings.items():
                self.adapter_manager.load_adapter(
                    'inf_logging', _adapter_id, _config['plugin']
                )

    def _init_inf_check_adapters(self):
        """
        初始化请求报文检查适配器
        """
        self.sys_logger.info(_('Initialize interface check adapters ...'))
        _inf_checks = self.app_config.get('inf_checks', None)
        if _inf_checks is not None:
            for _adapter_id, _config in _inf_checks.items():
                self.adapter_manager.load_adapter(
                    'inf_check', _adapter_id, _config['plugin']
                )

    def _init_remote_caller(self):
        """
        初始化远程调用对象
        """
        self.sys_logger.info(_('Initialize remote caller ...'))
        self.remote_caller = RemoteCaller(
            self.plugins_path, self.lib_loader, self.adapter_manager,
            global_config=self.global_config,
            namings_config=self.global_config.get('app_config', {}).get('namings', {}),
            default_naming_adapter=self.naming_adapter
        )
        GlobalManager.SET_SYS_REMOTE_CALLER(self.remote_caller)

        # 初始化请求报文格式转换插件
        self.sys_logger.info(_('Initialize caller formaters ...'))
        _caller_formaters = self.app_config['base_config'].get('caller_formaters', None)
        if _caller_formaters is not None:
            for _caller_formater_id in _caller_formaters:
                self.adapter_manager.load_adapter(
                    'formater_caller', _caller_formater_id,
                    self.app_config['caller_formaters'][_caller_formater_id]['plugin']
                )

        # 遍历添加远程调用服务配置
        self.sys_logger.info(_('Get remote services config ...'))
        self.remote_services_config = AsyncTools.sync_call(
            self.config_center.get_config_cached,
            'remoteServices.yaml', group='sys', content_type='yaml'
        )

        # 执行参数配置的初始化(复制通用配置)
        for _name in self.remote_services_config['services'].keys():
            _config = self.remote_services_config['services'][_name]
            _common_config = _config.get('common_config', None)
            if _common_config is not None:
                _config_list = list()
                # 按顺序添加到合并列表
                for _config_id in _common_config:
                    _config_list.append(
                        copy.deepcopy(self.remote_services_config['common_config'][_config_id])
                    )
                # 将当前配置放到最后一个合并列表并开始合并
                _config_list.append(_config)
                self.remote_services_config['services'][_name] = ValueTool.merge_dict(*_config_list)

        # 装载远程调用服务配置
        for _name, _config in self.remote_services_config['services'].items():
            self.remote_caller.add_remote_service(
                _name, _config
            )

    def _init_web(self):
        """
        初始化web服务器
        """
        # web服务器的配置
        _web_server_id = self.start_config.get('web_server', self.app_config['base_config']['default_web_server'])
        if _web_server_id is None:
            # 启动无Web服务的后台应用
            self.sys_logger.info(_('Initialize with no web server ...'))
            self.wsgi_start = False
            self.web_server = None
            GlobalManager.SET_SYS_WEB_SERVER(self.web_server)
            return

        # 初始化Web服务
        _web_server_config = self.app_config['web_servers'][_web_server_id]
        self.wsgi_start = _web_server_config.get('wsgi_start', False)
        _web_server_config['init_config']['use_asgi'] = self.wsgi_start

        # 处理监听地址的配置
        _host = _web_server_config.get('host', None)
        _port = _web_server_config.get('port', None)
        if self.start_config.get('host', None) is not None:
            _host = self.start_config['host']
        if self.start_config.get('port', None) is not None:
            _port = self.start_config['port']

        if _host is None:
            _host = self.app_config['base_config']['host']
        if _port is None:
            _port = self.app_config['base_config']['port']

        # 初始化服务报文格式转换插件
        self.sys_logger.info(_('Initialize server formaters ...'))
        for _server_formater_id in _web_server_config['server_formaters']:
            self.adapter_manager.load_adapter(
                'formater_server', _server_formater_id,
                self.app_config['server_formaters'][_server_formater_id]['plugin']
            )

        # 初始化Web服务器
        self.sys_logger.info(_('Initialize web server [$1] ...', _web_server_id))
        _web_server_class = self.lib_loader.load_by_config(
            _web_server_config['plugin'], self.plugins_path
        )
        self.web_server = _web_server_class(
            _web_server_id, self.app_config['base_config']['app_name'], _host, _port, _web_server_config['init_config'],
            logger_id=_web_server_config['logger'], formaters=_web_server_config['server_formaters'],
            after_server_start=self._after_server_start, before_server_stop=self._before_server_stop
        )
        GlobalManager.SET_SYS_WEB_SERVER(self.web_server)

    def _init_services(self):
        """
        装载服务清单
        """
        self.sys_logger.info(_('Get services config ...'))
        self.services_config = AsyncTools.sync_call(
            self.config_center.get_config_cached,
            'services.yaml', group='sys', content_type='yaml'
        )

        # 执行参数配置的初始化(复制通用配置)
        for _name in self.services_config['services'].keys():
            _config = self.services_config['services'][_name]
            _config['service_name'] = _name
            _common_config = _config.get('common_config', None)
            if _common_config is not None:
                _config_list = list()
                # 按顺序添加到合并列表
                for _config_id in _common_config:
                    _config_list.append(
                        copy.deepcopy(self.services_config['common_config'][_config_id])
                    )
                # 将当前配置放到最后一个合并列表并开始合并
                _config_list.append(_config)
                self.services_config['services'][_name] = ValueTool.merge_dict(*_config_list)

        for _name, _config in self.services_config['services'].items():
            # 遍历初始化服务实例对象并添加路由
            self.sys_logger.info(_('Initialize service [$1] ...', _name))
            _service_func = self.lib_loader.load_by_config(_config['plugin'], self.services_path, force_self_lib=True)

            # 添加报文处理的修饰符
            _service_func = self.get_wrapped_inf_deal(_service_func, service_config=_config)

            if _config.get('enable_tracer', False):
                # 开启调用链, 在函数外面添加修饰符
                _trace_options = _config.get('trace_options', None)
                if _trace_options is None:
                    _trace_options = {}

                # 处理调用链操作名
                if _trace_options.get('operation_name_para', None) is None:
                    _trace_options['operation_name_para'] = 'const:%s' % _name

                _service_func = self.tracer.get_wrapped_request_func_async(
                    _service_func, _trace_options
                )

            if _config.get('enable_service', True) and self.web_server is not None:
                # 开启服务(存在Web服务器的情况)
                AsyncTools.sync_run_coroutine(
                    self.web_server.add_service(
                        _service_func, _config['uri'], _config
                    )
                )

            # 添加本地访问支持
            if _config.get('allow_local_call', False):
                _service_naming_config = _config.get('naming', {})
                _service_name = _service_naming_config.get('service_name', None)
                if _service_name is None:
                    _service_name = _name

                self.remote_caller.add_local_service(
                    _name, _service_func, service_config={
                        'service_name': _service_name,
                        'group_name': _service_naming_config.get('group_name', None),
                        'protocol': _service_naming_config.get('protocol', None),
                        'uri': _service_naming_config.get('uri', None),
                        'metadata': _service_naming_config.get('metadata', None)
                    }
                )

    def _init_cluster(self):
        """
        装载集群适配器
        """
        self.cluster = None
        _cluster_id = self.app_config['base_config'].get('cluster_adapter', None)
        if _cluster_id is not None:
            self.sys_logger.info(_('Initialize cluster adapter ...'))

            # 初始化参数设置
            _cluster_config = copy.deepcopy(self.app_config['clusters'][_cluster_id])
            _init_config = _cluster_config['plugin']['init_args'][0]
            _init_config['namespace'] = self.global_config['configNamespace']
            _init_config['sys_id'] = self.app_config['base_config']['sys_id']
            _init_config['module_id'] = self.app_config['base_config']['module_id']
            _init_config['server_id'] = self.app_config['base_config']['server_id']
            _init_config['app_name'] = self.app_config['base_config']['app_name']

            # 执行事件参数设置
            for _task_type in ('after_register', 'after_deregister', 'after_own_master', 'after_lost_master'):
                if _init_config.get(_task_type, None) is not None:
                    # 加载任务
                    _task_config = self.app_config['tasks'][_init_config[_task_type]]

                    # 获取执行函数
                    _func = self.lib_loader.load_by_config(
                        _task_config['plugin'], self_lib_path=self.tasks_path, force_self_lib=True
                    )

                    _init_config[_task_type] = _func

            self.cluster = self.lib_loader.load_by_config(
                _cluster_config['plugin'], self_lib_path=self.plugins_path
            )

        # 设置集群对象
        GlobalManager.SET_SYS_CLUSTER(self.cluster)

    #############################
    # 服务启动和关闭的相关函数
    #############################
    async def _after_server_start(self, *args, **kwargs):
        """
        在web服务启动完成后执行的动作
        """
        if self.web_server is not None:
            # 向注册中心注册服务
            await self._register_services(*args, **kwargs)

        if self.cluster is not None:
            # 注册集群
            _ret = self.cluster.register_cluster()
            if _ret.is_success():
                self.sys_logger.info(_(
                    'Register cluster success: $1', '[namespace:%s] [sys_id:%s] [module_id:%s] [server_id:%s] [master:%s]' % (
                        self.cluster._namespace, self.cluster._sys_id, self.cluster._module_id,
                        self.cluster._server_id, str(self.cluster.master)
                    )
                ))
            else:
                self.sys_logger.error(_('Register cluster error: $1', str(_ret)))
                raise RuntimeError(_ret.msg)

        # 服务状态更新
        self.started = True

        # 执行后台任务
        _task_id = self.app_config['base_config'].get('after_server_start', None)
        if _task_id is not None:
            await self._run_task('after_server_start', _task_id)

    async def _before_server_stop(self, *args, **kwargs):
        """
        在web服务关闭前执行的动作
        """
        # 执行后台任务
        _task_id = self.app_config['base_config'].get('before_server_stop', None)
        if _task_id is not None:
            await self._run_task('before_server_stop', _task_id)

        # 服务状态更新
        self.started = False

        if self.cluster is not None:
            # 取消注册集群服务
            _ret = self.cluster.deregister_cluster()
            if _ret.is_success():
                self.sys_logger.info(_(
                    'Deregister cluster success: $1', '[namespace:%s] [sys_id:%s] [module_id:%s] [server_id:%s]' % (
                        self.cluster._namespace, self.cluster._sys_id, self.cluster._module_id,
                        self.cluster._server_id
                    )
                ))
            else:
                self.sys_logger.error(_('Deregister cluster error: $1', str(_ret)))

        if self.web_server is not None:
            # 向注册中心取消所有服务
            await self._deregister_services(*args, **kwargs)

        # 删除tracer适配器, 实际执行的是关闭tracer
        del self.tracer

    async def _register_services(self, *args, **kwargs):
        """
        向注册中心注册所有服务
        """
        if not self.is_main_process:
            self.sys_logger.info(_('Server process[$1] is not the main process, no register to naming server', self.pid))
            return

        if self.naming_adapter is None:
            self.sys_logger.info(_('There is no naming adapter, no register to naming server'))
            return

        # 将启动后的服务进行注册
        for _name, _config in self.services_config['services'].items():
            try:
                if not _config.get('enable_service', True):
                    self.sys_logger.info(_('Service [$1] not enable, no register to naming server', _name))
                    continue

                _naming_config = _config.get('naming', None)
                if _naming_config is None:
                    self.sys_logger.info(_('Service [$1] with no naming config, no register to naming server', _name))
                    continue

                # 处理metadata中的uri
                _metadata = _naming_config.get('metadata', None)
                if _metadata is not None and _metadata.get('uri', '') == '':
                    _metadata['uri'] = _config['uri']

                self.sys_logger.info(_('Register [$1] to naming server ...', _name))
                await AsyncTools.async_run_coroutine(
                    self.naming_adapter.add_instance(
                        _naming_config.get('service_name', _name), self.app_config['base_config']['host'],
                        self.app_config['base_config']['port'],
                        group_name=_naming_config.get('group_name', None),
                        metadata=_metadata,
                        **_naming_config['naming_config'].get(self.naming_id, {})
                    )
                )
            except:
                self.sys_logger.error(_(
                    'Register [$1] to naming server error: $2', _name, traceback.format_exc()
                ))
                raise

    async def _deregister_services(self, *args, **kwargs):
        """
        向注册中心取消所有服务
        """
        if not self.is_main_process:
            self.sys_logger.info(_('Server process[$1] is not the main process, no need to unregister naming server', self.pid))
            return

        if self.naming_adapter is None:
            return

        # 取消服务在注册中心的注册信息
        for _name, _config in self.services_config['services'].items():
            try:
                if not _config.get('enable_service', True):
                    continue

                _naming_config = _config.get('naming', None)
                if _naming_config is None:
                    continue

                self.sys_logger.info(_('Deregister [$1] from naming server ...', _name))
                await AsyncTools.async_run_coroutine(
                    self.naming_adapter.remove_instance(
                        _naming_config.get('service_name', _name),
                        group_name=_naming_config.get('group_name', None),
                        ip=self.app_config['base_config']['host'], port=self.app_config['base_config']['port']
                    )
                )
            except:
                self.sys_logger.error(_(
                    'Deregister [$1] from naming server error: $2',
                    _name, traceback.format_exc()
                ))

    async def _no_web_server_start(self):
        """
        无 Web Server 情况的后台应用启动函数(阻断交易)
        """
        # 执行after_server_start
        self._after_server_start()

        # 循环阻断交易并等待ctrl+c中断
        while True:
            try:
                await asyncio.sleep(1.0)
            except KeyboardInterrupt:
                # 获取到ctrl+c
                break
            except:
                # 出现其他已将
                self.sys_logger.error('No web server start get excepiton: %s' % traceback.format_exc())
                break

        # 执行before_server_stop
        self._before_server_stop()

    async def _run_task(self, task_type: str, task_id: str):
        """
        执行后台任务

        @param {str} task_type - 任务类型
        @param {str} task_id - 任务标识
        """
        self.sys_logger.info(_('Run [$1] task [$2] ...', task_type, task_id))
        try:
            _task_config = self.app_config['tasks'][task_id]

            # 获取执行参数
            _args = _task_config.get('args', None)
            if _args is None:
                _args = []

            _kwargs = _task_config.get('kwargs', None)
            if _kwargs is None:
                _kwargs = {}

            # 获取执行函数
            _func = self.lib_loader.load_by_config(
                _task_config['plugin'], self_lib_path=self.tasks_path, force_self_lib=True
            )

            # 执行
            await AsyncTools.async_run_coroutine(_func(*_args, **_kwargs))
        except:
            self.sys_logger.error(
                _('Run [$1] task [$2] error: [$3]', task_type, task_id, traceback.format_exc())
            )

    #############################
    # 服务标准报文处理的修饰符
    #############################
    def wrap_inf_deal(self, service_config: dict = {}):
        """
        请求报文处理的修饰符
        注: 支持修饰同步及异步函数, 但修饰后需按异步函数执行

        @param {dict} service_config={} - 接口对应的服务配置
        """
        def decorator(f):
            @wraps(f)
            async def decorated_function(*args, **kwargs):
                _std_request = args[0]

                # 进行报文检查
                _inf_check_adapter = self.adapter_manager.get_adapter(
                    'inf_check', service_config.get('inf_check', None)
                )
                if _inf_check_adapter is not None:
                    _check_resp = _inf_check_adapter.check(_std_request, service_config=service_config)
                else:
                    _check_resp = None

                if _check_resp is None:
                    # 检查通过, 执行请求处理函数
                    _response = f(*args, **kwargs)
                    if isawaitable(_response):
                        _response = await _response
                else:
                    # 检查不通过, 直接返回检查结果
                    _response = _check_resp

                # 对处理结果进行标准化处理
                _server_formater = self.adapter_manager.get_adapter(
                    'formater_server', service_config.get('formater', None)
                )
                if _server_formater is not None:
                    _response = _server_formater.format_response(
                        _std_request, _response, is_std_request=True
                    )

                return _response
            return decorated_function
        return decorator

    def get_wrapped_inf_deal(self, func, service_config: dict = {}):
        """
        获取包裹了请求报文处理修饰符的函数对象
        注: 支持修饰同步及异步函数, 但修饰后函数需按异步函数执行

        @param {function} func - 需要处理的函数对象
        @param {dict} service_config={} - 接口对应的服务配置

        @returns {function} - 包裹请求报文处理修饰符后的函数对象
        """
        # 包裹修饰函数
        @self.wrap_inf_deal(service_config=service_config)
        async def wraped_func(*args, **kwargs):
            _resp = func(*args, **kwargs)
            if isawaitable(_resp):
                _resp = await _resp
            return _resp

        return wraped_func
