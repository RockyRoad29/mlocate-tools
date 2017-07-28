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

MLOCATE_DEFAULT_DB = "/var/lib/mlocate/mlocate.db"
logging.basicConfig(level='DEBUG')
logger = logging.getLogger()


class DirStack:
    """
    Maintains a list of contents checksums for each level of ancestor directories.

    >>> ds = DirStack()
    >>> contents1 = [(False, b'some'), (False, b'file'), (False, b'and'), (True, b'dir'), (False, b'from'), (False, b'contents')]
    >>> contents2 = [(0, 'some'), (1, 'other'), (0, 'contents')]

    >>> ds.select(b"/a/b/c")
    [b'', b'a', b'b', b'c']
    >>> DirStack.INITIAL_CK
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    >>> DirStack.EMPTY_DIR_CK
    '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945'
    >>> ds.get_checksum(1) == DirStack.INITIAL_CK
    True
    >>> ds.get_checksums() == [DirStack.INITIAL_CK]*4
    True
    >>> ck1 = ds.sum_contents(contents1).hexdigest()
    >>> ds.get_checksums() == [ck1]*4
    True
    >>> ds.select(b"/a/b/e")
    [b'', b'a', b'b', b'e']
    >>> ck2 = ds.sum_contents(contents2).hexdigest(); ck2
    'c3519456f6e17deefa2f84dbd38d95b26dc36a4c68b84728bf73cb2d949b279f'
    >>> ck0=ds.get_checksum(0); ck3=ds.get_checksum(3); ck3 != ck0
    True
    >>> ds.entries() # doctest: +NORMALIZE_WHITESPACE
    [(b'',  'dbd445cc0fc3f1ffa5a78a69f16402ace7c7ec95462e20d808cd3ded6c8992f2'),
     (b'a', 'dbd445cc0fc3f1ffa5a78a69f16402ace7c7ec95462e20d808cd3ded6c8992f2'),
     (b'b', 'dbd445cc0fc3f1ffa5a78a69f16402ace7c7ec95462e20d808cd3ded6c8992f2'),
     (b'e', 'c3519456f6e17deefa2f84dbd38d95b26dc36a4c68b84728bf73cb2d949b279f')]
    >>> ds.get_checksums() == [ck0]*3 + [ck3]
    True


    """
    INITIAL_CK = hashlib.sha256().hexdigest()
    EMPTY_DIR_CK = hashlib.sha256(b'[]').hexdigest()

    def __init__(self, on_pop=None):
        self.stack = []
        self.on_pop = on_pop

    # -------------------------- Stack read access
    def level(self):
        return len(self.stack)

    def entries(self):
        """
        Snapshot of the stack, all checksums expressed as hexadecimal digests.

        :return: a list of length-2 tuples
        """
        return [(d[0], d[1].hexdigest()) for d in self.stack]

    def dir_names(self):
        """
        :return: list of directory names in stack
        """
        return [d[0] for d in self.stack]

    def get_checksums(self):
        return [l[1].hexdigest() for l in self.stack]

    def get_checksum(self, lvl):
        return self.stack[lvl][1].hexdigest()

    # -------------------------- Basic stack operations
    def push(self, entry):
        """
        Adds an empty subdirectory at the end of the stack,
        with a new cksum.

        >>> ds = DirStack()
        >>> ds.push(b'a')
        >>> ds.push(b'b')
        >>> ds.entries() # doctest: +NORMALIZE_WHITESPACE
        [(b'a', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
         (b'b', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')]

        :param entry:
        """
        logger.debug("push(%r)", entry)
        ck = hashlib.sha256()
        self.stack.append((entry, ck))

    def pop(self):
        """
        >>> ds = DirStack()
        >>> ds.push(b'a')
        >>> ds.push(b'b')
        >>> ds.pop() # doctest: +ELLIPSIS
        (b'b', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')

        """
        logger.debug("pop(): %r - %r", self.stack[-1][0], self.stack[-1][1].hexdigest())
        dpath = os.sep.encode().join(self.dir_names())
        name, h = self.stack.pop()
        ck = h.hexdigest()
        if self.on_pop:
            self.on_pop(dpath, ck)
        return (name, ck)

    # --------------------------------------- Multiple stack operation
    def pushx(self, entries):
        """
        >>> ds = DirStack()
        >>> ds.pushx([b'a', b'b', b'c', b'd'])
        [b'a', b'b', b'c', b'd']
        >>> ds.pushx([b"e", b"f", b"g"])
        [b'a', b'b', b'c', b'd', b'e', b'f', b'g']

        :param entries: list of directory names, high level first.
        :returns the new list
        """
        for e in entries:
            self.push(e)
        return self.dir_names()

    def popx(self, n):
        """
        Pops several directories at once.

        >>> ds = DirStack()
        >>> ds.pushx([b'a', b'b', b'c', b'd'])
        [b'a', b'b', b'c', b'd']
        >>> ds.popx(2)
        [b'a', b'b']

        :param n: number of directory levels to go up
        """
        while n:
            self.pop()
            n -= 1

        return self.dir_names()

    def select(self, dirpath):
        """
        >>> ds = DirStack()

        >>> ds.select(b"/a/b/c")
        [b'', b'a', b'b', b'c']
        >>> ds.select(b"/a/b/e")
        [b'', b'a', b'b', b'e']
        """
        logger.info("select(%r)", dirpath)
        l1 = dirpath.split(os.sep.encode())
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

    def sum_contents(self, contents, encoding='utf_8'):
        # Separate entries with "\0", dirs with "\n
        # chunk = ("\0".join(contents) + "\n").encode(encoding)
        chunk = repr(contents).encode(encoding)
        logger.debug("sum_contents(%r)", contents)
        for a, h in self.stack:
            h.update(chunk)
            logger.debug("%r: %r", a, h.hexdigest())
        return hashlib.sha256(chunk)

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
        """
        >> app=App(arg_parser().parse_args("-d /tmp/MyBook.db -I 100 .*[Pp]hotos?/?".split()))
        >>> app = App(arg_parser().parse_args('-d data/virtualenvs.db /home/mich/\\.virtualenvs/?'.split()))
        >>> app.run() # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
        Reporting Duplicates
        * ... : ... potential duplicates
           -  b'/home/mich/.virtualenvs/...'
           -  b'/home/mich/.virtualenvs/...'
           - ...
        * ... : ... potential duplicates
           -  b'/home/mich/.virtualenvs/...'
           -  b'/home/mich/.virtualenvs/...'
           - ...
        """
        mdb = mlocate.MLocateDB()
        mdb.connect(self.args.database)

        self.ds = DirStack(self.pop_handler)

        for d in mdb.load_dirs(self.args.limit_input_dirs):
            if self.match_path(d.name):
                self.process_dir(d)

        self.report()

    def match_path(self, name):
        """
        >>> app = App(arg_parser().parse_args(['/home/mich/\\.virtualenvs/?']))
        >>> app.match_path('/home/mich/.virtualenvs')
        True
        >>> app.match_path('/home/mich/.virtualenvs/py2/share')
        True

        :param name:
        :return:
        """
        # TODO Move matching methods to MLocateDB class
        # logger.debug("match_path(%r)", name)
        for s in self.selectors:
            if s.match(name):
                return True
        return False

    def process_dir(self,d):
        """

        :param d: an element returned by MLocate.load_dirs()
        """
        logger.info("process_dir(%r)", d)
        #dpath = d['name'].split(os.sep)
        self.ds.select(d.bname)
        self.ds.sum_contents(d.contents)

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
    >>> parser.parse_args("-L debug -d /tmp/MyBook.db -I 10 .*[Pp]hotos?/?".split())
    Namespace(database='/tmp/MyBook.db', dir_selectors=['.*[Pp]hotos?/?'], limit_input_dirs=10, log_level='debug')

   """
    # TODO allow glob expressions (use fnmatch)
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
