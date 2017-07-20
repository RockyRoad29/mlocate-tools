#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------
# Copyright (c) 2017 Michelle Baert
# Some rights reserved
# file: {} created by mich on 18/07/17.
# ----------------------------------------
"""
Parses and filter an mlocate database.

Filter directories which contain an entry matching some of the given regexps
>>> args = arg_parser().parse_args('-d /tmp/MyBook.db -M 10 .*\.ini'.split())
>>> run(args)
* 2013-08-16 17:03:59.956254 /run/media/mich/MyBook/$RECYCLE.BIN/S-1-5-21-1696441804-2191777423-1598828944-1001
    - desktop.ini

"""
import logging
import argparse
import re
import mlocate
import json

MLOCATE_DEFAULT_DB = "/var/lib/mlocate/mlocate.db"
logging.basicConfig(level='DEBUG')
logger = logging.getLogger()


def arg_parser():
    """
    Creates a command line parser suitable for this app.

    >>> parser = arg_parser()

    >>> parser.parse_args('.*\\.ini .*\\.desktop'.split()) # doctest: +ELLIPSIS
    Namespace(...database='/var/lib/mlocate/mlocate.db', ... regexps=['.*\\\\.ini', '.*\\\\.desktop']...)

    You can specify an alternate database
    >>> parser.parse_args('-d /tmp/MyBook.db'.split()) # doctest: +ELLIPSIS
    Namespace(..., database='/tmp/MyBook.db', ...)

    This doesn't work: >>> parser.parse_args(['--help'])
    >>> parser.print_help()
    usage: docrunner.py [-h] [-L LOG_LEVEL] [-C] [-d DATABASE] [-M LIMIT_INPUT]
                        [-m LIMIT_OUTPUT] [-a {test,count,list,json}]
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
      -M LIMIT_INPUT, --limit-input LIMIT_INPUT
                            Maximum directory entries read from db
      -m LIMIT_OUTPUT, --limit-output LIMIT_OUTPUT
                            Maximum count of selected directories
      -a {test,count,list,json}, --action {test,count,list,json}
                            what to do with matched directories

   """
    parser = argparse.ArgumentParser()
    parser.description = "Lookup items in mlocate database"
    # parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('-L', '--log-level', default='WARNING')
    parser.add_argument('-C', '--show-config', action='store_true', help="Dry run, only show current configuration")
    parser.add_argument('-d', '--database', help="name of the mlocate database", default=MLOCATE_DEFAULT_DB)
    parser.add_argument('-M', '--limit-input', help="Maximum directory entries read from db", type=int, default=-1)
    parser.add_argument('-m', '--limit-output', help="Maximum count of selected directories", type=int, default=-1)
    parser.add_argument('-a', '--action', help="what to do with matched directories",
                        choices=['test', 'count', 'list', 'json'],
                        default='list')
    parser.add_argument('regexps', nargs='*', help="filtering regexp for filename/dirname")

    return parser


def log_level(args):
    """
    adjust the logging level
    >>> arg_parser().parse_args('--log-level CRITICAL'.split()) # doctest: +ELLIPSIS
    Namespace(...log_level='CRITICAL'...)

    :param args:
    """
    logger.setLevel(args.log_level)


def show_config(args):
    """
    Dry-run, show config only
    >>> args = arg_parser().parse_args('--show-config'.split())
    >>> args # doctest: +ELLIPSIS
    Namespace(...show_config=True...)
    >>> run(args)
    action          : list
    database        : /var/lib/mlocate/mlocate.db
    limit_input     : -1
    limit_output    : -1
    log_level       : WARNING
    regexps         : []
    show_config     : True

    :param args:
    """
    for k, v in sorted(args.__dict__.items()):
        print("{0:15} : {1}".format(k, v))


def print_dir_test(d, r=True):
    """
    Prints a single line describing the given directory

    >>> from datetime import datetime
    >>> dt = datetime(2017, 7, 20, 13, 22, 43, 817771)
    >>> print_dir_test(dict(name='/some/directory/test', dt=dt), True)
    2017-07-20 13:22:43.817771 /some/directory/test

    :param d: dict representing a directory
    :param r: Unused. Present to match action signature
    """
    assert r
    print("{0} {1}".format(d['dt'], d['name']))


