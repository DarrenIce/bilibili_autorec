import subprocess
from pymediainfo import MediaInfo
from utils.log import Log
import threading
import os
import re
import datetime
import time
import json

logger = Log()()


class Queue():
    def __init__(self, qname, func):
        self._lock = threading.Lock()
        self._lock2 = threading.Lock()
        self.queue = []
        self.qname = qname
        self.func = func

    def func_call(self, key):
        with self._lock2:
            logger.info('%s 开始%s' % (key, self.qname))
            self.func(key)


    def enqueue(self, key):
        with self._lock:
            if key not in self.queue:
                self.queue.append(key)
                logger.info('%s 进入%s等待队列' % (key,self.qname))
            else:
                self.queue.remove(key)
                self.queue.append(key)
                logger.info('%s 在%s等待队列中的状态更新了' % (key,self.qname))

    def dequeue(self):
        if self._lock2.locked():
            return None
        with self._lock:
            with self._lock2:
                if len(self.queue) > 0:
                    key = self.queue[0]
                    del self.queue[0]
                    logger.info('%s 退出%s等待队列' % (key,self.qname))
                    return key
                else:
                    return None

    def run(self):
        while True:
            time.sleep(1)
            if len(self.queue) > 0:
                key = self.dequeue()
                if key is not None:
                    threading.Thread(target=self.func_call, args=[key, ],daemon=True).start()

    def heartbeat(self):
        while True:
            time.sleep(60)
            logger.info('当前%s队列情况: %s' % (self.qname, ' '.join(self.queue)))
            if self.queue == []:
                time.sleep(300)
