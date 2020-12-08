import toml
import threading


class Config():
    _first_init = True
    _lock = threading.Lock()
    _lock2 = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(Config, "_instance"):
            with Config._lock:
                if not hasattr(Config, "_instance"):
                    Config._instance = super(Config, cls).__new__(cls, *args, **kwargs)
        return Config._instance

    def __init__(self):
        if Config._first_init:
            with Config._lock2:
                if Config._first_init:
                    Config._first_init = False
                    with open('conf/tool.toml', "r", encoding='utf-8') as f:
                        self.config = toml.load(f)

    def load_cfg(self):
        with open('conf/tool.toml', "r", encoding='utf-8') as f:
            self.config = toml.load(f)
