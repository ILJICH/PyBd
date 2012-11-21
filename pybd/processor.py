# -*- coding: utf-8 -*-
from collections import defaultdict
from json import loads
from select import select
from evdev import ecodes, KeyEvent
from pybd.device import Device
from pybd.expression import Expression
from pybd.handler import HandlerFactory

__author__ = 'iljich'

def singleton(cls):
    instances = {}
    def inner(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return inner

@singleton
class Processor():
    event_buffer = []
    expressions = []
    devices = []

    def __init__(self, config_path):
        self.config = ConfigReader()
        for conf_file in ["defailts.conf", config_path]:
            with open(conf_file) as f:
                self.config = self.config.load(f.read())
        self.load_expressions()
        self.init_device()

    def load_expressions(self, sceme="default", flush=False):
        if flush:
            self.expressions = []
        for handler_header, expressions in self.config["expressions"][sceme].items():
            handler_name, handler_args = self.config.split_header(handler_header)
            Handler = HandlerFactory(handler_name, handler_args)
            for pattern, command in expressions.items():
                self.expressions.append((Expression(pattern), Handler(command)))

    def handle_event(self, event):
        self.event_buffer.append(event)
        flush = True
        for expression, handler in self.expressions:
            result, extracted = expression(self.event_buffer)
            if result is Expression.state_accept:
                handler(extracted)
                flush = True
                break
            if result is Expression.state_partial:
                flush = False
        if flush:
            self.flush_buffer() # either handled or cannot be

    def flush_buffer(self):
        self.event_buffer = []

    def init_device(self):
        device = Device(**self.config["device"])
        self.devices.append(device)

    def exit(self):
        for device in self.devices:
            device.exit()

    def run(self):
        while True:
            readable, w, x = select([device.listener for device in self.devices], [], [])
            events = [event for device in readable for event in device.read()
                      if event.type == ecodes.EV_KEY
                        and KeyEvent(event).keystate is not KeyEvent.key_hold]
            if events:
                for event in events:
                    self.handle_event(KeyEvent(event))


class d_dict(dict):
    def __getitem__(self, item):
        reply = self.get(item, None)
        return d_dict(reply) if isinstance(reply, dict) else reply


class ConfigReader():
    default_dict = lambda self, dict: defaultdict(lambda: None, dict)
    config = d_dict({})

    def __init__(self, config=""):
        self.load(config)

    def load(self, config=""):
        self.config.update(loads("\n".join([line for line in config.split("\n")
                                    if not line.strip().startswith("#")])))

    def __getitem__(self, item):
        return self.config[item]

    def split_header(self, header):
        args = header.split(" ")
        head, tail = args[0], args[1:]
        kwargs = [arg.split("=") for arg in tail]
        kwargs = [(kw[0], "=".join(kw[1:])) for kw in kwargs]
        return head, d_dict(kwargs)
