# -*- coding:utf-8 -*-

import yaml


# Control class
class Control:
    def __init__(self, config=None):
        if config is None:
            self.config = Config()

    # Parsing variable file
    def parsYaml(self, filename):
        with open(filename, "r") as f:
            s = yaml.load(f)
            version = 1.0
            if 'config' in s:
                c = s['config']
                if 'version' in c:
                    version = c['version']
                    self.config.version = version
                    if 'id' in c:
                        self.config.id = c['id']
                    else:
                        self.config.id = ''
                    if 'desc' in c:
                        self.config.desc = c['desc']
                    if 'cloud' in c:
                        self.config.cloud = c['cloud']
                    if 'mode' in c:
                        self.config.mode = c['mode']
                    if 'others' in c:
                        self.config.others = c['others']


class Config:
    def __init__(self, version=1.0, id='', desc=None):
        self.version = version
        self.id = id
        self.desc = desc
        self.cloud = 'inhand'
        self.mode = 'mqtt'
        self.others = None

    def has_option(self, section, option):
        return True if self.others and section in self.others and option in self.others[section] else False

    def get(self, section, option, raw=False, vars=None):
        return self.others[section][option]

    def getint(self, section, option, raw=False, vars=None):
        return int(self.others[section][option])