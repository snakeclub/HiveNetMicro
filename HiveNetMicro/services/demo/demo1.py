#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
示例1

@module demo1
@file demo1.py
"""
import os
import sys
import json
from logging import Logger
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.interface.platform import Platform


def main_func_no_para(request: dict):
    """
    模块中定义的函数, 无入参

    @param {dict} request - 请求信息
    """
    logger: Logger = Platform.Logger
    logger.info('main_func_no_para get request: %s' % json.dumps(request, ensure_ascii=False, indent=2))
    return {'msg': {'code': '00000', 'msg': '完成'}}
