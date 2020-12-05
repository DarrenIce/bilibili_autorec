import toml

class Config():
    def __init__(self):
        with open('conf/tool.toml', "r", encoding='utf-8') as f:
            self.config = toml.load(f)

    def load_cfg(self):
        with open('conf/tool.toml', "r", encoding='utf-8') as f:
            self.config = toml.load(f)

