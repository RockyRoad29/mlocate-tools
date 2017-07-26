#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------
# Copyright (c) 2017 Michelle Baert
# Some rights reserved
# file: {} created by mich on 25/07/17.
# ----------------------------------------
"""
Tries to identify duplicate directory trees, using an mlocate database.
"""
import hashlib
import logging
import argparse
import os
import re
import mlocate
import path

MLOCATE_DEFAULT_DB = "/var/lib/mlocate/mlocate.db"
logging.basicConfig(level='DEBUG')
logger = logging.getLogger()


class DirStack:
    """
    Maintains a list of contents checksums for each level of ancestor directories.

    >>> ds = DirStack()
    >>> ds.select("/a/b/c")
    ['', 'a', 'b', 'c']
    >>> ds.sum_contents(['some', 'file', 'and', 'dir', 'from', 'contents'])
    ... # doctest: +NORMALIZE_WHITESPACE
    ['c2f61950de5d7032353a4cfff12974f56a1f2934e4bd337cb8ebf6aa316f0e2b',
     'c2f61950de5d7032353a4cfff12974f56a1f2934e4bd337cb8ebf6aa316f0e2b',
     'c2f61950de5d7032353a4cfff12974f56a1f2934e4bd337cb8ebf6aa316f0e2b',
     'c2f61950de5d7032353a4cfff12974f56a1f2934e4bd337cb8ebf6aa316f0e2b']
    >>> ck = ds.get_checksum(-1); ck
    'c2f61950de5d7032353a4cfff12974f56a1f2934e4bd337cb8ebf6aa316f0e2b'
    >>> ds.select("/a/b/e")
    ['', 'a', 'b', 'e']
    >>> ds.sum_contents(['some', 'other', 'contents'])
    ... # doctest: +NORMALIZE_WHITESPACE
    ['dfda7c2df11412473dfb84b8060b2fd47afd5f42a51b033698ca1a9bf5d6dc88',
     'dfda7c2df11412473dfb84b8060b2fd47afd5f42a51b033698ca1a9bf5d6dc88',
     'dfda7c2df11412473dfb84b8060b2fd47afd5f42a51b033698ca1a9bf5d6dc88',
     'b79eadf1379aa3320833857715bc721291b823506accb4a4f8b86f7cdb71c4a1']
    >>> ds.get_checksum(2) != ds.get_checksum(3)
    True
    >>> ds.entries()
    ... # doctest: +NORMALIZE_WHITESPACE
        [('',  'dfda7c2df11412473dfb84b8060b2fd47afd5f42a51b033698ca1a9bf5d6dc88'),
         ('a', 'dfda7c2df11412473dfb84b8060b2fd47afd5f42a51b033698ca1a9bf5d6dc88'),
         ('b', 'dfda7c2df11412473dfb84b8060b2fd47afd5f42a51b033698ca1a9bf5d6dc88'),
         ('e', 'b79eadf1379aa3320833857715bc721291b823506accb4a4f8b86f7cdb71c4a1')]


    """
    def __init__(self):
        self.stack = []

    def dir_names(self):
        """
        :return: list of directory names in stack
        """
        return [d[0] for d in self.stack]

    def entries(self):
        """
        Snapshot of the stack, all checksums expressed as hexadecimal digests.

        :return: a list of length-2 tuples
        """
        return [(d[0], d[1].hexdigest()) for d in self.stack]

    def push(self, entry):
        """
        Adds an empty subdirectory at the end of the stack,
        with a new cksum.

        :param entry:
        """
        logger.debug("push(%r)", entry)
        ck = hashlib.sha256()
        self.stack.append((entry, ck))

    def pushx(self, entries):
        """
        >>> ds = DirStack()
        >>> ds.pushx(["a", "b","c"])
        ['a', 'b', 'c']

        :param entries: list of directory names, high level first.
        :returns the new list
        """
        for e in entries:
            self.push(e)
        return self.dir_names()

    def pop(self):
        """
        >>> ds = DirStack()
        >>> ds.pushx(["a", "b","c","d"])
        ['a', 'b', 'c', 'd']
        >>> ds.pop() # doctest: +ELLIPSIS
        ('d', <sha256 HASH object @ 0x...>)
        >>> ds.popx(2)
        ['a']

        """
        logger.debug("pop(): %r - %r", self.stack[-1][0], self.stack[-1][1].hexdigest())
        return self.stack.pop()

    def popx(self, n):
        """
        Pops several directories at once.
        
        >>> ds = DirStack()
        >>> ds.pushx(["a", "b","c","d"])
        ['a', 'b', 'c', 'd']
        >>> ds.popx(2)
        ['a', 'b']

        :param n: number of directory levels to go up
        """
        while n:
            self.pop()
            n -= 1

        return self.dir_names()

    def level(self):
        return len(self.stack)

    def select(self, dirpath):
        """
        >>> ds = DirStack()
        >>> ds.select("/a/b/c")
        ['', 'a', 'b', 'c']
        >>> ds.sum_contents(['some', 'file', 'and', 'dir', 'from', 'contents'])
        ... # doctest: +NORMALIZE_WHITESPACE
        ['c2f61950de5d7032353a4cfff12974f56a1f2934e4bd337cb8ebf6aa316f0e2b',
        'c2f61950de5d7032353a4cfff12974f56a1f2934e4bd337cb8ebf6aa316f0e2b',
        'c2f61950de5d7032353a4cfff12974f56a1f2934e4bd337cb8ebf6aa316f0e2b',
        'c2f61950de5d7032353a4cfff12974f56a1f2934e4bd337cb8ebf6aa316f0e2b']
        >>> ck = ds.get_checksum(-1); ck
        'c2f61950de5d7032353a4cfff12974f56a1f2934e4bd337cb8ebf6aa316f0e2b'
        >>> ds.select("/a/b/e")
        ['', 'a', 'b', 'e']
        >>> ds.sum_contents(['some', 'other', 'contents'])
        ... # doctest: +NORMALIZE_WHITESPACE
        ['dfda7c2df11412473dfb84b8060b2fd47afd5f42a51b033698ca1a9bf5d6dc88',
         'dfda7c2df11412473dfb84b8060b2fd47afd5f42a51b033698ca1a9bf5d6dc88',
         'dfda7c2df11412473dfb84b8060b2fd47afd5f42a51b033698ca1a9bf5d6dc88',
         'b79eadf1379aa3320833857715bc721291b823506accb4a4f8b86f7cdb71c4a1']
        >>> ds.get_checksum(2) != ds.get_checksum(3)
        True
        >>> ds.entries()
        ... # doctest: +NORMALIZE_WHITESPACE
            [('',  'dfda7c2df11412473dfb84b8060b2fd47afd5f42a51b033698ca1a9bf5d6dc88'),
             ('a', 'dfda7c2df11412473dfb84b8060b2fd47afd5f42a51b033698ca1a9bf5d6dc88'),
             ('b', 'dfda7c2df11412473dfb84b8060b2fd47afd5f42a51b033698ca1a9bf5d6dc88'),
             ('e', 'b79eadf1379aa3320833857715bc721291b823506accb4a4f8b86f7cdb71c4a1')]

        """
        logger.info("select(%r)", dirpath)
        l1 = dirpath.split(os.sep)
        # find common stem
        lvl=0
        while (lvl<self.level()) and (lvl<len(l1)):
            if l1[lvl] != self.stack[lvl][0]:
                logger.info("back to level %d", lvl)
                break
            lvl +=1
        self.popx(self.level() - lvl)
        self.pushx(l1[lvl:])
        return self.dir_names()

    def get_checksum(self, lvl):
        return self.stack[lvl][1].hexdigest()

    def sum_contents(self, contents, encoding='utf_8'):
        # Separate entries with "\0", dirs with "\n
        chunk = ("\0".join(contents) + "\n").encode(encoding)
        logger.debug("sum_contents(%r)", contents)
        r = [] # for tests
        for a, h in self.stack:
            h.update(chunk)
            logger.debug("%r: %r", a, h.hexdigest())
            r.append(h.hexdigest())
        return r

