import os
import logging
import threading


class Log():
    _first_init = True
    _lock = threading.Lock()
    _lock2 = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(Log, "_instance"):
            with Log._lock:
                if not hasattr(Log, "_instance"):
                    Log._instance = super(Log, cls).__new__(cls, *args, **kwargs)
        return Log._instance

    def __init__(self):
        if Log._first_init:
            with Log._lock2:
                if Log._first_init:
                    Log._first_init = False
                    self.logger = logging.getLogger()
                    self.logger.setLevel(logging.INFO)
                    fh = logging.FileHandler(
                        os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'log', 'log.log'),
                        mode='a', encoding='utf-8')
                    formatter = logging.Formatter(
                        '[%(levelname)s] %(asctime)s %(filename)s:%(lineno)d\tpid:%(thread)d\t%(message)s')
                    fh.setFormatter(formatter)
                    self.logger.addHandler(fh)

    def __call__(self):
        return self.logger
