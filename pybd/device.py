# -*- coding: utf-8 -*-
import logging
from re import search, findall
from subprocess import Popen, PIPE, check_call, check_output
from evdev.device import InputDevice
from evdev.util import list_devices

__author__ = 'iljich'

class DeviceError(Exception):
    pass

class Device(object):
    def __init__(self, xid=None, name=None, path=None, default_state=None):
        try:
            if path:
                self.from_path(path)
            elif xid:
                self.from_xid(xid)
            else:
                self.from_name(name)
            self.listener = [dev for dev in map(InputDevice, list_devices()) if dev.fn == self.path][0]
        except OSError as e:
            logging.critical("No xinput. %s", e)
            raise DeviceError
        except IndexError:
            logging.critical("Error opening device: not root")
            raise DeviceError
        self.initial_state = self.get_state()
        self.set_state(default_state or 0)

    def from_name(self, device_name):
        path = [dev.fn for dev in map(InputDevice, list_devices()) if dev.name==device_name]
        if not path:
            raise DeviceError("No device with name %s" % device_name)
        if len(path) > 1:
            raise DeviceError("Multiple devices with name %s, use xid or path instead" % device_name)
        self.path = path[0]
        devices = Popen(["xinput"], stdout=PIPE).communicate()[0]
        self.xid = search(r"\b%s\s*id=(\d*)" % device_name, devices).group(1)

    def from_xid(self, xid):
        self.xid = str(xid)
        info = Popen(["xinput", "list-props", str(xid)], stdout=PIPE).communicate()[0]
        try:
            self.path = search(r'Device Node \(\d*\):\s*"([a-zA-Z0-9_/]*)"', info).group(1)
        except AttributeError:
            raise DeviceError("No device with id %s" % xid)

    def from_path(self, path):
        self.path = path
        devices = Popen(["xinput"], stdout=PIPE).communicate()[0]
        xids = findall(r"\b%s\s*id=(\d*)" % InputDevice(path).name, devices)
        info = check_output(["xinput","list-props"] + xids)
        nodes = findall(r'Device Node \(\d*\):\s*"([a-zA-Z0-9_/]*)"', info)
        self.xid = xids[nodes.index(path)]

    def set_state(self, state):
        check_call(["xinput", "set-int-prop", str(self.xid),
                    "Device Enabled", "8", str(int(state))])

    def get_state(self):
        output = Popen(["xinput", "list-props", str(self.xid)],
            stdout=PIPE).communicate()[0]
        result = search(r'Device Enabled.*(\d)\n', output).group(1)
        return int(result)

    def toggle(self):
        state = self.get_state()
        if state:
            self.set_state(0)
        else:
            self.set_state(1)

    def exit(self):
        self.set_state(self.initial_state)
