#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
所有适配器的基类
注: 用于管理依赖等非逻辑内容

@module adapter_base
@file adapter_base.py
"""
import os
import sys
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))


class AdapterBaseFw(object):
    """
    所有适配器的基类
    """

    #############################
    # 继承类应重载实现的属性
    #############################
    @property
    def adapter_type(self) -> str:
        """
        适配器类型

        @property {str} - 指定适配器类型
        """
        return ''

    @property
    def lib_dependencies(self) -> list:
        """
        当前适配器的依赖库清单
        注: 列出需要安装的特殊依赖库(HiveNetMicro未依赖的库)

        @property {list} - 依赖库清单, 可包含版本信息
            例如: ['redis', 'xxx==1.0.1']
        """
        return []

    @property
    def adapter_dependencies(self):
        """
        当前适配器的依赖适配器清单
        注: 列出动态加载的适配器清单中应装载的适配器信息清单

        @property {list} - 依赖适配器清单, 每个值为适配器信息字典, 格式如下:
            [
                {
                    'adapter_type': '',  # 必须, 依赖适配器类型
                    'base_class': '',  # 可选, 依赖适配器的基类名
                    'adapter_id': ''  # 可选, 依赖适配器的id
                },
                ...
            ]
        """
        return []
