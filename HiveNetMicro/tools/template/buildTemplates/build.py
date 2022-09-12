#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
通用的构建应用脚本, 跟build.yaml放在同一个目录即可

@module build
@file build.py
"""
import os
from HiveNetMicro.tools.build_tool.build import BuildPipeline


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    _build_file = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '{$=build.yaml$}'
    ))
    _cmd_opts = {}
    _build_pipeline = BuildPipeline(
        None, _build_file, _cmd_opts, None
    )

    # 启动构建
    _build_pipeline.start_build()
