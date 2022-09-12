#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
主模块函数(标准接口)

@module demo_main
@file demo_main.py
"""
import os
import sys
from logging import Logger
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.global_manager import GlobalManager
from HiveNetMicro.interface.platform import Platform


def main_func_no_para(request: dict):
    """
    模块中定义的函数, 无入参

    @param {dict} request - 请求信息
    """
    return {'msg': {
            'head': {'errCode': '00000', 'errMsg': 'Success'},
            'body': {'fun': 'std.main_func_no_para'}
        }}


async def main_func_with_args(request: dict, para1: str, para2: int):
    """
    模块中定义的函数, 固定位置入参

    @param {dict} request - 请求信息
    """
    logger: Logger = Platform().Logger
    logger.info('std.main_func_with_args get args: para1 [%s], para2 [%d]' % (para1, para2))
    return {'msg': {
            'head': {'errCode': '00000', 'errMsg': 'Success'},
            'body': {'fun': 'std.main_func_with_args', 'args': [para1, para2]}
        }}


def main_func_with_kwargs(request: dict, kwpara1: str = 'abc', kwpara2: int = 1):
    """
    模块中定义的函数, kw入参

    @param {dict} request - 请求信息
    """
    logger: Logger = Platform().Logger
    logger.info('std.main_func_with_kwargs get kwargs: kwpara1 [%s], kwpara2 [%d]' % (kwpara1, kwpara2))
    return {'msg': {
            'head': {'errCode': '00000', 'errMsg': 'Success'},
            'body': {'fun': 'std.main_func_with_kwargs', 'kwargs': {'kwpara1': kwpara1, 'kwpara2': kwpara2}}
        }}


def main_func_with_paras(request: dict, para1: str, para2: int, kwpara1: str = 'abc', kwpara2: int = 1):
    """
    模块中定义的函数, 所有入参

    @param {dict} request - 请求信息
    """
    logger: Logger = Platform().Logger
    logger.info('std.main_func_with_paras get args: para1 [%s], para2 [%d]' % (para1, para2))
    logger.info('std.main_func_with_paras get kwargs: kwpara1 [%s], kwpara2 [%d]' % (kwpara1, kwpara2))
    return {'msg': {
            'head': {'errCode': '00000', 'errMsg': 'Success'},
            'body': {'fun': 'std.main_func_with_paras', 'args': [para1, para2], 'kwargs': {'kwpara1': kwpara1, 'kwpara2': kwpara2}}
        }}


async def main_func_remote_call(request: dict, para1: str):
    """
    内部执行远程调用的函数
    异步模式远程调用

    @param {dict} request - 请求信息
    @param {str} para1 - 入参
    """
    _platform = Platform()
    _logger: Logger = _platform.Logger
    _logger.info('std.main_func_remote_call get args: para1 [%s]' % para1)

    # 执行远程调用
    _tracer_adpater = GlobalManager.GET_SYS_TRACER()
    if _tracer_adpater is not None:
        _tracer_adpater.set_baggage('baggage_test_add', 'test')

    _caller = _platform.Caller
    _resp = await _caller.async_call(
        'stdLocalDemoMainFuncWithArgs',
        {
            'msg': {'msg_body': 'test stdLocalDemoMainFuncWithArgs with caller'}
        }, para1, 210
    )
    if _resp['network']['status'] != 200:
        raise RuntimeError(str(_resp))

    _logger.info('std.main_func_remote_call: async_call success')

    _resp = await _caller.async_call_with_settings(
        'stdLocalDemoMainFuncWithArgs',
        {
            'local_call_first': False
        },
        {
            'msg': {'msg_body': 'test stdLocalDemoMainFuncWithArgs with caller'}
        }, para1, 211
    )
    if _resp['network']['status'] != 200:
        raise RuntimeError(str(_resp))

    _logger.info('std.main_func_remote_call: async_call_with_settings success')

    # _resp = _caller.call(
    #     'localDemoMainFuncWithArgs',
    #     {
    #         'msg': {'msg_body': 'test localDemoMainFuncWithArgs with caller'}
    #     }, para1, 212
    # )
    # if _resp['network']['status'] != 200:
    #     raise RuntimeError(str(_resp))

    # _logger.info('main_func_remote_call: call success')

    return {'msg': {
            'head': {'errCode': '00000', 'errMsg': 'Success'},
            'body': {'fun': 'std.main_func_remote_call', 'args': [para1]}
        }}
