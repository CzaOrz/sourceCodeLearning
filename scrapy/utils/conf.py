import os
import sys
import numbers
from operator import itemgetter

import six
from six.moves.configparser import SafeConfigParser

from scrapy.settings import BaseSettings
from scrapy.utils.deprecate import update_classpath
from scrapy.utils.python import without_none_values


def build_component_list(compdict, custom=None, convert=update_classpath):
    """Compose a component list from a { class: order } dictionary."""

    def _check_components(complist):
        if len({convert(c) for c in complist}) != len(complist):
            raise ValueError('Some paths in {!r} convert to the same object, '
                             'please update your settings'.format(complist))

    def _map_keys(compdict):
        if isinstance(compdict, BaseSettings):
            compbs = BaseSettings()
            for k, v in six.iteritems(compdict):
                prio = compdict.getpriority(k)
                if compbs.getpriority(convert(k)) == prio:
                    raise ValueError('Some paths in {!r} convert to the same '
                                     'object, please update your settings'
                                     ''.format(list(compdict.keys())))
                else:
                    compbs.set(convert(k), v, priority=prio)
            return compbs
        else:
            _check_components(compdict)
            return {convert(k): v for k, v in six.iteritems(compdict)}

    def _validate_values(compdict):
        """Fail if a value in the components dict is not a real number or None."""
        for name, value in six.iteritems(compdict):
            if value is not None and not isinstance(value, numbers.Real):
                raise ValueError('Invalid value {} for component {}, please provide ' \
                                 'a real number or None instead'.format(value, name))

    # BEGIN Backwards compatibility for old (base, custom) call signature
    if isinstance(custom, (list, tuple)):
        _check_components(custom)
        return type(custom)(convert(c) for c in custom)

    if custom is not None:
        compdict.update(custom)
    # END Backwards compatibility

    _validate_values(compdict)
    compdict = without_none_values(_map_keys(compdict))
    return [k for k, v in sorted(six.iteritems(compdict), key=itemgetter(1))]


def arglist_to_dict(arglist):
    """Convert a list of arguments like ['arg1=val1', 'arg2=val2', ...] to a
    dict
    """
    return dict(x.split('=', 1) for x in arglist)


def closest_scrapy_cfg(path='.', prevpath=None):  # 从当前目录往父级目录递归，是否能够找到scrapy.cfg配置文件，能找到就表示属于项目内
    """Return the path to the closest scrapy.cfg file by traversing the current
    directory and its parents
    """
    if path == prevpath:
        return ''
    path = os.path.abspath(path)
    cfgfile = os.path.join(path, 'scrapy.cfg')  # 并没有对此文件进行读取的操作吗
    if os.path.exists(cfgfile):
        return cfgfile
    return closest_scrapy_cfg(os.path.dirname(path), path)  # 这个递归操作很骚，我喜欢


def init_env(project='default', set_syspath=True):
    """Initialize environment to use command-line tool from inside a project
    dir. This sets the Scrapy settings module and modifies the Python path to
    be able to locate the project module.
    """
    cfg = get_config()  # 但实际这里应该是找不到的把
    if cfg.has_option('settings', project):  # 通过SafeConfigParser模块，加载配置文件后，可以直接使用has_option寻找配置，如default
        os.environ['SCRAPY_SETTINGS_MODULE'] = cfg.get('settings', project)  # get 获取section下option的值，也就是default = scrapyProj.settings  # 把配置文件加载到os.environ里面，这确实是个骚操作呀
    closest = closest_scrapy_cfg()  # 从此处开始，递归查找父级元素，直至找到或者报错
    if closest:
        projdir = os.path.dirname(closest)  # 获取项目路径
        if set_syspath and projdir not in sys.path:  # 如果项目路径不在sys.path里面，也就是python的运行环境，则加载进python的运行环境
            sys.path.append(projdir)  # 这里是不是就是相当于pycharm的make_source_root，把项目加载到路径中


def get_config(use_closest=True):
    """Get Scrapy config file as a SafeConfigParser"""
    sources = get_sources(use_closest)  # list
    cfg = SafeConfigParser()
    cfg.read(sources)
    return cfg


def get_sources(use_closest=True):
    xdg_config_home = os.environ.get('XDG_CONFIG_HOME') or \
        os.path.expanduser('~/.config')
    sources = ['/etc/scrapy.cfg', r'c:\scrapy\scrapy.cfg',
               xdg_config_home + '/scrapy.cfg',
               os.path.expanduser('~/.scrapy.cfg')]  # 这儿的都感觉怪怪的
    if use_closest:
        sources.append(closest_scrapy_cfg())  # 应该是从这里加载了scrapy.cfg文件
    return sources
