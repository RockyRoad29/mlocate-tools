#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------
# Copyright (c) $(YEAR} Michelle Baert
# Some rights reserved
# file: {} created by mich on 30/07/17.
# ----------------------------------------
"""
Provides command line arguments parsers and common tools.

"""
import argparse
import logging
import mlocate

logging.basicConfig(level='DEBUG')
LOGGER = logging.getLogger()
MLOCATE_DEFAULT_DB = "/var/lib/mlocate/mlocate.db"

def base_parser(**kwargs):
    """
    Creates a simple argument parser with common options

    >>> from cli import *
    >>> parser = base_parser(description="Test parser")

    You can specify an alternate database
    >>> parser.parse_args('-d /tmp/MyBook.db'.split()) # doctest: +ELLIPSIS
    Namespace(..., database='/tmp/MyBook.db', ...)
    >>> parser.print_help() # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    usage: ... [-h] [-L LOG_LEVEL] [-C] [-n] [-r] [-D] [-d DATABASE]
              [-I LIMIT_INPUT_DIRS]
    <BLANKLINE>
    Test parser
    <BLANKLINE>
    optional arguments:
      -h, --help            show this help message and exit
      -L LOG_LEVEL, --log-level LOG_LEVEL
      -C, --app-config      Show active options
      -n, --dry-run         Dry run, don't parse database
      -r, --use-regexps     Patterns are given as regular expressions.
                            Default: False (glob)
      -D, --mdb-settings    Print mlocate database settings
      -d DATABASE, --database DATABASE
                            name of the mlocate database
      -I LIMIT_INPUT_DIRS, --limit-input-dirs LIMIT_INPUT_DIRS
                            Maximum directory entries read from db

        """
    parser = argparse.ArgumentParser(**kwargs)
    parser.add_argument('-L', '--log-level', default='WARNING')
    parser.add_argument('-C', '--app-config', action='store_true',
                        help="Show active options")
    parser.add_argument('-n', '--dry-run', action='store_true',
                        help="Dry run, don't parse database")
    parser.add_argument('-r', '--use-regexps', action='store_true',
                        help="Patterns are given as regular expressions." +
                        " Default: False (glob)")
    parser.add_argument('-D', '--mdb-settings', action='store_true',
                        help="Print mlocate database settings")
    parser.add_argument('-d', '--database', default=MLOCATE_DEFAULT_DB,
                        help="name of the mlocate database")
    parser.add_argument('-I', '--limit-input-dirs', type=int, default=0,
                        help="Maximum directory entries read from db")
    return parser

def main_parser():
    """
    Creates a command line parser suitable for this app.

    >>> parser = main_parser()

    >>> parser.parse_args('find .*\\.ini .*\\.desktop'.split())
    ... # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    Namespace(...database='/var/lib/mlocate/mlocate.db', ...
    patterns=['.*\\\\.ini', '.*\\\\.desktop']...)

    >>> parser.print_help() # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
     usage: ... [-h] [-L LOG_LEVEL] [-C] [-n] [-r] [-D] [-d DATABASE]
                        [-I LIMIT_INPUT_DIRS]
                        {find,dups,tree} ...
    <BLANKLINE>
    Explore filesystems through an mlocate database
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
    <BLANKLINE>
    subcommands:
      valid subcommands
    <BLANKLINE>
      {find,dups,tree}      Command specifier
        find                find files by pattern, list them grouped by directory
        dups                detect potential duplicate directory trees
        tree                prints selected subtrees

   >>> parser.parse_args(['find', '--help'])
   Traceback (most recent call last):
   SystemExit: 0

    """
    parser = base_parser(description="Explore filesystems through an mlocate database")
    cmds = parser.add_subparsers(dest='command',
                                 title='subcommands',
                                 description='valid subcommands',
                                 help='Command specifier')
    add_find_command(cmds)
    add_dups_command(cmds)
    add_tree_command(cmds)

    return parser

