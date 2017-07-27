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


def read_cstring(f):
    #https://stackoverflow.com/questions/44296354/valueerror-source-code-string-cannot-contain-null-bytes
    r"""
    Reads a null-terminated byte sequence from a binary file.

    In order be able to better deal with potential string encoding
    errors, without altering the real filenames,
    no assumption is made as this stage about encoding.

    In a utf-8 based system, it may occasionally happen that a filename
    has a different encoding, or encoded twice.

    OS may replace problematic characters with an interrogation point.
    Similar behavior may be obtained like this:

    >>> import io
    >>> s = read_cstring(io.BytesIO(b'3v_laiton_motoris\xe9e.pdf\0\more data'))
    >>> s
    b'3v_laiton_motoris\xe9e.pdf'
    >>> s.decode(errors='replace')
    '3v_laiton_motoris�e.pdf'

    Another bonus for decoding late is to be able to report the cause of the error in filesystem,
    the full path of the problematic name.

    :param f: opened readable binary stream (typically a file)
    :return: a byte array, excluding the final b'\0'
            You
    """
    buf = b''
    b = f.read(1)
    while b != b'\0':
        buf += b
        b = f.read(1)
    # work with byte arrays, decode late, for printing.
    return buf


def safe_decode(bname, prefix=''):
    r"""
    >>> safe_decode(b'some/messy\xe9ename/in/path')
    'some/messy\\xe9ename/in/path'

    Check the warning messages triggered below: they should include full path
    >>> safe_decode(b'messy\xe9efilename.jpg', "some/regular/path/")
    'messy\\xe9efilename.jpg'
    >>> safe_decode(b'messy\xe9efilename.jpg', "some/messy\xe9ename/in/path/")
    'messy\\xe9efilename.jpg'

    :rtype : string decoded
    :param bname:
    :param prefix:
    """
    try:
        name = bname.decode()
    except UnicodeDecodeError as e:
        logger.warning("Error decoding %r: %s", bname, e.reason)
        name = bname.decode(errors='backslashreplace')
        logger.warning("Entry parsed as %r", prefix + name)
    return name

class MLocateDB:
    """
    Handles a mlocate database.

    >>> mdb = MLocateDB()
    >>> mdb.connect('/tmp/MyBook.db')
    >>> sorted(mdb.header.items())
    [('conf_block_size', 544), ('file_format', 0), ('req_visibility', 0), ('root', b'/run/media/mich/MyBook')]
    >>> mdb.tell()
    583
    >>> mdb.db.seek(583)
    583
    >>> #[mdb.load_dirs() for i in range(3)]
    >>> for i, d in enumerate(mdb.load_dirs()): # doctest: +ELLIPSIS,+NORMALIZE_WHITESPACE
    ...     print (i, json.dumps(d.decode(),indent=2,sort_keys=True))
    ...     i += 1
    ...     if i >= 3:
    ...         break
    0 {
      "contents": [ [ true, "$RECYCLE.BIN" ], ... [ true, "media" ] ],
      "dt": "2013-08-20 01:55:07.653616",
      "name": "/run/media/mich/MyBook"
    }
    1 {
      "contents": [ [  true, "S-1-5-21-1696441804-2191777423-1598828944-1001" ] ],
      "dt": "2013-08-16 17:03:59.550653",
      "name": "/run/media/mich/MyBook/$RECYCLE.BIN"
    }
    2 {
      "contents": [ [  false, "desktop.ini" ] ],
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
        self.header['root'] = read_cstring(self.db)
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
        ...     print (json.dumps(d.decode(),indent=2,sort_keys=True))
        {
          "contents": [ [ true, "$RECYCLE.BIN" ], ... [ true, "media" ] ],
          "dt": "2013-08-20 01:55:07.653616",
          "name": "/run/media/mich/MyBook"
        }
        {
          "contents": [ [  true, "S-1-5-21-1696441804-2191777423-1598828944-1001" ] ],
          "dt": "2013-08-16 17:03:59.550653",
          "name": "/run/media/mich/MyBook/$RECYCLE.BIN"
        }
        {
          "contents": [ [  false, "desktop.ini" ] ],
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
            d = DirEntry(bname=read_cstring(self.db),
                         dt=datetime.datetime.fromtimestamp(dir_seconds).replace(microsecond=round(dir_nanos / 1000)),
                         contents= [t for t in iter(self._read_direntry, None)]
            )
            # NOTE generator not wanted for dir entries: data must be read now.
            yield d

    def _read_direntry(self):
        flag = struct.unpack('b', self.db.read(1))[0]
        if flag == 2:
            # print('end of dir')
            return None  # end of directory contents
        name = read_cstring(self.db)
        # print (flag, name)
        return bool(flag), name


class DirEntry:
    def __init__(self, bname, dt, contents):
        self.bname = bname
        self.dt = dt
        self.contents = contents

    def decode(self):
        r"""
        Returns a printable and readable equivalent of the given direntry.

          - the byte arrays are decoded, errors are handled
              - with backslash replacement
              - and a warning is issued with full path of problematique entry
          - the datetime is converted to its string representation

        Check the warning messages triggered below: they should include full path

        >>> import datetime
        >>> d = DirEntry(bname=b"/some/messy\xe9ename/in/path",
        ...              dt=datetime.datetime(2013, 8, 16, 17, 37, 18, 885441),
        ...              contents=[(False, b'messy\xe9efilename.jpg'),
        ...                        (False, b'110831202504820_47_000_apx_470_.jpg')])
        >>> d.decode() ==  {
        ...        'dt': '2013-08-16 17:37:18.885441',
        ...        'name': '/some/messy\\xe9ename/in/path',
        ...        'contents': [(False, 'messy\\xe9efilename.jpg'), (False, '110831202504820_47_000_apx_470_.jpg')]}
        True

        :return:
        """
        dirname = safe_decode(self.bname)
        return dict(name=dirname,
                    dt=str(self.dt),
                    contents=[(flag, safe_decode(f, dirname+"/")) for flag,f in self.contents]
        )
