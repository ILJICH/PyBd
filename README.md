#Pybd
Control board daemon

## Overwiew
This daemon will listen your button device from under the X, interpret any input by certain rules and execute corresponding commands, including executing shell commands, writing to pipes or files and running external functions. Also can pass text input from keyboard-like devices.

Any device that has buttons on it and is working well with X will do.

## Requirements
This software needs \*nix system with X system, as well as xinput program.

Required libraries:

* python-Xlib

* python-evdev

* python-daemon

## Using

### Config file

Config file has 3 sections: *device*, *processor* and *expressions*.

#### Device section
In *device* section one should define `name`, `xid`, or `path` to node of desired device. Optional `default_state` argument sets device on or off after start. Of omitted, device state is not changed.
Note that name can be non-unique and can be prefixed with "keyboard:" or "pointer:", as in xinput. Xid is guranteed to be unique, but can change after system reboot.

#### Processor section
*Processor* sets `logfile` path, `loglevel`, expression reset key (`reset_key`) and wildcard exit key (`input_end_key`). `Loglevel` must be integer or string as in `logging` module param.
`Reset_key` defines key, that interrupts any expression. `Input_end_key` is used during wildcard handling and shows which key ends user input.

#### Expression section
`Expression` section defines all expression-handler pairs. It divided into namespaces, the "default" namespace is loaded during startup. Inside namespace there are blocks of handlers.

There are 3 types of handlers:

* shell -- execute command in shell. Accepted parameters:<br>
    * `user` - name of user, from which command is run. Default: nobody.

* pipe -- write data in pipe (or file). Accepted parameters:<br>
    * `path` - path to pipe or file. Required.
    * `mode` - file open mode. Default: "w".

* callback -- run python code from external module. Parameters:<br>
    * `path` - path to file that contains executed function. Required. Also, it will be it's global scope.

Handlers can have its own parameters. Inside handler block there are `expression: handler_command` pairs.

Example:
>"shell user=nobody": {<br>
        "me": "mpc enable 1",<br>
        "md": "mpc disable 1",<br>
        "mt": "mpc outputs | head -n 1 | grep enabled && mpc disable 1 || mpc enable 1",<br>
        "mr*": "mpc {0}"<br>
    }

Obiously, after "me" if pressed, `mpc enable 1` command will be executed in *shell* from user *nobody*. Last expression is wildcard one and it accepts user input to include it into handler command.
So, *"mrstop\<ENTER\>"* will run `mpc stop` command.

Expressions are defined by patterns. Input pattern rules:

* Any buttons that might be represented by string are to be wrote in such way.

    >Example: **"a"** or **"A"** for **'a'** button.

* Buttons than can not, should be embraced in **'\<\>'** and called by name.

    >Example: **"\<ENTER\>"**, **"\<F12\>"**, **"\<DELETE\>"**.

* String of several characters means buttons pressed in sequence.

    >Example: **"abc"** will respond to **"a"**, **"b"** and **"c"**, pressed one after another.

* Wildcards - any sequence of buttons that can be passed to the executed command, represented by **"\*"**.

    >Example: **"a\*"** means **"a"** pressed, then any sequence, finished by wildcard breaker (can be changed in config, default: **"\<ENTER\>"**).

## Installation
First of all, make shure you have all dependencies installed.
>\# apt-get install xinput python-daemon python-xlib<br>
\# pip install evdev

To install you need to run:

>$ git clone https://github.com/ILJICH/PyBd.git<br>
$ cd PyBd

Then you need to edit config file
>$ gedit pybd.conf

You might want to use interactive tool to determine needed device and key names:
>\# python run.py -i

Finally, run
>\# python run.py -c pybd.conf

Note that you need to run as root in order to listen devices properly.