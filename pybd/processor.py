# -*- coding: utf-8 -*-
from collections import defaultdict
from json import loads
from select import select
from unittest import TestCase
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

#@singleton
class Processor():
    event_buffer = []
    expressions = []
    devices = []

    def __init__(self, config_path):
        with open(config_path) as f:
            self.config = ConfigReader(f.read())
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
            print result,
            if result is Expression.state_accept:
                handler(extracted)
                flush = True
                break
            if result is Expression.state_partial:
                flush = False
        if flush:
            self.flush_buffer() # either handled or cannot be
        print [(key.keycode[4:], key.keystate) for key in self.event_buffer]

    def flush_buffer(self):
        self.event_buffer = []

    def init_device(self):
        state = 1 if self.config["device"]["default_state"].upper() in ["1", "ON", "TRUE"] else 0
        conf = self.config["device"].copy()
        conf.update({"default_state":state})
        device = Device(**conf)
        self.devices.append(device)

    def exit(self):
        for device in self.devices:
            device.exit()

    def run(self):
        while True:
            r, w, x = select([device.listener for device in self.devices], [], [])
            events = [event for device in r for event in device.read()
                      if event.type == ecodes.EV_KEY
                        and KeyEvent(event).keystate is not KeyEvent.key_hold]
            if events:
                for event in events:
                    self.handle_event(KeyEvent(event))


class ConfigReader():
    default_dict = lambda self, dict: defaultdict(lambda: None, dict)

    def __init__(self, config=""):
        self.config = d_dict(loads("\n".join([line for line in config.split("\n")
                                    if not line.strip().startswith("#")])))

    def __getitem__(self, item):
        return self.config[item]

    def split_header(self, header):
        args = header.split(" ")
        head, tail = args[0], args[1:]
        kwargs = [arg.split("=") for arg in tail]
        kwargs = [(kw[0], "=".join(kw[1:])) for kw in kwargs]
        return head, d_dict(kwargs)

class d_dict(dict):
    def __getitem__(self, item):
        reply = self.get(item, None)
        return d_dict(reply) if isinstance(reply, dict) else reply



class ProcessorTest(TestCase):
    def test_init(self):
        processer = Processor("test.conf")
        expression = processer.expressions[0][0]

class ConfigTest(TestCase):
    def setUp(self):
        with open("test.conf") as f:
            self.c = ConfigReader(f.read())

    def test_config(self):
        self.assertEqual(self.c["none"], None)
        self.assertEqual(self.c["device"]["none"], None)

    def test_split(self):
        handler_header, expressions =  self.c["expressions"]["default"].items()[0]
        handler, params = self.c.split_header(handler_header)
        self.assertEqual(params["user"], "iljich")
        self.assertEqual(params["none"], None)
        self.assertEqual(handler, "shell")