import six
import signal
import logging
import warnings

import sys
from twisted.internet import reactor, defer
from zope.interface.verify import verifyClass, DoesNotImplement

from scrapy.core.engine import ExecutionEngine
from scrapy.resolver import CachingThreadedResolver
from scrapy.interfaces import ISpiderLoader
from scrapy.extension import ExtensionManager
from scrapy.settings import overridden_settings, Settings
from scrapy.signalmanager import SignalManager
from scrapy.exceptions import ScrapyDeprecationWarning
from scrapy.utils.ossignal import install_shutdown_handlers, signal_names
from scrapy.utils.misc import load_object
from scrapy.utils.log import (
    LogCounterHandler, configure_logging, log_scrapy_info,
    get_scrapy_root_handler, install_scrapy_root_handler)
from scrapy import signals

logger = logging.getLogger(__name__)


class Crawler(object):

    def __init__(self, spidercls, settings=None):
        if isinstance(settings, dict) or settings is None: # 此处应该直接就是一个False
            settings = Settings(settings)

        self.spidercls = spidercls  # 获取了爬虫对象，，但是还是没有实例化  # 所以流程就是获取爬虫对象，在实例化之前，执行了一次update_settings，就是针对custom setting的一次操作嘛
        self.settings = settings.copy()
        self.spidercls.update_settings(self.settings)  # 就是在这里执行了对custom_setting的设置嘛，可以很强，把爬虫里面的custom_setting更新到setting里面?好吧没事共同维护的一个setting对象，确实是直接更新到了setting里面
        # 所以在实例化之前，他只是更新了settings而已，你写在__init__其实一点用都得的，根本就没有执行到哪一步
        # todo 总结。我以前是想把custiom_settings卸载init里面，但是并没有起作用，因为此时的爬虫也就是 self.spidercls 根本就还没有进行初始化，而是先执行的update_settings
        d = dict(overridden_settings(self.settings))  # 找出相同的，取overridden里面的值
        logger.info("Overridden settings: %(settings)r", {'settings': d})  # 这就是打印那句log的地方，打印出Overridden属性。现遍历默认属性，找出已有属性中对应的值，看那些有修改

        self.signals = SignalManager(self)
        self.stats = load_object(self.settings['STATS_CLASS'])(self)  # STATS_CLASS = 'scrapy.statscollectors.MemoryStatsCollector' -- 统计机制

        handler = LogCounterHandler(self, level=self.settings.get('LOG_LEVEL'))  # LOG_LEVEL = 'DEBUG'
        logging.root.addHandler(handler)
        if get_scrapy_root_handler() is not None:
            # scrapy root handler already installed: update it with new settings
            install_scrapy_root_handler(self.settings)
        # lambda is assigned to Crawler attribute because this way it is not
        # garbage collected after leaving __init__ scope
        self.__remove_handler = lambda: logging.root.removeHandler(handler)
        self.signals.connect(self.__remove_handler, signals.engine_stopped)

        lf_cls = load_object(self.settings['LOG_FORMATTER'])   # LOG_FORMATTER = 'scrapy.logformatter.LogFormatter'
        self.logformatter = lf_cls.from_crawler(self)
        self.extensions = ExtensionManager.from_crawler(self)  # extensions是干嘛用的，杵这干啥呢，闹呢。卧槽，貌似不需要使用这些扩展件呀

        self.settings.freeze()
        self.crawling = False
        self.spider = None
        self.engine = None

    @property
    def spiders(self):
        if not hasattr(self, '_spiders'):
            warnings.warn("Crawler.spiders is deprecated, use "
                          "CrawlerRunner.spider_loader or instantiate "
                          "scrapy.spiderloader.SpiderLoader with your "
                          "settings.",
                          category=ScrapyDeprecationWarning, stacklevel=2)
            self._spiders = _get_spider_loader(self.settings.frozencopy())
        return self._spiders  # SpiderLoader类，还不是直接的爬虫类

    @defer.inlineCallbacks
    def crawl(self, *args, **kwargs):
        assert not self.crawling, "Crawling already taking place"
        self.crawling = True

        try:  # 终于实例化了啊
            self.spider = self._create_spider(*args, **kwargs)  # 这个spider就是我们编写的爬虫，如MySpider
            self.engine = self._create_engine()
            start_requests = iter(self.spider.start_requests())  # Request / FormRequest，第一步就在这里获取所有的start_requests函数逻辑
            yield self.engine.open_spider(self.spider, start_requests)
            yield defer.maybeDeferred(self.engine.start)  # todo, 在这列插入日志，看下到底是谁先执行，这个yield是不是可以随意设置啊
        except Exception:
            # In Python 2 reraising an exception after yield discards
            # the original traceback (see https://bugs.python.org/issue7563),
            # so sys.exc_info() workaround is used.
            # This workaround also works in Python 3, but it is not needed,
            # and it is slower, so in Python 3 we use native `raise`.
            if six.PY2:
                exc_info = sys.exc_info()

            self.crawling = False
            if self.engine is not None:
                yield self.engine.close()

            if six.PY2:
                six.reraise(*exc_info)
            raise

    def _create_spider(self, *args, **kwargs):
        return self.spidercls.from_crawler(self, *args, **kwargs)  # 找到了，在这里使用from_crawler进行实例化的，实例化一个Spider类，主要是初始化crawler和setting

    def _create_engine(self):
        return ExecutionEngine(self, lambda _: self.stop())

    @defer.inlineCallbacks
    def stop(self):
        if self.crawling:
            self.crawling = False
            yield defer.maybeDeferred(self.engine.stop)