def print_dir_count(d, r):
    """
    Prints a single line describing the given directory, with match count

    >>> from datetime import datetime
    >>> dt = datetime(2017, 7, 20, 13, 22, 43, 817771)
    >>> print_dir_count(dict(name='/some/directory/test', dt=dt), 12)
    [2017-07-20 13:22:43.817771] 12 matches in /some/directory/test

    :param d: dict representing a directory
    :param r: the matches count
    """
    print("[{0}] {2} matches in {1}".format(d['dt'], d['name'], r))


def print_dir_list(d, r):
    """
    Prints a section showing matches for a single directory
    >>> from datetime import datetime
    >>> dt = datetime(2017, 7, 20, 13, 22, 43, 817771)
    >>> print_dir_list(dict(name='/some/directory/test', dt=dt), [(1,'some_dir'), (0,'some_file')])
    * 2017-07-20 13:22:43.817771 /some/directory/test
        - some_dir/
        - some_file

    :param d: dict representing a directory
    :param r: list of matched entries
    """
    print("* {0} {1}".format(d['dt'], d['name']))
    for f in r:
        print("    - {0}{1}".format(f[1], ["", "/"][f[0]]))


def print_dir_json(d, r):
    """
    Prints a section showing matches for a single directory
    >>> from datetime import datetime
    >>> dt = datetime(2017, 7, 20, 13, 22, 43, 817771)
    >>> print_dir_json(dict(name='/some/directory/test', dt=dt),
    ...                [(1, 'some_dir'), (0, 'some_file')]) # doctest: +NORMALIZE_WHITESPACE
    {
      "dt": "2017-07-20 13:22:43.817771",
      "matches": [
        [ 1, "some_dir" ],
        [ 0, "some_file" ]
      ],
      "name": "/some/directory/test"
    }

    :param d: dict representing a directory
    :param r: list of matched entries
    """
    data = dict(name=d['name'], dt=d['dt'], matches=r)
    print(json.dumps(data, indent=2, sort_keys=True, default=str))


actions = {
    'test': print_dir_test,
    'count': print_dir_count,
    'list': print_dir_list,
    'json': print_dir_json
}


def do_filter(mdb, args):
    """
    >>> args = arg_parser().parse_args('-d /tmp/MyBook.db -M 100 .*\.ini'.split())
    >>> run(args)
    * 2013-08-16 17:03:59.956254 /run/media/mich/MyBook/$RECYCLE.BIN/S-1-5-21-1696441804-2191777423-1598828944-1001
        - desktop.ini

    :param mdb:
    :param args:
    :return:
    """
    selectors = [re.compile(r) for r in args.regexps]
    count = args.limit_output
    for d in mdb.load_dirs(args.limit_input):
        r = match_dir(d, selectors, args.action)
        if r:
            actions[args.action](d, r)
            count -= 1
            if count <= 0:
                break


def match_dir(d, selectors, action='test'):
    """
    Tests a directory
    :param action:
    :param d: dict as generated by MLocate
    :param selectors:
    :return:
    """
    count = 0
    rslts = []
    for f in d['contents']:
        for s in selectors:
            if s.match(f[1]):
                if action == 'test':
                    return True
                elif action == 'count':
                    count += 1
                elif action == 'list':
                    rslts.append(f)

    if action == 'test':
        return False
    if action == 'count':
        return count
    elif action == 'list':
        return rslts
    else:
        raise Exception('Unknown action: ', action)


def run(args):
    """
    Runs the program according to given arguments.

    :param args: the parsed arguments from command line
    """
    # if args.log_level:
    log_level(args)
    logger.info("Running with %r", args)
    if args.show_config:
        show_config(args)
        # TODO show mdb config
    else:
        mdb = mlocate.MLocateDB()
        mdb.connect(args.database)
        do_filter(mdb, args)


if __name__ == '__main__':
    cli_args = arg_parser().parse_args()
    # print "Would run with", args
    run(cli_args)
