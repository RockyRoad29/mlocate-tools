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
    >>> ds.sum_contents([(0, 'some'), (0, 'file'), (0, 'and'), (1, 'dir'), (0, 'from'), (0, 'contents')])
    ... # doctest: +NORMALIZE_WHITESPACE
    ['ae4889154c74294cd83990f3d767e5cdcddc68dbefbda5255c3813201ddf859e',
     'ae4889154c74294cd83990f3d767e5cdcddc68dbefbda5255c3813201ddf859e',
     'ae4889154c74294cd83990f3d767e5cdcddc68dbefbda5255c3813201ddf859e',
     'ae4889154c74294cd83990f3d767e5cdcddc68dbefbda5255c3813201ddf859e']
    >>> ck = ds.get_checksum(-1); ck
    'ae4889154c74294cd83990f3d767e5cdcddc68dbefbda5255c3813201ddf859e'
    >>> ds.select("/a/b/e")
    ['', 'a', 'b', 'e']
    >>> ds.sum_contents([(0, 'some'), (1, 'other'), (0, 'contents')])
    ... # doctest: +NORMALIZE_WHITESPACE
    ['65416eddfded80e9ba9de1c99a3c68e365425df49466e9782fa836af0b933c10',
     '65416eddfded80e9ba9de1c99a3c68e365425df49466e9782fa836af0b933c10',
     '65416eddfded80e9ba9de1c99a3c68e365425df49466e9782fa836af0b933c10',
     'c3519456f6e17deefa2f84dbd38d95b26dc36a4c68b84728bf73cb2d949b279f']
    >>> ds.get_checksum(2) != ds.get_checksum(3)
    True
    >>> ds.entries()
    ... # doctest: +NORMALIZE_WHITESPACE
    [('', '65416eddfded80e9ba9de1c99a3c68e365425df49466e9782fa836af0b933c10'),
     ('a', '65416eddfded80e9ba9de1c99a3c68e365425df49466e9782fa836af0b933c10'),
     ('b', '65416eddfded80e9ba9de1c99a3c68e365425df49466e9782fa836af0b933c10'),
     ('e', 'c3519456f6e17deefa2f84dbd38d95b26dc36a4c68b84728bf73cb2d949b279f')]


    """
    EMPTY_DIR_CK = hashlib.sha256(b'[]')

    def __init__(self, on_pop=None):
        self.stack = []
        self.on_pop = on_pop

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
        ('d', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
        >>> ds.popx(2)
        ['a']

        """
        logger.debug("pop(): %r - %r", self.stack[-1][0], self.stack[-1][1].hexdigest())
        dpath = os.sep.join(self.dir_names())
        name, h = self.stack.pop()
        ck = h.hexdigest()
        if self.on_pop:
            self.on_pop(dpath, ck)
        return (name, ck)

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
        >>> ds.sum_contents([(0, 'some'), (0, 'file'), (0, 'and'), (1, 'dir'), (0, 'from'), (0, 'contents')])
        ... # doctest: +NORMALIZE_WHITESPACE
        ['ae4889154c74294cd83990f3d767e5cdcddc68dbefbda5255c3813201ddf859e',
         'ae4889154c74294cd83990f3d767e5cdcddc68dbefbda5255c3813201ddf859e',
         'ae4889154c74294cd83990f3d767e5cdcddc68dbefbda5255c3813201ddf859e',
         'ae4889154c74294cd83990f3d767e5cdcddc68dbefbda5255c3813201ddf859e']
        >>> ck = ds.get_checksum(-1); ck
        'ae4889154c74294cd83990f3d767e5cdcddc68dbefbda5255c3813201ddf859e'
        >>> ds.select("/a/b/e")
        ['', 'a', 'b', 'e']
        >>> ds.sum_contents([(0, 'some'), (1, 'other'), (0, 'contents')])
        ... # doctest: +NORMALIZE_WHITESPACE
        ['65416eddfded80e9ba9de1c99a3c68e365425df49466e9782fa836af0b933c10',
         '65416eddfded80e9ba9de1c99a3c68e365425df49466e9782fa836af0b933c10',
         '65416eddfded80e9ba9de1c99a3c68e365425df49466e9782fa836af0b933c10',
         'c3519456f6e17deefa2f84dbd38d95b26dc36a4c68b84728bf73cb2d949b279f']
        >>> ds.get_checksum(2) != ds.get_checksum(3)
        True
        >>> ds.entries()
        ... # doctest: +NORMALIZE_WHITESPACE
        [('', '65416eddfded80e9ba9de1c99a3c68e365425df49466e9782fa836af0b933c10'),
         ('a', '65416eddfded80e9ba9de1c99a3c68e365425df49466e9782fa836af0b933c10'),
         ('b', '65416eddfded80e9ba9de1c99a3c68e365425df49466e9782fa836af0b933c10'),
         ('e', 'c3519456f6e17deefa2f84dbd38d95b26dc36a4c68b84728bf73cb2d949b279f')]

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
        # chunk = ("\0".join(contents) + "\n").encode(encoding)
        chunk = repr(contents).encode(encoding)
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
        self.by_ck = {}
        logger.info("App(%r)", args)
        self.args = args
        logger.setLevel(self.args.log_level.upper())
        self.selectors = [re.compile(r) for r in args.dir_selectors]

    def run(self):
        mdb = mlocate.MLocateDB()
        mdb.connect(self.args.database)

        self.ds = DirStack(self.pop_handler)

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
        self.ds.sum_contents(d['contents'])

    def pop_handler(self, dpath, ck):
        if ck in self.by_ck:
            self.by_ck[ck].append(dpath)
        else:
            self.by_ck[ck] = [dpath]

    def report(self):
        """
        Instead of reporting each single duplicated directory,
        try to identify highest level of each set.

        """
        # TODO Test the restriction to top level
        print ("Reporting Duplicates ")
        prev = None
        for ck, dirs in self.by_ck.items():
            if ck == DirStack.EMPTY_DIR_CK:
                continue
            if len(dirs) > 1:
                print("* {0} : {1} potential duplicates".format(ck, len(dirs)))
                for d in dirs:
                    if prev and (d.startswith(prev + "/")):
                        # ignore subdir
                        pass
                    else:
                        print("   - ", d)


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