class CrawlerRunner(object):
    """
    This is a convenient helper class that keeps track of, manages and runs
    crawlers inside an already setup Twisted `reactor`_.

    The CrawlerRunner object must be instantiated with a
    :class:`~scrapy.settings.Settings` object.

    This class shouldn't be needed (since Scrapy is responsible of using it
    accordingly) unless writing scripts that manually handle the crawling
    process. See :ref:`run-from-script` for an example.
    """

    crawlers = property(
        lambda self: self._crawlers,
        doc="Set of :class:`crawlers <scrapy.crawler.Crawler>` started by "
            ":meth:`crawl` and managed by this class."
    )  # 骚操作

    def __init__(self, settings=None):
        if isinstance(settings, dict) or settings is None:
            settings = Settings(settings)
        self.settings = settings
        self.spider_loader = _get_spider_loader(settings)  # self.spider_loader.load(spidercls) 加载所有爬虫，根据setting中定义的SPIDER_MODULES = ['czaSpider.spiders']
        self._crawlers = set()
        self._active = set()
        self.bootstrap_failed = False

    @property
    def spiders(self):
        warnings.warn("CrawlerRunner.spiders attribute is renamed to "
                      "CrawlerRunner.spider_loader.",
                      category=ScrapyDeprecationWarning, stacklevel=2)
        return self.spider_loader

    def crawl(self, crawler_or_spidercls, *args, **kwargs):
        """
        Run a crawler with the provided arguments.

        It will call the given Crawler's :meth:`~Crawler.crawl` method, while
        keeping track of it so it can be stopped later.

        If `crawler_or_spidercls` isn't a :class:`~scrapy.crawler.Crawler`
        instance, this method will try to create one using this parameter as
        the spider class given to it.

        Returns a deferred that is fired when the crawling is finished.

        :param crawler_or_spidercls: already created crawler, or a spider class
            or spider's name inside the project to create it
        :type crawler_or_spidercls: :class:`~scrapy.crawler.Crawler` instance,
            :class:`~scrapy.spiders.Spider` subclass or string

        :param list args: arguments to initialize the spider

        :param dict kwargs: keyword arguments to initialize the spider
        """
        crawler = self.create_crawler(crawler_or_spidercls)
        return self._crawl(crawler, *args, **kwargs)

    def _crawl(self, crawler, *args, **kwargs):
        self.crawlers.add(crawler)  # 把name爬虫加载进crawlers属性中去了
        d = crawler.crawl(*args, **kwargs)  # 调用爬虫的crawl方法，获取一个defer对象
        self._active.add(d)

        def _done(result):
            self.crawlers.discard(crawler)
            self._active.discard(d)
            self.bootstrap_failed |= not getattr(crawler, 'spider', None)
            return result

        return d.addBoth(_done)

    def create_crawler(self, crawler_or_spidercls):
        """
        Return a :class:`~scrapy.crawler.Crawler` object.

        * If `crawler_or_spidercls` is a Crawler, it is returned as-is.
        * If `crawler_or_spidercls` is a Spider subclass, a new Crawler
          is constructed for it.
        * If `crawler_or_spidercls` is a string, this function finds
          a spider with this name in a Scrapy project (using spider loader),
          then creates a Crawler instance for it.
        """
        if isinstance(crawler_or_spidercls, Crawler):
            return crawler_or_spidercls
        return self._create_crawler(crawler_or_spidercls)

    def _create_crawler(self, spidercls):
        if isinstance(spidercls, six.string_types):  # 这里是name，通过name加载对应的爬虫，很强
            spidercls = self.spider_loader.load(spidercls)  # 首次传入的是spider name，通过load加载。我去，首先会加载项目下所有爬虫，然后再单独加载某一爬虫嘛==僵硬啊
        return Crawler(spidercls, self.settings)  # 这里的spidercls，装的就是指定的爬虫吗

    def stop(self):
        """
        Stops simultaneously all the crawling jobs taking place.

        Returns a deferred that is fired when they all have ended.
        """
        return defer.DeferredList([c.stop() for c in list(self.crawlers)])

    @defer.inlineCallbacks
    def join(self):
        """
        join()

        Returns a deferred that is fired when all managed :attr:`crawlers` have
        completed their executions.
        """
        while self._active:
            yield defer.DeferredList(self._active)


