#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
NoSql数据库处理的工具模块

@module nosql
@file nosql.py
"""
import os
import sys
import xlrd
import json
from HiveNetCore.formula import FormulaTool, StructFormulaKeywordPara
from HiveNetCore.yaml import SimpleYaml, EnumYamlObjType
from HiveNetCore.utils.file_tool import FileTool
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.import_tool import DynamicLibManager
from HiveNetNoSql.base.driver_fw import NosqlDriverFW
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.adapter_manager import AdapterManager
from HiveNetMicro.tools.utils.env import EnvTools


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


class NoSqlTools(object):
    """
    处理NoSql的工具类
    """

    @classmethod
    def get_db_driver(cls, output_path: str, adapter_id: str, adapter_manager: AdapterManager = None) -> NosqlDriverFW:
        """
        获取指定标识的NoSql数据库驱动

        @param {str} output_path - 应用输出目录
        @param {str} adapter_id - 适配器标识
        @param {AdapterManager} adapter_manager=None - 插件管理对象

        @returns {NosqlDriverFW} - 获取到的NoSql驱动对象
        """
        # 获取配置信息
        _adapter_config = SimpleYaml(
            os.path.join(output_path, 'config/adapters.yaml'),
            obj_type=EnumYamlObjType.File, encoding='utf-8'
        )
        _yaml_adapters_dict = _adapter_config.yaml_config

        _adapter_config = _yaml_adapters_dict['adapters'].get(adapter_id, None)
        if _adapter_config is None:
            raise AttributeError('adapter_id [%s] not found in adapters.yaml' % _adapter_config)

        # 初始化插件管理对象
        _adapter_manager = adapter_manager
        if adapter_manager is None:
            _adapter_manager = EnvTools.get_adapter_manager(output_path)

        # 初始化驱动对象
        return _adapter_manager.load_adapter(adapter_id, **_adapter_config)

    #############################
    # build参数构建yaml文件
    #############################
    @classmethod
    def build_db_para_to_yaml(cls, build_para: dict, yaml_file: str, append: bool = True):
        """
        构建参数数据库转为yaml初始化文件

        @param {dict} build_para - 构建参数, 类型为: db-初始化数据库
        @param {str} yaml_file - 要保存的yaml文件
        @param {bool} append=True - 指定是否追加模式, 为False代表覆盖文件
        """
        _yaml_file = os.path.abspath(os.path.join(os.getcwd(), yaml_file))

        # 要生成的yaml对象
        _yaml = SimpleYaml('build:\ninit_db:\n', obj_type=EnumYamlObjType.String, encoding='utf-8')

        # 处理构建参数
        _yaml.set_value('build', {
            'existed': build_para.get('existed', 'none'),
            'updateToDriverOpts': build_para.get('updateToDriverOpts', True)
        })

        # 处理数据库参数
        for _para in build_para.get('deals', []):
            _yaml.set_value(
                'init_db/%s' % _para['dbName'], {
                    'index_only': _para.get('indexOnly', True),
                    'comment': '' if _para.get('comment', None) is None else _para['comment'],
                    'args': [] if _para.get('args', None) is None else _para['args'],
                    'kwargs': {} if _para.get('kwargs', None) is None else _para['kwargs']
                }, auto_create=True
            )

        # 保存初始化配置文件
        if append and os.path.exists(_yaml_file):
            # 追加模式
            _old_yaml = SimpleYaml(
                _yaml_file, obj_type=EnumYamlObjType.File, encoding='utf-8'
            )

            # 仅覆盖数据库参数
            if _yaml.yaml_config['init_db'] is not None:
                for _db_name, _db_para in _yaml.yaml_config['init_db'].items():
                    _yaml_path = 'init_db/%s' % _db_name
                    _old_yaml.set_value(_yaml_path, _db_para, auto_create=True)

            # 最后保存文件
            _old_yaml.save()
        else:
            # 覆盖模式, 直接保存就好
            _yaml.save(file=_yaml_file)

    @classmethod
    def build_collection_para_to_yaml(cls, source_path: str, build_para: dict, yaml_file: str, append: bool = True):
        """
        构建参数集合转为yaml初始化文件

        @param {str} source_path - 源目录路径
        @param {dict} build_para - 构建参数, 类型为: db-初始化数据库
        @param {str} yaml_file - 要保存的yaml文件
        @param {bool} append=True - 指定是否追加模式, 为False代表覆盖文件
        """
        _yaml_file = os.path.abspath(os.path.join(os.getcwd(), yaml_file))

        # 处理构建参数
        _build_para = {
            'existed': build_para.get('existed', 'none'),
            'updateToDriverOpts': build_para.get('updateToDriverOpts', True)
        }

        # 处理建表参数
        _append = append
        for _para in build_para.get('deals', []):
            _file = os.path.abspath(os.path.join(source_path, _para['file']))
            cls.collection_excel_to_yaml(
                _file, yaml_file=_yaml_file, append=_append,
                index_only=_para.get('indexOnly', True),
                db_filter=_para.get('dbFilter', None), collection_filter=_para.get('collectionFilter', None),
                db_mapping=_para.get('dbMapping', {}), build_para=_build_para
            )
            _append = True  # 第2个处理对象为追加方式

    @classmethod
    def build_data_para_to_yaml(cls, source_path: str, build_para: dict, yaml_file: str, append: bool = True):
        """
        构建参数初始化数据转为yaml初始化文件

        @param {str} source_path - 源目录路径
        @param {dict} build_para - 构建参数, 类型为: db-初始化数据库
        @param {str} yaml_file - 要保存的yaml文件
        @param {bool} append=True - 指定是否追加模式, 为False代表覆盖文件
        """
        _yaml_file = os.path.abspath(os.path.join(os.getcwd(), yaml_file))

        # 处理构建参数
        _build_para = {}

        # 处理建表参数
        _append = append
        for _para in build_para.get('deals', []):
            _file = os.path.abspath(os.path.join(source_path, _para['file']))
            cls.init_data_excel_to_yaml(
                _file, _yaml_file, append=_append,
                db_filter=_para.get('dbFilter', None), collection_filter=_para.get('collectionFilter', None),
                db_mapping=_para.get('dbMapping', {}), build_para=_build_para
            )
            _append = True  # 第2个处理对象为追加方式

    #############################
    # excel转换
    #############################
    @classmethod
    def collection_excel_to_yaml(cls, excel_file: str, yaml_file: str, append: bool = True,
            index_only: bool = True, db_filter=None, collection_filter=None, db_mapping: dict = {},
            build_para: dict = {}):
        """
        集合(表)设计Excel文件转换为Yaml初始化文件

        @param {str} excel_file - 集合(表)设计Excel文件
        @param {str} yaml_file - 要保存到的Yaml初始化文件, 如果为None返回SimpleYaml对象
        @param {bool} append=True - 指定是否追加模式, 为False代表覆盖文件
        @param {bool} index_only=True - 是否仅用于索引, 不创建
        @param {str|list} db_filter=None - 指定要生成的数据库名(或数据库列表), 为转换前的数据库名, 不传代表全部转换
        @param {str|list} collection_filter=None - 指定要处理的集合名(或集合列表), 不传代表全部转换
        @param {dict} db_mapping={} - 数据库的映射字典
            key为转换前的数据库名, value为转换后的数据库名
            注: 可以将key指定为*, 代表将所有匹配不到的的数据库名都转换为该key为*的数据库名
        @param {dict} build_para={} - 创建参数
            existed: str, 当表已存在时的处理方式, none-不处理(默认), rebuild-重建表

        @returns {None|SimpleYaml} - 如果指定保存文件返回None, 否则返回SimpleYaml对象
        """
        # 参数处理
        _excel_file = os.path.abspath(os.path.join(os.getcwd(), excel_file))
        _yaml_file = None
        if yaml_file is not None:
            _yaml_file = os.path.abspath(os.path.join(os.getcwd(), yaml_file))

        # 自动索引名的参数
        _formula_string_para = StructFormulaKeywordPara()
        _formula_string_para.is_string = True  # 声明是字符串参数
        _formula_string_para.has_sub_formula = False  # 声明公式中不会有子公式
        _formula_keywords = {'auto_name': [
            ['{$auto_name=', [], []], ['$}', [], []], _formula_string_para
        ]}  # 解析{$auto_name=xx$}的公式

        # 要生成的yaml对象
        _yaml = SimpleYaml('build:\ninit_collections:\n', obj_type=EnumYamlObjType.String, encoding='utf-8')

        # 处理构建参数
        _yaml.set_value('build', build_para, auto_create=True)

        # 获取清单
        _wb: xlrd.book.Book = xlrd.open_workbook(_excel_file)
        _list_name_index = cls._get_name_index_by_sheet_header(
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
            if db_filter is not None:
                if type(db_filter) in (list, tuple) and _micro_id not in db_filter:
                    continue
                elif _micro_id != db_filter:
                    continue

            if collection_filter is not None:
                if type(collection_filter) in (list, tuple) and _entity_name not in collection_filter:
                    continue
                elif _entity_name != collection_filter:
                    continue

            # 处理数据库初始化信息
            _real_db_name = db_mapping.get(_micro_id, None)
            if _real_db_name is None:
                if db_mapping.get('*', None) is not None:
                    _real_db_name = db_mapping['*']
                else:
                    _real_db_name = _micro_id

            # 处理实体信息
            _entity_sheet_name = '%s.%s' % (_micro_id, _entity_name)
            _entity_name_index = cls._get_name_index_by_sheet_header(
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

    @classmethod
    def init_data_excel_to_yaml(cls, excel_file: str, yaml_file: str, append: bool = True,
            db_filter=None, collection_filter=None, db_mapping: dict = {}, build_para: dict = {}):
        """
        初始化数据Excel文件转换为Yaml初始化文件

        @param {str} excel_file - 集合(表)设计Excel文件
        @param {str} yaml_file - 要保存到的Yaml初始化文件
        @param {bool} append=True - 指定是否追加模式, 为False代表覆盖文件
        @param {str|list} db_filter=None - 指定要处理的数据库名(或数据库列表), 为转换前的数据库名
        @param {str|list} collection_filter=None - 指定要处理的集合名(或集合列表)
        @param {dict} db_mapping={} - 数据库的映射字典
            key为转换前的数据库名, value为转换后的数据库名
            注: 可以将key指定为*, 代表将所有匹配不到的的数据库名都转换为该key为*的数据库名
        @param {dict} build_para={} - 创建参数
            existed: str, 当表已存在时的处理方式, none-不处理(默认), rebuild-重建表

        @returns {None|SimpleYaml} - 如果指定保存文件返回None, 否则返回SimpleYaml对象
        """
        # 参数处理
        _excel_file = os.path.abspath(os.path.join(os.getcwd(), excel_file))
        _yaml_file = None
        if yaml_file is not None:
            _yaml_file = os.path.abspath(os.path.join(os.getcwd(), yaml_file))

        # 要生成的yaml对象
        _yaml = SimpleYaml('build:\npre_deal:\ninit_data:\n', obj_type=EnumYamlObjType.String, encoding='utf-8')

        # 处理构建参数
        _yaml.set_value('build', build_para, auto_create=True)

        # 处理预处理信息
        _wb: xlrd.book.Book = xlrd.open_workbook(_excel_file)
        _deal_name_index = cls._get_name_index_by_sheet_header(
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
            if db_filter is not None:
                if type(db_filter) in (list, tuple) and _db_name not in db_filter:
                    continue
                elif _db_name != db_filter:
                    continue

            if collection_filter is not None:
                if type(collection_filter) in (list, tuple) and _collection_name not in collection_filter:
                    continue
                elif _collection_name != collection_filter:
                    continue

            # 数据库映射
            _real_db_name = db_mapping.get(_db_name, None)
            if _real_db_name is None:
                if db_mapping.get('*', None) is not None:
                    _real_db_name = db_mapping['*']
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

        # 保存为文件
        if append and os.path.exists(_yaml_file):
            # 追加模式
            _old_yaml = SimpleYaml(
                _yaml_file, obj_type=EnumYamlObjType.File, encoding='utf-8'
            )

            # 处理pre_deal
            if _yaml.yaml_config['pre_deal'] is not None:
                if _old_yaml.get('pre_deal', None) is None:
                    _old_yaml.set_value('pre_deal', _yaml.yaml_config['pre_deal'])
                else:
                    _old_yaml['pre_deal'].extend(_yaml.yaml_config['pre_deal'])

            # 处理 init_data
            if _yaml.yaml_config['init_data'] is not None:
                if _old_yaml.get('init_data', None) is None:
                    _old_yaml.set_value('init_data', _yaml.yaml_config['init_data'])
                else:
                    for _db_name, _collection_list in _yaml.yaml_config['init_data'].items():
                        if _old_yaml['init_data'].get(_db_name, None) is None:
                            _old_yaml.set_value('init_data/%s' % _db_name, _collection_list)
                        else:
                            for _collection, _op_datas in _collection_list.items():
                                if _old_yaml['init_data'][_db_name].get(_collection, None) is None:
                                    _old_yaml.set_value('init_data/%s/%s' % (_db_name, _collection), _op_datas)
                                else:
                                    _old_yaml['init_data'][_db_name][_collection]['insert'].extend(
                                        _op_datas['insert']
                                    )
                                    _old_yaml['init_data'][_db_name][_collection]['update'].extend(
                                        _op_datas['update']
                                    )

            # 最后保存文件
            _old_yaml.save()
        else:
            # 覆盖模式, 直接保存就好
            _yaml.save(file=_yaml_file)

    #############################
    # 数据库操作
    #############################
    @classmethod
    def init_dbs(cls, output_path: str, yaml_file: str, db_driver: NosqlDriverFW):
        """
        初始化数据库(创建数据库)

        @param {str} output_path - 应用输出目录
        @param {str} yaml_file - 初始化数据库的yaml文件
        @param {NosqlDriverFW} db_driver - 数据库驱动
        """
        _yaml_file = os.path.abspath(os.path.join(output_path, yaml_file))
        _yaml = SimpleYaml(
            _yaml_file, obj_type=EnumYamlObjType.File, encoding='utf-8'
        ).yaml_dict

        # 构建参数
        _existed = _yaml.get('build', {}).get('existed', 'none')

        # 遍历进行数据库处理
        _dbs = AsyncTools.sync_run_coroutine(db_driver.list_dbs())
        for _db_name, _para in _yaml.get('init_db', {}).items():
            if _db_name in _dbs:
                # 数据库已存在
                if _existed == 'rebuild':
                    AsyncTools.sync_run_coroutine(db_driver.drop_db(_db_name))
                else:
                    # 已存在, 不处理
                    continue

            # 创建数据库
            AsyncTools.sync_run_coroutine(db_driver.create_db(
                _db_name, *_para.get('args', []), **_para.get('kwargs', {})
            ))

    @classmethod
    def init_collections(cls, output_path: str, yaml_file: str, db_driver: NosqlDriverFW):
        """
        初始化集合(创建表)

        @param {str} output_path - 应用输出目录
        @param {str} yaml_file - 初始化集合的yaml文件
        @param {NosqlDriverFW} db_driver - 数据库驱动
        """
        _yaml_file = os.path.abspath(os.path.join(output_path, yaml_file))
        _yaml = SimpleYaml(
            _yaml_file, obj_type=EnumYamlObjType.File, encoding='utf-8'
        ).yaml_dict

        # 构建参数
        _existed = _yaml.get('build', {}).get('existed', 'none')

        # 遍历进行建表处理
        _init_collections = _yaml.get('init_collections', None)
        if _init_collections is None:
            # 无需处理
            return

        for _db_name, _temp_collections in _init_collections.items():
            # 先切换数据库
            AsyncTools.sync_run_coroutine(db_driver.switch_db(_db_name))
            for _collection_name, _collection_para in _temp_collections.items():
                if AsyncTools.sync_run_coroutine(db_driver.collections_exists(_collection_name)):
                    if _existed == 'rebuild':
                        # 删除表
                        AsyncTools.sync_run_coroutine(db_driver.drop_collection(_collection_name))
                    else:
                        # 已存在则不创建
                        continue

                # 创建表
                AsyncTools.sync_run_coroutine(db_driver.create_collection(
                    _collection_name, indexs=_collection_para.get('indexs', None),
                    fixed_col_define=_collection_para.get('fixed_col_define', None),
                    comment=_collection_para.get('comment', None)
                ))

    @classmethod
    def init_datas(cls, output_path: str, yaml_file: str, db_driver: NosqlDriverFW,
            init_dbs_yaml_file: str = None, init_collections_yaml_file: str = None):
        """
        初始化集合数据

        @param {str} output_path - 应用输出目录
        @param {str} yaml_file - 初始化数据的yaml文件
        @param {NosqlDriverFW} db_driver - 数据库驱动
        @param {str} init_dbs_yaml_file=None - 初始化数据库的yaml文件
        @param {str} init_collections_yaml_file=None - 初始化表的yaml文件
        """
        # 尝试将数据库和表定义加载到驱动
        if init_dbs_yaml_file is not None:
            _dbs_yaml = SimpleYaml(
                os.path.abspath(os.path.join(output_path, init_dbs_yaml_file)),
                obj_type=EnumYamlObjType.File, encoding='utf-8'
            )
            _init_db = _dbs_yaml.get_value('init_db', default=None)
            if _init_db is not None:
                db_driver.init_index_extend_dbs(_init_db)

        if init_collections_yaml_file is not None:
            _collections_yaml = SimpleYaml(
                os.path.abspath(os.path.join(output_path, init_collections_yaml_file)),
                obj_type=EnumYamlObjType.File, encoding='utf-8'
            )
            _init_collections = _collections_yaml.get_value('init_collections', default=None)
            if _init_collections is not None:
                db_driver.init_index_extend_collections(_init_collections)

        # 处理数据导入
        _yaml_file = os.path.abspath(os.path.join(output_path, yaml_file))
        _yaml = SimpleYaml(
            _yaml_file, obj_type=EnumYamlObjType.File, encoding='utf-8'
        )

        # 先做预处理
        _pre_deal = _yaml.get_value('pre_deal', None)
        if _pre_deal is not None:
            for _deal_info in _pre_deal:
                # 切换数据库
                AsyncTools.sync_run_coroutine(db_driver.switch_db(_deal_info['db_name']))
                if _deal_info['deal_type'] == 'truncate':
                    # 清空表
                    AsyncTools.sync_run_coroutine(
                        db_driver.turncate_collection(_deal_info['collection'])
                    )
                elif _deal_info['deal_type'] == 'delete':
                    # 删除指定记录
                    AsyncTools.sync_run_coroutine(
                        db_driver.delete(
                            _deal_info['collection'], filter=_deal_info['filter']
                        )
                    )
                elif _deal_info['deal_type'] == 'update':
                    # 更新记录
                    AsyncTools.sync_run_coroutine(
                        db_driver.update(
                            _deal_info['collection'], filter=_deal_info['filter'], update=_deal_info['update']
                        )
                    )

        # 进行数据导入处理
        _init_data = _yaml.get_value('init_data', default={})
        if _init_data is None:
            _init_data = {}

        for _db_name, _temp_collections in _init_data.items():
            # 先切换数据库
            AsyncTools.sync_run_coroutine(db_driver.switch_db(_db_name))
            for _collection_name, _datas in _temp_collections.items():
                # 插入数据
                _insert_datas = _datas.get('insert', None)
                if _insert_datas is not None:
                    AsyncTools.sync_run_coroutine(db_driver.insert_many(
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

                    AsyncTools.sync_run_coroutine(db_driver.update(
                        _collection_name, _filter, {'$set': _data}, upsert=True
                    ))

    @classmethod
    def update_dbs_to_driver_opts(cls, output_path: str, yaml_file: str, db_driver_adapter_id: str):
        """
        更新数据库初始化信息到驱动适配器的初始化参数文件中

        @param {str} output_path - 应用输出目录
        @param {str} yaml_file - 初始化数据库的yaml文件
        @param {str} db_driver_adapter_id - 数据库驱动标识
        """
        # 初始化配置文件
        _yaml_file = os.path.abspath(os.path.join(output_path, yaml_file))
        _yaml = SimpleYaml(
            _yaml_file, obj_type=EnumYamlObjType.File, encoding='utf-8'
        )

        _init_db = _yaml.get_value('init_db')
        if _init_db is None:
            # 没有信息, 无需处理
            return

        # 适配器初始化的配置文件
        _adapter_file_name = 'adapter_init_yaml_file_%s.yaml' % db_driver_adapter_id
        _adapter_file = os.path.abspath(os.path.join(output_path, 'config', _adapter_file_name))
        _adapter_yaml = cls._get_yaml_file(_adapter_file, 'init_db')

        # 进行处理
        _old_init_db = _adapter_yaml.get_value('init_db')
        if _old_init_db is None:
            _old_init_db = {}

        for _db_name, _para in _init_db.items():
            _old_init_db[_db_name] = _para

        # 保存配置文件
        _adapter_yaml.save()

        # 设置适配器参数
        cls._set_adapter_init_yaml_file(output_path, db_driver_adapter_id)

    @classmethod
    def update_collections_to_driver_opts(cls, output_path: str, yaml_file: str, db_driver_adapter_id: str):
        """
        更新数集合初始化信息到驱动适配器的初始化参数中

        @param {str} output_path - 应用输出目录
        @param {str} yaml_file - 初始化集合的yaml文件
        @param {str} db_driver_adapter_id - 数据库驱动标识
        """
        # 初始化配置文件
        _yaml_file = os.path.abspath(os.path.join(output_path, yaml_file))
        _yaml = SimpleYaml(
            _yaml_file, obj_type=EnumYamlObjType.File, encoding='utf-8'
        )

        # 遍历进行建表处理
        _init_collections = _yaml.get_value('init_collections')
        if _init_collections is None:
            # 无需处理
            return

        # 适配器初始化的配置文件
        _adapter_file_name = 'adapter_init_yaml_file_%s.yaml' % db_driver_adapter_id
        _adapter_file = os.path.abspath(os.path.join(output_path, 'config', _adapter_file_name))
        _adapter_yaml = cls._get_yaml_file(_adapter_file, 'init_collections')

        # 进行处理
        _old_init_collections = _adapter_yaml.get_value('init_collections')
        if _old_init_collections is None:
            _old_init_collections = {}

        for _db_name, _collections in _init_collections.items():
            if _old_init_collections.get(_db_name, None) is None:
                _old_init_collections[_db_name] = _collections
                continue

            for _collection, _para in _collections.items():
                _old_init_collections[_db_name][_collection] = _para

        # 保存配置文件
        _adapter_yaml.save()

        # 设置适配器参数
        cls._set_adapter_init_yaml_file(output_path, db_driver_adapter_id)

    #############################
    # 内部函数
    #############################
    @classmethod
    def _get_name_index_by_sheet_header(cls, book: xlrd.book.Book, sheet_name: str, header_row_index: int = 1,
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

    @classmethod
    def _get_yaml_file(cls, file: str, default_key: str) -> SimpleYaml:
        """
        获取yaml文件配置(文件不存在创建文件)

        @param {str} file - 文件路径
        @param {str} default_key - 默认要创建的key

        @returns {SimpleYaml} - 返回文件对应的Yaml对象
        """
        # 文件不存在则创建文件
        if not os.path.exists(file):
            _yaml = SimpleYaml('%s:\n' % default_key, obj_type=EnumYamlObjType.String, encoding='utf-8')
            _yaml.save(file=file, encoding='utf-8')

        # 返回yaml对象
        return SimpleYaml(
            file, obj_type=EnumYamlObjType.File, encoding='utf-8'
        )

    @classmethod
    def _set_adapter_init_yaml_file(cls, output_path: str, db_driver_adapter_id: str):
        """
        设置适配器的初始化yaml文件配置

        @param {str} output_path - 应用输出目录
        @param {str} db_driver_adapter_id - 适配器id
        """
        # 适配器配置文件
        _adapter_yaml = SimpleYaml(
            os.path.join(output_path, 'config/adapters.yaml'),
            obj_type=EnumYamlObjType.File, encoding='utf-8'
        )

        _path = 'adapters/%s/plugin/init_kwargs/driver_config/init_yaml_file' % db_driver_adapter_id
        _init_yaml_file = _adapter_yaml.get_value(_path)
        if _init_yaml_file is not None:
            # 已经进行了设置, 无需处理
            return

        # 设置配置值
        _init_yaml_file = 'config/adapter_init_yaml_file_%s.yaml' % db_driver_adapter_id
        _adapter_yaml.set_value(_path, _init_yaml_file)

        _convert_relative_paths = _adapter_yaml.get_value(
            'adapters/%s/convert_relative_paths' % db_driver_adapter_id, default=None
        )
        _convert_path = 'init_kwargs/driver_config/init_yaml_file'
        if _convert_relative_paths is None:
            _convert_relative_paths = [_convert_path]
        else:
            if _convert_path not in _convert_relative_paths:
                _convert_relative_paths.append(_convert_path)
        _adapter_yaml.set_value(
            'adapters/%s/convert_relative_paths' % db_driver_adapter_id, _convert_relative_paths
        )

        # 保存
        _adapter_yaml.save()




