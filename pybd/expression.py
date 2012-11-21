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

    @classmethod
    def set_wildchar(cls, wildchar):
        cls.wildchar = Translator.char_to_code(wildchar.strip("<>"))

    def __init__(self, pattern = "", wildchar = "<ENTER>"):
        self.set_wildchar(wildchar)
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
        reply = ["".join(Translator.code_to_char(key) for key in reply_) for reply_ in extracted]
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

    def compile(self, parsed):
        name, params = parsed[0], parsed[1:]
        if name is "literal":
            return self.compile(params[0])
        elif name is "button":
            code = Translator.char_to_code(params[0].strip("<>"))
            return self.button(code)
        elif name is "wild":
            return self.wild(self.wildchar)
        elif name is "sequence":
            return self.sequence(*[self.compile(param) for param in params])
        raise ValueError("No such method: %s" % name)


class Translator(object):
    device = "key"
    display = None

    @classmethod
    def set_device_type(cls, device="key"):
        cls.device = device

    @classmethod
    def char_to_code(cls, char):
        template = {"key": "KEY_%s", "button": "BTN_%s"}[cls.device]
        return ecodes.ecodes.get(template % char.upper(), None)

    @classmethod
    def code_to_char(cls, code, modifiers=0):
        if cls.device is "button":
            return "<%s>" % cls.key_to_name(code)
        if not cls.display:
            cls.display = Display()
        return XK.keysym_to_string(cls.display.keycode_to_keysym(code + 8, modifiers))

    @classmethod
    def key_to_name(cls, key):
        try:
            name = key.keycode[4:].lower()
        except AttributeError:
            prefix = {"key": "KEY_", "button": "BTN_"}[cls.device]
            keys = [(key_[4:],code) for key_, code in ecodes.ecodes.items()
                                    if key_.startswith(prefix)]
            name = sorted(filter(lambda (k,v): v==key, keys), key=lambda (x,y): len(x))[0][0]
        return name