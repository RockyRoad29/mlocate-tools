#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------
# Copyright (c) $(YEAR} Michelle Baert
# Some rights reserved
# file: {$FILENAME} created by mich on 02/08/17.
# ----------------------------------------
"""
Utilities for processing binary streams.
"""

import logging
import sys

logger = logging.getLogger(__name__)

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
    :return: bytes string excluding the final b'\0'

    """
    buf = b''
    b = f.read(1)
    while b != b'\0':
        buf += b
        b = f.read(1)
    # work with byte arrays, decode late, for printing.
    return buf


def safe_decode(data, prefix=''):
    r"""
    Decodes binary data to a string in default encoding.
    If an error occurs, it is reported (logger)
    then decoding is performed with `errors='backslashreplace'`
    to return a printable string.

    >>> safe_decode(b'some/messy\xe9ename/in/path')
    'some/messy\\xe9ename/in/path'

    Check the warning messages triggered below: they should include full path
    >>> safe_decode(b'messy\xe9efilename.jpg', "some/regular/path/")
    'messy\\xe9efilename.jpg'
    >>> safe_decode(b'messy\xe9efilename.jpg', "some/messy\xe9ename/in/path/")
    'messy\\xe9efilename.jpg'

    :rtype : string decoded
    :param data: bytes
    :param prefix:
    """
    try:
        decoded = data.decode()
    except UnicodeDecodeError as e:
        logger.warning("Error decoding %r: %s", data, e.reason)
        decoded = data.decode(errors='backslashreplace')
        logger.warning("Entry parsed as %r", prefix + decoded)
    return decoded