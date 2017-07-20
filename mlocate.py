#!/usr/bin/env python3
# coding=utf-8

"""
Parse and use mlocate databases.
"""

import logging
import struct
import datetime
import json
import sys

logger = logging.getLogger()
logger.setLevel('INFO')


def read_cstring(f, coding='utf-8'):
    """
    Reads a null-terminated string from a binary file.

    :param f: opened readable stream (file)
    :param coding: text encoding
    :return: a string
    """
    buf = b''
    b = f.read(1)
    while b != b'\0':
        buf += b
        b = f.read(1)
    return ''.join(buf.decode(coding))


class MLocateDB:
    """
    Handles a mlocate database.

    >>> mdb = MLocateDB()
    >>> mdb.connect('/tmp/MyBook.db')
    >>> sorted(mdb.header.items())
    [('conf_block_size', 544), ('file_format', 0), ('req_visibility', 0), ('root', '/run/media/mich/MyBook')]
    >>> mdb.tell()
    583
    >>> mdb.db.seek(583)
    583
    >>> #[mdb.load_dirs() for i in range(3)]
    >>> for i, d in enumerate(mdb.load_dirs()): # doctest: +ELLIPSIS,+NORMALIZE_WHITESPACE
    ...     print (i, json.dumps(d,indent=2,sort_keys=True, default=str))
    ...     i += 1
    ...     if i >= 3:
    ...         break
    0 {
      "contents": [ [ 1, "$RECYCLE.BIN" ], ... [ 1, "media" ] ],
      "dt": "2013-08-20 01:55:07.653616",
      "name": "/run/media/mich/MyBook"
    }
    1 {
      "contents": [ [  1, "S-1-5-21-1696441804-2191777423-1598828944-1001" ] ],
      "dt": "2013-08-16 17:03:59.550653",
      "name": "/run/media/mich/MyBook/$RECYCLE.BIN"
    }
    2 {
      "contents": [ [ 0, "desktop.ini" ] ],
      "dt": "2013-08-16 17:03:59.956254",
      "name": "/run/media/mich/MyBook/$RECYCLE.BIN/S-1-5-21-1696441804-2191777423-1598828944-1001"
    }
    """

    def __init__(self):
        self.db = None
        self.header = None
        self.conf = None
        self.dirs = None
        self.pos = None

    def connect(self, path):
        """
        Opens the database file, reads the header and configuration.

        :param path: path to the mlocate database
        """
        self.db = open(path, 'rb')
        self._read_header()
        self._read_conf()

    def tell(self):
        """
        Reads and stores current file position.
        For testing and debugging.

        :return: current position in the file.
        """
        self.pos = self.db.tell()
        return self.pos

    def _read_header(self):
        logger.info('reading header')
        magic = self.db.read(8)
        assert (magic == b"\0mlocate")

        # int.from_bytes(buf,'big')
        data = struct.unpack('>ibbh', self.db.read(8))
        flds = 'conf_block_size, file_format, req_visibility'.split(', ')
        self.header = dict(zip(flds, data[:-1]))  # padding ignored
        self.header['root'] = read_cstring(self.db, 'utf-8')
        self.tell()

    def _read_conf(self):
        logger.info('reading config block')
        if not self.header:
            self._read_header()

        conf_block = self.db.read(self.header['conf_block_size'])
        self.conf = {}
        grp = []
        for s in conf_block.split(b'\x00'):
            if s == b'':
                # logger.info("Closing group")
                if len(grp) > 0:
                    self.conf[grp[0]] = grp[1:]
                    grp = []
                else:
                    logger.info("Empty group. End of conf?")
            else:
                # print("Adding: ",s)
                grp.append(s)
        logger.debug("Final group: %r", grp)
        # assert(len(grp)==0)
        self.tell()

    def load_dirs(self, limit=0):
        """
        Generator for directory elements.

        :param limit: int maximum count of directories, 0 for unlimited (default)
        :return: each yielded element is a dictionary of
                  'name': the full path of the directory,
                  'dt': the directory's modification time,
                  'contents': a list of directory contents, each element being
                     - a flag : 1 for a subdirectory, 0 otherwise
                     - the basename of the entry

        >>> mdb = MLocateDB()
        >>> mdb.connect('/tmp/MyBook.db')
        >>> for d in mdb.load_dirs(3): # doctest: +ELLIPSIS,+NORMALIZE_WHITESPACE
        ...     print (json.dumps(d,indent=2,sort_keys=True, default=str))
        {
          "contents": [ [ 1, "$RECYCLE.BIN" ], ... [ 1, "media" ] ],
          "dt": "2013-08-20 01:55:07.653616",
          "name": "/run/media/mich/MyBook"
        }
        {
          "contents": [ [  1, "S-1-5-21-1696441804-2191777423-1598828944-1001" ] ],
          "dt": "2013-08-16 17:03:59.550653",
          "name": "/run/media/mich/MyBook/$RECYCLE.BIN"
        }
        {
          "contents": [ [ 0, "desktop.ini" ] ],
          "dt": "2013-08-16 17:03:59.956254",
          "name": "/run/media/mich/MyBook/$RECYCLE.BIN/S-1-5-21-1696441804-2191777423-1598828944-1001"
        }
        """
        if (limit==0):
            limit = sys.maxsize

        while limit != 0:
            limit -= 1
            # header
            buf = self.db.read(16)
            if len(buf) < 16:
                break
                # raise StopIteration

            # directory details
            dir_seconds, dir_nanos, padding = struct.unpack('>qli', buf)
            yield {
                'name': read_cstring(self.db),
                'dt': datetime.datetime.fromtimestamp(dir_seconds).replace(microsecond=round(dir_nanos / 1000)),
                'contents': [t for t in iter(self._read_direntry, None)]
                # NOTE generator not wanted for dir entries: data must be read now.
            }

    def _read_direntry(self):
        flag = struct.unpack('b', self.db.read(1))[0]
        if flag == 2:
            # print('end of dir')
            return None  # end of directory contents
        name = read_cstring(self.db)
        # print (flag, name)
        return int(flag), name
