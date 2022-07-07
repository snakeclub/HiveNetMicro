#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
yaml配置信息的处理

@module yaml
@file yaml.py
"""
import yaml


class YamlConfig(object):
    """
    获取yaml配置文件的通用类
    """
    def __init__(self, file: str = None, yaml_str: str = None) -> None:
        """
        装载yaml配置信息
        """
        if yaml_str is not None:
            self.yaml_str = yaml_str
        else:
            # 从文件获取配置信息
            with open(file, 'r', encoding='utf-8') as fileio:
                self.yaml_str = fileio.read()

        # 将yaml字符串转换为字典对象
        self.yaml_config = yaml.load(self.yaml_str, Loader=yaml.FullLoader)

    #############################
    # 静态工具
    #############################
    @classmethod
    def to_yaml_str(cls, data) -> str:
        """
        将Python对象转换为yaml配置字符串

        @param {Any} data - 要转换的Python对象

        @returns {str} - yaml字符串
        """
        return yaml.dump(data)
