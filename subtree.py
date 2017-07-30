#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------
# Copyright (c) 2017 Michelle Baert
# Some rights reserved
# file: {} created by mich on 18/07/17.
# ----------------------------------------
"""
Parses an mlocate database and prints parts of its contents.

>> args = arg_parser().parse_args('-d /tmp/MyBook.db  /run/media/mich/MyBook/Archives --levels 3'.split())
>>> args = arg_parser().parse_args('-L INFO -d /tmp/MyBook.db  /run/media/mich/MyBook/backups --levels 3'.split())
>>> run(args) # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
    ├── Ovi
    │   └── Sauvegardes
    ├── WD-MyBookEssential
    ├── backup-manager
    ├── bacula
    │   ├── claddagh
    │   └── claddagh2
    ├── claddagh2
    │   ├── mysql
    │   └── winfiles
    │       ├── Contacts
    │       ├── Downloads
    │       ├── Progs
    │       └── mich
    ├── dennet
    │   ├── 2013-08-02-21-img
    │   └── 2013-08-02-21-imgRestore
    └── vrac
        ├── claddagh
        │   ├── Palm-SD
        │   ├── Postgres
        │   ├── SD2
        │   ├── backup
        │   ├── claddaghwiki
        │   ├── drupal
        │   ├── flash1
        │   ├── flyspray
        │   ├── free.fr
        │   ├── mail
        │   ├── mysql
        │   ├── nokia
        │   ├── palm
        │   └── tmp
        └── claddagh2
            └── 9F40-5815


"""
import fnmatch
import logging
import argparse
import re
import sys
import mlocate
from tree import Tree

MLOCATE_DEFAULT_DB = "/var/lib/mlocate/mlocate.db"
logging.basicConfig(level='DEBUG')
logger = logging.getLogger()

def arg_parser():
    """
    Creates a command line parser suitable for this app.

    >>> parser = arg_parser()

   """
    parser = argparse.ArgumentParser()
    parser.description = "Lookup items in mlocate database"
    # parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('-L', '--log-level', default='WARNING')
    parser.add_argument('-n', '--dry-run', action='store_true', help="Dry run, don't parse database")
    parser.add_argument('-r', '--use-regexps', action='store_true', help="Patterns are given as regular expressions." +
                                                                        " Default: False (glob)")
    parser.add_argument('-D', '--mdb-settings', action='store_true', help="Print mlocate database settings")
    parser.add_argument('-d', '--database', help="name of the mlocate database", default=MLOCATE_DEFAULT_DB)
    parser.add_argument('-I', '--limit-input-dirs', help="Maximum directory entries read from db", type=int, default=0)
    parser.add_argument('-M', '--limit-output-dirs', help="Maximum count of selected directories", type=int, default=0)
    parser.add_argument('-l', '--levels', help="Maximum depth of subtree reporting", type=int, default=sys.maxsize)

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



def print_tree(tree, depth=0):
    tree.print_graph(depth)


def do_subtree(mdb, args):
    """
    """
    # convert and compile patterns
    if args.use_regexps:
        regexps = args.patterns
    else:
        regexps = [fnmatch.translate(p) for p in args.patterns]
    selectors = [re.compile(r) for r in regexps]

    tree = None
    count = 0
    for d in mdb.load_dirs(args.limit_input_dirs):
        if tree:
            if tree.load(d.name):
                logger.info("loaded %s", d.name)
            else:
                logger.debug("end of subtree")
                print_tree(tree, args.levels)
                tree = None
                count += 1
                if args.limit_output_dirs and (count >= args.limit_output_dirs):
                    break
        else:
            if d.match_path(selectors):
                tree = Tree(d.name + "/")
    if tree:
        print_tree(tree, args.levels)


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

    # error if no pattern provided
    if not args.dry_run and args.patterns == []:
        print("You should explicitly provide entries patterns, '*' for all.")

    mdb = mlocate.MLocateDB()
    mdb.connect(args.database)
    if args.mdb_settings:
        print_mdb_settings(mdb)
    if not args.dry_run:
        do_subtree(mdb, args)


if __name__ == '__main__':
    cli_args = arg_parser().parse_args()
    # print "Would run with", args
    run(cli_args)
