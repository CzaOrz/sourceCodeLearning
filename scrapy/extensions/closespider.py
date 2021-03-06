"""CloseSpider is an extension that forces spiders to be closed after certain
conditions are met.

See documentation in docs/topics/extensions.rst
"""

from collections import defaultdict

from twisted.internet import reactor

from scrapy import signals
from scrapy.exceptions import NotConfigured


class CloseSpider(object):

    def __init__(self, crawler):
        self.crawler = crawler

        self.close_on = {
            'timeout': crawler.settings.getfloat('CLOSESPIDER_TIMEOUT'),
            'itemcount': crawler.settings.getint('CLOSESPIDER_ITEMCOUNT'),
            'pagecount': crawler.settings.getint('CLOSESPIDER_PAGECOUNT'),
            'errorcount': crawler.settings.getint('CLOSESPIDER_ERRORCOUNT'),
            }

        if not any(self.close_on.values()):  # 好吧，原来是不能全为0的意思
            raise NotConfigured

        self.counter = defaultdict(int)

        if self.close_on.get('errorcount'):
            crawler.signals.connect(self.error_count, signal=signals.spider_error)
        if self.close_on.get('pagecount'):  # 这三貌似都没得
            crawler.signals.connect(self.page_count, signal=signals.response_received)
        if self.close_on.get('timeout'):
            crawler.signals.connect(self.spider_opened, signal=signals.spider_opened)
        if self.close_on.get('itemcount'):
            crawler.signals.connect(self.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(self.spider_closed, signal=signals.spider_closed)

    @classmethod
    def from_crawler(cls, crawler):  # from_crawler获取实例化对象
        return cls(crawler)

    def error_count(self, failure, response, spider):
        self.counter['errorcount'] += 1
        if self.counter['errorcount'] == self.close_on['errorcount']:
            self.crawler.engine.close_spider(spider, 'closespider_errorcount')  # 哦豁，直接就找到了，原来你就是直接调用的engine关闭爬虫的啊，看来zty也是copy的这里

    def page_count(self, response, request, spider):
        self.counter['pagecount'] += 1
        if self.counter['pagecount'] == self.close_on['pagecount']:
            self.crawler.engine.close_spider(spider, 'closespider_pagecount')

    def spider_opened(self, spider):
        self.task = reactor.callLater(self.close_on['timeout'], \
            self.crawler.engine.close_spider, spider, \
            reason='closespider_timeout')  # 在spider_opened中，直接挂起一个延迟任务

    def item_scraped(self, item, spider):
        self.counter['itemcount'] += 1
        if self.counter['itemcount'] == self.close_on['itemcount']:
            self.crawler.engine.close_spider(spider, 'closespider_itemcount')

    def spider_closed(self, spider):
        task = getattr(self, 'task', False)  # 我戳，这个task是指的什么玩意啊。好吧，原来是一个reactor.callLater
        if task and task.active():
            task.cancel()  # 不应该是task.stop吗


if __name__ == '__main__':
    print(any([10, 0, 0, 0]))