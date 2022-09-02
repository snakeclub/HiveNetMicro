#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
启动微服务模块

@module start_service
@file start_service.py
"""
import os
import sys
from HiveNetCore.utils.run_tool import RunTool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetMicro.core.server import ServerStarter
from HiveNetMicro.core.global_manager import GlobalManager

# 帮助文档内容
HELP_DOC = """
HiveNetMicro start_service 命令使用帮助

start_service [help=y] [base_path=""] [logs_path=""] ...
  参数说明如下:
  help : [y/n], 指示打印命令的帮助信息
  base_path : 指定服务的启动路径(启动路径中应包含实际应用的各类目录), 为当前工作目录的相对路径, 路径含空格的情况可用双引号处理
    启动路径下所需的应用目录说明如下:
    config: 本地配置文件所在目录
    plugins: 应用自有插件所在目录, 插件配置中遇到自有插件的情况下, 会以该目录的相对路径搜索插件文件
    tasks: 启动后要执行的后台任务插件所在目录, 配置了后台任务的情况下, 会以该目录的相对路径搜索任务插件文件
    services: 应用服务插件所在目录, 会以该目录的相对路径搜索要装载的服务插件文件
  logs_path : 指定服务的日志文件路径, 为启动路径的相对路径, 如不传入将使用application.yaml的base_config.logs_path配置
  web_server : 指定要启动的web服务标识, 如不传入将使用application.yaml的base_config.default_web_server配置
    注: 如果传入空(参数送入为: web_server=)代表启动无Web Server的后台服务器
  visit_host : 外部访问的主机地址(针对设置了代理的情况), 如果传入将覆盖application.yaml的base_config.host配置
  visit_port : 外部访问的主机端口(针对设置了代理的情况), 如果传入将覆盖application.yaml的base_config.port配置
  host : 服务器监听的ip地址, 如果传入将覆盖web服务器的监听ip
  port : 服务监听的端口, 如果传入将覆盖web服务器的监听端口
  server_id : 服务实例序号(标准为2个字符, 建议为数字), 如果传入将覆盖application.yaml的base_config.server_id配置

"""

# 为了支持asgi启动模式, 服务初始化放在主模块中执行
# 启动参数, 支持的参数见ServerStarter的定义
_kv_opts = RunTool.get_kv_opts()
_is_help = _kv_opts.get('help', 'n')  # 指示是否查看帮助材料

starter = None  # 应用服务对象
app = None  # 原生app对象

if _is_help == 'y':
    # 打印帮助文档
    print(HELP_DOC)
    exit(0)
else:
    _start_config = dict()
    _start_config.update(_kv_opts)
    # 处理基础目录的参数
    _base_path = os.getcwd()
    _base_path = os.path.abspath(os.path.join(
        _base_path, _kv_opts.get('base_path', '')
    ))
    _start_config['base_path'] = _base_path

    # 处理 web_server 为None的情况
    if 'web_server' in _start_config.keys() and _start_config['web_server'] == '':
        _start_config['web_server'] = None

    # 转换参数的数据类型
    if 'visit_port' in _start_config.keys():
        _start_config['visit_port'] = int(_start_config['visit_port'])
    if 'port' in _start_config.keys():
        _start_config['port'] = int(_start_config['port'])

    # 初始化服务启动器
    starter = ServerStarter(_start_config)
    app = GlobalManager.GET_SYS_WEB_SERVER().native_app


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 判断是否需要主动启动服务
    if _is_help != 'y':
        if starter.wsgi_start:
            print('web server must use wsgi to start!')
        else:
            starter.start_sever()
