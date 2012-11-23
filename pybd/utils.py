# -*- coding: utf-8 -*-
import logging

__author__ = 'iljich'

def singleton(cls):
    instances = {}
    def inner(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return inner


class d_dict(dict):
    def __getitem__(self, item):
        reply = self.get(item, None)
        return d_dict(reply) if isinstance(reply, dict) else reply

class FileLikeLogger(object):
    """wraps a logging.Logger into a file like object"""

    fileno = lambda s: 1 # sys.stdout

    def __init__(self, level=logging.WARNING, logger="root"):
        self.level = level
        self.logger = logging.getLogger(logger)

    def write(self, str):
        str = str.rstrip("\n")
        if str:
            self.logger.log(self.level, str)

    def flush(self):
        for handler in self.logger.handlers:
            handler.flush()

    def close(self):
        for handler in self.logger.handlers:
            handler.close()