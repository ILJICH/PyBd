# -*- coding: utf-8 -*-
from re import match
from unittest import TestCase
from Xlib import XK
from Xlib.display import Display
from evdev import KeyEvent, InputEvent, ecodes
from itertools import permutations

__author__ = 'iljich'

class Expression():
    state_accept = 0
    state_reject = 1
    state_partial = 2
    wildchar = 28
    grammar = {
        "literal": [["button"], ["wild"]],
        "button": [["[0-9a-zA-Z]"], ["<[0-9a-zA-Z_]*>"]],
        "sequence": [["literal", "sequence"], ["literal"]],
        "wild": [["[*]"]]
    }

    def __init__(self, pattern = "", wildchar = 28):
        self.wildchar = wildchar
        if pattern:
            parsed, extra = self.parse(pattern)
            if extra:
                raise ValueError("Not valid pattern: %s" % pattern)
            self.compiled = self.compile(parsed)
        else:
            self.compiled = lambda x: self.state_reject, [], []

    def __call__(self, keys):
        return self.process(keys)

    def process(self, keys):
        state, extra, extracted = self.compiled(keys)
        reply = ["".join(key.keycode[4:].lower() for key in reply_) for reply_ in extracted]
        return self.state_reject if len(extra) else state, reply

    def parse_seq(self, seq, text):
        result = []
        for atom in seq:
            tree, text = self.parse(text, atom)
            if text is None:
                return None, None
            result.append(tree)
        return result, text

    def parse(self, text, atom="sequence"):
        if atom in self.grammar:
            for variant in self.grammar[atom]:
                tree, rem = self.parse_seq(variant, text)
                if rem is not None:
                    return [atom] + tree, rem
            return None, None
        else:
            m = match(atom, text)
            return (None, None) if (not m) else (m.group(0), text[m.end():])

    def button(self, scancode, keystate=KeyEvent.key_down):
        def f(keys):
            _reject = self.state_reject, keys, []
            _partial = self.state_partial, keys, []
            _accept = self.state_accept, keys[1:], []
            _ignore = lambda: f(keys[1:])
            if not keys:
                return _partial
            if keys[0].keystate != keystate:
                return _ignore() if keystate is KeyEvent.key_down else _reject
            if keys[0].scancode != scancode:
                return _reject  if keystate is KeyEvent.key_down else _ignore()
            return _accept
        return f

    def sequence(self, *literals):
        def f(keys):
            state = self.state_accept
            reply = []
            for literal in literals:
                state, keys, _reply = literal(keys)
                if state == self.state_reject:
                    break
                if _reply:
                    reply += _reply
            return state, keys, reply
        return f

    def wild(self, end_scancode):
        def f(keys):
            extracted = []
            for n, key in enumerate(keys):
                if key.scancode == end_scancode and key.keystate == KeyEvent.key_down:
                    return self.state_accept, keys[n+1:], [extracted]
                if key.keystate == KeyEvent.key_down:
                    extracted.append(key)
            return self.state_partial, [], []
        return f

    def translate_code(self, key):
        return ecodes.ecodes.get("KEY_%s" % key.upper(), None)

    def event_to_string(self, events):
        d = Display(":0")
        code_to_string = lambda x: XK.keysym_to_string(d.keycode_to_keysym(x+8,0))
        return "".join(code_to_string(event.scancode) for event in events)

    def compile(self, parsed):
        name, params = parsed[0], parsed[1:]
        if name is "literal":
            return self.compile(params[0])
        elif name is "button":
            code = self.translate_code(params[0].strip("<>"))
            return self.button(code)
        elif name is "wild":
            return self.wild(self.wildchar)
        elif name is "sequence":
            return self.sequence(*[self.compile(param) for param in params])
        raise ValueError("No such method: %s" % name)


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
        self.assertEqual(seq([k]), (ex.state_reject, [], []))
        self.assertEqual(seq([k,k1]), (ex.state_accept, [], []))
        self.assertEqual(seq([k,k2]), (ex.state_reject, [], []))
        self.assertEqual(seq([k,k1,k2]), (ex.state_accept, [k2], []))
        self.assertEqual(seq([k,k2,k1]), (ex.state_accept, [], []))

        wild = ex.sequence(ex.wild(28))
        k3 = KeyEvent(InputEvent(0,0,0,28,1))
        self.assertEqual(wild([k,k1,k2,k3]), (ex.state_accept, [], [[k,k1,k2]]))
        self.assertEqual(wild([k1,k3,k2,k]), (ex.state_accept, [k2,k], [[k1]]))
        self.assertEqual(wild([k1,k2]), (ex.state_reject, [k1,k2], []))

        seq1 = ex.sequence(seq, wild)
        seq2 = ex.sequence(wild, seq1)
        self.assertEqual(seq1([k,k1,k2,k3]), (ex.state_accept, [], [[k2]]))
        self.assertEqual(seq2([k,k1,k3,k,k1,k2,k3]), (ex.state_accept, [], [[k,k1], [k2]]))

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
            data = [(e, a, keysets[i], ex.parse(line)) \
                    for i, (a, e) in enumerate(zip(result_actual, result_expected)) \
                    if a[0] != e[0] or a[2] != e[2]
            ]
            self.assertEquals(data, [])

    def test_init(self):
        ex = Expression("ab")
        keys = [KeyEvent(InputEvent(0, 0, 0, code, state)) \
                for code in [30, 48] for state in [0, 1]]
        result, extracted = ex(keys)
        self.assertEqual(result, Expression.state_accept)
        self.assertEqual(extracted, [])