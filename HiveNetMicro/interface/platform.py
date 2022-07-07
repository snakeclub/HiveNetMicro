#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
底层框架通用功能基础模块
注: 业务逻辑模块应仅通过当前模块访问框架底层数据及方法

@module platform
@file platform.py
"""
import os
import sys
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetMicro.core.global_manager import GlobalManager
from HiveNetMicro.core.caller import RemoteCaller


class PlatformLibLoader(object):
    """
    通用动态库加载功能封装
    """

    def __init__(self) -> None:
        """
        构造函数

        @throws {NotImplementedError} - 从全局变量未能获取到需加载对象时抛出
        """
        self.lib_loader = GlobalManager.GET_PLATFORM_LIB_LOADER()
        if self.lib_loader is None:
            raise NotImplementedError('lib loader is not implemented')

    #############################
    # 接口封装函数
    #############################
    def load(self, path: str = None, module_name: str = None, as_name: str = None, class_mapping: dict = None):
        """
        装载指定模块模块

        @param {str} path=None - 文件路径或加载模块的指定搜索路径
        @param {str} module_name=None - 要加载的模块名, 注意模块名必须全局唯一
        @param {str} as_name=None - 获取模块对象的检索名
        @param {dict} class_mapping=None - 类名映射字典, key为类别名, value为真实的类名
            注: 类名映射是设置在as_name下, 因此如果要使用该参数, 请设置as_name(例如设置为和模块名一致)

        @returns {tuple} - 返回 (module_name, module_obj)

        @example path和module_name组合使用的例子
            1、path为完整文件路径, module_name不设置, 则导入模块名为文件名(不含.py)
                例如: path='/test/xxx.py', module_name=None
            2、path为文件所在目录, module_name设置为文件名(不含.py), 按文件名自动获取文件进行导入
                例如: path='/test', module_name='xxx'
            3、path为包所在目录, module_name设置为包含后续包路径的模块名, 需注意每个包路径下要有__init__.py文件
                例如: path='./test', module_name='aaa.bbb.xxx'
            4、path设置为None, module_name设置为要搜索的模块名, 会自动从python搜索路径(sys.path)中查找模块
        """
        return self.lib_loader.load(
            path=path, module_name=module_name, as_name=as_name, class_mapping=class_mapping
        )

    def set_as_name(self, module_name: str, as_name: str, class_mapping: dict = None, as_name_first: bool = True):
        """
        为模块获取设置检索名

        @param {str} module_name - 模块名
        @param {str} as_name - 模块对象的检索名
        @param {dict} class_mapping=None - 类名映射字典, key为类别名, value为真实的类名
        @param {bool} as_name_first=True - 优先按检索名查找模块

        @throws {ModuleNotFoundError} - 当模块名找不到模块时抛出异常
        """
        return self.lib_loader.set_as_name(
            module_name, as_name, class_mapping=class_mapping, as_name_first=as_name_first
        )

    def remove_as_name(self, as_name: str):
        """
        删除指定模块检索别名

        @param {str} as_name - 要删除的别名
        """
        return self.lib_loader.remove_as_name(as_name)

    def get_module(self, module_name: str, as_name_first: bool = True):
        """
        获取指定模块对象

        @param {str} module_name - 模块名或检索名
        @param {bool} as_name_first=True - 优先按检索名查找模块

        @returns {ModuleType} - 返回模块对象

        @throws {ModuleNotFoundError} - 当模块名找不到模块时抛出异常
        """
        return self.lib_loader.get_module(module_name, as_name_first=as_name_first)

    def get_class(self, module_name: str, class_name: str, as_name_first: bool = True):
        """
        获取指定模块的类对象(或成员函数)

        @param {str} module_name - 模块名或检索名
        @param {str} class_name - 类名
        @param {bool} as_name_first=True - 优先按检索名查找模块

        @returns {Any} - 查找到的类对象

        @throws {ModuleNotFoundError} - 当模块名找不到模块时抛出异常
        """
        return self.lib_loader.get_class(
            module_name, class_name, as_name_first=as_name_first
        )

    def init_class(self, module_name: str, class_name: str, init_config=None, stand_alone: bool = False,
            as_name_first: bool = True):
        """
        初始化类实例

        @param {str} module_name - 模块名或检索名
        @param {str} class_name - 类名
        @param {dict|list} init_config=None - 初始化参数
            注: 如果是dict类型, 会通过**init_config方式初始化；如果是list类型, 则通过*init_config方式初始化
        @param {bool} stand_alone=False - 是否生成新的独立实例(不缓存)
        @param {bool} as_name_first=True - 优先按检索名查找模块

        @returns {object} - 返回初始化后的实例对象

        @throws {ModuleNotFoundError} - 当模块名找不到模块时抛出异常
        """
        return self.lib_loader.init_class(
            module_name, class_name, init_config=init_config, stand_alone=stand_alone, as_name_first=as_name_first
        )

    def get_instance(self, module_name: str, class_name: str, as_name_first: bool = True):
        """
        获取缓存的类实例对象

        @param {str} module_name - 模块名或检索名
        @param {str} class_name - 类名

        @returns {object} - 返回实例对象

        @throws {ModuleNotFoundError} - 当模块名找不到模块时抛出异常
        """
        return self.lib_loader.get_instance(
            module_name, class_name, as_name_first=as_name_first
        )

    def load_by_config(self, plugin_config: dict, plugin_base_path: str):
        """
        装载动态库

        @param {dict} plugin_config - 插件配置
            path {str} - 文件路径或加载模块的指定搜索路径, 该参数可以设置为None或不设置
            module_name {str} - 指定要加载的模块名, 如果path包含完整文件名可以不设置
            class {str} - 指定要获取的类名
            function {str} - 指定要获取的函数名
            instantiation {bool} - 是否要初始化类(缓存实例), 默认为False
            stand_alone {bool} - 是否生成新的独立实例(不缓存), 默认为False
            init_args {list} - 类实例的初始化固定参数, 以*args方式传入
            init_kwargs {dict} - 类实例的初始化kv参数, 以*kwargs方式传入
        @param {str} plugin_base_path - 查找差距的基础路径

        @returns {str|object} - 根据不同情况返回不同的结果
            class和function均不设置: 返回模块名
            设置了class, 未设置function: 返回class类或class实例对象(instantiation为True的情况)
            设置了function: 返回指定的函数对象(如果class未指定, 返回的是模块中定义的函数)
        """
        return self.lib_loader.load_by_config(
            plugin_config, plugin_base_path
        )


class PlatformConfig(object):
    """
    通用配置功能接口封装
    """

    def __init__(self) -> None:
        """
        构造函数

        @throws {NotImplementedError} - 从全局变量未能获取到需加载对象时抛出
        """
        # 从全局变量中获取ConfigCenter模块
        self.config_center = GlobalManager.GET_SYS_CONFIG_CENTER()
        if self.config_center is None:
            raise NotImplementedError('config center is not implemented')

    #############################
    # 接口封装函数
    #############################
    def get_config(self, data_id: str, group: str = None, timeout: int = 3000) -> str:
        """
        获取指定配置信息

        @param {str} data_id - 配置ID
        @param {str} group=None - 配置所属分组
        @param {int} timeout=3000 - 超时时间, 单位为毫秒

        @returns {str} - 返回配置信息的字符串
        """
        return self.config_center.get_config(
            data_id, group=group, timeout=timeout
        )

    def set_config(self, data_id: str, content: str, group: str = None, content_type: str = 'text',
                timeout: int = 3000):
        """
        设置指定的配置信息

        @param {str} data_id - 配置ID
        @param {str} content - 要设置的内容
        @param {str} group=None - 配置所属分组
        @param {str} content_type='text' - 内容类型, 支持:
            text - 文本
            xml - xml格式内容
            json - json格式的内容
            yaml - yaml格式
        @param {int} timeout=3000 - 超时时间, 单位为毫秒
        """
        return self.config_center.set_config(
            data_id, content, group=group, content_type=content_type, timeout=timeout
        )

    def get_config_cached(self, data_id: str, group: str = None, timeout: int = 3000,
            content_type: str = 'text'):
        """
        从管理的缓存中获取配置

        @param {str} data_id - 配置ID
        @param {str} group=None - 配置所属分组
        @param {int} timeout=3000 - 超时时间, 单位为毫秒
        @param {str} content_type='text' - 配置的数据类型
            text - 文本
            xml - xml格式内容
            json - json格式的内容
            yaml - yaml格式

        @returns {str|dict} - 如果数据类型为text, 则返回str；其他类型返回dict
        """
        return self.config_center.get_config_cached(
            data_id, group=group, timeout=timeout, content_type=content_type
        )

    def yaml_to_dict(self, config_str: str) -> dict:
        """
        将yaml配置转换为字典对象

        @param {str} config_str - 配置字符串

        @returns {dict} - 转换后的配置字典
        """
        return self.config_center.yaml_to_dict(config_str)

    def dict_to_yaml(self, config_dict: dict) -> str:
        """
        将配置字典转换为yaml字符串

        @param {dict} config_dict - 配置字典

        @returns {str} - 转换后的yaml配置字符串
        """
        return self.config_center.dict_to_yaml(config_dict)

    def json_to_dict(self, config_str: str) -> dict:
        """
        将json配置转换为字典对象

        @param {str} config_str - 配置字符串

        @returns {dict} - 转换后的配置字典
        """
        return self.config_center.json_to_dict(config_str)

    def dict_to_json(self, config_dict: dict) -> str:
        """
        将配置字典转换为json字符串

        @param {dict} config_dict - 配置字典

        @returns {str} - 转换后的json配置字符串
        """
        return self.config_center.dict_to_json(config_dict)

    def xml_to_dict(self, config_str: str) -> dict:
        """
        将xml配置转换为字典对象
        注: 自动去掉根节点root

        @param {str} config_str - 配置字符串

        @returns {dict} - 转换后的配置字典
        """
        return self.config_center.xml_to_dict(config_str)

    def dict_to_xml(self, config_dict: dict, root_name: str = 'root') -> str:
        """
        将配置字典转换为xml字符串

        @param {dict} config_dict - 配置字典
        @param {str} root_name='root' - 根节点名称设置

        @returns {str} - 转换后的json配置字符串
        """
        return self.config_center.dict_to_xml(config_dict, root_name=root_name)


class Platform(object):
    """
    底层框架通用功能基础模块
    注: 业务逻辑模块应仅通过当前模块访问框架底层数据及方法
    """

    def __init__(self) -> None:
        """
        构造函数, 加载所有的平台通用功能接口
            Config - 通用配置功能接口

        @throws {NotImplementedError} - 从全局变量未能获取到需加载对象时抛出
        """
        self._LibLoader = PlatformLibLoader()
        self._Config = PlatformConfig()
        self._Logger = GlobalManager.GET_PLATFORM_LOGGER()
        self._caller: RemoteCaller = GlobalManager.GET_SYS_REMOTE_CALLER()

    #############################
    # 公共封装的属性对象
    #############################
    @property
    def LibLoader(self) -> PlatformLibLoader:
        """
        获取动态库加载接口对象
        @property {PlatformLibLoader}
        """
        return self._LibLoader

    @property
    def Config(self) -> PlatformConfig:
        """
        获取配置中心接口对象
        @property {PlatformConfig}
        """
        return self._Config

    @property
    def Logger(self):
        """
        获取日志接口对象
        @property {logging.Logger}
        """
        return self._Logger

    @property
    def Caller(self):
        """
        获取远程调用接口对象
        @property {caller.RemoteCaller}
        """
        return self._caller
