import threading
from utils.singleton import singleton
from utils.log import Log
import copy

logger = Log()()

@singleton
class Infos():
    def __init__(self):
        self.live_infos = {}
        self._lock = threading.Lock()
        logger.info('数据结构初始化完成')

    def update(self, key, value):
        with self._lock:
            if key not in self.live_infos:
                self.live_infos[key] = {}
            for k in value:
                self.live_infos[key][k] = value[k]

    def delete(self,key):
        with self._lock:
            del self.live_infos[key]

    def get(self,key):
        with self._lock:
            return self.live_infos[key]

    def copy(self):
        return copy.deepcopy(self.live_infos)

    def overload(self,live_infos):
        with self._lock:
            self.live_infos = live_infos


'''
'room_id': {
    'record_start_time': '',
    'need_rec': '1',
    'need_mask': '0',
    'maxsecond': '28800',
    'need_upload': '0',
    'duration': '0',
    'cookies': {
        'DedeUserID': '5259276',
        'DedeUserID__ckMd5': 'e86975bfe5e11d36',
        'SESSDATA': '276f5b3a%2C1610076024%2C0cb342c1',
        'bili_jct': '3ddd284537f568ad39cc15b3b9ff28dd',
        'sid': 'hx0tlrj8'
    },
    'base_path': 'C:\\Coding\\python\\bilibili_autorec\\rec',
    'room_id': '12607506',
    'real_id': 12607506,
    'live_status': 1,
    'uid': 353708919,
    'uname': '夢冬oTo',
    'save_name': '夢冬oTo_20201209112028.flv',
    'title': '【3D】无人声~喜欢·',
    'live_start_time': 1607436889,
    'recording': 0
}
'''