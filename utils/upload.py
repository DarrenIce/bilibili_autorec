from utils.log import Log
from utils.bilibili_api import video
from utils.load_conf import Config
import threading
import time
import os

logger = Log()()


class Upload():
    def __init__(self):
        self._lock = threading.Lock()
        self._lock2 = threading.Lock()
        self.config = Config()
        self.upload_queue = []

    def upload(self, live_info):
        logger.info('%s[RoomID:%s]等待上传' % (live_info['uname'], live_info['room_id']))
        with self._lock2:
            logger.info('%s[RoomID:%s]开始本次上传，投稿名称: %s, 本地位置: %s' % (live_info['uname'], live_info['room_id'],live_info['filename'],live_info['filepath']))
            filename = video.video_upload(live_info['filepath'], cookies=live_info['cookies'])
            logger.info('%s[RoomID:%s]%s上传成功' % (live_info['uname'], live_info['room_id'],live_info['filename']))
            data = {
                "copyright": 2,
                "source": "https://live.bilibili.com/%s" % live_info['room_id'],
                "cover": "",
                "desc": "",
                "desc_format_id": 0,
                "dynamic": "",
                "interactive": 0,
                "no_reprint": 0,
                "subtitles": {
                    "lan": "",
                    "open": 0
                },
                "tag": "录播,%s" % live_info['uname'],
                "tid": 174,
                "title": live_info['filename'],
                "videos": [
                    {
                        "desc": "",
                        "filename": filename,
                        "title": "P1"
                    }
                ]
            }
            result = video.video_submit(data, cookies=live_info['cookies'])
            logger.info('上传结果: %s' % (result))

    def enqueue(self, live_info):
        with self._lock:
            unames = {}
            live_info['expire'] = self.config.config['paras']['expire']
            for i in range(len(self.upload_queue)):
                unames[self.upload_queue[i]['uname']] = i
            if live_info['uname'] not in unames:
                self.upload_queue.append(live_info)
                logger.info('%s 进入上传等待队列' % live_info['uname'])
            else:
                del self.upload_queue[unames[live_info['uname']]]
                self.upload_queue.append(live_info)
                logger.info('%s 在上传等待队列中的状态更新了' % live_info['uname'])

    def dequeue(self):
        if self._lock2.locked():
            return None
        with self._lock:
            with self._lock2:
                if len(self.upload_queue) > 0 and self.upload_queue[0]['expire'] <= 0:
                    live_info = self.upload_queue[0]
                    del self.upload_queue[0]
                    if os.path.exists(live_info['filepath']):
                        logger.info('%s 本地文件存在，已转码完毕' % live_info['uname'])
                        logger.info('%s 退出上传等待队列' % live_info['uname'])
                        return live_info
                    else:
                        logger.info('%s 本地文件不存在，转码未完成，继续放回上传队列' % live_info['uname'])
                        live_info['expire'] = self.config.config['paras']['expire']
                        self.upload_queue.append(live_info)
                        return None
                else:
                    return None

    def run(self):
        while True:
            time.sleep(1)
            if len(self.upload_queue) > 0:
                with self._lock:
                    for i in range(len(self.upload_queue)):
                        self.upload_queue[i]['expire'] -= 1
                live_info = self.dequeue()
                if live_info is not None:
                    t = threading.Thread(target=self.upload, args=[live_info, ],daemon=True)
                    t.start()

    def heartbeat(self):
        while True:
            time.sleep(60)
            unames = [i['uname'] for i in self.upload_queue]
            logger.info('当前上传队列情况: %s' % (' '.join(unames)))
            if unames == []:
                time.sleep(300)

    def remove(self,live_infos):
        with self._lock:
            unames = {}
            for i in range(len(self.upload_queue)):
                unames[self.upload_queue[i]['uname']] = i
            for key in live_infos:
                if live_infos[key]['uname'] in unames:
                    del self.upload_queue[unames[live_infos[key]['uname']]]
                    logger.info('%s正在直播，移出上传队列' % live_infos[key]['uname'])
            