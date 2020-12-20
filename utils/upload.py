from utils.log import Log
from utils.bilibili_api import video
from utils.infos import Infos
from utils.queue import Queue
from utils.singleton import singleton
import threading
import time
import os
import datetime

logger = Log()()

@singleton
class Upload(Queue):
    def __init__(self):
        super().__init__()
        self.qname = '上传'
        self.func = self.upload
        self.base_num = 2000

    def check_live(self, key):
        duration = self.infos.get(key)['duration']
        if duration == '0':
            return True
        lst = duration.split('-')
        now_time = datetime.datetime.now()
        if len(lst) == 2:
            start_time = datetime.datetime.strptime(lst[0], '%Y%m%d %H%M%S')
            end_time = datetime.datetime.strptime(lst[1], '%Y%m%d %H%M%S')
            if now_time > start_time and now_time < end_time:
                return True
            else:
                logger.debug('%s[RoomID:%s]不在直播时间段' % (self.infos.get(key)['uname'], key))
                return False
        else:
            return False

    def upload(self, key):
        room_lst = [i[0] for i in self.config.config['live']['room_info']]
        if key not in room_lst:
            return None
        live_info = self.infos.copy()[key]
        if live_info['live_status'] == 1 and self.check_live(key):
            logger.info('%s[RoomID:%s]直播中，暂不上传' % (live_info['uname'], live_info['room_id']))
            live_info['queue_status'] = 0
            self.infos.update(key,live_info)
            return None
        logger.info('%s[RoomID:%s]开始本次上传，投稿名称: %s, 本地位置: %s' % (live_info['uname'], live_info['room_id'],live_info['filename'],live_info['filepath']))
        try:
            filename = video.video_upload(live_info['filepath'], cookies=live_info['cookies'])
        except:
            logger.error('%s[RoomID:%s]上传失败' % (live_info['uname'], live_info['room_id']))
            self.enqueue(key)
            return None
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
        try:
            result = video.video_submit(data, cookies=live_info['cookies'])
            logger.info('上传结果: %s' % (result))
        except:
            logger.error('%s[RoomID:%s]投稿失败' % (live_info['uname'], live_info['room_id']))
            self.enqueue(key)
            return None