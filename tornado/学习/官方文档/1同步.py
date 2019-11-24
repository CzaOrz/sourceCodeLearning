import asyncio
from tornado.httpclient import HTTPClient, AsyncHTTPClient
from tornado.concurrent import Future
loop = asyncio.get_event_loop()

def test(url):
    http_client = HTTPClient()
    response = http_client.fetch(url)
    return response.body
async def test1(url):  # ? 怎么执行啊
    http_client = AsyncHTTPClient()
    response = await http_client.fetch(url)
    return response.body
def test2(url):
    http_client = AsyncHTTPClient()
    my_future = Future()
    fetch_future = http_client.fetch(url)
    def on_fetch(f):
        my_future.set_result(f.result().body)
    fetch_future.add_done_callback(on_fetch)
    return my_future
#
# if __name__ == '__main__':
#     url = "http://fanyi.youdao.com/"
#     # for _ in range(10):
#     #     # print(test(url))
#     #     print(test1(url))
#
#     loop.run_until_complete(asyncio.wait([test1(url) for _ in range(10)]))



from html.parser import HTMLParser

def get_links(html):
    class UrlSeeker(HTMLParser):
        def __init__(self):
            super(UrlSeeker, self).__init__()
            self.urls = set()
            self.url = []
        def handle_starttag(self, tag, attrs):
            href = dict(attrs).get("href")
            if href and tag == "a":
                self.url.append(href)
                self.urls.add(href)
    url_seeker = UrlSeeker()
    url_seeker.feed(html)
    return url_seeker.urls

