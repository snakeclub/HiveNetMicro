#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
http请求测试工具
@module http_test
@file http_test.py
"""
import os
import json
from HiveNetCore.yaml import SimpleYaml
from HiveNetCore.utils.run_tool import RunTool
from HiveNetWebUtils.client import HttpClient


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    _kv_opts = RunTool.get_kv_opts()
    _config = {}
    if _kv_opts.get('config_file', None) is not None:
        _config = SimpleYaml(
            os.path.join(os.getcwd(), _kv_opts['config_file']), encoding='utf-8'
        ).yaml_dict

    # 处理参数
    _conn_config = dict(_config.get('conn_config', {}))
    if _kv_opts.get('protocol', None) is not None:
        _conn_config['protocol'] = _kv_opts['protocol']
    if _kv_opts.get('host', None) is not None:
        _conn_config['host'] = _kv_opts['host']
    if _kv_opts.get('port', None) is not None:
        _conn_config['port'] = int(_kv_opts['port'])

    _headers = dict(_config.get('headers', {}))
    if _kv_opts.get('headers', None) is not None:
        _headers.update(json.loads(_kv_opts['headers']))

    _request = None if _config.get('std_request', None) is None else dict(_config['std_request'])
    if _kv_opts.get('request', None) is not None:
        _opts_json = json.loads(_kv_opts['request'])
        if _request is None:
            _request = json.loads(_opts_json)
        else:
            _request.update(_opts_json)

    # 初始化客户端
    _client = HttpClient(_conn_config)

    # 执行调用
    _resp = _client.call(
        service_uri=_kv_opts.get('url', ''), request=_request,
        headers=_headers,
        method=_kv_opts.get('method', 'GET'), debug=True
    )
