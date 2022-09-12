#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# 初始化数据库

from HiveNetMicro.tools.utils.nosql import NoSqlTools

if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    _output_path = '{$=output_path$}'
    _adapter_id = '{$=adapter_id$}'
    _init_file = 'nosql_init/{$=init_filename$}'

    # 初始化驱动对象
    _db_driver = NoSqlTools.get_db_driver(
        _output_path, _adapter_id
    )

    # 执行处理
    NoSqlTools.init_dbs(_output_path, _init_file, _db_driver)
