import configparser

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

class Config():
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('conf/main.cfg')

        self.conf = dotdict()

        for section in self.config.sections():
            self.conf[section] = dotdict()
            for item in self.config.items(section):
                self.conf[section][item[0]] = item[1]

    def __getattr__(self,key):
        return self.conf[key]

# print(Config().user.csrf)