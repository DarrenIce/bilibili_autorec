from utils.singleton import singleton
from utils.log import Log
import threading
import time

logger = Log()()

@singleton
class threadRecorder():
    def __init__(self):
        self.threads = {}
        self._lock = threading.Lock()
        logger.info('threadRecoder 初始化完成')

    def add(self,tname,func,args,daemon):
        with self._lock:
            if args is not None:
                a = threading.Thread(target=func,args=args,daemon=daemon)
            else:
                a = threading.Thread(target=func,daemon=daemon)
            a.start()
            self.threads[a.native_id] = [tname,a]
            logger.info('[%s:%s]线程已启动，当前调起线程数: %s' % (a.native_id,tname, threading.active_count()-4))
    
    def heartbeat(self):
        while True:
            time.sleep(180)
            logger.info('%s' % threading.enumerate())
            need_del = []
            with self._lock:
                for pid in self.threads:
                    if not self.threads[pid][1].is_alive():
                        need_del.append(pid)
                for pid in need_del:
                    logger.info('[%s:%s]已结束' % (pid,self.threads[pid][0]))
                    del self.threads[pid]
                op_lst = ['[%s:%s]' % (pid,self.threads[pid][0]) for pid in self.threads]
                logger.info('当前调起线程数: %s, Details: %s' % (threading.active_count()-4, ', '.join(op_lst)))