if __name__ == '__main__':
    html = """


<!DOCTYPE html>

<html xmlns="http://www.w3.org/1999/xhtml" lang="zh_CN">
  <head>
    <meta charset="utf-8" /><title>3.8.0 Documentation</title>
    <link rel="stylesheet" href="_static/pydoctheme.css" type="text/css" />
    <link rel="stylesheet" href="_static/pygments.css" type="text/css" />
    
    <script type="text/javascript" id="documentation_options" data-url_root="./" src="_static/documentation_options.js"></script>
    <script type="text/javascript" src="_static/jquery.js"></script>
    <script type="text/javascript" src="_static/underscore.js"></script>
    <script type="text/javascript" src="_static/doctools.js"></script>
    <script type="text/javascript" src="_static/language_data.js"></script>
    <script type="text/javascript" src="_static/translations.js"></script>
    
    <script type="text/javascript" src="_static/sidebar.js"></script>
    
    <link rel="search" type="application/opensearchdescription+xml"
          title="在 Python 3.8.0 文档 中搜索"
          href="_static/opensearch.xml"/>
    <link rel="author" title="关于这些文档" href="about.html" />
    <link rel="index" title="索引" href="genindex.html" />
    <link rel="search" title="搜索" href="search.html" />
    <link rel="copyright" title="版权所有" href="copyright.html" />
    <link rel="canonical" href="https://docs.python.org/3/index.html" />
    
      
      <script type="text/javascript" src="_static/switchers.js"></script>
      
    

    
    <style>
      @media only screen {
        table.full-width-table {
            width: 100%;
        }
      }
    </style>

    <link rel="shortcut icon" type="image/png" href="_static/py.png" />
    
    <script type="text/javascript" src="_static/copybutton.js"></script>
    
     


  </head><body>
  
    <div class="related" role="navigation" aria-label="related navigation">
      <h3>导航</h3>
      <ul>
        <li class="right" style="margin-right: 10px">
          <a href="genindex.html" title="总目录"
             accesskey="I">索引</a></li>
        <li class="right" >
          <a href="py-modindex.html" title="Python 模块索引"
             >模块</a> |</li>

    <li><img src="_static/py.png" alt=""
             style="vertical-align: middle; margin-top: -1px"/></li>
    <li><a href="https://www.python.org/">Python</a> &#187;</li>
    

    <li>
      <span class="language_switcher_placeholder">zh_CN</span>
      <span class="version_switcher_placeholder">3.8.0</span>
      <a href="#">文档</a> &#187;
    </li>

    <li class="right">
        

    <div class="inline-search" style="display: none" role="search">
        <form class="inline-search" action="search.html" method="get">
          <input placeholder="快速搜索" type="text" name="q" />
          <input type="submit" value="转向" />
          <input type="hidden" name="check_keywords" value="yes" />
          <input type="hidden" name="area" value="default" />
        </form>
    </div>
    <script type="text/javascript">$('.inline-search').show(0);</script>
         |
    </li>

      </ul>
    </div>    

    <div class="document">
      <div class="documentwrapper">
        <div class="bodywrapper">
          <div class="body" role="main">
            
  <h1>Python 3.8.0 文档</h1>
  <p>
  欢迎！这里是 Python 3.8.0 的中文文档。
  </p>
  <p><strong>按章节浏览文档：</strong></p>
  <table class="contentstable" align="center"><tr>
    <td width="50%">
      <p class="biglink"><a class="biglink" href="whatsnew/3.8.html">Python 3.8 有什么新变化？</a><br/>
        <span class="linkdescr"> 或显示自 2.0 以来的<a href="whatsnew/index.html">全部新变化</a></span></p>
      <p class="biglink"><a class="biglink" href="tutorial/index.html">入门教程</a><br/>
         <span class="linkdescr">从这里看起</span></p>
      <p class="biglink"><a class="biglink" href="library/index.html">标准库参考</a><br/>
         <span class="linkdescr">放在枕边作为参考</span></p>
      <p class="biglink"><a class="biglink" href="reference/index.html">语言参考</a><br/>
         <span class="linkdescr">讲解基础内容和基本语法</span></p>
      <p class="biglink"><a class="biglink" href="using/index.html">安装和使用 Python</a><br/>
         <span class="linkdescr">各种操作系统的介绍都有</span></p>
      <p class="biglink"><a class="biglink" href="howto/index.html">Python 常用指引</a><br/>
         <span class="linkdescr">深入了解特定主题</span></p>
    </td><td width="50%">
      <p class="biglink"><a class="biglink" href="installing/index.html">安装 Python 模块</a><br/>
         <span class="linkdescr">从官方的 PyPI 或者其他来源安装模块</span></p>
      <p class="biglink"><a class="biglink" href="distributing/index.html">分发 Python 模块</a><br/>
         <span class="linkdescr">发布模块，供其他人安装</span></p>
      <p class="biglink"><a class="biglink" href="extending/index.html">扩展和嵌入</a><br/>
         <span class="linkdescr">给 C/C++ 程序员的教程</span></p>
      <p class="biglink"><a class="biglink" href="c-api/index.html">Python/C API 接口</a><br/>
         <span class="linkdescr">给 C/C++ 程序员的参考手册</span></p>
      <p class="biglink"><a class="biglink" href="faq/index.html">常见问题</a><br/>
         <span class="linkdescr">经常被问到的问题（答案也有！）</span></p>
    </td></tr>
  </table>

  <p><strong>索引和表格：</strong></p>
  <table class="contentstable" align="center"><tr>
    <td width="50%">
      <p class="biglink"><a class="biglink" href="py-modindex.html">全局模块索引</a><br/>
         <span class="linkdescr">快速查看所有的模块</span></p>
      <p class="biglink"><a class="biglink" href="genindex.html">总目录</a><br/>
         <span class="linkdescr">所的函数，类，术语</span></p>
      <p class="biglink"><a class="biglink" href="glossary.html">术语表</a><br/>
         <span class="linkdescr">解释最重要的术语</span></p>
    </td><td width="50%">
      <p class="biglink"><a class="biglink" href="search.html">搜索页面</a><br/>
         <span class="linkdescr">搜索文档</span></p>
      <p class="biglink"><a class="biglink" href="contents.html">完整的内容表</a><br/>
         <span class="linkdescr">列出所有的章节和部分</span></p>
    </td></tr>
  </table>

  <p><strong>元信息：</strong></p>
  <table class="contentstable" align="center"><tr>
    <td width="50%">
      <p class="biglink"><a class="biglink" href="bugs.html">报告 Bug</a></p>
      <p class="biglink"><a class="biglink" href="https://devguide.python.org/docquality/#helping-with-documentation">向文档提交贡献</a></p>
      <p class="biglink"><a class="biglink" href="about.html">关于此文档</a></p>
    </td><td width="50%">
      <p class="biglink"><a class="biglink" href="license.html">Python 的历史和许可证</a></p>
      <p class="biglink"><a class="biglink" href="copyright.html">版权所有</a></p>
    </td></tr>
  </table>

          </div>
        </div>
      </div>
      <div class="sphinxsidebar" role="navigation" aria-label="main navigation">
        <div class="sphinxsidebarwrapper"><h3>下载</h3>
<p><a href="download.html">下载这些文档</a></p>
<h3>各版本文档</h3>
<ul>
  <li><a href="https://docs.python.org/3.9/">Python 3.9 （开发中）</a></li>
  <li><a href="https://docs.python.org/3.8/">Python 3.8 （稳定版）</a></li>
  <li><a href="https://docs.python.org/3.7/">Python 3.7 （稳定版）</a></li>
  <li><a href="https://docs.python.org/3.6/">Python 3.6 （安全修正）</a></li>
  <li><a href="https://docs.python.org/3.5/">Python 3.5 （安全修正）</a></li>
  <li><a href="https://docs.python.org/2.7/">Python 2.7 （稳定版）</a></li>
  <li><a href="https://www.python.org/doc/versions/">所有版本</a></li>
</ul>

<h3>其他资源</h3>
<ul>
  
  <li><a href="https://www.python.org/dev/peps/">PEP 索引</a></li>
  <li><a href="https://wiki.python.org/moin/BeginnersGuide">初学者指南（维基）</a></li>
  <li><a href="https://wiki.python.org/moin/PythonBooks">推荐书单</a></li>
  <li><a href="https://www.python.org/doc/av/">音视频小讲座</a></li>
  <li><a href="https://devguide.python.org/">Python 开发者指南</a></li>
</ul>
        </div>
      </div>
      <div class="clearer"></div>
    </div>  
    <div class="related" role="navigation" aria-label="related navigation">
      <h3>导航</h3>
      <ul>
        <li class="right" style="margin-right: 10px">
          <a href="genindex.html" title="总目录"
             >索引</a></li>
        <li class="right" >
          <a href="py-modindex.html" title="Python 模块索引"
             >模块</a> |</li>

    <li><img src="_static/py.png" alt=""
             style="vertical-align: middle; margin-top: -1px"/></li>
    <li><a href="https://www.python.org/">Python</a> &#187;</li>
    

    <li>
      <span class="language_switcher_placeholder">zh_CN</span>
      <span class="version_switcher_placeholder">3.8.0</span>
      <a href="#">文档</a> &#187;
    </li>

    <li class="right">
        

    <div class="inline-search" style="display: none" role="search">
        <form class="inline-search" action="search.html" method="get">
          <input placeholder="快速搜索" type="text" name="q" />
          <input type="submit" value="转向" />
          <input type="hidden" name="check_keywords" value="yes" />
          <input type="hidden" name="area" value="default" />
        </form>
    </div>
    <script type="text/javascript">$('.inline-search').show(0);</script>
         |
    </li>

      </ul>
    </div>  
    <div class="footer">
    &copy; <a href="copyright.html">版权所有</a> 2001-2019, Python Software Foundation.
    <br />

    The Python Software Foundation is a non-profit corporation.
<a href="https://www.python.org/psf/donations/">Please donate.</a>
<br />
    <br />

    最后更新于 11月 24, 2019.
    <a href="https://docs.python.org/3/bugs.html">Found a bug</a>?
    <br />

    Created using <a href="http://sphinx.pocoo.org/">Sphinx</a> 2.0.1.
    </div>

  </body>
</html>
    """
    from pprint import pprint
    # pprint(get_links(html))
    from minitools import UrlParser
    from urllib.parse import urljoin
    # pprint(UrlSeeker.get_links(html))
    url = "htt"
    for i in UrlParser.get_links(html, "http://fanyi.youdao.com/"):
        print(i)

