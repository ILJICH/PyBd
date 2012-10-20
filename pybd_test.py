# -*- coding: utf-8 -*-
from subprocess import CalledProcessError, Popen, PIPE
from pybd import Dispatcher, DeviceManager, Interpreter

__author__ = 'iljich'

from unittest import main, TestCase


class DispatcherTest(TestCase):
    def setUp(self):
        self.dispatcher = Dispatcher("AT Translated Set 2 keyboard")


class DeviceManagerTest(TestCase):
    def setUp(self):
        self.device = DeviceManager()
        self.device.from_name("AT Translated Set 2 keyboard")

    def test_nonexistant(self):
        self.assertRaises(Exception, Dispatcher, "Nonexistent")
        self.device.device_name = "Dummy"
        self.assertRaises(CalledProcessError, self.device.set_state, 0)

    def test_set_state(self):
        self.device.set_state(0)
        output_1 = Popen(["xinput", "list-props", self.device.device_name],
            stdout=PIPE).communicate()[0]
        self.device.set_state(1)
        output_2 = Popen(["xinput", "list-props", self.device.device_name],
            stdout=PIPE).communicate()[0]
        self.assertNotEqual(output_1,output_2)

    def test_get_path(self):
        self.assertEqual(self.device.get_path(), "/dev/input/event0")


class ListenerTest(TestCase):
    def setUp(self):
        self.listener = Listener("/dev/input/event0")

    def test_step(self):
        self.assertIsNotNone(self.listener.step())

    def test_run(self):
        self.listener.run()
        self.listener.stop()


class InterpreterTest(TestCase):
    def setUp(self):
        self.interpreter = Interpreter()
        config = """{"main":{"user":"iljich","reset_key":"ESC","eol_key":"ENTER",
        "shift_key":"SHIFT",device_name:"AT Translated Set 2 keyboard"},"scripts":{"t":"touch 1","r":"rm 1","a*":"hello",
        "s *":"$1"}}"""
        self.interpreter.read_config(config)

    def test_config(self):
        self.assertEqual(self.interpreter.get_config("main", "user"), "iljich")
        self.assertEqual(self.interpreter.get_config("main", "foo", "dummy"), "")

    def test_process(self):
        self.assertEqual(self.interpreter.process("t"), "touch 1")
        self.assertEqual(self.interpreter.process("any"), "hello")
        self.assertEqual(self.interpreter.process("s ls"), "ls")


if __name__ == '__main__':
    main()
