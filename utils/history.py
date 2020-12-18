'''
开播时间
下播时间
开播时每5分钟输出一次状态
转码、上传的状态
'''
import os
import time
import threading
import datetime

from utils.log import Log
from utils.infos import Infos
from utils.singleton import singleton

@singleton
class History():
    def __init__(self):
        self._lock = threading.Lock()
        self.live_infos = Infos()
        self.base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'history')
        self.init()
        Log().debug_logger('History模块初始化完成')

    def init(self):
        if not os.path.exists(self.base_path):
            os.mkdir(self.base_path)
        for key in self.live_infos.copy():
            history_file = os.path.join(self.base_path, '%s_%s' % (key, self.live_infos.get(key)['uname']))
            if not os.path.exists(history_file):
                with open(history_file,'w',encoding='utf-8') as a:
                    pass

    def add_info(self, key, para, output):
        self.init()
        history_file = os.path.join(self.base_path, '%s_%s' % (key, self.live_infos.get(key)['uname']))
        with self._lock:
            with open(history_file, 'a', encoding='utf-8') as a:
                a.write('####📢 %s, 当前%s状态为: %s, 当前时间: %s\n' % (output, para, self.live_infos.get(key)[para], datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    def heartbeat(self):
        while True:
            time.sleep(600)
            self.init()
            for key in self.live_infos.copy():
                history_file = os.path.join(self.base_path, '%s_%s' % (key, self.live_infos.get(key)['uname']))
                with self._lock:
                    with open(history_file, 'a', encoding='utf-8') as a:
                        a.write('####✨ 当前时间: %s\n' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                        a.write('录制时段: %s\n' % (self.live_infos.get(key)['duration']))
                        a.write('直播状态: %s\n' % (self.live_infos.get(key)['live_status']))
                        a.write('录制状态: %s\n' % (self.live_infos.get(key)['recording']))
                        a.write('是否录制: %s\n' % (self.live_infos.get(key)['need_rec']))
                        a.write('是否遮挡: %s\n' % (self.live_infos.get(key)['need_mask']))
                        a.write('是否上传: %s\n' % (self.live_infos.get(key)['need_upload']))
                        
