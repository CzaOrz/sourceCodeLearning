"""
Downloader Middleware manager

See documentation in docs/topics/downloader-middleware.rst
"""
import six

from twisted.internet import defer

from scrapy.http import Request, Response
from scrapy.middleware import MiddlewareManager
from scrapy.utils.defer import mustbe_deferred
from scrapy.utils.conf import build_component_list


class DownloaderMiddlewareManager(MiddlewareManager):

    component_name = 'downloader middleware'

    @classmethod
    def _get_mwlist_from_settings(cls, settings):
        return build_component_list(  # 获取BASE中间件，这个厉害了
            settings.getwithbase('DOWNLOADER_MIDDLEWARES'))

    def _add_middleware(self, mw):  # 中间件的三个常用方法咯
        if hasattr(mw, 'process_request'):
            self.methods['process_request'].append(mw.process_request)
        if hasattr(mw, 'process_response'):
            self.methods['process_response'].appendleft(mw.process_response)
        if hasattr(mw, 'process_exception'):
            self.methods['process_exception'].appendleft(mw.process_exception)

    def download(self, download_func, request, spider):
        @defer.inlineCallbacks
        def process_request(request):
            for method in self.methods['process_request']:
                response = yield method(request=request, spider=spider)
                assert response is None or isinstance(response, (Response, Request)), \
                        'Middleware %s.process_request must return None, Response or Request, got %s' % \
                        (six.get_method_self(method).__class__.__name__, response.__class__.__name__)  # 规定返回类型，None，response，request这三种
                if response:  # 如果是空，则会继续处理所有的中间件，但是一旦不是了，就会提前跑路，对，应该就是这个意思，可以很骚
                    defer.returnValue(response)
            defer.returnValue((yield download_func(request=request,spider=spider)))

        @defer.inlineCallbacks
        def process_response(response):
            assert response is not None, 'Received None in process_response'
            if isinstance(response, Request):
                defer.returnValue(response)

            for method in self.methods['process_response']:
                response = yield method(request=request, response=response,
                                        spider=spider)
                assert isinstance(response, (Response, Request)), \
                    'Middleware %s.process_response must return Response or Request, got %s' % \
                    (six.get_method_self(method).__class__.__name__, type(response))
                if isinstance(response, Request):
                    defer.returnValue(response)
            defer.returnValue(response)

        @defer.inlineCallbacks
        def process_exception(_failure):
            exception = _failure.value
            for method in self.methods['process_exception']:
                response = yield method(request=request, exception=exception,
                                        spider=spider)
                assert response is None or isinstance(response, (Response, Request)), \
                    'Middleware %s.process_exception must return None, Response or Request, got %s' % \
                    (six.get_method_self(method).__class__.__name__, type(response))
                if response:
                    defer.returnValue(response)
            defer.returnValue(_failure)

        deferred = mustbe_deferred(process_request, request)  # 执行顺序，现执行request，再执行exception，最后才是response
        deferred.addErrback(process_exception)
        deferred.addCallback(process_response)
        return deferred
