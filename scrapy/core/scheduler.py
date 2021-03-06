import os
import json
import logging
from os.path import join, exists

from scrapy.utils.reqser import request_to_dict, request_from_dict
from scrapy.utils.misc import load_object, create_instance
from scrapy.utils.job import job_dir

logger = logging.getLogger(__name__)


class Scheduler(object):

    def __init__(self, dupefilter, jobdir=None, dqclass=None, mqclass=None,
                 logunser=False, stats=None, pqclass=None):
        self.df = dupefilter
        self.dqdir = self._dqdir(jobdir)  # 还支持把他写到文件里面咯，存的是json
        self.pqclass = pqclass  # 优先级队列
        self.dqclass = dqclass  # lifo队列，经过pickle序列化，但没有存储到文件哦
        self.mqclass = mqclass  # 内存中，lifo队列，
        self.logunser = logunser
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):  # 这里是真正的实例化入口
        settings = crawler.settings
        dupefilter_cls = load_object(settings['DUPEFILTER_CLASS'])  # 'scrapy.dupefilters.RFPDupeFilter' 过滤的咯
        dupefilter = create_instance(dupefilter_cls, settings,
                                     crawler)  # objcls.from_crawler(crawler, *args, **kwargs)执行from-settings实例化
        pqclass = load_object(settings['SCHEDULER_PRIORITY_QUEUE'])  # 'queuelib.PriorityQueue'
        dqclass = load_object(
            settings['SCHEDULER_DISK_QUEUE'])  # 'scrapy.squeues.PickleLifoDiskQueue'，先进先出，使用pickle模块序列化
        mqclass = load_object(settings['SCHEDULER_MEMORY_QUEUE'])  # 'scrapy.squeues.LifoMemoryQueue'
        logunser = settings.getbool('LOG_UNSERIALIZABLE_REQUESTS', settings.getbool(
            'SCHEDULER_DEBUG'))  # ('LOG_UNSERIALIZABLE_REQUESTS', 'use SCHEDULER_DEBUG instead')
        return cls(dupefilter, jobdir=job_dir(settings), logunser=logunser,
                   stats=crawler.stats, pqclass=pqclass, dqclass=dqclass, mqclass=mqclass)  # 初始化时队列为空，并没有往里面推数据

    def has_pending_requests(self):
        return len(self) > 0

    def open(self, spider):  # 首先执行了这个，
        self.spider = spider
        self.mqs = self.pqclass(self._newmq)  # 创建优先级最低的队列。还是一个LIFO队列，，醉了
        self.dqs = self._dq() if self.dqdir else None
        return self.df.open()

    def close(self, reason):
        if self.dqs:
            prios = self.dqs.close()
            with open(join(self.dqdir, 'active.json'), 'w') as f:
                json.dump(prios, f)
        return self.df.close(reason)

    def enqueue_request(self, request):  # 终于走到了这，请求指纹过滤，如果没问题就把新的request请求push到队列中
        if not request.dont_filter and self.df.request_seen(request):
            self.df.log(request, self.spider)
            return False
        dqok = self._dqpush(request)  # 如果存在disk队列，就推到disk里面，不走mq-push的流程了
        if dqok:
            self.stats.inc_value('scheduler/enqueued/disk', spider=self.spider)
        else:
            self._mqpush(request)
            self.stats.inc_value('scheduler/enqueued/memory', spider=self.spider)
        self.stats.inc_value('scheduler/enqueued', spider=self.spider)
        return True

    def next_request(self):
        request = self.mqs.pop()  # 首次从mqs中取不出数据，转而重dqs中取上次剩下的数据，可以的
        if request:
            self.stats.inc_value('scheduler/dequeued/memory', spider=self.spider)
        else:
            request = self._dqpop()
            if request:
                self.stats.inc_value('scheduler/dequeued/disk', spider=self.spider)
        if request:
            self.stats.inc_value('scheduler/dequeued', spider=self.spider)
        return request

    def __len__(self):
        return len(self.dqs) + len(self.mqs) if self.dqs else len(self.mqs)

    def _dqpush(self, request):
        if self.dqs is None:
            return
        try:
            reqd = request_to_dict(request, self.spider)
            # reqd is {'url': 'https://www.baidu.com', 'callback': 'parse1', 'errback': None, 'method': 'GET', 'headers': {b'Accept': [b'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'], b'Accept-Language': [b'en'], b'User-Agent': [b'Scrapy/1.6.0 (+https://scrapy.org)'], b'Accept-Encoding': [b'gzip,deflate'], b'Referer': [b'https://www.baidu.com']}, 'body': b'', 'cookies': {}, 'meta': {'download_timeout': 180.0, 'download_slot': 'www.baidu.com', 'download_latency': 0.16184186935424805, 'depth': 1}, '_encoding': 'utf-8', 'priority': 0, 'dont_filter': True, 'flags': []}
            self.dqs.push(reqd, -request.priority)
        except ValueError as e:  # non serializable request
            if self.logunser:
                msg = ("Unable to serialize request: %(request)s - reason:"
                       " %(reason)s - no more unserializable requests will be"
                       " logged (stats being collected)")
                logger.warning(msg, {'request': request, 'reason': e},
                               exc_info=True, extra={'spider': self.spider})
                self.logunser = False
            self.stats.inc_value('scheduler/unserializable',
                                 spider=self.spider)
            return
        else:
            return True

    def _mqpush(self, request):  # 也就是对于设置了代理的爬虫可以早点让他重试是没问题的
        self.mqs.push(request, -request.priority)

    def _dqpop(self):
        if self.dqs:
            d = self.dqs.pop()
            if d:
                return request_from_dict(d, self.spider)

    def _newmq(self, priority):
        return self.mqclass()

    def _newdq(self, priority):
        return self.dqclass(join(self.dqdir, 'p%s' % priority))

    def _dq(self):
        activef = join(self.dqdir, 'active.json')
        if exists(activef):
            with open(activef) as f:
                prios = json.load(f)  # get the priority level of active.json
        else:
            prios = ()
        q = self.pqclass(self._newdq, startprios=prios)
        if q:
            logger.info("Resuming crawl (%(queuesize)d requests scheduled)",
                        {'queuesize': len(q)}, extra={'spider': self.spider})
        return q

    def _dqdir(self, jobdir):
        if jobdir:
            dqdir = join(jobdir, 'requests.queue')
            if not exists(dqdir):
                os.makedirs(dqdir)
            return dqdir
