# -*- coding: utf-8 -*-
from imp import load_source
from os.path import dirname, isabs, join
from subprocess import call

__author__ = 'iljich'

class HandlerFactory(object):
    products = {}

    def __init__(self, product_name, params):
        self.product = self.products[product_name]
        self.params = params

    def __call__(self, cmd):
        return self.product(cmd, self.params)

    @classmethod
    def register(cls, product_name, product):
        cls.products[product_name] = product

def handler(name):
    def inner(cls):
        HandlerFactory.register(name, cls)
        return cls
    return inner

class AbstractHandler(object):
    params = {}
    def __init__(self, cmd, params):
        self.cmd = cmd
        self.params.update(params)

    def apply(self, params):
        return self.cmd.format(*params)

    def param(self, name):
        return self.params.get(name, None)

    def __call__(self, params):
        pass

    def __str__(self):
        return self.cmd

@handler("dummy")
class DummyHandler(AbstractHandler):
    pass

@handler("shell")
class ShellHandler(AbstractHandler):
    params = {"user": "nobody"}

    def __call__(self, params):
        cmd = "sudo -u %s sh -c '%s' > /dev/null" % \
            (self.param("user"), self.apply(params))
        call(cmd, shell=True)

@handler("pipe")
class PipeHandler(AbstractHandler):
    params = {
        "path": "/dev/null",
        "mode": "w"
    }

    def __call__(self, params):
        with open(self.param("path"), self.param("mode")) as pipe:
            pipe.write(self.apply(params))

@handler("callback")
class CallbackHandler(AbstractHandler):
    params = {"path": "../callbacks/callbacks.py"}

    def __init__(self, cmd, params):
        super(CallbackHandler, self).__init__(cmd, params)
        path = self.params["path"]
        if not isabs(path):
            path = join(dirname(__file__), path)
        self.global_scope = load_source("_", path).__dict__

    def __call__(self, params):
        local_scope = {"_%d" % i: params[i] for i in range(len(params))}
        eval(self.apply(local_scope.keys()),
            dict(local_scope.items() + self.global_scope.items())) # god save the kitten
