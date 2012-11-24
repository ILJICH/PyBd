# -*- coding: utf-8 -*-
from argparse import ArgumentParser
from signal import SIGTERM, SIGHUP
from daemon import daemon
from daemon.pidlockfile import PIDLockFile
from lockfile import FileLock
import sys
from pybd.device import Device
from pybd.processor import Processor
from pybd.utils import FileLikeLogger, input_devices, listen_device, MyPIDLockFile
from os import path

__author__ = 'iljich'

parser = ArgumentParser()
parser.add_argument("-c", "--config", help="path to config file")
parser.add_argument("-i", "--interactive", action="store_true",
    help="interactive tool for testing devices output")

args = parser.parse_args()

if args.config and not args.interactive:

    context = daemon.DaemonContext(
        pidfile=MyPIDLockFile('/var/run/pybd.pid'),
        uid = 0,
        stderr=FileLikeLogger("ERROR"),
        stdout=FileLikeLogger("INFO"),
    )

    context.signal_map = {
        SIGTERM: lambda s,f: Processor.instance().exit(),
        #SIGHUP: lambda s,f: Processor.instance().exit()
    }

    config_path = path.abspath(args.config)

    with context:
        p = Processor(config_path)

if args.interactive:

    print "Available devices:"
    for name, xid in input_devices():
        print "    %s: %s" % (xid, name)
    print "Select device:"
    id = raw_input(">>")
    try:
        xid = int(id)
    except ValueError, IndexError:
        exit(0)
    device = Device(xid=xid)
    try:
        device.set_state(0)
        print "Now press some buttons or any key on main keyboard to exit"
        listen_device(device.listener)
    finally:
        device.set_state(1)

else:
    parser.print_help()