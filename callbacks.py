# -*- coding: utf-8 -*-
from re import search
from subprocess import Popen, PIPE

__author__ = 'iljich'

def mpd_search_and_play(name, extra=""):
    cmd = "mpc %s" % extra
    output = Popen("%s playlist -f '%%position%% %%title%%' | grep -i %s" % (cmd, name),
        stdout=PIPE, shell=True).communicate()[0]
    pos = [int(line.split(" ")[0]) for line in output.split("\n")[:-1]]
    if not pos:
        return
    output = Popen(cmd, stdout=PIPE, shell=True).communicate()[0]
    try:
        current = int(search(r" #(\d*)/\d* ", output).group(1))
    except AttributeError:
        current = 0
    try:
        next = filter(lambda x: x>current, pos)[0]
    except IndexError:
        next = pos[0] # current greater than last - return first
    Popen("%s play %s > /dev/null" % (cmd, next), shell=True)
