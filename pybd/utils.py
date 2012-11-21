# -*- coding: utf-8 -*-

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