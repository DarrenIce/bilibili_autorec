from utils.log import Log
from utils.bilibili_api import video

logger = Log()()

class Upload():
    def __init__(self,uname,roomid,filepath,filename,cookies):
        self.uname = uname
        self.roomid = roomid
        self.filepath = filepath
        self.filename = filename
        self.cookies = cookies

    def upload(self):
        logger.info('%s[RoomID:%s]开始本次上传' % (self.uname,self.roomid))
        filename = video.video_upload(self.filepath,cookies=self.cookies)
        data = {
            "copyright": 2,
            "source": "https://live.bilibili.com/%s" % self.roomid,
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
            "tag": "录播,%s" % self.uname,
            "tid": 174,
            "title": self.filename,
            "videos": [
                {
                    "desc": "",
                    "filename": filename,
                    "title": "P1"
                }
            ]
        }
        result = video.video_submit(data,cookies=self.cookies)
        logger.info('上传结果: %s' % (result))