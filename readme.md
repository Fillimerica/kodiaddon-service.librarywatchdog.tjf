### Kodi Service Addon to Monitor Library Media Folders

This addon service updates and extends the original Library Watchdog background service to include physical media folder management and related files management features.

Tested with Kodi Omega and Piers on Windows 10.

Note: This Addon is a fork of Addon Library Watchdog. Therefore some of this documentation may be incomplete, based on false assumptions, or may be incorrect.

#### Installation in Kodi:

<u>Method 1: From the TJF Repository</u>

Repository link:  https://fillimerica.github.io/kodirepo/

1. Enable "Unknown Sources" in Kodi Settings > System > Add-ons
2. Add the TJF Repository to the Kodi Sources in the Kodi File Manager
   1. Go to Settings > File manager
   2. Select "Add source" in either pane.
   3. Copy and paste (or type) the repository link listed above into the larger "Enter path..." edit box.
   4. In the smaller edit box under "Enter a name for this media source.", give the repository link a meaningful name such as "TJF Repository"
   5. Select OK to save this source.
3. Install the Repository as an add-on:
   1. Go to Settings > Add-ons
   2. Select "Install from zip file" (NOT install from repository at this point)
   3. In the "install from zip file" dialog, select the source that was added in step #2 above.
   4. A single zip file should appear in the list, select it to install the TJF Repository.
4. Install the Library WatchdogPlus add-on from the TJF Repository
   1. Go to Settings > Add-ons (if not already there)
   2. This time choose "Install from repository", and select the "TJF Repository" from the list.
   3. Choose "Program add-ons" from the category list.
   4. Choose "Library WatchdogPlus" from the list. The Library WatchdogPlus add-on will be installed.

<u>Method 2: From the Github Code Source</u>

Github Source link:  [](https://github.com/Fillimerica/kodiaddon-service.librarywatchdog.tjf)

From the github project repository, click on the green Code button and choose the "Download ZIP" option.

1. Depending on your browser configuration you may be prompted to choose a download location and/or a file name. In some configurations this is bypassed in favor of automatic downloading into a designated Downloads folder. In either case make sure the zip file that is downloaded is copied or moved into a location that Kodi can access in the Kodi File Manager.
2. Enable "Unknown Sources" in Kodi Settings > System > Add-ons
3. Install the Library WatchdogPlus add-on:
   1. Go to Settings > Add-ons
   2. Select "Install from zip file"
   3. In the "install from zip file" dialog, select the zip file that was downloaded in step #2 above. The Library WatchdogPlus add-on will be installed.

### Configuration

To configure the add-on, go to Settings > Add-ons > My Add-ons > Services, and select "Library WatchdogPlus" from the list. Then Choose the Configure Option Button.

###### General Category

* Remove from library when files are removed [default is enabled] = Attempt to locate the deleted media file in the Kodi Library using the Kodi JSON-RPC interface and remove it from the library.

* Clean on startup [default is disabled] = Perform a Kodi CleanLibrary on startup.

* Scan on startup [default is disabled] = Perform a Kodi UpdateLibrary on startup.

* Pause on playback [default is enabled] = Queue operations until playback has ended.

* Hide progress of library scan/clean [default is enabled] = Don't show the progress dialog box when performing an UpdateLibrary or CleanLibrary, just do it silently.

* Show status dialog on startup [default is disabled] = Shows a user-dismissible dialog that indicates which file system folders are being monitored for changes.

  ###### New Functionality in this Plus Version

* Delete Associated Files when Prmary Media File is Deleted [default is enabled] = When enabled and a media file is removed by any means, also erase any file in the same folder that has the same file name (with just a different extension).

* Also Remove Parent Folder if it is Empty [default is enabled, if Delete Associated Files is enabled] = When enabled and after deletion of any associated files, if the folder is now completely empty (and it isn't a root Library Folder) erase it as well and clean up the orphaned path in the Kodi database.

###### Video Sources Category

* Auto detect video sources [default is enabled] = Determine the file system paths to be monitored based upon the Videos Library Media Paths configured in Settings > Media > Library > Videos...
* Video Source 1 -- 9 [default is disabled] = If Auto detect video sources is disabled, then a specific file system path to be monitored (up to 9) can be specified instead.

###### Music Sources Category

* Auto detect video sources [default is enabled] = Determine the file system paths to be monitored based upon the Videos Library Media Paths configured in Settings > Media > Library > Music...
* Music Source 1 -- 9 [default is disabled] = If Auto detect video sources is disabled, then a specific file system path to be monitored (up to 9) can be specified instead.

###### Advanced Category

* TBD


#### Usage

This addon is a service that runs continuously while Kodi is running. It monitors the underlying file system that is assigned to the Kodi media libraries for changes and attempts to update the Kodi Library. It generally supports the following operations:

###### Media Addition

* When new media is saved or copied into a local file system folder that is assigned to a Kodi Library, the media is immediately imported into the Kodi Library using the Kodi UpdateLibrary command.

###### Media Deletion (Initiated when the underlying file is erased 1st)

* When existing media residing in a local file system folder and present in the Kodi library is deleted from the local file system, the addon attempts to use JSON-RPC to remove the media (only tv shows and movie media types) from the Kodi Library.

  *Note: Kodi has a built-in to the UI function to both remove media from the library and simultaneously delete the media from the file system. Using the native Kodi deletion functionality rather than Library Watchdog is probably safer and more reliable than deleting the media from the file system first.*

###### Media Deletion (Initiated when Kodi removes the media from the Library 1st)

When Kodi initiates a media removal using the built-in UI functionality. 

* The act of Kodi deleting the media from the file system triggers a deletion event in Library Watchdog. The media has already been removed from the media library by Kodi and the primary media file may have also been erased by Kodi.

  * If enabled Library Watchdog may be configured to delete files from the file sytem that are related to the media such as .edl (commercial-skip)  .xml , and .nfo files that are left behind by Kodi. 

  * In addition folders that previously contained these files may now be empty and those empty folders can also be deleted if they are empty (season folders)

  * Finally there is a supplemental cleanup that is performed directly on the Kodi MyVideosnn.db database for file system paths that previously contained media but have been deleted because they are empty. Both the files and path tables are purged of orphaned paths, a cleanup step that is not part of the regular UpdateLibrary nor CleanLibrary processes.
