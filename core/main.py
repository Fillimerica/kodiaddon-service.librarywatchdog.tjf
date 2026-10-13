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



import os
import time
import traceback
import threading
import xbmc
import xbmcgui
import glob
from . import utils
from . import settings
from . import emitters
from . import videolibrary
from .utils import escape_param, log
from itertools import repeat
from threading import Event
from watchdog.events import FileSystemEventHandler
from .emitters import MultiEmitterObserver
#import web_pdb

class XBMCIF(threading.Thread):
    """Wrapper around the builtins to make sure no two commands are executed at
    the same time (xbmc will cancel previous if not finished)
    """

    def __init__(self):
        threading.Thread.__init__(self)
        self._stop_event = Event()
        self._cmd_queue = utils.OrderedSetQueue()

    def stop(self):
        self._stop_event.set()
        self._cmd_queue.put("stop")  # unblock wait

    def queue_scan(self, library, path=None):
        path = escape_param(path) if path else ""
        cmd = "UpdateLibrary(%s,%s,%s)" % (library, path,
                                           settings.SHOW_PROGRESS_DIALOG)
        self._cmd_queue.put(cmd)

    def queue_clean(self, library):
        self._cmd_queue.put("CleanLibrary(%s,%s)"
                            % (library, settings.SHOW_PROGRESS_DIALOG))

    def queue_remove(self, library, path=None):
        if settings.REMOVAL_ENABLED:
            if settings.PER_FILE_REMOVE and path and library == 'video':
                videolibrary.remove_video(path)
            else:
                self._cmd_queue.put("CleanLibrary(%s,%s)"
                                    % (library, settings.SHOW_PROGRESS_DIALOG))

    def run(self):
        player = xbmc.Player()
        while True:
            self._cmd_queue.wait()
            if self._stop_event.wait(settings.SCAN_DELAY):
                return
            while player.isPlaying():
                self._stop_event.wait(1)
            if self._stop_event.is_set():
                return

            # Remove item right before it's executed so that any duplicates of
            # this commands gets flushed from the queue.
            cmd = self._cmd_queue.get_nowait()
            log("[xbmcif] executing builtin: '%s'" % cmd)
            xbmc.executebuiltin(cmd)

            # wait for scan to start. we need a timeout or else we a screwed
            # if we missed it.
            # TODO: replace this crap with Monitor callbacks in Helix
            log("[xbmcif] waiting for scan/clean start..")
            timeout = 3000
            while not xbmc.getCondVisibility('Library.IsScanning') \
                    and not self._stop_event.is_set():
                xbmc.sleep(100)
                timeout -= 100
                if timeout <= 0:
                    log("[xbmcif] wait for scan/clean timed out.")
                    break
            log("[xbmcif] scan/clean started.")
            log("[xbmcif] waiting for scan/clean end..")

            # wait for scan to end
            while xbmc.getCondVisibility('Library.IsScanning') \
                    and not self._stop_event.is_set():
                xbmc.sleep(100)
            log("[xbmcif] scan/clean ended.")

