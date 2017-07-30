#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------
# Copyright (c) 2017 Michelle Baert
# Some rights reserved
# file: {} created by mich on 18/07/17.
# ----------------------------------------
"""
Parses and filter an mlocate database.

Filter directories which contain an entry matching some of the given patterns
>>> args = arg_parser().parse_args('-d /tmp/MyBook.db -I 10 *.ini'.split())
>>> run(args) # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
* 2013-08-16 17:03:59.956254 /run/media/mich/MyBook/$RECYCLE.BIN/S-1-5-21-1696441804-2191777423-1598828944-1001
    - desktop.ini

"""
import fnmatch
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
    Namespace(...database='/var/lib/mlocate/mlocate.db', ... patterns=['.*\\\\.ini', '.*\\\\.desktop']...)

    You can specify an alternate database
    >>> parser.parse_args('-d /tmp/MyBook.db'.split()) # doctest: +ELLIPSIS
    Namespace(..., database='/tmp/MyBook.db', ...)

    This doesn't work: >>> parser.parse_args(['--help'])
    >>> parser.print_help()
    usage: docrunner.py [-h] [-L LOG_LEVEL] [-C] [-n] [-r] [-D] [-d DATABASE]
                        [-I LIMIT_INPUT_DIRS] [-M LIMIT_OUTPUT_DIRS]
                        [-m LIMIT_OUTPUT_MATCH] [-a {test,count,list,json}]
                        [patterns [patterns ...]]
    <BLANKLINE>
    Lookup items in mlocate database
    <BLANKLINE>
    positional arguments:
      patterns              Select only directories with entries matching those
                            patterns
    <BLANKLINE>
    optional arguments:
      -h, --help            show this help message and exit
      -L LOG_LEVEL, --log-level LOG_LEVEL
      -C, --app-config      Show active options
      -n, --dry-run         Dry run, don't parse database
      -r, --use-regexps     Patterns are given as regular expressions. Default:
                            False (glob)
      -D, --mdb-settings    Print mlocate database settings
      -d DATABASE, --database DATABASE
                            name of the mlocate database
      -I LIMIT_INPUT_DIRS, --limit-input-dirs LIMIT_INPUT_DIRS
                            Maximum directory entries read from db
      -M LIMIT_OUTPUT_DIRS, --limit-output-dirs LIMIT_OUTPUT_DIRS
                            Maximum count of selected directories
      -m LIMIT_OUTPUT_MATCH, --limit-output-match LIMIT_OUTPUT_MATCH
                            Maximum count of selected directories
      -a {test,count,list,json}, --action {test,count,list,json}
                            what to do with matched directories
   """
    parser = argparse.ArgumentParser()
    parser.description = "Lookup items in mlocate database"
    # parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('-L', '--log-level', default='WARNING')
    parser.add_argument('-C', '--app-config', action='store_true', help="Show active options")
    parser.add_argument('-n', '--dry-run', action='store_true', help="Dry run, don't parse database")
    parser.add_argument('-r', '--use-regexps', action='store_true', help="Patterns are given as regular expressions." +
                                                                        " Default: False (glob)")
    parser.add_argument('-D', '--mdb-settings', action='store_true', help="Print mlocate database settings")
    parser.add_argument('-d', '--database', help="name of the mlocate database", default=MLOCATE_DEFAULT_DB)
    parser.add_argument('-I', '--limit-input-dirs', help="Maximum directory entries read from db", type=int, default=0)
    parser.add_argument('-M', '--limit-output-dirs', help="Maximum count of selected directories", type=int, default=0)
    parser.add_argument('-m', '--limit-output-match', help="Maximum count of selected directories", type=int, default=0)
    parser.add_argument('-a', '--action', help="what to do with matched directories",
                        choices=['test', 'count', 'list', 'json'],
                        default='list')
    parser.add_argument('patterns', nargs='*', help="Select only directories with entries matching those patterns")

    return parser


def log_level(args):
    """
    adjust the logging level
    >>> arg_parser().parse_args('--log-level CRITICAL'.split()) # doctest: +ELLIPSIS
    Namespace(...log_level='CRITICAL'...)

    :param args:
    """
    logger.setLevel(args.log_level)


def print_app_config(args):
    """
    Dry-run, show config only
    >>> args = arg_parser().parse_args('--app-config --dry-run'.split())
    >>> args # doctest: +ELLIPSIS
    Namespace(...app_config=True...)
    >>> run(args) # doctest: +NORMALIZE_WHITESPACE
    action               : list
    app_config           : True
    database             : /var/lib/mlocate/mlocate.db
    dry_run              : True
    limit_input_dirs     : 0
    limit_output_dirs    : 0
    limit_output_match   : 0
    log_level            : WARNING
    mdb_settings         : False
    patterns             : []
    use_regexps          : False

    :param args:
    """
    for k, v in sorted(args.__dict__.items()):
        print("{0:20} : {1}".format(k, v))


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
    >>> args = arg_parser().parse_args('-d /tmp/MyBook.db -I 10 *.ini'.split())
    >>> run(args)
    * 2013-08-16 17:03:59.956254 /run/media/mich/MyBook/$RECYCLE.BIN/S-1-5-21-1696441804-2191777423-1598828944-1001
        - desktop.ini

    >>> args = arg_parser().parse_args('-L INFO -d /tmp/MyBook.db -a json -I 100 -M 3 -m 5 *.jpg'.split())
    >>> run(args) # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
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


    :param mdb:
    :param args:
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


def print_mdb_settings(mdb):
    logger.info("mlocate database header: %r", sorted(mdb.header.items()))
    # [('conf_block_size', 544), ('file_format', 0), ('req_visibility', 0), ('root', b'/run/media/mich/MyBook')]
    logger.info("mlocate database configuration: %r", sorted(mdb.conf.items()))

    # import json
    conf = [(mlocate.safe_decode(k),[mlocate.safe_decode(e) for e in v]) for k,v in sorted(mdb.conf.items())]
    #        json.dumps(conf, indent=2)

    print("""mlocate database details
    ====================================
    Root: {0}
    Requires visibility: {1}
    File format: {2}

    Configuration:
    """.format(
        mlocate.safe_decode(mdb.header['root']),
        mdb.header['req_visibility'],
        mdb.header['file_format'],
        ))
    for k,v in conf:
        print("    - {0} = {1}".format( k,v))
    print("     ====================================\n\n")

def run(args):
    """
    Runs the program according to given arguments.

    :param args: the parsed arguments from command line
    """
    # if args.log_level:
    log_level(args)
    logger.info("Running with %r", args)

    if args.app_config:
        print_app_config(args)

    # error if no pattern provided
    if not args.dry_run and args.patterns == []:
        print("You should explicitly provide entries patterns, '*' for all.")

    mdb = mlocate.MLocateDB()
    mdb.connect(args.database)
    if args.mdb_settings:
        print_mdb_settings(mdb)
    if not args.dry_run:
        do_filter(mdb, args)


if __name__ == '__main__':
    cli_args = arg_parser().parse_args()
    # print "Would run with", args
    run(cli_args)
