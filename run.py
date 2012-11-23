# -*- coding: utf-8 -*-
import logging
from signal import SIGTERM, SIGHUP
from daemon import daemon
from lockfile import FileLock
from pybd.processor import Processor
from pybd.utils import FileLikeLogger

__author__ = 'iljich'


context = daemon.DaemonContext(
    pidfile=FileLock('/var/run/pybd.pid'),
    uid = 0,
    stderr=open("e","w+"),#FileLikeLogger(logging.getLogger(), logging.ERROR)
    stdout=open("o","w+")#FileLikeLogger(logging.INFO),
)

context.signal_map = {
    SIGTERM: lambda s,f: Processor().exit(),
    SIGHUP: lambda s,f: Processor().exit()
}

with context:
    p = Processor("/home/iljich/PycharmProjects/pybd/pybd.conf")
    p.run()