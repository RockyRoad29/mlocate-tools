# file: {} created by mich on 02/08/17.
# -*- coding: utf-8 -*-
# --------------------------------------------------------
# Copyright (c) Michelle Baert
# Some rights reserved
# --------------------------------------------------------
import logging
from binutils import safe_decode

logger = logging.getLogger(__name__)

class DirBlock:
    """
    Represents a directory entry as known from an mlocate database.

    :param bname: bytes
    :param dt: datetime latest of last modification (mtime) and status time (ctime)
    :param contents: list of byte strings representing the names of this dir entries
    """

    def __init__(self, bname, dt, contents):
        # TODO accept bytes or strings transparently. Conversion is client responsability
        self.bname = bname
        self.dt = dt
        self.contents = contents
        self.selection = None

    def decode(self):
        # TODO confusing definition and use cases
        r"""
        Returns a printable and readable dict representing the current instance.

          - the byte arrays are decoded, errors are handled
              - with backslash replacement
              - and a warning is issued with full path of problematique entry
          - the datetime is converted to its string representation

        Check the warning messages triggered below: they should include full path

        >>> import datetime
        >>> d = DirBlock(bname=b"/some/messy\xe9ename/in/path",
        ...              dt=datetime.datetime(2013, 8, 16, 17, 37, 18, 885441),
        ...              contents=[(False, b'messy\xe9efilename.jpg'),
        ...                        (False, b'110831202504820_47_000_apx_470_.jpg')])
        >>> d.decode() ==  {
        ...        'dt': '2013-08-16 17:37:18.885441',
        ...        'name': '/some/messy\\xe9ename/in/path',
        ...        'contents': [(False, 'messy\\xe9efilename.jpg'), (False, '110831202504820_47_000_apx_470_.jpg')]}
        True

        :return: dict
        """
        dirname = safe_decode(self.bname)
        return dict(name=dirname,
                    dt=str(self.dt),
                    contents=[(flag, safe_decode(f, dirname+"/")) for flag,f in self.contents]
        )

    @property
    def name(self):
        """
        The directory path as decoded string, using `safe_decode()`

        :return: str
        """
        return safe_decode(self.bname)

    def match_path(self, selectors):
        for s in selectors:
            if s.match(self.bname):
                return True

    def match_contents(self, selectors, limit=0):
        """
        Filters or test directory entries by regexps

        :param selectors: list of compiled string regexps to apply to dir contents
        :param limit: maximum count of matched entries to return
        :return:
        """
        logger.info("match_contents(%s,%r) for %s" % (selectors, limit, self.bname))
        rslts = []
        for e in self.contents:
            # FIXME why not encoding regexs and match bytes ?
            name = e[1]
            for s in selectors:
                if s.match(name):
                    rslts.append(e)
                    break
            if limit and (limit <= len(rslts)):
                break

        self.selection = rslts
        return rslts

    def limit_dir_count(self, idx, dlimit=0):
        """
        Simple directory input selector for `MLocateDB.load_some_dirs()` :
        select all directories until a given count has been reached

        :param idx: 1-based index of this element
        :param dlimit: maximum count before stopping iteration
        :return: int -1 when limit has been reached, 1 otherwise
        """
        if dlimit and idx > dlimit:
            return -1
        return 1

    def regex_include(self, idx, paths_limit=0, names_limit=0,
                      path_selectors=None, name_selectors=None):
        """
        Directory input selector for `MLocateDB.load_some_dirs()` :
        select directories matching given selectors, optionally limiting results counts.

        Note: combining excluding paths and names patterns would involve
              some potentially tricky logic assumptions.
              Consider the --pruneXXX options of updatedb or subclass

        :param idx: 1-based index of this element
        :param paths_limit: maximum count before stopping iteration
        :param names_limit: maximum count of names to select
        :param path_selectors : list of compiled regexp patterns for directory path
        :param name_selectors : list of compiled regexp patterns for contents
        :return: int -1 to stop iteration, 0 to skip dir, 1 to accept it
        """
        if paths_limit and idx > paths_limit:
            return -1

        if path_selectors:
            if not self.match_path(path_selectors):
                return 0
        if name_selectors:
            if not self.match_contents(name_selectors, names_limit):
                return 0
        return 1

    def regex_exclude(self, idx, paths_limit=0, names_limit=0,
                      path_selectors=None, name_selectors=None):
        """
        Directory input selector for `MLocateDB.load_some_dirs()` :
        select directories *not* matching given selectors, optionally limiting results counts.

        :param idx: 1-based index of this element
        :param paths_limit: maximum count before stopping iteration
        :param names_limit: maximum count of names to select
        :param path_selectors : list of compiled regexp patterns for directory path
        :param name_selectors : list of compiled regexp patterns for contents
        :return: int -1 to stop iteration, 0 to skip dir, 1 to accept it
        """
        if paths_limit and idx > paths_limit:
            return -1

        if path_selectors:
            if self.match_path(path_selectors):
                return 0
        if name_selectors:
            # find all names to exclude
            if self.match_contents(name_selectors):
                # complement selection
                rslts = [name for name in self.contents if name not in self.selection]
                # apply limit to selected entries
                if names_limit:
                    rslts = rslts[:names_limit]
                self.selection = rslts
                if not rslts:
                    return 0
        return 1

    # TODO write an external selector for pictures, module named from command line.
