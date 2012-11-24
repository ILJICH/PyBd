# -*- coding: utf-8 -*-
from argparse import ArgumentParser
from signal import SIGTERM, SIGHUP
from daemon import daemon
from lockfile import FileLock
from pybd.processor import Processor
from pybd.utils import FileLikeLogger
from os import path

__author__ = 'iljich'

parser = ArgumentParser()
parser.add_argument("-c", "--config", help="path to config file")

args = parser.parse_args()

if args.config:
    context = daemon.DaemonContext(
        pidfile=FileLock('/var/run/pybd.pid'),
        uid = 0,
        stderr=FileLikeLogger("ERROR"),
        stdout=FileLikeLogger("INFO"),
    )

    context.signal_map = {
        SIGTERM: lambda s,f: Processor().exit(),
        SIGHUP: lambda s,f: Processor().exit()
    }

    config_path = path.abspath(args.config)

    with context:
        p = Processor(config_path)
        p.run()

parser.print_help()