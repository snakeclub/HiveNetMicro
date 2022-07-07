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

# 为了支持asgi启动模式, 服务初始化放在主模块中执行
# 启动参数, 支持的参数见ServerStarter的定义
_kv_opts = RunTool.get_kv_opts()
_start_config = dict()
_start_config.update(_kv_opts)
if 'visit_port' in _start_config.keys():
    _start_config['visit_port'] = int(_start_config['visit_port'])
if 'port' in _start_config.keys():
    _start_config['port'] = int(_start_config['port'])

# 初始化服务启动器
_starter = ServerStarter(_start_config)
app = GlobalManager.GET_SYS_WEB_SERVER().native_app


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 判断是否需要主动启动服务
    if _starter.wsgi_start:
        print('web server must use wsgi to start!')
    else:
        _starter.start_sever()