# TF 10/2026 Added new function to handle associated media files deletion.
# Passing in a FQFN to the media file that was deleted. If the media file has
# been erased, then erase all files in the folder that share the same base name.
    def eraseRelated(self,pFQFN):
        #web_pdb.set_trace()
        #xbmc.log("[EraseRelated] Called Entry Point. Media=%s" % pFQFN, xbmc.LOGINFO)
        if os.path.isfile(pFQFN):
            log("[EraseRelated] The media file still exists. Erasure abandoned. Media=%s" % pFQFN)
            return
        log("[EraseRelated] The media deletion has started. Media=%s" % pFQFN)
        mPathNoExt=os.path.splitext(pFQFN)[0]
        mPathWC=mPathNoExt+'.*'
        # glob finds all the full file paths that match the wildcard pattern
        for file_path in glob.glob(mPathWC):
            try:
                if os.path.isfile(file_path):
                    log("[EraseRelated] Attempt to erase a related file. Filename="+file_path)
                    os.remove(file_path)
            except Exception as e:
                xbmc.log("[EraseRelated] Error while attempting to delete a related file. Filename=%s" % file_path, xbmc.LOGERROR)
                xbmc.log("[EraseRelated] Error: %s" % e , xbmc.LOGERROR)

        # See if parent folder erasure has also been requested.
        if settings.ERASE_RELATED_FOLDER:
            # See if the source path matches any Kodi Video sources.
            mRelPath=""
            mLibMatch=""
            for kodiSource in settings.VIDEO_SOURCES:
                if pFQFN.startswith(kodiSource):
                    mLibMatch=kodiSource
                    mRelFN=pFQFN.removeprefix(mLibMatch)
                    mRelPath=os.path.dirname(mRelFN)
                    break
            # If there is a source match mLibMatch will hold the fixed source path
            # and mRelPath will hold the relative folders that need to be erased.
            log("[EraseRelated] Folder Deletion Requested. Relative Path=%s" % mRelPath)
            if mRelPath:
                # Have folders that possibly should be removed (if empty)
                if mLibMatch:
                    l_CWDPath=os.getcwd()
                    try:
                        os.chdir(mLibMatch)
                        os.removedirs(mRelPath)
                    except Exception as e:
                        xbmc.log("[EraseRelated] Error while attempting to delete a related folder. Folder=%s" % mRelPath, xbmc.LOGERROR)
                        xbmc.log("[EraseRelated] Error: %s" % e , xbmc.LOGERROR)
                    else:
                        log("[EraseRelated] Folder Deletion Completed without Error")
                    finally:
                        # Always try to restore the current working directory
                        os.chdir(l_CWDPath)
                else:
                    xbmc.log("[EraseRelated] Folder Deletion Error. Can't determine Kodi Source path.", xbmc.LOGERROR)


class EventHandler(FileSystemEventHandler):
    """
    Handles raw incoming events for single root path and library,
    and queues scan/clean commands to the xbmcif singleton.
    """

    def __init__(self, library, path, xbmcif):
        FileSystemEventHandler.__init__(self)
        self.library = library
        self.path = path
        self.xbmcif = xbmcif
# TF 10/2026 Bug resolved, Kodi includes a trailing pipe, so no need to add one on the end.
# previously the extra pipe was causing erroneous media matches on files (and folders)
# that did not have an extension. This fixes behavior in _can_skip as well.
        self.supported_media = '|' + xbmc.getSupportedMedia(library)

    def on_created(self, event):
        log("[librarywatchdog] ON_CREATED Path=%s" % event.src_path)
        if not event.is_directory and not self._can_skip(event, event.src_path):
            # TODO: remove this hack when fixed in xbmc
            if settings.FORCE_GLOBAL_SCAN and self.library == 'video':
                self.xbmcif.queue_scan(self.library)
            else:
                self.xbmcif.queue_scan(self.library, self.path)

    def on_deleted(self, event):
        xbmc.log("[EraseRelated] ON_DELETED Called. Media=%s" % event.src_path, xbmc.LOGINFO)
        if (not event.is_directory) and (not self._can_skip(event, event.src_path)):
            self.xbmcif.queue_remove(self.library, event.src_path)
# TF 10/2026 Implement the related files deletion feature.
# Caution. File operations (such as deleting related non-media files and folder removal)
# will cause a re-trigger of this event for each element. The self._can_skip function
# handles filtering so that the function isn't called repeatedly.
            if settings.ERASE_RELATED_FILES:
                self.xbmcif.eraseRelated(event.src_path)
                

    def on_moved(self, event):
        log("[librarywatchdog] ON_MOVED Path=%s" % event.src_path)
        self.on_deleted(event)
        if not self._can_skip(event, event.dest_path):
            # TODO: remove this hack when fixed in xbmc
            if settings.FORCE_GLOBAL_SCAN and self.library == 'video':
                self.xbmcif.queue_scan(self.library)
            else:
                self.xbmcif.queue_scan(self.library, self.path)

