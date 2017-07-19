#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------
# Copyright (c) 2017 Michelle Baert
# Some rights reserved
# file: {} created by mich on 18/07/17.
# ----------------------------------------
"""
Parses and filter an mlocate database.

>>> args = arg_parser().parse_args(['--show-config'])
>>> args
Namespace(database='/var/lib/mlocate/mlocate.db', log_level='WARNING', regexps=[], show_config=True)
>>> run(args)
database        : /var/lib/mlocate/mlocate.db
log_level       : WARNING
regexps         : []
show_config     : True

"""
import logging
import argparse

MLOCATE_DEFAULT_DB = "/var/lib/mlocate/mlocate.db"
logging.basicConfig(level='DEBUG')
logger = logging.getLogger()

def arg_parser():
    """
    Creates a command line parser suitable for this app.

    >>> parser = arg_parser()


    You can specify an alternate database
    >>> parser.parse_args('-d /tmp/MyBook.db'.split())
    Namespace(database='/tmp/MyBook.db', log_level='WARNING', regexps=[], show_config=False)
    >>> parser.parse_args('--log-level CRITICAL'.split())
    Namespace(database='/var/lib/mlocate/mlocate.db', log_level='CRITICAL', regexps=[], show_config=False)

    Dry-run, show config only
    >>> parser.parse_args('--show-config'.split())
    Namespace(database='/var/lib/mlocate/mlocate.db', log_level='WARNING', regexps=[], show_config=True)

    This doesn't work: >>> parser.parse_args(['--help'])
    >>> parser.print_help()
    usage: docrunner.py [-h] [-L LOG_LEVEL] [-C] [-d DATABASE]
                        [regexps [regexps ...]]
    <BLANKLINE>
    Lookup items in mlocate database
    <BLANKLINE>
    positional arguments:
      regexps               filtering regexp for filename/dirname
    <BLANKLINE>
    optional arguments:
      -h, --help            show this help message and exit
      -L LOG_LEVEL, --log-level LOG_LEVEL
      -C, --show-config     Dry run, only show current configuration
      -d DATABASE, --database DATABASE
                            name of the mlocate database



    """
    parser = argparse.ArgumentParser()
    parser.description = "Lookup items in mlocate database"
    #parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('-L', '--log-level', default='WARNING')
    parser.add_argument('-C', '--show-config', action='store_true', help="Dry run, only show current configuration")
    parser.add_argument('-d', '--database', help="name of the mlocate database", default=MLOCATE_DEFAULT_DB)
    parser.add_argument('regexps', nargs='*',help="filtering regexp for filename/dirname")
    return parser

def log_level(args):
    logger.setLevel(args.log_level)

def show_config(args):
    for k,v in sorted(args.__dict__.items()):
        print("{0:15} : {1}".format(k, v))

def run(args):
    """
    Does great things.
    """
    #if args.log_level:
    log_level(args)
    logger.info("Running with %r", args)
    if args.show_config:
        show_config(args)
    else:
        print("Not implemented")

if __name__ == '__main__':
    import argparse, sys
    args = arg_parser().parse_args()
    # print "Would run with", args
    run(args)
