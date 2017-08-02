#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------
# Copyright (c) 2017 Michelle Baert
# Some rights reserved
# file: {} created by mich on 18/07/17.
# ----------------------------------------
"""
Parses an mlocate database and prints parts of its contents.

>>> mdb = mlocate.MLocateDB()

>> args = arg_parser().parse_args('-d /tmp/MyBook.db  /run/media/mich/MyBook/Archives --levels 3'.split())
>>> args = argparse.Namespace(app_config=False, command='tree', database='/tmp/MyBook.db', dry_run=False,
...                           levels=3, patterns=['/run/media/mich/MyBook/Archives'],limit_output_dirs=0,
...                           limit_input_dirs=0, log_level='WARNING', mdb_settings=False, use_regexps=False)
>>> mdb.connect(args.database)
>>> do_subtree(mdb, args) # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
    ├── Admin
    └── Devlp

>> args = arg_parser().parse_args('-L INFO -d /tmp/MyBook.db  /run/media/mich/MyBook/backups --levels 3'.split())
>>> args = argparse.Namespace(database='/tmp/MyBook.db',levels=3, use_regexps=False,
...                           patterns=['/run/media/mich/MyBook/backups'],limit_output_dirs=0,
...                           limit_input_dirs=0)
>>> mdb.connect(args.database)
>>> do_subtree(mdb, args) # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
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
logger = logging.getLogger(__name__)


def print_tree(tree, depth=0):
    tree.print_graph(depth)


def do_subtree(mdb, args):
    # convert and compile patterns
    if args.use_regexps:
        regexps = args.patterns
    else:
        regexps = [fnmatch.translate(p) for p in args.patterns]
    selectors = [re.compile(r.encode()) for r in regexps]

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
                tree = Tree(d.name + b"/")
    if tree:
        print_tree(tree, args.levels)


