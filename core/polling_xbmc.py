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
from .utils import raise_if_aborted, vfs_lock


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
        dirs = [current + _ for _ in dirs if not hidden(_)]
        files = [current + _ for _ in files if not hidden(_)]
        yield dirs, files
        pending.extend(d + '/' for d in dirs)


def _list_files(path):
    with vfs_lock:
        dirs, files = xbmcvfs.listdir(path)
    return [path + '/' + f for f in files if not hidden(f)]


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
