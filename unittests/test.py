# -*- coding: utf-8 -*-
from itertools import permutations
from subprocess import CalledProcessError
from tempfile import NamedTemporaryFile
from evdev import KeyEvent, InputEvent
from pybd.device import Device, DeviceError
from pybd.expression import Expression
from pybd.handler import HandlerFactory
from pybd.processor import Processor, ConfigReader

__author__ = 'iljich'

from unittest import TestCase, main

class ConfigTest(TestCase):
    def setUp(self):
        try:
            f = open("test.conf")
        except IOError:
            f = open("unittests/test.conf")
        self.c = ConfigReader(f.read())
        f.close()

    def test_config(self):
        self.assertEqual(self.c["none"], None)
        self.assertEqual(self.c["device"]["none"], None)

    def test_split(self):
        handler_header, expressions =  self.c["expressions"]["default"].items()[0]
        handler, params = self.c.split_header(handler_header)
        self.assertEqual(params["user"], "iljich")
        self.assertEqual(params["none"], None)
        self.assertEqual(handler, "shell")

class DeviceManagerTest(TestCase):
    def setUp(self):
        self.device = Device(name="AT Translated Set 2 keyboard")

    def test_nonexistant(self):
        self.assertRaises(DeviceError, Device, None, "Nonexistent")
        self.assertRaises(DeviceError, Device, 22)
        self.device.xid = "Dummy"
        self.assertRaises(CalledProcessError, self.device.set_state, 0)

    def test_set_state(self):
        self.device.set_state(0)
        self.assertEqual(self.device.get_state(), 0)
        self.device.set_state(1)
        self.assertEqual(self.device.get_state(), 1)

    def test_from_xid(self):
        d = Device(name="AT Translated Set 2 keyboard")
        d1 = Device(xid=d.xid)
        self.assertEqual(d.path, d1.path)

    def test_from_path(self):
        d = Device(xid=10)
        d1 = Device(path=d.path)
        self.assertEqual(d.xid, d1.xid)

class ExpressionTest(TestCase):

    def test_function(self):
        ex = Expression()
        btn = ex.button(25)
        k = KeyEvent(InputEvent(0,0,0,25,1))
        k1 = KeyEvent(InputEvent(0,0,0,26,1))
        k2 = KeyEvent(InputEvent(0,0,0,25,0))
        self.assertEqual(btn([k]), (ex.state_accept, [], []))
        self.assertEqual(btn([k,k1]), (ex.state_accept, [k1], []))
        self.assertEqual(btn([k1,k]), (ex.state_reject, [k1,k], []))
        self.assertEqual(btn([k2,k]), (ex.state_accept, [], []))

        btn1 = ex.button(26)
        seq = ex.sequence(btn, btn1)
        self.assertEqual(seq([k]), (ex.state_partial, [], []))
        self.assertEqual(seq([k,k1]), (ex.state_accept, [], []))
        self.assertEqual(seq([k,k2]), (ex.state_partial, [], []))
        self.assertEqual(seq([k,k1,k2]), (ex.state_accept, [k2], []))
        self.assertEqual(seq([k,k2,k1]), (ex.state_accept, [], []))

        wild = ex.sequence(ex.wild(28))
        k3 = KeyEvent(InputEvent(0,0,0,28,1))
        self.assertEqual(wild([k,k1,k2,k3]), (ex.state_accept, [], [[k,k1]]))
        self.assertEqual(wild([k1,k3,k2,k]), (ex.state_accept, [k2,k], [[k1]]))
        self.assertEqual(wild([k1,k2]), (ex.state_partial, [], []))

        seq1 = ex.sequence(seq, wild)
        seq2 = ex.sequence(wild, seq1)
        self.assertEqual(seq1([k,k1,k2,k3]), (ex.state_accept, [], [[]]))
        self.assertEqual(seq2([k,k1,k3,k,k1,k2,k3]), (ex.state_accept, [], [[k,k1], []]))

    def test_parse(self):
        ex = Expression()
        self.assertEqual(ex.parse("a"), (["sequence" ,["literal", ["button", "a"]]], ""))
        self.assertEqual(ex.parse("ab"), (["sequence" ,["literal", ["button", "a"]],
                                              ["sequence", ["literal", ["button", "b"]]]], ""))
        self.assertEqual(ex.parse("a*b"), (["sequence" ,["literal", ["button", "a"]],
                                               ["sequence", ["literal", ["wild", "*"]],
                                                   ["sequence", ["literal", ["button", "b"]]]]], ""))
        self.assertEqual(ex.parse("<Enter>a"), (["sequence" ,["literal", ["button", "<Enter>"]],
                                                    ["sequence", ["literal", ["button", "a"]]]], ""))

    def test_translate_code(self):
        ex = Expression()
        matches = {"a": 30, "A": 30, "ENTER": 28, "NONE": None}
        for key, result in matches.items():
            self.assertEqual(ex.translate_code(key), result)

    def test_compile(self):
        ex = Expression()
        btn_a = ex.button(30)
        btn_b = ex.button(48)
        btn_enter = ex.button(28)
        btn_wild = ex.wild(28)
        key = lambda code, state: KeyEvent(InputEvent(0, 0, 0, code, state))
        keys = [key(code,state) for code in [28,30,46,48] for state in [0,1,2]]
        keysets = [list(i) for i in permutations(keys, 3)]
        matches = {
            "a": btn_a,
            "<Enter>": btn_enter,
            "ab": ex.sequence(btn_a, btn_b),
            "a*b": ex.sequence(btn_a, ex.sequence(btn_wild, btn_b))
        }
        for line, expected in matches.items():
            result_expected = map(expected, keysets)
            result_actual = map(ex.compile(ex.parse(line)[0]), keysets)
            data = [(e, a, keysets[i], ex.parse(line))\
            for i, (a, e) in enumerate(zip(result_actual, result_expected))\
            if a[0] != e[0] or a[2] != e[2]
            ]
            self.assertEquals(data, [])

    def test_init(self):
        ex = Expression("ab")
        keys = [KeyEvent(InputEvent(0, 0, 0, code, state))\
                for code in [30, 48] for state in [0, 1]]
        result, extracted = ex(keys)
        self.assertEqual(result, Expression.state_accept)
        self.assertEqual(extracted, [])

class HandlerTest(TestCase):
    def test_pipehandler(self):
        tmp = NamedTemporaryFile(delete=False)
        tmp.close()
        Handler = HandlerFactory("pipe", {"path":tmp.name})
        h = Handler("test")
        h([])
        with open(tmp.name,"r") as f:
            self.assertEqual(f.read(), "test")
        tmp.unlink(tmp.name)

    def test_clbhandler(self):
        tmp = NamedTemporaryFile(delete=False)
        tmp.file.write("def raise_(): raise FutureWarning\n")
        tmp.file.write("def raise__(smt): raise smt")
        tmp.close()

        Handler = HandlerFactory("callback", {"path": tmp.name})
        self.assertRaises(FutureWarning, Handler("raise_()"), [])
        self.assertRaises(FutureWarning, Handler("raise__({0})"), [FutureWarning])

        tmp.unlink(tmp.name)

if __name__ == '__main__':
    main()