class CrawlerProcess(CrawlerRunner):  # 针对执行后的爬虫，在终端监控特殊指令，进而执行相对应的功能
    """
    A class to run multiple scrapy crawlers in a process simultaneously.

    This class extends :class:`~scrapy.crawler.CrawlerRunner` by adding support
    for starting a Twisted `reactor`_ and handling shutdown signals, like the
    keyboard interrupt command Ctrl-C. It also configures top-level logging.

    This utility should be a better fit than
    :class:`~scrapy.crawler.CrawlerRunner` if you aren't running another
    Twisted `reactor`_ within your application.

    The CrawlerProcess object must be instantiated with a
    :class:`~scrapy.settings.Settings` object.

    :param install_root_handler: whether to install root logging handler
        (default: True)

    This class shouldn't be needed (since Scrapy is responsible of using it
    accordingly) unless writing scripts that manually handle the crawling
    process. See :ref:`run-from-script` for an example.
    """

    def __init__(self, settings=None, install_root_handler=True):
        super(CrawlerProcess, self).__init__(settings)
        install_shutdown_handlers(self._signal_shutdown)  # 监控键盘按键，然后发送signal.signal(相关指令)进行控制
        configure_logging(self.settings, install_root_handler)
        log_scrapy_info(self.settings)

    def _signal_shutdown(self, signum, _):
        install_shutdown_handlers(self._signal_kill)  # 这一步安装的监控，都是和键盘指令相关的耶
        signame = signal_names[signum]
        logger.info("Received %(signame)s, shutting down gracefully. Send again to force ",
                    {'signame': signame})
        reactor.callFromThread(self._graceful_stop_reactor)

    def _signal_kill(self, signum, _):
        install_shutdown_handlers(signal.SIG_IGN)
        signame = signal_names[signum]
        logger.info('Received %(signame)s twice, forcing unclean shutdown',
                    {'signame': signame})
        reactor.callFromThread(self._stop_reactor)

    def start(self, stop_after_crawl=True):
        """
        This method starts a Twisted `reactor`_, adjusts its pool size to
        :setting:`REACTOR_THREADPOOL_MAXSIZE`, and installs a DNS cache based
        on :setting:`DNSCACHE_ENABLED` and :setting:`DNSCACHE_SIZE`.

        If `stop_after_crawl` is True, the reactor will be stopped after all
        crawlers have finished, using :meth:`join`.

        :param boolean stop_after_crawl: stop or not the reactor when all
            crawlers have finished
        """
        if stop_after_crawl:
            d = self.join()
            # Don't start the reactor if the deferreds are already fired
            if d.called:
                return
            d.addBoth(self._stop_reactor)

        reactor.installResolver(self._get_dns_resolver())
        tp = reactor.getThreadPool()
        tp.adjustPoolsize(maxthreads=self.settings.getint('REACTOR_THREADPOOL_MAXSIZE'))
        reactor.addSystemEventTrigger('before', 'shutdown', self.stop)
        reactor.run(installSignalHandlers=False)  # blocking call

    def _get_dns_resolver(self):
        if self.settings.getbool('DNSCACHE_ENABLED'):
            cache_size = self.settings.getint('DNSCACHE_SIZE')
        else:
            cache_size = 0
        return CachingThreadedResolver(
            reactor=reactor,
            cache_size=cache_size,
            timeout=self.settings.getfloat('DNS_TIMEOUT')
        )

    def _graceful_stop_reactor(self):
        d = self.stop()
        d.addBoth(self._stop_reactor)
        return d

    def _stop_reactor(self, _=None):
        try:
            reactor.stop()
        except RuntimeError:  # raised if already stopped or in shutdown stage
            pass


def _get_spider_loader(settings):
    """ Get SpiderLoader instance from settings """
    if settings.get('SPIDER_MANAGER_CLASS'):
        warnings.warn(
            'SPIDER_MANAGER_CLASS option is deprecated. '
            'Please use SPIDER_LOADER_CLASS.',
            category=ScrapyDeprecationWarning, stacklevel=2
        )
    cls_path = settings.get('SPIDER_MANAGER_CLASS',  # 看来还是有限推荐使用管理类
                            settings.get('SPIDER_LOADER_CLASS'))  # SPIDER_LOADER_CLASS = 'scrapy.spiderloader.SpiderLoader'  # zty就是该的这里咯
    loader_cls = load_object(cls_path)
    try:
        verifyClass(ISpiderLoader, loader_cls)  # 即使重写，也必须要是重ISpider接口竭诚的是吧
    except DoesNotImplement:
        warnings.warn(
            'SPIDER_LOADER_CLASS (previously named SPIDER_MANAGER_CLASS) does '
            'not fully implement scrapy.interfaces.ISpiderLoader interface. '
            'Please add all missing methods to avoid unexpected runtime errors.',
            category=ScrapyDeprecationWarning, stacklevel=2
        )
    return loader_cls.from_settings(settings.frozencopy())  # 这是一个SpiderLoader对象的实例化  # 调用from_settings进行初始化
