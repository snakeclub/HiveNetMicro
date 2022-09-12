#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
通过指定路径方式安装包

@module install_all_by_path
@file install_all_by_path.py
"""
import os
from HiveNetCore.utils.pyenv_tool import PythonEnvTools


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    PythonEnvTools.set_local_packages(
        'HiveNetMicro', os.path.abspath(os.path.join(
            os.path.dirname(__file__)
        ))
    )
    print('set success!')
