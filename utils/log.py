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
        fh = logging.FileHandler(
            os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'log', 'log.log'),
            mode='a', encoding='utf-8')
        formatter = logging.Formatter(
            '[%(levelname)s]\t%(asctime)s\t%(filename)s:%(lineno)d\tpid:%(thread)d\t%(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.info('log模块初始化完成')

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
