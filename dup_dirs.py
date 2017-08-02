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
import fnmatch
import hashlib
import logging
import argparse
import os
import re

from binutils import safe_decode
import mlocate
from dict_of_lists import DictOfLists

LOGGER = logging.getLogger(__name__)

class DirHashStack:
    """
    Maintains a list of contents checksums for each level of ancestor directories.

    >>> ds = DirHashStack()
    >>> contents1 = [(False, b'some'), (False, b'file'), (False, b'and'), (True, b'dir'), (False, b'from'), (False, b'contents')]
    >>> contents2 = [(0, 'some'), (1, 'other'), (0, 'contents')]

    >>> ds.select(b"/a/b/c")
    [b'', b'a', b'b', b'c']
    >>> DirHashStack.INITIAL_CK
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    >>> DirHashStack.EMPTY_DIR_CK
    '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945'
    >>> ds.get_checksum(1) == DirHashStack.INITIAL_CK
    True
    >>> ds.get_checksums() == [DirHashStack.INITIAL_CK]*4
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

    def __init__(self,on_push=None, on_pop=None):
        self.stack = []
        self.on_push = on_push
        self.on_pop = on_pop

    # -------------------------- Stack read access
    def level(self):
        """
        Current depth in subdirectories

        :return: int
        """
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
        """
        :return: list of directory checksums digests
        """
        return [l[1].hexdigest() for l in self.stack]

    def get_checksum(self, lvl):
        """
        checksum digest for directory at given depth
        :return: str
        """
        return self.stack[lvl][1].hexdigest()

    # -------------------------- Basic stack operations
    def push(self, entry):
        """
        Adds an empty subdirectory at the end of the stack,
        with a new cksum.

        >>> ds = DirHashStack()
        >>> ds.push(b'a')
        >>> ds.push(b'b')
        >>> ds.entries() # doctest: +NORMALIZE_WHITESPACE
        [(b'a', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
         (b'b', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')]

        :param entry:
        """
        LOGGER.debug("push(%r)", entry)
        if self.on_push:
            self.on_push(self, entry)
        ck = hashlib.sha256()
        self.stack.append((entry, ck))

    def pop(self):
        """
        >>> ds = DirHashStack()
        >>> ds.push(b'a')
        >>> ds.push(b'b')
        >>> ds.pop() # doctest: +ELLIPSIS
        (b'b', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')

        """
        LOGGER.debug("pop(): %r - %r", self.stack[-1][0], self.stack[-1][1].hexdigest())
        name, h = self.stack.pop()
        ck = h.hexdigest()
        if self.on_pop:
            self.on_pop(self, name, ck)
        return (name, ck)

    # --------------------------------------- Multiple stack operation
    def pushx(self, entries):
        """
        >>> ds = DirHashStack()
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

        >>> ds = DirHashStack()
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
        >>> ds = DirHashStack()

        >>> ds.select(b"/a/b/c")
        [b'', b'a', b'b', b'c']
        >>> ds.select(b"/a/b/e")
        [b'', b'a', b'b', b'e']
        """
        LOGGER.info("select(%r)", dirpath)
        l1 = dirpath.split(os.sep.encode())
        # find common stem
        lvl=0
        while (lvl<self.level()) and (lvl<len(l1)):
            if l1[lvl] != self.stack[lvl][0]:
                LOGGER.info("back to level %d", lvl)
                break
            lvl +=1
        self.popx(self.level() - lvl)
        self.pushx(l1[lvl:])
        return self.dir_names()

    def sum_contents(self, contents, encoding='utf_8'):
        # Separate entries with "\0", dirs with "\n
        # chunk = ("\0".join(contents) + "\n").encode(encoding)
        chunk = repr(contents).encode(encoding)
        LOGGER.debug("sum_contents(%r)", contents)
        for a, h in self.stack:
            h.update(chunk)
            LOGGER.debug("%r: %r", a, h.hexdigest())
        return hashlib.sha256(chunk)

class App:
    """
    Encapsulates application arguments and workflow.

    :param args: dict, typically generated with argparser
    """

    def __init__(self, args):
        self.args = args
        # convert and compile patterns
        if args.use_regexps:
            regexps = args.dir_selectors
        else:
            regexps = [fnmatch.translate(p) for p in args.dir_selectors]
        self.selectors = [re.compile(r) for r in regexps]

        self.ds = DirHashStack(self.push_handler, self.pop_handler)
        self.tree = DictOfLists()
        self.rtree = DictOfLists()
        self.by_ck = DictOfLists()


    def run(self):
        """
        >> from cli import main_parser
        >> args = main_parser().parse_args("-d /tmp/MyBook.db -I 100 dups .*[Pp]hotos?/?".split())
        >>> args = argparse.Namespace(database='data/virtualenvs.db', dir_selectors=['/home/mich/.virtualenvs/*'],
        ...         limit_input_dirs=0, use_regexps=False)
        >>> app = App(args)
        >>> app.run() # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
        Reporting Duplicates
        * ... : ... potential duplicates...
           - /home/mich/.virtualenvs/...
        ...
        * ... : ... potential duplicates...
           - /home/mich/.virtualenvs/...
           - /home/mich/.virtualenvs/...
        ...
        """
        mdb = mlocate.MLocateDB()
        mdb.connect(self.args.database)

        for d in mdb.load_dirs(self.args.limit_input_dirs):
            if self.match_path(d.name):
                self.process_dir(d)

        self.report()

    def match_path(self, name):
        """
        >>> args = argparse.Namespace(app_config=False, command='dups', database='/var/lib/mlocate/mlocate.db', dry_run=False, limit_input_dirs=0, log_level='WARNING', mdb_settings=False, dir_selectors=['/home/mich/\\.virtualenvs/?'], use_regexps=True)
        >>> app = App(args)
        >>> app.match_path('/home/mich/.virtualenvs')
        True
        >>> app.match_path('/home/mich/.virtualenvs/py2/share')
        True

        :param name:
        :return:
        """
        # LOGGER.debug("match_path(%r)", name)
        for s in self.selectors:
            if s.match(name):
                return True
        return False

    def process_dir(self,d):
        """

        :param d: an element returned by MLocate.load_dirs()
        """
        LOGGER.info("process_dir(%r)", d)
        #dpath = d['name'].split(os.sep)
        self.ds.select(d.bname)
        self.ds.sum_contents(d.contents)

    def push_handler(self, ds, entry):
        """
        :type ds: DirHashStack
        :param ds:
        :param entry:
        """
        pass

    def pop_handler(self, ds, name, ck):
        """


        :type ds: DirHashStack
        :type ck: str
        """
        self.tree.add_to(ds.get_checksum(-1), ck)
        dpath = os.sep.encode().join(ds.dir_names()+[name])
        self.by_ck.add_to(ck, dpath)

    def report(self):
        """
        Instead of reporting each single duplicated directory,
        try to identify highest level of each set.

        """
        # Build reversed tree (parents)
        for ck, contents in self.tree.items():
            for d in contents:
                self.rtree.add_to(d, ck)

        # Select duplicated checksums
        dups = [ck for ck, l in self.by_ck.items() if (ck != DirHashStack.EMPTY_DIR_CK) and (len(l) > 1)]
        if not dups:
            print("No duplicate found")
            return None

        print ("Reporting Duplicates ")
        for ck in dups:
            # Check if all parents are as well duplicates (subdup)
            parents = self.rtree[ck]
            top = [p for p in parents if p not in dups]
            if not top:
                LOGGER.info("Skipping subdup: %s", ck)
                #typ = 'sub'
                continue
            if len(top) < len(parents):
                typ = 'mix'
                LOGGER.info("Mixed dup %s", ck)
            else:
                typ = 'top'

            dirs = self.by_ck[ck]
            print("* {0} : {1} potential duplicates ({2})".format(ck, len(dirs), typ))
            for d in sorted(dirs):
                print("   -", safe_decode(d))

    def dups(self):
        #return [(name, len(l))
        return [ck for ck, l in self.by_ck.items() if len(l) > 1]

    def top_dups(self):
        dups = [name for name, l in self.rtree.items() if len(l) > 1]
        return [(name, self.dirpaths(name, dups)) for name in dups]
