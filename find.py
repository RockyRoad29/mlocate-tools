#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------
# Copyright (c) 2017 Michelle Baert
# Some rights reserved
# file: {} created by mich on 18/07/17.
# ----------------------------------------
"""
Filter directories which contain an entry matching some of the given patterns

"""
import fnmatch
import logging
import argparse
import re
import mlocate
import json


def print_dir_test(d, r=True):
    """
    Prints a single line describing the given directory

    >>> from datetime import datetime
    >>> dt = datetime(2017, 7, 20, 13, 22, 43, 817771)
    >>> print_dir_test(mlocate.DirBlock(b'/some/directory/test', dt, []), True)
    2017-07-20 13:22:43.817771 /some/directory/test

    :param d: dict representing a directory
    :param r: Unused. Present to match action signature
    """
    assert r
    print("{0} {1}".format(d.dt, d.name))


def print_dir_count(d, r):
    """
    Prints a single line describing the given directory, with match count

    >>> from datetime import datetime
    >>> dt = datetime(2017, 7, 20, 13, 22, 43, 817771)
    >>> print_dir_count(mlocate.DirBlock(b'/some/directory/test', dt, []), [(True, b'some_dir'), ( False,b'some_file')])
    [2017-07-20 13:22:43.817771] 2 matches in /some/directory/test

    :param d: dict representing a directory
    :param r: the matches count
    """
    print("[{0}] {2} matches in {1}".format(d.dt, d.name, len(r)))


def print_dir_list(d, r):
    """
    Prints a section showing matches for a single directory
    >>> from datetime import datetime
    >>> dt = datetime(2017, 7, 20, 13, 22, 43, 817771)
    >>> print_dir_list(mlocate.DirBlock(b'/some/directory/test', dt, []), [(True, b'some_dir'), ( False,b'some_file')])
    * 2017-07-20 13:22:43.817771 /some/directory/test
        - some_dir/
        - some_file

    :param d: dict representing a directory
    :param r: list of matched entries
    """
    print("* {0} {1}".format(d.dt, d.name))
    for f in r:
        print("    - {0}{1}".format(mlocate.safe_decode(f[1]), ["", "/"][f[0]]))


def print_dir_json(d, r):
    """
    Prints a section showing matches for a single directory
    >>> from datetime import datetime
    >>> dt = datetime(2017, 7, 20, 13, 22, 43, 817771)
    >>> print_dir_json(mlocate.DirBlock(b'/some/directory/test', dt, []),
    ...                [(True, b'some_dir'), ( False,b'some_file')])
    ... # doctest: +NORMALIZE_WHITESPACE
    {
      "dt": "2017-07-20 13:22:43.817771",
      "matches": [
        [ true, "some_dir" ],
        [ false, "some_file" ]
      ],
      "name": "/some/directory/test"
    }

    :param d: dict representing a directory
    :param r: list of matched entries
    """
    data = dict(name=d.name, dt=str(d.dt), matches=[(flag, mlocate.safe_decode(f)) for flag, f in r])
    print(json.dumps(data, indent=2, sort_keys=True))


actions = {
    'test': print_dir_test,
    'count': print_dir_count,
    'list': print_dir_list,
    'json': print_dir_json
}


def do_filter(mdb, args):
    """
    >>> import argparse
    >>> mdb = mlocate.MLocateDB()
    >>> mdb.connect("/tmp/MyBook.db")
    >>> args = argparse.Namespace(database='/tmp/MyBook.db',
    ...                           action='list', patterns=['*.ini'],
    ...                           use_regexps=False,
    ...                           limit_input_dirs=10,
    ...                           limit_output_dirs=0,
    ...                           limit_output_match=0)
    >>> do_filter(mdb,args)
    * 2013-08-16 17:03:59.956254 /run/media/mich/MyBook/$RECYCLE.BIN/S-1-5-21-1696441804-2191777423-1598828944-1001
        - desktop.ini
    >>> args = argparse.Namespace(database='/tmp/MyBook.db',
    ...                           action='json', patterns=['*.jpg'],
    ...                           use_regexps=False,
    ...                           limit_input_dirs=100,
    ...                           limit_output_dirs=3,
    ...                           limit_output_match=5)
    >>> do_filter(mdb,args) # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    [
    {
      "dt": "2013-08-16 17:37:18.885441",
      "matches": [
        [  false, "1823661_calendrierscolaire.jpg" ],
        [  false, "517-OF-25.02.121-b.jpg" ],
        [  false, "6760135001_14c59a1490_o.jpg" ],
        [  false, "Affiche26-02.jpg" ],
        [  false, "Dejeuner-canotiers.jpg" ]
      ],
      "name": "/run/media/mich/MyBook/Downloads"
    }
    ,
    {
      "dt": "2012-10-12 13:52:42.634545",
      "matches": [
        [  false, "17634466_q.jpg" ],
        [  false, "31140656_q.jpg" ],
        [  false, "312002.jpg" ],
        [  false, "40647860_q.jpg" ],
        [  false, "53683208_q.jpg" ]
      ],
      "name": "/run/media/mich/MyBook/Downloads/Comment la Gr..."
     }
    ,
    {
      "dt": "2012-10-12 13:52:42.713111",
      "matches": [
        [  false, "110831202339112_42_000_apx_470_.jpg" ],
        [  false, "110831202401729_44_000_apx_470_.jpg" ],
        [  false, "110831202504820_47_000_apx_470_.jpg" ]
      ],
      "name": "/run/media/mich/MyBook/Downloads/OpenHydro"
    }
    ]


    :param mdb: mlocate.MLocateDB
    :param args: argparse.Namespace
    :return:
    """
    # convert and compile patterns
    if args.use_regexps:
        regexps = args.patterns
    else:
        regexps = [fnmatch.translate(p) for p in args.patterns]
    selectors = [re.compile(r) for r in regexps]
    count = 0

    if args.action == 'test':
        limit = 1
    else:
        limit = args.limit_output_match
    if args.action == 'json': print("[")

    for d in mdb.load_dirs(args.limit_input_dirs):
        r = d.match_contents(selectors, limit)
        if r:
            #d1 = d.decode()
            if count and args.action == 'json': print(",")
            # noinspection PyCallingNonCallable
            actions[args.action](d, r)
            count += 1
            if args.limit_output_dirs and (count >= args.limit_output_dirs):
                break
    if args.action == 'json': print("]")

