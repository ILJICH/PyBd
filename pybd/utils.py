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

class FileLikeLogger:
    """wraps a logging.Logger into a file like object"""
    def __init__(self, level=logging.WARNING, logger="root"):
        self.level = level
        self.logger = logger

    def write(self, str):
        str = str.rstrip() #get rid of all tailing newlines and white space
        if str: #don't log emtpy lines
            for line in str.split('\n'):
                logging.getLogger(self.logger).log(self.level, line) #critical to log at any logLevel

    def flush(self):
        for handler in logging.getLogger(self.logger).handlers:
            handler.flush()

    def close(self):
        for handler in logging.getLogger(self.logger).handlers:
            handler.close()