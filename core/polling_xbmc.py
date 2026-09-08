# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.



import xbmcvfs
from . import settings
from functools import partial
from .polling import Poller, PollerNonRecursive, file_list_from_walk, hidden
from .utils import log, raise_if_aborted, vfs_lock


def _has_bad_encoding(name):
    # xbmcvfs.listdir() decodes filenames leniently (surrogateescape-style),
    # so a name which isn't valid UTF-8 on the source filesystem (e.g. Latin-1
    # accented characters on an NFS share) comes back as a str containing
    # lone surrogate codepoints. Passing such a string back into xbmcvfs
    # can crash when it tries to re-encode it for the native VFS layer, so
    # any such name has to be skipped rather than ever handed back to xbmcvfs.
    try:
        name.encode('utf-8')
        return False
    except UnicodeEncodeError:
        return True


def _filter_names(current, names):
    ok = []
    for name in names:
        if hidden(name):
            continue
        if _has_bad_encoding(name):
            log("skipping <%s> in <%s>: not representable as utf-8" % (name, current))
            continue
        ok.append(name)
    return ok


def _walk(path):
    # recurse through xbmcvfs.listdir() via nested generator delegation:
    # a flat, explicit work list means that every call to xbmcvfs.listdir()
    # is made from the same context
    pending = [path]
    while pending:
        current = pending.pop()
        raise_if_aborted()
        with vfs_lock:
            dirs, files = xbmcvfs.listdir(current)
        # sometimes xbmcvfs returns an invalid utf-8 encoding. we only care
        # about finding changed paths so it's ok to ignore here
        dirs = [current + d for d in _filter_names(current, dirs)]
        files = [current + f for f in _filter_names(current, files)]
        yield dirs, files
        pending.extend(d + '/' for d in dirs)


def _list_files(path):
    with vfs_lock:
        dirs, files = xbmcvfs.listdir(path)
    return [path + '/' + f for f in _filter_names(path, files)]


def _get_mtime(path):
    with vfs_lock:
        return xbmcvfs.Stat(path).st_mtime()


class _Recursive(Poller):
    polling_interval = settings.POLLING_INTERVAL
    list_files = partial(file_list_from_walk(_walk))

    def is_offline(self):
        # Since path is always a media source, it's unlikely the user would
        # delete it. Assume it's offline if it doesn't exist.
        with vfs_lock:
            return not xbmcvfs.exists(self.watch.path)


class _NonRecursive(PollerNonRecursive):
    polling_interval = 1
    list_files = partial(_list_files)
    get_mtime = partial(_get_mtime)

VFSPoller = _Recursive if settings.RECURSIVE else _NonRecursive
