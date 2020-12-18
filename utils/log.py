import os
import logging
import threading
from utils.load_conf import Config
from utils.singleton import singleton

@singleton
class Log():
    def __init__(self):
        self.logger = logging.getLogger()
        self.config = Config()
        self.setLevel(self.config.config['log']['level'])
        info_log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'log', 'info.log')
        debug_log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'log', 'debug.log')
        if not os.path.exists(info_log_path):
            with open(info_log_path, 'w', encoding='utf-8') as a:
                pass
        if not os.path.exists(debug_log_path):
            with open(debug_log_path, 'w', encoding='utf-8') as a:
                pass
        info_fh = logging.FileHandler(info_log_path,mode='a', encoding='utf-8')
        formatter = logging.Formatter(
            '[%(levelname)s]\t%(asctime)s\t%(filename)s:%(lineno)d\tpid:%(thread)d\t%(message)s')
        info_fh.setFormatter(formatter)
        self.logger.addHandler(info_fh)

        debug_fh = logging.FileHandler(debug_log_path,mode='a', encoding='utf-8')
        debug_fh.setFormatter(formatter)
        self.debug_logger = logging.getLogger()
        self.debug_logger.addHandler(debug_fh)
        self.debug_logger.setLevel(logging.DEBUG)
        self.debug_logger.info('log模块初始化完成')

    def __call__(self):
        return self.logger

    def setLevel(self,level):
        lmap = {
            'NOTSET':logging.NOTSET,
            'DEBUG':logging.DEBUG,
            'INFO':logging.INFO,
            'WARNING':logging.WARNING,
            'ERROR':logging.ERROR,
            'CRITICAL':logging.CRITICAL
        }
        self.logger.setLevel(lmap[level])
