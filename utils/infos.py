import threading
from utils.singleton import singleton
import copy


@singleton
class Infos():
    def __init__(self):
        self.live_infos = {}
        self._lock = threading.Lock()

    def __setitem__(self, key, value):
        with self._lock:
            self.live_infos[key] = value

    def __delitem__(self,key):
        with self._lock:
            del self.live_infos[key]

    def __getitem__(self,key):
        with self._lock:
            return self.live_infos[key]

    def copy(self):
        with self._lock:
            return copy.deepcopy(self.live_infos)

    def overload(self,live_infos):
        with self._lock:
            self.live_infos = live_infos
