#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
类中定义的函数

@module demo_class
@file demo_class.py
"""
import os
import sys
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.interface.platform import Platform


class StaticClassService(object):
    """
    静态函数示例
    """

    @staticmethod
    def static_func_with_paras(request: dict, para1: str, para2: int, kwpara1: str = 'abc', kwpara2: int = 1):
        """
        模块中定义的函数, 所有入参

        @param {dict} request - 请求信息
        """
        logger = Platform().Logger
        logger.info('static_func_with_paras get args: para1 [%s], para2 [%d]' % (para1, para2))
        logger.info('static_func_with_paras get kwargs: kwpara1 [%s], kwpara2 [%d]' % (kwpara1, kwpara2))
        return {
            'msg': {
                'code': '00000', 'fun': 'static_func_with_paras',
                'args': [para1, para2],
                'kwargs': {'kwpara1': kwpara1, 'kwpara2': kwpara2}
            }
        }

    @classmethod
    def class_func_with_paras(cls, request: dict, para1: str, para2: int, kwpara1: str = 'abc', kwpara2: int = 1):
        """
        模块中定义的函数, 所有入参

        @param {dict} request - 请求信息
        """
        logger = Platform().Logger
        logger.info('class_func_with_paras get args: para1 [%s], para2 [%d]' % (para1, para2))
        logger.info('class_func_with_paras get kwargs: kwpara1 [%s], kwpara2 [%d]' % (kwpara1, kwpara2))
        return {
            'msg': {
                'code': '00000', 'fun': 'class_func_with_paras',
                'args': [para1, para2],
                'kwargs': {'kwpara1': kwpara1, 'kwpara2': kwpara2}
            }
        }


class ObjectClassService(object):
    """
    需初始化的类的服务定义
    """

    def __init__(self) -> None:
        self.tips = 'ObjectClassService'
        return

    @staticmethod
    def static_func_with_paras(request: dict, para1: str, para2: int, kwpara1: str = 'abc', kwpara2: int = 1):
        """
        模块中定义的函数, 所有入参

        @param {dict} request - 请求信息
        """
        logger = Platform().Logger
        logger.info('static_func_with_paras get args: para1 [%s], para2 [%d]' % (para1, para2))
        logger.info('static_func_with_paras get kwargs: kwpara1 [%s], kwpara2 [%d]' % (kwpara1, kwpara2))
        return {
            'msg': {
                'code': '00000', 'fun': 'obj.static_func_with_paras',
                'args': [para1, para2],
                'kwargs': {'kwpara1': kwpara1, 'kwpara2': kwpara2}
            }
        }

    @classmethod
    def class_func_with_paras(cls, request: dict, para1: str, para2: int, kwpara1: str = 'abc', kwpara2: int = 1):
        """
        模块中定义的函数, 所有入参

        @param {dict} request - 请求信息
        """
        logger = Platform().Logger
        logger.info('class_func_with_paras get args: para1 [%s], para2 [%d]' % (para1, para2))
        logger.info('class_func_with_paras get kwargs: kwpara1 [%s], kwpara2 [%d]' % (kwpara1, kwpara2))
        return {
            'msg': {
                'code': '00000', 'fun': 'obj.class_func_with_paras',
                'args': [para1, para2],
                'kwargs': {'kwpara1': kwpara1, 'kwpara2': kwpara2}
            }
        }

    def member_func_with_paras(self, request: dict, para1: str, para2: int, kwpara1: str = 'abc', kwpara2: int = 1):
        """
        模块中定义的函数, 所有入参

        @param {dict} request - 请求信息
        """
        logger = Platform().Logger
        logger.info('class_func_with_paras get args: para1 [%s], para2 [%d]' % (para1, para2))
        logger.info('class_func_with_paras get kwargs: kwpara1 [%s], kwpara2 [%d]' % (kwpara1, kwpara2))
        return {
            'msg': {
                'code': '00000', 'fun': 'obj.member_func_with_paras',
                'args': [para1, para2],
                'kwargs': {'kwpara1': kwpara1, 'kwpara2': kwpara2},
                'self.tips': self.tips
            }
        }
