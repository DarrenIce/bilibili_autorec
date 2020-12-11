import subprocess
from pymediainfo import MediaInfo
from utils.log import Log
from utils.load_conf import Config
from utils.infos import Infos
import threading
import os
import re
import datetime
import time
import json

logger = Log()()


class Queue():
    def __init__(self):
        self._lock = threading.Lock()
        self._lock2 = threading.Lock()
        self.config = Config()
        self.infos = Infos()
        self.queue = []
        self.qname = ''
        self.func = lambda x:time.sleep(400)

    def func_call(self, key):
        with self._lock2:
            logger.info('%s 开始%s' % (self.infos.copy()[key]['uname'], self.qname))
            self.func(key)


    def enqueue(self, key):
        with self._lock:
            if key not in self.queue:
                self.queue.append(key)
                logger.info('%s 进入%s等待队列' % (self.infos.copy()[key]['uname'],self.qname))
            else:
                self.queue.remove(key)
                self.queue.append(key)
                logger.info('%s 在%s等待队列中的状态更新了' % (self.infos.copy()[key]['uname'],self.qname))

    def dequeue(self):
        if self._lock2.locked():
            return None
        with self._lock:
            with self._lock2:
                if len(self.queue) > 0:
                    key = self.queue[0]
                    del self.queue[0]
                    logger.info('%s 退出%s等待队列' % (self.infos.copy()[key]['uname'],self.qname))
                    return key
                else:
                    return None

    def run(self):
        threading.Thread(target=self.heartbeat,daemon=True).start()
        while True:
            time.sleep(1)
            if len(self.queue) > 0:
                key = self.dequeue()
                if key is not None:
                    threading.Thread(target=self.func_call, args=[key, ]).start()

    def heartbeat(self):
        while True:
            logger.info('当前%s队列情况: %s' % (self.qname, ' '.join([self.infos.copy()[key]['uname'] for key in self.queue])))
            if self.queue == []:
                time.sleep(300)
            else:
                time.sleep(60)