def add_find_command(cmds):
    """
    >>> parser = base_parser(description="Test parser")
    >>> cmds = parser.add_subparsers(help='Command specifier', dest='cmd', title="command")
    >>> cmd = add_find_command(cmds)
    >>> cmd.print_help() # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    usage: ... find [-h] [-M LIMIT_OUTPUT_DIRS] [-m LIMIT_OUTPUT_MATCH]
                        [-a {test,count,list,json}]
                        [patterns [patterns ...]]
    <BLANKLINE>
    positional arguments:
      patterns              Select only directories with entries matching those
                            patterns
    <BLANKLINE>
    optional arguments:
      -h, --help            show this help message and exit
      -M LIMIT_OUTPUT_DIRS, --limit-output-dirs LIMIT_OUTPUT_DIRS
                            Maximum count of selected directories
      -m LIMIT_OUTPUT_MATCH, --limit-output-match LIMIT_OUTPUT_MATCH
                            Maximum count of selected entries
      -a {test,count,list,json}, --action {test,count,list,json}
                            what to do with matched directories

    >>> args = main_parser().parse_args('-d /tmp/MyBook.db -I 10 find *.ini'.split())
    >>> run(args)
    * 2013-08-16 17:03:59.956254 /run/media/mich/MyBook/$RECYCLE.BIN/S-1-5-21-1696441804-2191777423-1598828944-1001
        - desktop.ini

    >>> args = main_parser().parse_args('-L INFO -d /tmp/MyBook.db -I 100 find -a json -M 3 -m 5 *.jpg'.split())
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
    """
    cmd = cmds.add_parser('find',
                          help='find files by pattern, list them grouped by directory')
    cmd.add_argument('-M', '--limit-output-dirs', type=int, default=0,
                     help="Maximum count of selected directories")
    cmd.add_argument('-m', '--limit-output-match', type=int, default=0,
                     help="Maximum count of selected entries")
    cmd.add_argument('-a', '--action', choices=['test', 'count', 'list', 'json'],
                     default='list',
                     help="what to do with matched directories")
    cmd.add_argument('patterns', nargs='*',
                     help="Select only directories with entries matching those patterns")
    return cmd

def add_dups_command(cmds):
    """
    >>> parser = base_parser(description="Test parser")
    >>> cmds = parser.add_subparsers(help='Command specifier', dest='cmd', title="command")
    >>> cmd = add_dups_command(cmds)
    >>> cmd.print_help() # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    usage: ... dups [-h] [patterns [patterns ...]]
    <BLANKLINE>
    positional arguments:
      patterns    Select only directories with entries matching those patterns
    <BLANKLINE>
    optional arguments:
      -h, --help  show this help message and exit


    """
    cmd = cmds.add_parser('dups',
                          help='detect potential duplicate directory trees')
    cmd.add_argument('patterns', nargs='*',
                     help="Select only directories with entries matching those patterns")
    return cmd

def add_tree_command(cmds):
    """
    >>> parser = base_parser(description="Test parser")
    >>> cmds = parser.add_subparsers(help='Command specifier', dest='cmd', title="command")
    >>> cmd = add_tree_command(cmds)
    >>> cmd.print_help()# doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    usage: ... tree [-h]
    <BLANKLINE>
    optional arguments:
      -h, --help  show this help message and exit

    """
    cmd = cmds.add_parser('tree', help='prints selected subtrees')
    return cmd

def log_level(args):
    """
    adjust the logging level
    >>> main_parser().parse_args('--log-level CRITICAL'.split()) # doctest: +ELLIPSIS
    Namespace(...log_level='CRITICAL'...)

    :param args:
    """
    LOGGER.setLevel(args.log_level)


def print_app_config(args):
    """
    Dry-run, show config only
    >>> args = main_parser().parse_args('--app-config --dry-run find'.split())
    >>> args # doctest: +ELLIPSIS
    Namespace(...app_config=True...)
    >>> run(args) # doctest: +NORMALIZE_WHITESPACE
    action               : list
    app_config           : True
    command              : find
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
    for k, value in sorted(args.__dict__.items()):
        print("{0:20} : {1}".format(k, value))

def print_mdb_settings(mdb):
    """
    Formats and prints details about an open mlocate database

    :param mdb: MLocateDB object, properly initialized
    """
    LOGGER.info("mlocate database header: %r", sorted(mdb.header.items()))
    # [('conf_block_size', 544), ('file_format', 0), ('req_visibility', 0),
    # ('root', b'/run/media/mich/MyBook')]
    LOGGER.info("mlocate database configuration: %r", sorted(mdb.conf.items()))

    conf = [(mlocate.safe_decode(k),
             [mlocate.safe_decode(e) for e in v])
            for k, v in sorted(mdb.conf.items())]

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
    for k, value in conf:
        print("    - {0} = {1}".format(k, value))
    print("     ====================================\n\n")

def run(args):
    """
    Runs the program according to given arguments.

    :param args: the parsed arguments from command line
    """
    # if args.log_level:
    log_level(args)
    LOGGER.info("Running with %r", args)

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
        # FIXME dry_run may be redundant
        if args.command == 'find':
            from filter import do_filter
            do_filter(mdb, args)
        elif args.command:
            print("FIXME NotImplemented")

if __name__ == '__main__':
    import sys
    run(main_parser().parse_args(sys.argv))
