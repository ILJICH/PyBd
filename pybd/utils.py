# -*- coding: utf-8 -*-
import logging
from re import findall
from select import select
from subprocess import PIPE, Popen
from time import sleep
from evdev import list_devices, InputDevice
from evdev import ecodes
from evdev.events import KeyEvent
from pybd.expression import Translator

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

def input_devices():
    devices = Popen(["xinput"], stdout=PIPE).communicate()[0]
    params = findall(r"\b([a-zA-Z0-9 _.]+?)\s*id=(\d*)", devices)
    return params

def listen_device(device):
    sleep(1)
    main = InputDevice("/dev/input/event0")
    while True:
        r,w,x = select([device, main], [], [])
        events = {}
        for dev in r:
            events[dev] = [event for event in dev.read()
                  if event.type == ecodes.EV_KEY
                    and KeyEvent(event).keystate is KeyEvent.key_down]
        if events.has_key(main):
            break
        for event in events[device]:
            name = Translator.key_to_name(KeyEvent(event)).upper()
            if name:
                print name

