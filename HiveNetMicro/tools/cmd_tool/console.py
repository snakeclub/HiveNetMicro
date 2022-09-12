#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
微服务框架命令行工具

@module cmd_tool
@file cmd_tool.py
"""
import sys
import os
from HiveNetCore.utils.file_tool import FileTool
from HiveNetConsole import ConsoleServer
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)))


def main(**kwargs):
    ConsoleServer.console_main(
        execute_file_path=os.path.realpath(FileTool.get_file_path(__file__)),
        **kwargs
    )


if __name__ == '__main__':
    main()
