#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
NoSql数据库的工具处理模块

@module nosql_db
@file nosql_db.py
"""
import os
import sys
from typing import OrderedDict
import xlrd
import json
from HiveNetCore.formula import FormulaTool, StructFormulaKeywordPara
from HiveNetCore.yaml import SimpleYaml, EnumYamlObjType
from HiveNetCore.utils.file_tool import FileTool
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetNoSql.base.driver_fw import NosqlDriverFW
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.adapter_manager import AdapterManager


#############################
# 公共参数
#############################
EXCEL_ENTITY_LIST_SHEET_NAME = 'entity_list'  # Excel文件的实体清单sheet页签名

# Excel文件的实体清单标题名映射字典
EXCEL_ENTITY_LIST_HEADER_NAME_MAPPING = {
    '微服务名': 'micro_name',
    '微服务标识': 'micro_id',
    '所属模块': 'module',
    '实体名': 'entity_name',
    '实体描述': 'entity_desc'
}

# Excel文件的实体定义页标题名映射字典
EXCEL_ENTITY_HEADER_NAME_MAPPING = {
    '序号': 'order',
    '属性': 'property',
    '属性描述': 'property_desc',
    '数据类型': 'data_type',
    '数据长度': 'data_len',
    '默认值': 'default',
    '是否可空': 'nullable',
    '是否扩展': 'is_extend',
    '普通索引标识清单': 'normal_index_list',
    '唯一索引标识清单': 'unique_index_list'
}

EXCEL_DATA_PRE_DEAL_SHEET_NAME = 'pre_deal'  # Excel数据初始化预处理sheet页签名

# Excel数据初始化预处理标题名映射字典
EXCEL_DATA_PRE_DEAL_HEADER_NAME_MAPPING = {
    '操作集合': 'collection',
    '操作类型': 'deal_type',
    '过滤条件': 'filter',
    '更新信息': 'update',
    '操作说明': 'remark'
}


class NoSqlDbTools(object):
    """
    NoSQL数据库的工具处理类
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, adapter_manager: AdapterManager) -> None:
        """
        NoSQL数据库的工具处理类
        """
        # 参数管理
        self.app_base_path = os.getcwd()  # 应用目录
        self.nosql_adapter_id = None  # nosql数据库驱动对象的配置id
        self.nosql_driver: NosqlDriverFW = None  # nosql数据库驱动对象
        self.nosql_adapter_list = []  # nosql数据库驱动对象的清单
        self.adapter_config: SimpleYaml = None  # 适配器配置文件对象

        # 插件管理对象
        self.adapter_manager = adapter_manager

        # 尝试初始化数据库驱动对象, 失败不抛出异常
        try:
            self._init_nosql_driver()
        except:
            self.nosql_driver = None

    #############################
    # 公共函数
    #############################
    def set_base_path(self, base_path: str):
        """
        设置应用目录

        @param {str} base_path - 应用目录
        """
        # 设置基础目录
        _base_path = os.path.abspath(os.path.join(os.getcwd(), base_path))
        if os.path.exists(_base_path):
            self.app_base_path = _base_path
        else:
            raise FileNotFoundError('path [%s] not exists!' % _base_path)

        # 尝试初始化数据库驱动对象
        try:
            self._init_nosql_driver()
        except:
            self.nosql_driver = None
            self.nosql_adapter_list = []
            raise

    def set_nosql_driver(self, adapter_id: str = None):
        """
        设置NoSql驱动对象

        @param {str} adapter_id=None - adapters.yaml上配置的NoSqlDb适配器对象
            注: 如果不传则代表获取第一个adapter_type为NoSqlDb的数据库配置
        """
        self._init_nosql_driver(adapter_id=adapter_id)

    #############################
    # excel转换
    #############################

    def collection_excel_to_yaml(self, excel_file: str, yaml_file: str = None, append: bool = True,
            index_only: bool = True, db_name=None, collection_name=None, db_name_mapping: dict = {}):
        """
        集合(表)设计Excel文件转换为Yaml初始化文件

        @param {str} excel_file - 集合(表)设计Excel文件, 为base_path的相对路径
        @param {str} yaml_file=None - 要保存到的Yaml初始化文件, 为base_path的相对路径
            注: 如果yaml_file为None, 代表只是形成SimpleYaml对象并返回
        @param {bool} append=True - 指定是否追加模式, 为False代表覆盖文件
        @param {bool} index_only=True - 是否仅用于索引, 不创建
        @param {str|list} db_name=None - 指定要处理的数据库名(或数据库列表), 为转换前的数据库名
        @param {str|list} collection_name=None - 指定要处理的集合名(或集合列表)
        @param {dict} db_name_mapping={} - 数据库的映射字典
            key为转换前的数据库名, value为转换后的数据库名
            注: 可以将key指定为*, 代表将所有匹配不到的的数据库名都转换为该key为*的数据库名

        @returns {None|SimpleYaml} - 如果指定保存文件返回None, 否则返回SimpleYaml对象
        """
        # 参数处理
        _excel_file = os.path.abspath(os.path.join(self.app_base_path, excel_file))
        _yaml_file = None if yaml_file is None else os.path.abspath(os.path.join(self.app_base_path, yaml_file))

        # 自动索引名的参数
        _formula_string_para = StructFormulaKeywordPara()
        _formula_string_para.is_string = True  # 声明是字符串参数
        _formula_string_para.has_sub_formula = False  # 声明公式中不会有子公式
        _formula_keywords = {'auto_name': [
            ['{$auto_name=', [], []], ['$}', [], []], _formula_string_para
        ]}  # 解析{$auto_name=xx$}的公式

        # 要生成的yaml对象
        _yaml = SimpleYaml('init_db:\ninit_collections:\n', obj_type=EnumYamlObjType.String, encoding='utf-8')

        # 获取清单
        _wb: xlrd.book.Book = xlrd.open_workbook(_excel_file)
        _list_name_index = self._get_name_index_by_sheet_header(
            _wb, EXCEL_ENTITY_LIST_SHEET_NAME, name_mapping=EXCEL_ENTITY_LIST_HEADER_NAME_MAPPING
        )  # 获取列表名字索引

        # 遍历清单进行处理
        _list_sheet = _wb.sheet_by_name(EXCEL_ENTITY_LIST_SHEET_NAME)
        for _list_row_index in range(1, _list_sheet.nrows):
            _list_row = _list_sheet.row(_list_row_index)  # 行数据
            _micro_id = _list_row[_list_name_index['micro_id'] - 1].value
            _entity_name = _list_row[_list_name_index['entity_name'] - 1].value

            if _micro_id == '':
                continue

            # 判断是否在处理范围
            if db_name is not None:
                if type(db_name) in (list, tuple) and _micro_id not in db_name:
                    continue
                elif _micro_id != db_name:
                    continue

            if collection_name is not None:
                if type(collection_name) in (list, tuple) and _entity_name not in collection_name:
                    continue
                elif _entity_name != collection_name:
                    continue

            # 处理数据库初始化信息
            _real_db_name = db_name_mapping.get(_micro_id, None)
            if _real_db_name is None:
                if db_name_mapping.get('*', None) is not None:
                    _real_db_name = db_name_mapping['*']
                else:
                    _real_db_name = _micro_id

            if _yaml.yaml_config['init_db'] is None or _real_db_name not in _yaml.yaml_config['init_db'].keys():
                _yaml.set_value(
                    'init_db/%s' % _real_db_name, {
                        'index_only': index_only,
                        'comment': '', 'args': [], 'kwargs': {}
                    }, auto_create=True
                )

            # 处理实体信息
            _entity_sheet_name = '%s.%s' % (_micro_id, _entity_name)
            _entity_name_index = self._get_name_index_by_sheet_header(
                _wb, _entity_sheet_name, name_mapping=EXCEL_ENTITY_HEADER_NAME_MAPPING
            )  # 获取实体名字索引
            _entity_sheet = _wb.sheet_by_name(_entity_sheet_name)

            # 设置基础配置
            _yaml_path = 'init_collections/%s/%s' % (_real_db_name, _entity_name)
            _yaml.set_value(
                _yaml_path, {
                    'index_only': index_only,
                    'comment': _list_row[_list_name_index['entity_desc'] - 1].value
                }
            )

            # 处理固定字段定义, 同时形成索引清单
            _fixed_col_define = {}
            _temp_indexs = {}
            for _entity_row_index in range(1, _entity_sheet.nrows):
                _entity_row = _entity_sheet.row(_entity_row_index)  # 行数据
                _property = _entity_row[_entity_name_index['property'] - 1].value
                if _property == '':
                    # 没有属性信息
                    continue

                # 处理索引
                _normal_index_list = _entity_row[_entity_name_index['normal_index_list'] - 1].value
                if _normal_index_list != '':
                    _index_list = _normal_index_list.split(',')  # 多个索引之间用逗号分隔
                    for _temp_str in _index_list:
                        _index_para = _temp_str.split('|')  # 通过|添加升序和降序标识
                        if _index_para[0] not in _temp_indexs.keys():
                            _temp_indexs[_index_para[0]] = {
                                'keys': {},
                                'paras': {'unique': False}
                            }

                        _temp_indexs[_index_para[0]]['keys'][_property] = {
                            'asc': -1 if len(_index_para) > 1 and _index_para[1].lower() == 'desc' else 1
                        }

                _unique_index_list = _entity_row[_entity_name_index['unique_index_list'] - 1].value
                if _unique_index_list != '':
                    _index_list = _unique_index_list.split(',')  # 多个索引之间用逗号分隔
                    for _temp_str in _index_list:
                        _index_para = _temp_str.split('|')  # 通过|添加升序和降序标识
                        if _index_para[0] not in _temp_indexs.keys():
                            _temp_indexs[_index_para[0]] = {
                                'keys': {},
                                'paras': {'unique': True}
                            }

                        _temp_indexs[_index_para[0]]['keys'][_property] = {
                            'asc': -1 if len(_index_para) > 1 and _index_para[1].lower() == 'desc' else 1
                        }

                # 处理固定字段定义
                _is_extend = _entity_row[_entity_name_index['is_extend'] - 1].value
                if _is_extend == 'YES':
                    # 扩展字段不处理
                    continue

                _fixed_col_define[_property] = {
                    'type': _entity_row[_entity_name_index['data_type'] - 1].value,
                    'len': _entity_row[_entity_name_index['data_len'] - 1].value,
                    'nullable': _entity_row[_entity_name_index['nullable'] - 1].value == 'YES',
                    'default': _entity_row[_entity_name_index['default'] - 1].value,
                    'comment': _entity_row[_entity_name_index['property_desc'] - 1].value
                }

                # 数据标准化处理
                if _fixed_col_define[_property]['len'] == '':
                    _fixed_col_define[_property]['len'] = 30
                else:
                    _fixed_col_define[_property]['len'] = int(_fixed_col_define[_property]['len'])

                if _fixed_col_define[_property]['default'] == '':
                    _fixed_col_define[_property]['default'] = None

                if _fixed_col_define[_property]['comment'] == '':
                    _fixed_col_define[_property]['comment'] = None

            _yaml.set_value(
                '%s/fixed_col_define' % _yaml_path, _fixed_col_define, auto_create=True
            )

            # 处理索引
            _indexs = {}
            for _index_name, _index_para in _temp_indexs.items():
                _formula_match = FormulaTool.analyse_formula(
                    _index_name, keywords=_formula_keywords
                )
                if _formula_match.keyword == '':
                    # 非公式
                    _indexs[_index_name] = _index_para
                else:
                    _index_name = 'idx_%s_%s' % (
                        '_'.join(list(_index_para['keys'].keys())), _formula_match.content_string
                    )
                    _indexs[_index_name] = _index_para

            _yaml.set_value(
                '%s/indexs' % _yaml_path, _indexs, auto_create=True
            )

        # 处理返回
        if _yaml_file is None:
            return _yaml

        # 保存为文件
        if append and os.path.exists(_yaml_file):
            # 追加模式
            _old_yaml = SimpleYaml(
                _yaml_file, obj_type=EnumYamlObjType.File, encoding='utf-8'
            )

            # 数据库初始化仅不存在才覆盖
            if _yaml.yaml_config['init_db'] is not None:
                for _db_name, _db_para in _yaml.yaml_config['init_db'].items():
                    _yaml_path = 'init_db/%s' % _db_name
                    if _old_yaml.get_value(_yaml_path) is None:
                        _old_yaml.set_value(_yaml_path, _db_para, auto_create=True)

            # 表设置直接覆盖
            if _yaml.yaml_config['init_collections'] is not None:
                for _db_name, _entity_list in _yaml.yaml_config['init_collections'].items():
                    for _entity_name, _entity_para in _entity_list.items():
                        _yaml_path = 'init_collections/%s/%s' % (_db_name, _entity_name)
                        _old_yaml.set_value(
                            _yaml_path, _entity_para, auto_create=True
                        )
            # 最后保存文件
            _old_yaml.save()
        else:
            # 覆盖模式, 直接保存就好
            _yaml.save(file=_yaml_file)

    def init_data_excel_to_yaml(self, excel_file: str, yaml_file: str = None,
            db_name=None, collection_name=None, db_name_mapping: dict = {}):
        """
        初始化数据Excel文件转换为Yaml初始化文件

        @param {str} excel_file - 集合(表)设计Excel文件, 为base_path的相对路径
        @param {str} yaml_file=None - 要保存到的Yaml初始化文件, 为base_path的相对路径
            注: 如果yaml_file为None, 代表只是形成SimpleYaml对象并返回
        @param {str|list} db_name=None - 指定要处理的数据库名(或数据库列表), 为转换前的数据库名
        @param {str|list} collection_name=None - 指定要处理的集合名(或集合列表)
        @param {dict} db_name_mapping={} - 数据库的映射字典
            key为转换前的数据库名, value为转换后的数据库名
            注: 可以将key指定为*, 代表将所有匹配不到的的数据库名都转换为该key为*的数据库名

        @returns {None|SimpleYaml} - 如果指定保存文件返回None, 否则返回SimpleYaml对象
        """
        # 参数处理
        _excel_file = os.path.abspath(os.path.join(self.app_base_path, excel_file))
        _yaml_file = None if yaml_file is None else os.path.abspath(os.path.join(self.app_base_path, yaml_file))

        # 要生成的yaml对象
        _yaml = SimpleYaml('pre_deal:\ninit_data:\n', obj_type=EnumYamlObjType.String, encoding='utf-8')

        # 处理预处理信息
        _wb: xlrd.book.Book = xlrd.open_workbook(_excel_file)
        _deal_name_index = self._get_name_index_by_sheet_header(
            _wb, EXCEL_DATA_PRE_DEAL_SHEET_NAME, name_mapping=EXCEL_DATA_PRE_DEAL_HEADER_NAME_MAPPING
        )  # 获取列表名字索引

        _deal_list = []  # 预处理清单
        _deal_sheet = _wb.sheet_by_name(EXCEL_DATA_PRE_DEAL_SHEET_NAME)
        for _deal_row_index in range(1, _deal_sheet.nrows):
            _deal_row = _deal_sheet.row(_deal_row_index)  # 行数据
            _collection = _deal_row[_deal_name_index['collection'] - 1]
            if _collection.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                # 空单元格, 不处理
                continue

            _db_name, _collection_name = _collection.value.split('.')

            _deal_info = {
                'db_name': _db_name,
                'collection': _collection_name,
                'deal_type': _deal_row[_deal_name_index['deal_type'] - 1].value,
                'remark': _deal_row[_deal_name_index['remark'] - 1].value,
            }

            _filter = _deal_row[_deal_name_index['filter'] - 1].value
            if _filter != '':
                _deal_info['filter'] = json.loads(_filter)

            _update = _deal_row[_deal_name_index['update'] - 1].value
            if _update != '':
                _deal_info['update'] = json.loads(_update)

            # 添加到清单中
            _deal_list.append(_deal_info)

        # 预处理放进yaml文件
        _yaml.set_value('pre_deal', _deal_list)

        # 遍历每个页签进行处理
        for _sheet_name in _wb.sheet_names():
            if _sheet_name == EXCEL_DATA_PRE_DEAL_SHEET_NAME:
                # 预处理标签不处理
                continue

            _db_name, _collection_name = _sheet_name.split('.')

            # 判断是否在处理范围
            if db_name is not None:
                if type(db_name) in (list, tuple) and _db_name not in db_name:
                    continue
                elif _db_name != db_name:
                    continue

            if collection_name is not None:
                if type(collection_name) in (list, tuple) and _collection_name not in collection_name:
                    continue
                elif _collection_name != collection_name:
                    continue

            # 数据库映射
            _real_db_name = db_name_mapping.get(_db_name, None)
            if _real_db_name is None:
                if db_name_mapping.get('*', None) is not None:
                    _real_db_name = db_name_mapping['*']
                else:
                    _real_db_name = _db_name

            # 获取字段名和类型配置
            _sheet = _wb.sheet_by_name(_sheet_name)
            _cols = _sheet.row(0)
            _cols_len = len(_cols)
            _types = _sheet.row(2)
            _types_len = len(_types)

            # 遍历数据生成数据字典
            _insert_datas = []  # 插入数据
            _update_datas = []  # 更新数据
            for _data_row_index in range(3, _sheet.nrows):
                _data_row = _sheet.row(_data_row_index)
                if _data_row[2].ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                    # 第1个字段为空单元格, 不处理
                    continue

                # 组成数据
                _data = {}
                for _col_index in range(2, len(_data_row)):
                    if _col_index >= _cols_len:
                        # 数据已在字段定义范围外
                        continue
                    elif _data_row[_col_index].ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                        # 空单元格, 不处理
                        continue

                    # 获取数据类型
                    if _col_index >= _types_len:
                        _type = 'str'
                    else:
                        _type = _types[_col_index].value
                        if _type == '':
                            _type = 'str'

                    # 进行数据转换
                    _val = str(_data_row[_col_index].value)
                    if _type == 'int':
                        _val = int(float(_val))
                    elif _type == 'float':
                        _val = float(_val)
                    elif _type == 'bool':
                        _val = True if _val.lower() == 'true' else False
                    elif _type == 'json':
                        _val = json.loads(_val)
                    elif _data_row[_col_index].ctype in (xlrd.XL_CELL_NUMBER, ) and _val.endswith('.0'):
                        # 解决xlrd无法区分数字形式的文本的情况, 但这样就不支持0.0这类的输入
                        _val = _val[:-2]

                    # 放入数据字典
                    _data[_cols[_col_index].value] = _val

                # 根据不同操作类型放入数组
                if _data_row[0].value == 'update':
                    # 更新操作
                    _update_datas.append({
                        'keys': _data_row[1].value,
                        'data': _data
                    })
                else:
                    # 插入操作
                    _insert_datas.append(_data)

            # 放进yaml文件
            _yaml.set_value(
                'init_data/%s/%s' % (_real_db_name, _collection_name),
                {'insert': _insert_datas, 'update': _update_datas}
            )

        # 处理返回
        if _yaml_file is None:
            return _yaml

        # 直接保存文件
        _yaml.save(file=_yaml_file)

    #############################
    # 数据库操作
    #############################

    def create_db(self, db_name: str, *args, **kwargs):
        """
        创建数据库

        @param {str} db_name - 数据库名
        """
        # 创建数据库
        AsyncTools.sync_run_coroutine(
            self.nosql_driver.create_db(db_name, *args, **kwargs)
        )

    def init_database(self, collection_file: str = None, db_option: str = None,
            collection_option: str = None, driver_option: str = None):
        """
        初始化NoSql数据库

        @param {str} collection_file=None - 初始化集合的yaml文件
            注: 如果不送代表直接使用base_path/nosql_init目录下的默认创建集合文件
        @param {str} db_option=None - 初始化数据库的选项, 默认为no_existed
            no - 不执行创建操作
            no_existed - 不存在时创建
            overwrite - 删除并重新创建
        @param {str} collection_option=None - 初始化集合的选项, 默认为no_existed
            no - 不执行创建操作
            no_existed - 不存在时创建
            overwrite - 删除并重新创建
        @param {str} driver_option=None - 初始化驱动配置文件的选项, 在配置文件上添加相应的数据库和表初始化参数, 默认为no_existed
            no - 不执行操作
            no_existed - 不存在时添加
            overwrite - 删除并重新添加
            link_yaml - 连接到yaml配置文件(配置文件为config/nosql_init_collection.yaml)
        """
        # 参数处理
        _collection_file = 'nosql_init/init_collection.yaml' if collection_file is None else collection_file
        _collection_file = os.path.abspath(os.path.join(
            self.app_base_path, _collection_file
        ))

        _db_option = 'no_existed' if db_option is None else db_option
        _collection_option = 'no_existed' if collection_option is None else collection_option
        _driver_option = 'link_yaml' if driver_option is None else driver_option

        _yaml_collection = None

        # 创建数据库
        if _db_option != 'no':
            _db_list = AsyncTools.sync_run_coroutine(self.nosql_driver.list_dbs())
            _yaml_collection = SimpleYaml(_collection_file, obj_type=EnumYamlObjType.File, encoding='utf-8')
            _init_db = _yaml_collection.get_value('init_db', default={})
            if _init_db is None:
                _init_db = {}
            for _db_name, _db_para in _init_db.items():
                if _db_name in _db_list:
                    if _db_option == 'no_existed':
                        # 已存在则不创建
                        continue

                    if _db_option == 'overwrite':
                        # 删除数据库
                        AsyncTools.sync_run_coroutine(self.nosql_driver.drop_db(_db_name))

                # 创建数据库
                _args = _db_para.get('args', [])
                if _args is None:
                    _args = []
                _kwargs = _db_para.get('kwargs', {})
                if _kwargs is None:
                    _kwargs = {}

                AsyncTools.sync_run_coroutine(
                    self.nosql_driver.create_db(_db_name, *_args, **_kwargs)
                )

        # 创建数据表
        if _collection_option != 'no':
            if _yaml_collection is None:
                _yaml_collection = SimpleYaml(_collection_file, obj_type=EnumYamlObjType.File, encoding='utf-8')

            _init_collections = _yaml_collection.get_value('init_collections', default={})
            if _init_collections is None:
                _init_collections = {}

            for _db_name, _temp_collections in _init_collections.items():
                # 先切换数据库
                AsyncTools.sync_run_coroutine(self.nosql_driver.switch_db(_db_name))
                for _collection_name, _collection_para in _temp_collections.items():
                    if AsyncTools.sync_run_coroutine(self.nosql_driver.collections_exists(_collection_name)):
                        if _collection_option == 'no_existed':
                            # 已存在则不创建
                            continue

                        if _collection_option == 'overwrite':
                            # 删除表
                            AsyncTools.sync_run_coroutine(self.nosql_driver.drop_collection(_collection_name))

                    # 创建表
                    AsyncTools.sync_run_coroutine(self.nosql_driver.create_collection(
                        _collection_name, indexs=_collection_para.get('indexs', None),
                        fixed_col_define=_collection_para.get('fixed_col_define', None),
                        comment=_collection_para.get('comment', None)
                    ))

        # 初始化配置选项
        if _driver_option != 'no':
            if _yaml_collection is None:
                _yaml_collection = SimpleYaml(_collection_file, obj_type=EnumYamlObjType.File, encoding='utf-8')

            _init_db = _yaml_collection.get_value('init_db', default=None)
            _init_collections = _yaml_collection.get_value('init_collections', default=None)

            # 判断是否要清空初始化参数
            _path = 'adapters/%s/plugin/init_kwargs/driver_config' % self.nosql_adapter_id
            if _driver_option == 'overwrite':
                # 覆盖模式
                self.adapter_config.remove('%s/init_db' % _path)
                self.adapter_config.remove('%s/init_collections' % _path)
                if _init_db is not None:
                    self.adapter_config.set_value('%s/init_db' % _path, _init_db)
                    self.adapter_config.set_value('%s/init_collections' % _path, _init_collections)
            elif _driver_option == 'link_yaml':
                # 连接到配置文件, 复制配置文件到config目录
                _yaml_file_path = 'config/init_collection.yaml'
                FileTool.copy_file(
                    _collection_file, os.path.join(self.app_base_path, _yaml_file_path), overwrite=True
                )
                # 设置参数
                self.adapter_config.remove('%s/init_db' % _path)
                self.adapter_config.remove('%s/init_collections' % _path)
                self.adapter_config.set_value('%s/init_yaml_file' % _path, _yaml_file_path)
                _convert_relative_paths = self.adapter_config.get_value(
                    'adapters/%s/convert_relative_paths' % self.nosql_adapter_id, default=None
                )
                _convert_path = 'init_kwargs/driver_config/init_yaml_file'
                if _convert_relative_paths is None:
                    _convert_relative_paths = [_convert_path]
                else:
                    if _convert_path not in _convert_relative_paths:
                        _convert_relative_paths.append(_convert_path)
                self.adapter_config.set_value(
                    'adapters/%s/convert_relative_paths' % self.nosql_adapter_id, _convert_relative_paths
                )
            else:
                # 不存在时添加模式
                if _init_db is not None:
                    for _db_name, _db_para in _init_db.items():
                        _set_path = '%s/init_db/%s' % (_path, _db_name)
                        _existed = self.adapter_config.get_value(_set_path)
                        if _existed is None:
                            self.adapter_config.set_value(_set_path, _db_para)

                if _init_collections is not None:
                    for _db_name, _temp_collections in _init_collections.items():
                        for _collection_name, _collection_para in _temp_collections.items():
                            _set_path = '%s/init_collections/%s/%s' % (_path, _db_name, _collection_name)
                            _existed = self.adapter_config.get_value(_set_path)
                            if _existed is None:
                                self.adapter_config.set_value(_set_path, _collection_para)

            # 保存文件
            self.adapter_config.save()

    def init_data(self, collection_file: str = None, data_file: str = None):
        """
        初始化NoSql数据

        @param {str} collection_file=None - 初始化集合的yaml文件
            注: 如果不送代表直接使用base_path/nosql_init目录下的默认创建集合文件
        @param {str} data_file=None - 初始化数据的yaml文件
            注: 如果不送代表直接使用base_path/nosql_init目录下的默认创建数据文件
        """
        # 参数处理
        _collection_file = 'nosql_init/init_collection.yaml' if collection_file is None else collection_file
        _collection_file = os.path.abspath(os.path.join(
            self.app_base_path, _collection_file
        ))

        _data_file = 'nosql_init/init_data.yaml' if data_file is None else data_file
        _data_file = os.path.abspath(os.path.join(
            self.app_base_path, _data_file
        ))

        # 尝试将数据库和表定义加载到驱动
        _yaml_collection = SimpleYaml(_collection_file, obj_type=EnumYamlObjType.File, encoding='utf-8')
        _init_db = _yaml_collection.get_value('init_db', default=None)
        if _init_db is not None:
            self.nosql_driver.init_index_extend_dbs(_init_db)
        _init_collections = _yaml_collection.get_value('init_collections', default=None)
        if _init_collections is not None:
            self.nosql_driver.init_index_extend_collections(_init_collections)

        # 装载数据文件进行处理
        _yaml_data = SimpleYaml(_data_file, obj_type=EnumYamlObjType.File, encoding='utf-8')

        # 先做预处理
        _pre_deal = _yaml_data.get_value('pre_deal', None)
        if _pre_deal is not None:
            for _deal_info in _pre_deal:
                # 切换数据库
                AsyncTools.sync_run_coroutine(self.nosql_driver.switch_db(_deal_info['db_name']))
                if _deal_info['deal_type'] == 'truncate':
                    # 清空表
                    AsyncTools.sync_run_coroutine(
                        self.nosql_driver.turncate_collection(_deal_info['collection'])
                    )
                elif _deal_info['deal_type'] == 'delete':
                    # 删除指定记录
                    AsyncTools.sync_run_coroutine(
                        self.nosql_driver.delete(
                            _deal_info['collection'], filter=_deal_info['filter']
                        )
                    )
                elif _deal_info['deal_type'] == 'update':
                    # 更新记录
                    AsyncTools.sync_run_coroutine(
                        self.nosql_driver.update(
                            _deal_info['collection'], filter=_deal_info['filter'], update=_deal_info['update']
                        )
                    )

        # 进行数据导入处理
        _init_data = _yaml_data.get_value('init_data', default={})
        if _init_data is None:
            _init_data = {}

        for _db_name, _temp_collections in _init_data.items():
            # 先切换数据库
            AsyncTools.sync_run_coroutine(self.nosql_driver.switch_db(_db_name))
            for _collection_name, _datas in _temp_collections.items():
                # 插入数据
                _insert_datas = _datas.get('insert', None)
                if _insert_datas is not None:
                    AsyncTools.sync_run_coroutine(self.nosql_driver.insert_many(
                        _collection_name, _insert_datas
                    ))

                # 更新数据
                _update_datas = _datas.get('update', None)
                if _update_datas is None:
                    _update_datas = []
                for _update_info in _update_datas:
                    _data = _update_info['data']
                    # 组成查询条件
                    _filter = {}
                    for _col in _update_info['keys'].split(','):
                        _filter[_col] = _data.get(_col, None)

                    AsyncTools.sync_run_coroutine(self.nosql_driver.update(
                        _collection_name, _filter, {'$set': _data}, upsert=True
                    ))

    #############################
    # 内部函数
    #############################
    def _init_nosql_driver(self, adapter_id: str = None):
        """
        初始化NoSql驱动对象

        @param {str} adapter_id=None - adapters.yaml上配置的NoSqlDb适配器对象
            注: 如果不传则代表获取第一个adapter_type为NoSqlDb的数据库配置
        """
        # 主动销毁原来的连接
        if self.nosql_driver is not None:
            AsyncTools.sync_run_coroutine(
                self.nosql_driver.destroy()
            )
            self.nosql_driver = None
            self.nosql_adapter_id = None
            self.adapter_config = None

        # 获取配置信息
        self.adapter_config = SimpleYaml(
            os.path.join(self.app_base_path, 'config/adapters.yaml'),
            obj_type=EnumYamlObjType.File, encoding='utf-8'
        )
        _yaml_adapters_dict = self.adapter_config.yaml_config

        # 获取适配器清单
        self.nosql_adapter_list = []
        for _adapter_id, _config in _yaml_adapters_dict['adapters'].items():
            if _config['adapter_type'] == 'NoSqlDb':
                self.nosql_adapter_list.append(_adapter_id)

        # 查找适配器id和配置
        if adapter_id is None:
            # 遍历查找
            for _adapter_id, _config in _yaml_adapters_dict['adapters'].items():
                if _config['adapter_type'] == 'NoSqlDb':
                    self.nosql_adapter_id = _adapter_id
                    break
        else:
            _config = _yaml_adapters_dict['adapters'].get(adapter_id, None)
            if _config is not None:
                self.nosql_adapter_id = adapter_id

        if self.nosql_adapter_id is None:
            raise ModuleNotFoundError('nosql driver not found in adapters.yaml')

        # 初始化驱动对象
        _adapter_config = _yaml_adapters_dict['adapters'][self.nosql_adapter_id]
        self.nosql_driver = self.adapter_manager.load_adapter(
            self.nosql_adapter_id, **_adapter_config
        )

    #############################
    # excel操作相关的内部函数
    #############################
    def _get_name_index_by_sheet_header(self, book: xlrd.book.Book, sheet_name: str, header_row_index: int = 1,
            name_mapping: dict = {}) -> dict:
        """
        通过excel页的标题行获取名字索引

        @param {xlrd.book.Book} book - 打开的excel文件
        @param {str} sheet_name - 页签名
        @param {int} header_row_index=1 - 标题行索引, 默认为第1行
        @param {dict} name_mapping={} - 名字映射索引(将不同语言转换为英文)

        @returns {dict} - 返回名字映射列的索引, key为名字, value为位置索引(int)
        """
        _name_index = {}  # 要返回的名字索引

        _sheet = book.sheet_by_name(sheet_name)
        _col_index = 0
        _row_index = header_row_index - 1
        for _cell in _sheet.row(_row_index):
            _col_index += 1
            if _cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                # 空单元格
                continue

            # 映射列名转换
            _name = _cell.value
            _name = name_mapping.get(_name, _name)
            _name_index[_name] = _col_index

        # 返回名字索引
        return _name_index


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # _db = NoSqlDbTools()
    # _db.set_base_path(r'/Users/lhj/opensource/HiveNetMicro-Ser-User/HiveNetMicro-Ser-User/back')
    # _db.collection_excel_to_yaml(
    #     excel_file=r'/Users/lhj/opensource/HiveNetMicro-Ser-User/docs/source/designs/entity-design.xlsx',
    #     yaml_file=r'/Users/lhj/opensource/HiveNetMicro-Ser-User/docs/source/designs/entity-design.yaml',
    # )
    # _db.init_data_excel_to_yaml(
    #     excel_file=r'/Users/lhj/opensource/HiveNetMicro-Ser-User/docs/source/designs/entity-init-data.xlsx',
    #     yaml_file=r'/Users/lhj/opensource/HiveNetMicro-Ser-User/docs/source/designs/entity-init-data.yaml',
    #     append=False
    # )

    # set_base_path /Users/lhj/opensource/HiveNetMicro-Ser-User/HiveNetMicro-Ser-User/back
    # nosql_convert_init_file type=init_collection src_excel=/Users/lhj/opensource/HiveNetMicro-Ser-User/docs/source/designs/entity-design.xlsx append=n index_only=y
    # nosql_convert_init_file type=init_data src_excel=/Users/lhj/opensource/HiveNetMicro-Ser-User/docs/source/designs/entity-init-data.xlsx

    # a = OrderedDict()
    # a['abc'] = 'cd'
    # print(json.dumps(a, ensure_ascii=False))

    a = [1, 2, 3, 4]
    print(','.join(a))
