#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
日志管理模块
@module logger_manager
@file logger_manager.py
"""
import os
import sys
import logging
from HiveNetCore.logging_hivenet import Logger
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))


# JSON格式的日志配置文件默认字符串, 需注意disable_existing_loggers的设置, 如果为true会导致多个logger实例有被屏蔽的问题
_LOGGER_DEFAULT_JSON_STR = u'''{
    "version": 1,
    "disable_existing_loggers": false,
    "formatters": {
        "simpleFormatter": {
            "format": "[%(asctime)s.%(millisecond)s][%(levelname)s][PID:%(process)d][TID:%(thread)d][FILE:%(filename)s][FUN:%(funcName)s]%(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },

    "handlers": {
        "ConsoleHandler": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simpleFormatter",
            "stream": "ext://sys.stdout"
        },

        "FileHandler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "simpleFormatter",
            "filename": "{$log_file_path$}",
            "maxBytes": 10485760,
            "backupCount": 1000,
            "encoding": "utf8"
        }
    },

    "loggers": {
        "Console": {
            "level": "DEBUG",
            "handlers": ["ConsoleHandler"]
        },

        "File": {
            "level": "INFO",
            "handlers": ["FileHandler"],
            "propagate": "no"
        },

        "ConsoleAndFile": {
            "level": "DEBUG",
            "handlers": ["ConsoleHandler", "FileHandler"],
            "propagate": "no"
        }
    },

    "root": {
        "level": "DEBUG",
        "handlers": []
    }
}
'''


class LoggerManager(object):
    """
    日志管理模块
    """

    def __init__(self, default_log_path: str) -> None:
        """
        日志管理模块构造函数

        @param {str} default_log_path - 默认日志存放路径
        """
        self.default_log_path = default_log_path

        # 存储已创建的日志对象的字典
        self._loggers = dict()

        # 默认的日志对象
        logging.basicConfig()
        self._default_logger = logging.getLogger(__name__)

    def create_logger(self, logger_id: str, config: dict) -> Logger:
        """
        创建日志对象

        @param {str} logger_id - 日志标识
        @param {dict} config - 日志配置信息
            config_json_str {str} - 日志配置的json字符串, 如为None则直接使用_LOGGER_DEFAULT_JSON_STR
            logfile_path {str} - 日志输出文件的路径(含文件名), 为default_log_path的相对路径
            logger_name {str} - 指定使用config_json_str中的logger配置名

        @returns {Logger} - 返回日志对象
        """
        _logger = self.get_logger(logger_id)
        if _logger is None:
            # 创建日志对象
            _config_dict = {
                'conf_file_name': None,
                'logger_name': config['logger_name'],
                'logfile_path': os.path.abspath(os.path.join(self.default_log_path, config['logfile_path'])),
                'config_type': 'JSON_STR',
                'auto_create_conf': False,
                'is_create_logfile_by_day': True,
                'call_fun_level': '0'
            }
            _json_str = config.get('config_json_str', None)
            if _json_str is None:
                _json_str = _LOGGER_DEFAULT_JSON_STR
            _config_dict['json_str'] = _json_str

            _logger = Logger.create_logger_by_dict(_config_dict)

            # 添加到已创建字典
            self._loggers[logger_id] = _logger

        return _logger

    def get_logger(self, logger_id: str, none_with_default_logger: bool = False) -> Logger:
        """
        根据日志id获取已加载的日志对象

        @param {str} logger_id - 日志标识
        @param {bool} none_with_default_logger=False - 如果标识不存在, 返回默认的logger
            注: 避免没有logger的报错

        @returns {Logger} - 日志对象, 如果标识不存在返回None
        """
        _logger: Logger = self._loggers.get(logger_id, None)
        if _logger is None and none_with_default_logger:
            _logger = self._default_logger

        return _logger
