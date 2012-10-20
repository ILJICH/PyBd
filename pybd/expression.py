# -*- coding: utf-8 -*-
from re import match
from Xlib import XK
from Xlib.display import Display
from evdev import KeyEvent, ecodes

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