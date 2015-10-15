#!/usr/bin/env python
# -*- coding:utf-8 -*-

import time
from datetime import timedelta
from tornado import httpclient, gen, ioloop, queues


class AsySpider(object):
    """A simple class of asynchronous spider."""
    def __init__(self, urls, concurrency=10):
        urls.reverse()
        self.urls = urls
        self.concurrency = concurrency
        self._q = queues.Queue()
        self._fetching = set()
        self._fetched = set()

    def handle_page(self, url, html):
        """inherit and rewrite this method"""
        print(url, html)

    @gen.coroutine
    def get_page(self, url, **kwargs):
        try:
            response = yield httpclient.AsyncHTTPClient().fetch(url, **kwargs)
            print('######fetched %s' % url)
        except Exception as e:
            print('Exception: %s %s' % (e, url))
            if e.code == 599:    # timeout or no response
                self._q.put(url)
            raise gen.Return(None)
        raise gen.Return(response.body)

    @gen.coroutine
    def _run(self):

        @gen.coroutine
        def fetch_url():
            current_url = yield self._q.get()
            try:
                if current_url in self._fetching:
                    return

                print('fetching****** %s' % current_url)
                self._fetching.add(current_url)
                html = yield self.get_page(current_url)
                self._fetched.add(current_url)

                if html is not None:
                    self.handle_page(current_url, html)

                for i in range(self.concurrency):
                    if self.urls:
                        yield self._q.put(self.urls.pop())

            finally:
                self._q.task_done()

        @gen.coroutine
        def worker():
            while True:
                yield fetch_url()

        self._q.put(self.urls.pop())

        # Start workers, then wait for the work queue to be empty.
        for _ in range(self.concurrency):
            worker()
        yield self._q.join(timeout=timedelta(seconds=300000))
        assert self._fetching == self._fetched

    def run(self):
        io_loop = ioloop.IOLoop.current()
        io_loop.run_sync(self._run)


def main():
    urls = []
    for page in range(-1, 0):
        urls.append('http://www.jb51.net/article/%s.htm' % page)
    s = AsySpider(urls, 10)
    s.run()

if __name__ == '__main__':
    main()