class App:
    """
    Encapsulates application arguments and workflow.

    :param args: dict, typically generated with argparser
    """

    def __init__(self, args):
        logger.info("App(%r)", args)
        self.args = args
        logger.setLevel(self.args.log_level.upper())
        self.selectors = [re.compile(r) for r in args.dir_selectors]

    def run(self):
        mdb = mlocate.MLocateDB()
        mdb.connect(self.args.database)

        self.ds = DirStack()

        for d in mdb.load_dirs(self.args.limit_input_dirs):
            if self.match_dir(d):
                self.process_dir(d)

        self.report()

    def match_dir(self, d):
        """
        >>> app = App(arg_parser().parse_args('-L debug -d /tmp/MyBook.db /home/mich/\\.virtualenvs/?'.split()))
        >>> app = App(arg_parser().parse_args(['/home/mich/\\.virtualenvs/?']))
        >>> app.match_dir(dict(name='/home/mich/.virtualenvs'))
        True
        >>> app.match_dir(dict(name='/home/mich/.virtualenvs/py2/share'))
        True

        :param d:
        :return:
        """
        # logger.debug("match_dir(%r)", d)
        for s in self.selectors:
            if s.match(d['name']):
                return True
        return False

    def process_dir(self,d):
        """

        :param d: an element returned by MLocate.load_dirs()
        """
        logger.info("process_dir(%r)", d)
        #dpath = d['name'].split(os.sep)
        self.ds.select(d['name'])
        # TODO handle popped directories

    def report(self):
        """
        Instead of reporting each single duplicated directory,
        try to identify highest level of each set.

        """
        # TODO implement reporting
        pass


def arg_parser():
    """
    Creates a command line parser suitable for this app.

    >>> parser = arg_parser()
    >>> parser.print_help()
    usage: docrunner.py [-h] [-L LOG_LEVEL] [-d DATABASE] [-I LIMIT_INPUT_DIRS]
                        [dir_selectors [dir_selectors ...]]
    <BLANKLINE>
    Lookup items in mlocate database
    <BLANKLINE>
    positional arguments:
      dir_selectors         filtering regexp for input directories
    <BLANKLINE>
    optional arguments:
      -h, --help            show this help message and exit
      -L LOG_LEVEL, --log-level LOG_LEVEL
      -d DATABASE, --database DATABASE
                            name of the mlocate database
      -I LIMIT_INPUT_DIRS, --limit-input-dirs LIMIT_INPUT_DIRS
                            Maximum directory entries read from db

   """
    parser = argparse.ArgumentParser()
    parser.description = "Lookup items in mlocate database"
    # parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('-L', '--log-level', default='WARNING')
    parser.add_argument('-d', '--database', help="name of the mlocate database", default=MLOCATE_DEFAULT_DB)
    parser.add_argument('-I', '--limit-input-dirs', help="Maximum directory entries read from db", type=int, default=0)
    parser.add_argument('dir_selectors', nargs='*', help="filtering regexp for input directories")

    return parser


if __name__ == '__main__':
    cli_args = arg_parser().parse_args()
    # print "Would run with", args
    App(cli_args).run()

