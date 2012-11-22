# -*- coding: utf-8 -*-
from signal import SIGTERM, SIGHUP
from daemon import daemon
from lockfile import FileLock
from os.path import dirname
from pybd.processor import Processor

__author__ = 'iljich'


context = daemon.DaemonContext(
    pidfile=FileLock('/var/run/pybd.pid'),
    uid = 0
)

context.signal_map = {
    SIGTERM: lambda : Processor().exit(),
    SIGHUP: lambda : Processor().exit()
}

with context:
    p = Processor("/home/iljich/PycharmProjects/pybd/pybd.conf")
    p.run()