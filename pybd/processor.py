# -*- coding: utf-8 -*-
from collections import defaultdict
from json import loads
import logging
from os.path import dirname
from select import select
from evdev import ecodes, KeyEvent
from pybd.device import Device
from pybd.expression import Expression, Translator
from pybd.handler import HandlerFactory
from pybd.utils import singleton, d_dict

__author__ = 'iljich'

@singleton
class Processor():
    event_buffer = []
    expressions = []
    devices = []

    def __init__(self, config_path):
        with open(config_path) as f:
            self.config = ConfigReader(f.read())
        self.init_logging()
        logging.info("loading expressions")
        self.load_expressions()
        logging.info("initializing device")
        self.init_device()
        logging.debug("starting up done")

    def load_expressions(self, sceme="default", flush=False):
        if flush:
            self.expressions = []
        Expression.set_wildchar(self.config["processor"]["input_end_key"])
        for handler_header, expressions in self.config["expressions"][sceme].items():
            handler_name, handler_args = self.config.split_header(handler_header)
            Handler = HandlerFactory(handler_name, handler_args)
            for pattern, command in expressions.items():
                self.expressions.append((Expression(pattern), Handler(command)))

    def handle_event(self, event):
        self.event_buffer.append(event)
        logging.debug("caught key, new buffer: %s", self.event_buffer)
        if Translator.key_to_name(event) == self.config["processor"]["reset_key"]:
            self.flush_buffer()
            return
        handled = False
        result = Expression.state_reject
        for expression, handler in self.expressions:
            result, extracted = expression(self.event_buffer)
            if result is Expression.state_accept:
                handler(extracted)
                handled = True
                break
            elif result is Expression.state_partial:
                handled = True
            elif result is Expression.state_reject:
                pass
            else:
                raise AttributeError("Unexpected expression reply")
        logging.debug("reply: %s", ["accept", "reject", "partial"][result])
        if not handled:
            self.flush_buffer()

    def flush_buffer(self):
        self.event_buffer = []

    def init_device(self):
        device = Device(**self.config["device"])
        self.devices.append(device)

    def exit(self):
        logging.info("cleaning up")
        for device in self.devices:
            device.exit()

    def run(self):
        logging.info("starting main loop")
        while True:
            readable, w, x = select([device.listener for device in self.devices], [], [])
            events = [event for device in readable for event in device.read()
                      if event.type == ecodes.EV_KEY
                        and KeyEvent(event).keystate is not KeyEvent.key_hold]
            if events:
                for event in events:
                    self.handle_event(KeyEvent(event))

    def init_logging(self):
        logging.basicConfig(level=self.config["processor"]["loglevel"],
            format='%(asctime)s : [%(levelname)s]  %(message)s',
            filename=self.config["processor"]["logfile"], filemode="w+")
        logging.info("Logging system initialized")


class ConfigReader():
    default_dict = lambda self, dict: defaultdict(lambda: None, dict)
    config = d_dict({})

    def __init__(self, config="{}"):
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
