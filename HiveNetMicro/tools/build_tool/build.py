#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
应用构建工具

@module build
@file build.py
"""
import os
import copy
from HiveNetCore.utils.run_tool import RunTool
from HiveNetBuildTool.build import BuildPipeline


class HiveNetMicroBuildPipeline(BuildPipeline):
    """
    微服务的构建管道
    """

    def __init__(self, build_file: str = None, cmd_opts: dict = {}):
        """
        初始化微服务的构建管道

        @param {str} build_file=None - 要处理的构建文件(当前工作目录的相对路径), 不传则自动获取当前工作目录下的build.yaml文件
        @param {dict} cmd_opts - 命令行参数
            source: str, 指定构建源码目录(当前工作目录的相对路径), 不传则获取构建文件配置中的路径(build.yaml文件的相对路径), 如果为None则为build.yaml所在的目录
            output: str, 构建结果输出目录(当前工作目录的相对路径), 不传则获取构建文件配置中的路径(build.yaml文件的相对路径), 如果为None则为build.yaml所在的目录
            type: str, 构建类型, 不传则获取构建文件配置中的配置
        """
        _base_path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(_base_path, build_file=build_file, cmd_opts=cmd_opts)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    _opts = RunTool.get_kv_opts()  # 获取命令行参数

    if _opts.get('file', None) is None:
        _build_file = os.path.abspath(os.path.join(os.getcwd(), 'build.yaml'))
    else:
        _build_file = os.path.abspath(os.path.join(os.getcwd(), _opts['file']))

    # 初始化构建管道对象
    _pipeline = HiveNetMicroBuildPipeline(
        build_file=_build_file, cmd_opts=_opts
    )

    # 启动构建
    _pipeline.start_build()
