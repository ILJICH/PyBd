# -*- coding: utf-8 -*-
from json import loads
import logging
from re import search
from select import select
from subprocess import check_call, CalledProcessError, call, Popen, PIPE
from evdev import InputDevice, ecodes, list_devices, KeyEvent

__author__ = "iljich"

class DeviceError(Exception):
    pass

class Dispatcher(object):
    _config = {}
    events = []
    expressions = {}

    def __init__(self, config):
        self.read_config(config)
        self.device = DeviceManager().from_name(
            self.get_config("main", "device"))
        self.listener = InputDevice(self.device.path)
        self.interpreter = Interpreter(self)

    def read_config(self, config):
        self._config = loads(config)

    def get_config(self, *args):
        child = self._config
        for name in args:
            child = child.get(name, "")
            if not child:
                break
        return child

    def run(self):
        while True:
            r, w, x = select([self.listener], [], [])
            events = [event for event in self.listener.read()
                      if event.type == ecodes.EV_KEY]
            if events:
                self.interpreter.process(events)

    def exit(self):
        self.device.exit()



class DeviceManager(object):
    def from_name(self, device_name):
        self.device_name = device_name
        call("export DISPLAY=:0", shell=True)
        try:
            check_call(["xinput", "list-props", device_name])
            self.path = self.get_path()
        except OSError as error:
            logging.critical("No xinput. %s", error)
        except CalledProcessError as error:
            logging.critical("X error. %s", error)
        except DeviceError as error:
            logging.critical("No device with name %s", self.device_name)
        self.initial_state = self.get_state()

    def get_path(self):
        devices = map(InputDevice, list_devices())
        for device in devices:
            if device.name == self.device_name:
                return device.fn
            # shoud not be reached normally, CalledProcessError would be raised above instead
        raise DeviceError("No such device")

    def set_state(self, state):
        check_call(["xinput", "set-int-prop", self.device_name,
                    "Device Enabled", "8", str(state)])
    def get_state(self):
        output = Popen(["xinput", "list-props", self.device_name],
            stdout=PIPE).communicate()[0]
        result = search(r'Device Enabled.*(\d)\n', output).group(1)
        return int(result)

    def turn_on(self):
        self.set_state('1')

    def turn_off(self):
        self.set_state('0')

    def toggle(self):
        state = self.get_state()
        if state:
            self.turn_off()
        else:
            self.turn_on()

    def exit(self):
        self.set_state(self.initial_state)

class Interpreter():
    expressions = {}

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        expressions = self.dispatcher.get_config("expressions").items()
        for handler_name, expressions_ in expressions:
            Handler = HandlerFactory(handler_name)
            for pattern, handler in expressions_.items():
                self.expressions[Expression(pattern)] = Handler(handler)

    def process(self, events):
        for event in events:
            self.events.append(event)
            if self.process_internally() or self.process_externally():
                self.events = []

    def process_internally(self):
        return False

    def process_externally(self):
        for expression, handler in self.dispatcher.get_config("scripts").items():
            reply = expression.process(self.events)
            if reply is True:
                handler.run()
            elif reply:
                handler.run(reply)
            else:
                continue
            return True
        return False



class Expression(object):
    literals = []

    def __init__(self, pattern):
        for letter in pattern:
            if letter == "*":
                self.literals.append(Sequence())

    def process(self, command):
        items = (item for item in command)
        result = ""
        for literal in self.literals:
            state = Literal.state_accept
            while state is Literal.state_accept:
                state, reply = literal.process()
                if reply is not None:
                    result += reply
            if state is Literal.state_reject:
                return False, None
        return True, result if result else None

class Literal():
    state_end = 0
    state_reject = 1
    state_accept = 2

    def __init__(self, keycode):
        self.keycode = keycode

    def process(self, event):
        if event.keystate == KeyEvent.key_down:
            return event.keycode == self.keycode, None
        else:
            return self.state_accept, None

class Sequence(Literal):
    def process(self, event):
        if event.keystate == KeyEvent.key_down:
            if event.keycode == self.keycode:
                return self.state_end, None
            else:
                char = self.keycode[4:]
                if len(char) == 1:
                    return self.state_accept, char
                else:
                    return self.state_accept, None
        return self.state_accept, None