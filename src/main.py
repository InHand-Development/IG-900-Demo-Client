#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
App example
Created on 2018/3/5
@author: Zhengyb
'''
import sys
import getopt
from Processor import App


def usage(cmd):
    print("usage: ")
    print("\t%s -[h]" % cmd)
    print("\t\t-h|--help\tprint this help info")
    sys.exit(255)


def main(argv=sys.argv):
    short_args = "h:c"
    long_args = [
        "help",
    ]

    arguments = argv[1:]
    try:
        opts, args = getopt.getopt(arguments, short_args, long_args)
    except:
        usage(argv[0])
    for option, value in opts:
        if option in ('-h', '--help'):
            usage(argv[0])

    app = App('Inhand', 'InModbusSimplify')
    app.init()
    app.run()
    print("App InModbusSimplify exited.")


if __name__ == '__main__':
    main()