# TF 10/2026 Disabled the log on every event to help reduce logging volume
# when debugging other events.
#    def on_any_event(self, event):
        #log("[event] <%s> <%r>" % (event.event_type, event.src_path))

    def _is_hidden(self, path):
        sep = '/' if utils.is_url(self.path) else os.sep
        relpath = path[len(self.path):] if path.startswith(self.path) else path
        for part in relpath.split(sep):
            if part.startswith('.') or part.startswith('_UNPACK'):
                return True
        return False

    def _can_skip(self, event, path):
        if not path:
            return False
        if self._is_hidden(path):
            log("[librarywatchdog] CAN_SKIP skipping hidden <%s> <%r>" % (event.event_type, path))
            return True
        if not event.is_directory:
            _, ext = os.path.splitext(path)
            ext = ext.lower()
# TF 10/2026 Fixed the media return string so that paths with no extension aren't erroneously marked as valid media.
            if self.supported_media.find('|%s|' % ext) == -1:
                log("[librarywatchdog] CAN_SKIP file is not media (extension) <%s> <%r>" % (event.event_type, path))
                return True
        return False


def main():
    monitor = xbmc.Monitor()
    progress = xbmcgui.DialogProgressBG()
    try:
        progress.create("Watchdog starting. Please wait...")
    except:
        progress = None

    if settings.STARTUP_DELAY > 0:
        log("waiting for user delay of %d seconds" % settings.STARTUP_DELAY)
        msg = "Delaying startup by %d seconds."
        if progress:
            progress.update(0, message=msg % settings.STARTUP_DELAY)
        start = time.time()
        while time.time() - start < settings.STARTUP_DELAY:
            xbmc.sleep(100)
            if monitor.abortRequested():
                if progress:
                    progress.close()
                return

    sources = []
    video_sources = settings.VIDEO_SOURCES
    sources.extend(list(zip(repeat('video'), video_sources)))
    log("video sources %s" % video_sources)

    music_sources = settings.MUSIC_SOURCES
    sources.extend(list(zip(repeat('music'), music_sources)))
    log("music sources %s" % music_sources)

    xbmcif = XBMCIF()
    if settings.CLEAN_ON_START:
        if video_sources:
            xbmcif.queue_clean('video')
        if music_sources:
            xbmcif.queue_clean('music')

    if settings.SCAN_ON_START:
        if video_sources:
            xbmcif.queue_scan('video')
        if music_sources:
            xbmcif.queue_scan('video')

    observer = MultiEmitterObserver()
    observer.start()  # start so emitters are started on schedule

# TF 10/2026 Code cleanup to remove the break in the finally block (no longer permitted)
# code logic re-worked to remove the need for the finally clauses.

    for i, (libtype, path) in enumerate(sources):
        if progress:
            progress.update(int((i+1)/len(sources)*100), message="Setting up %s" % path)
        
        skipIteration=False # Flag to trigger the continue flow outside the try...block
        
        try:
            emitter_cls = emitters.select_emitter(path)
        except IOError:
            log("not watching <%s>. does not exist" % path)
            skipIteration=True

        if monitor.abortRequested():
            break
            
        if skipIteration:
            continue

        eh = EventHandler(libtype, path, xbmcif)
        try:
            observer.schedule(eh, path=path, emitter_cls=emitter_cls)
            log("watching <%s> using %s" % (path, emitter_cls))
        except Exception:
            traceback.print_exc()
            log("failed to watch <%s>" % path)

        if monitor.abortRequested():
            break
# End of for loop code refasctoring

    xbmcif.start()
    if progress:
        progress.close()
    log("initialization done")

    if settings.SHOW_STATUS_DIALOG:
        watching = "\n".join("Watching '%s'" % path for _, path in sources if path in observer.paths)
        not_watching = "\n".join("Not watching '%s'" % path for _, path in sources if path not in observer.paths)
        dialog = xbmcgui.Dialog()
        try:
            dialog.ok('Watchdog status', watching + not_watching)
        except:
            dialog = None

    monitor.waitForAbort()

    log("stopping..")
    observer.stop()
    xbmcif.stop()
    observer.join()
    xbmcif.join()

if __name__ == "__main__":
    main()
