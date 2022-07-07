#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
后台执行任务的demo

@module task_demo
@file task_demo.py
"""
import os
import sys
from logging import Logger
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.interface.platform import Platform


def main_task_no_para():
    """
    模块中定义的执行任务, 无入参
    """
    logger: Logger = Platform.Logger
    logger.info('run main_task_no_para')
