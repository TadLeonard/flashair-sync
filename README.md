<img align="right" src="_docs/flashair.jpg">

# tfatool: *T*oshiba *F*lash*A*ir Tool

[![License](http://img.shields.io/:license-mit-blue.svg?style=flat-blue)](http://badges.mit-license.org)
[![PyPI version](https://badge.fury.io/py/tfatool.svg)](https://badge.fury.io/py/tfatool)

This package provides easy access to the
Toshiba FlashAir wireless SD card. As a library,
`tfatool` provides an easy-to-use abstraction of the FlashAir API.
The package includes two command line utilities:
`flashair-util` gives the user a way of synchronizing/mirroring
files and directories between the local filesystem and FlashAir,
while `flashair-config` lets the user configure the the deivce.

### Command line usage at a glance

  Action                                                      | Command                                         
  ----------------------------------------------------------- | ------------------------------------------------
  Monitor FlashAir for new JPEGs, download to ~/Photos        | `flashair-util -s -d /home/tad/Photos --only-jpg`
  Monitor working dir for new files, upload to FlashAir       | `flashair-util -s -y up`
  Monitor a local and remote dir for new files, sync them     | `flashair-util -s -y both`
  Sync down the 10 most recent to a local dir, then quit      | `flashair-util -S time -d images/new/`
  Sync up all files created in 1999 and afterwards            | `flashair-util -S all -t 1999`
  Sync down files created between Jan 23rd and Jan 26th       | `flashair-util -S all -t 1-23 -T 01/26`
  Sync files (up AND down) created this afternoon             | `flashair-util -S all -t 12:00 -T 16:00 -y  both`
  Sync files up created after a very specific date/time       | `flashair-util -S all -t '2016-1-25 11:38:22'`
  Sync (up and down) 5 most recent files of a certain name    | `flashair-util -S time -k 'IMG-08.+\.raw' -y both`
  List files on FlashAir created after a certain time         | `flashair-util -l -t '1-21-2016 8:30:11'`
  Change FlashAir network SSID                                | `flashair-config --wifi-ssid myflashairnetwork`
  Show FlashAir network password & firmware version           | `flashair-config --show-wifi-key --show-fw-version`

### Package contents at a glance

* `flashair-util`: a command line tool for mirroring and listing files on FlashAir
* `flashair-config`: a command line tool for configuring FlashAir
* `tfatool.command`: abstraction of FlashAir's [command.cgi](https://flashair-developers.com/en/documents/api/commandcgi/)
* `tfatool.upload`: abstraction of FlashAir's [upload.cgi](https://flashair-developers.com/en/documents/api/uploadcgi/)
* `tfatool.config`: abstraction of FlashAir's [config.cgi](https://flashair-developers.com/en/documents/api/configcgi/)
* `tfatool.sync`: functions for synchronizing local dirs with remote FlashAir dirs
* `tfatool.session`: a `Session` object for managing the state of your connection to FlashAir (filters, URLs, and local/remote directories)

Read the [FlashAir documentation](https://flashair-developers.com/en/documents/api/)
for more information about the API `tfatool` uses.

# Usage guide
## Using the `flashair-util` script
### Help menu

```
usage: flashair-util [-h] [-v] [-l] [-c] [-s] [-S {time,name,all}]
                     [-y {up,down,both}] [-r REMOTE_DIR] [-d LOCAL_DIR]
                     [-u URL] [-j] [-n N_FILES] [-k MATCH_REGEX]
                     [-t EARLIEST_DATE] [-T LATEST_DATE]

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose

Actions:
  -l, --list-files
  -c, --count-files
  -s, --sync-forever    watch for new files in REMOTE_DIR, copy them to
                        LOCAL_DIR (runs until CTRL-C)
  -S {time,name,all}, --sync-once {time,name,all}
                        move files (all or by most recent name/timestamp) from
                        REMOTE_DIR to LOCAL_DIR, then quit

Setup:
  -y {up,down,both}, --sync-direction {up,down,both}
                        'up' to upload, 'down' to download, 'both' for both
                        (default: down)
  -r REMOTE_DIR, --remote-dir REMOTE_DIR
                        FlashAir directory to work with (default:
                        /DCIM/100__TSB)
  -d LOCAL_DIR, --local-dir LOCAL_DIR
                        local directory to work with (default: working dir)
  -u URL, --url URL     URL of your FlashAir device (must start with http://)

File filters:
  -j, --only-jpg        filter for only JPEG files
  -n N_FILES, --n-files N_FILES
                        Number of files to move in --sync-once mode
  -k MATCH_REGEX, --match-regex MATCH_REGEX
                        filter for files that match the given pattern
  -t EARLIEST_DATE, --earliest-date EARLIEST_DATE
                        work on only files AFTER datetime of any reasonable
                        format such as YYYY, YYYY-MM, MM/DD, HH:mm (today), or
                        'YYYY-MM-DD HH:mm:ss'
  -T LATEST_DATE, --latest-date LATEST_DATE
                        work on only files BEFORE given datetime
```

### Prelude: filtering files by name, creation time

All operations `flashair-util` carries out (both remote and local) can be restricted
to a subset of files with some simple arguments. We can filter by filename and
by creation date/time.

#### Filtering by date and time

Date/times are parsed from the command line in a human-friendly manner.
If you pass "1998", it'll be parsed as "1998-01-01 00:00:00". Passing
a string like "11/4" or "11-04" will be be seen as "{current year}-11-04 00:00:00".

The `-t` or `--earliest-date` option filters for only files AFTER the given date/time.
The `-T` or `--latest-date` option filters for only files BEFORE the given date/time.
You can use `-t` and `-T` together to filter for files within a slice of time. Some examples:

* `-T 2015`: all files created before 2015
* `-t 18:00`: all files created this evening (after 6:00 pm today)
* `-t 2014 -T 2015`: all files created in 2014
* `-t 11/4 -T 11/28`: all files created between Nov. 4 and Nov 28 of this year
* `-t '2016-4-02 11:30' -T '2016/04/02 13:30'`: all files created Apr.
   2nd between 11:30 am and 2:30 pm.
* `-t 7:00 -T 11:00`: all files created this morning

#### Filtering by filename

Files can also be filtered by their name. The `-j` or `--only-jpg` option
filters for JPEG files. Filters of greater complexity can be made with
the `-k/--match-regex` option, which matches the filename against
a regular expression pattern. Some examples:

* `--match-regex '.+\.raw'`: match all files ending in `.raw`
* `-k 'IMG-08.+\.jpg'`: match all JPEGs starting with `IMG-08`

### Example 1: sync newly created files on FlashAir card

The `-s/--sync-forever` mode watches for new files. When new files are found,
they're synchronized with the specified local or remote directory.

File synchronizing can be done in one of three ways:

1. Download only (default or chosen with `-y down/--sync-direction down`)
2. Upload only (`-y up/--sync-direction up`)
3. Bidirectional (`-y both/--sync-direction both`)

Monitor FlashAir for JPEGs and copy them to `path/to/files` as they appear.

```
$ flashair-util -s -d path/to/files --only-jpg
2016-01-22 21:29:12,336 | INFO | main | Syncing files from /DCIM/100__TSB to path/to/files
2016-01-22 21:28:44,035 | INFO | main | Creating directory 'path/to/files'
2016-01-22 21:29:27,412 | INFO | tfatool.sync | Ready to sync new files (39 existing files ignored)
```

Some time later, a new photo appears in the default remote directory.

```
2016-01-22 21:30:05,770 | INFO | tfatool.sync | Files to sync:
  IMG_0802.JPG
2016-01-22 21:30:05,770 | INFO | tfatool.sync | Copying remote file IMG_0802.JPG to stuff/IMG_0802.JPG
2016-01-22 21:30:05,771 | INFO | tfatool.sync | Requesting file: http://flashair/DCIM/100__TSB/IMG_0802.JPG
2016-01-22 21:30:05,866 | INFO | tfatool.sync | Wrote IMG_0802.JPG in 1.00 s (4.31 MB, 4.31 MB/s)
```

### Example 2: sync subset of files on FlashAir *just once*

Sync JPEG files that were created between December 15th, 2015 (at 3:00 pm)
and January 12, 2016 with the local `stuff/` directory.
Notice that *files which already exist and match the size in bytes of those on FlashAir*
are not overwritten.

```
flashair-util -S all -d stuff/ -j -t '2015-12-15 15:00' -T 2016-01-12
2016-01-22 22:29:02,228 | INFO | main | Syncing files from /DCIM/100__TSB to stuff/
2016-01-22 22:29:02,330 | INFO | tfatool.sync | File 'stuff/IMG_0800.JPG' already exists; not syncing from SD card
2016-01-22 22:29:02,331 | INFO | tfatool.sync | Copying remote file IMG_0801.JPG to stuff/IMG_0801.JPG
2016-01-22 22:29:02,331 | INFO | tfatool.sync | Requesting file: http://flashair/DCIM/100__TSB/IMG_0801.JPG
2016-01-22 22:29:17,831 | INFO | tfatool.sync | Wrote IMG_0801.JPG in 9.40 s (4.31 MB, 0.46 MB/s)
2016-01-22 22:29:17,833 | INFO | tfatool.sync | File 'stuff/IMG_0802.JPG' already exists; not syncing from SD card
2016-01-22 22:29:17,833 | INFO | tfatool.sync | Copying remote file IMG_0803.JPG to stuff/IMG_0803.JPG
2016-01-22 22:29:17,834 | INFO | tfatool.sync | Requesting file: http://flashair/DCIM/100__TSB/IMG_0803.JPG
2016-01-22 22:29:30,855 | INFO | tfatool.sync | Wrote IMG_0803.JPG in 10.07 s (4.55 MB, 0.45 MB/s)
``` 

Other simple `--sync-once` examples:

* Just grab the most recent JPEG: `flashair-util -S time -n 1`
* Sync most recent 5 files by timestamp: `flashair-util -S time --n-files 5`
* Make sure `stuff/` local dir and `/DCIM` remote dir are completely
  synchronized: `flashair-util -S all -y both -d stuff/ -r /DCIM`
* Of all files that end in `08.JPG`, sync the 10 
  greatest filenames: `flashair-util -S name --n-files 10 -k '.+08\.JPG'`


### Example 3: listing files on FlashAir

List all remote files created after 3:00 pm today:

```
$ flashair-util -l -t 15:00
2016-01-29 16:26:55,287 | INFO | main | Filtering from [2016-01-29 15:00:00] to [end of time]

Files in /DCIM/100__TSB

filename      date        time       MB  created
------------  ----------  ------  -----  -----------
IMG_1184.JPG  2016-01-29  15:03    5.13  7 hours ago
IMG_1184.CR2  2016-01-29  15:03   18.8   7 hours ago
IMG_1185.JPG  2016-01-29  15:03    5.82  7 hours ago
IMG_1185.CR2  2016-01-29  15:03   19.6   7 hours ago

(4 files, 49.34 MB total)
```

List JPEGs that match a certain filename regex pattern:

```
flashair-util -l -k 'IMG_058.+' --only-jpg

Files in /DCIM/100__TSB

filename      date        time      MB  created
------------  ----------  ------  ----  -----------
IMG_0583.JPG  2016-01-16  18:54   5.16  13 days ago
IMG_0584.JPG  2016-01-16  18:54   5.12  13 days ago

(2 files, 10.27 MB total)
```

List all JPEGs created in the years 2014, 2015 and 2016.

```
flashair-util -l -t 2014 -T 2017 -j
2016-01-29 16:31:26,286 | INFO | main | Filtering from [2012-01-01 00:00:00] to [2017-01-01 00:00:00]

Files in /DCIM/100__TSB

filename       date        time      MB  created
-------------  ----------  ------  ----  -----------
FA000001.JPG   2013-08-29  09:00   0.13  2 years ago
IMG_0583.JPG   2016-01-16  18:54   5.16  13 days ago
IMG_0617.JPG   2016-01-17  00:31   5.55  12 days ago
IMG_1066.JPG   2016-01-26  06:39   3.53  3 days ago
...
IMG_1185.JPG   2016-01-29  15:03   5.82  7 hours ago

(61 files, 0.26 GB total)
```

## Using the `flashair-config` script
### Help menu

```
flashair-config -h
usage: flashair-config [-h] [-m MASTERCODE] [-v] [-t WIFI_TIMEOUT]
                       [-w {access_point,station,passthrough}] [-W]
                       [-k WIFI_KEY] [-K PASSTHROUGH_KEY] [-s WIFI_SSID]
                       [-S PASSTHROUGH_SSID] [--app-info APP_INFO]
                       [--bootscreen-path BOOTSCREEN_PATH] [-M]
                       [--timezone TIMEZONE] [-d {disable,enable,upload}]
                       [--show-wifi-ssid] [--show-wifi-key] [--show-mac]
                       [--show-fw-version] [--show-wifi-mode]

optional arguments:
  -h, --help            show this help message and exit
  -m MASTERCODE, --mastercode MASTERCODE
                        12-digit hex mastercode to enable configuration of the
                        FlashAir device
  -v, --verbose

WiFi settings:
  -t WIFI_TIMEOUT, --wifi-timeout WIFI_TIMEOUT
                        set WiFi timeout of device
  -w {access_point,station,passthrough}, --wifi-mode {access_point,station,passthrough}
                        set WiFi mode of device
  -W, --wifi-mode-on-boot
                        set the WiFi mode on next boot, not immediately
  -k WIFI_KEY, --wifi-key WIFI_KEY
                        set WiFi security key
  -K PASSTHROUGH_KEY, --passthrough-key PASSTHROUGH_KEY
                        set internet passthrough security key
  -s WIFI_SSID, --wifi-ssid WIFI_SSID
                        set WiFi SSID
  -S PASSTHROUGH_SSID, --passthrough-ssid PASSTHROUGH_SSID
                        set internet passthrough SSID

Misc settings:
  --app-info APP_INFO   set application-specific info
  --bootscreen-path BOOTSCREEN_PATH
                        set path to boot screen image
  -M, --clear-mastercode
  --timezone TIMEZONE   set timezone in hours offset (e.g. -8)
  -d {disable,enable,upload}, --drive-mode {disable,enable,upload}
                        set WebDAV drive mode

Show configuration parameters:
  --show-wifi-ssid
  --show-wifi-key
  --show-mac
  --show-fw-version
  --show-wifi-mode
```

### Sample configurations of FlashAir

Set the FlashAir WiFi network's SSID and password.

```flashair-config -k supersecretekey -s myflashairnetwork```

Prepare for Internet passthrough mode. This sets the LAN SSID, password, and
the FlashAir WiFi mode. If this is successful, the device will pass through
Internet access to all connected clients.

```flashair-config -K supersecretekey -S coffeeshopssid -w passthrough```

Set the WiFi mode *on boot* instead of immediately with the *-W* flag:

```flashair-config -w station -W```


## Using the `tfatool` Python library
### Example 1: using FlashAir's command.cgi

Listing, counting files on FlashAir:

```python
import arrow  # 
from tfatool import command

# get files in a FlashAir directory as a list of namedtuples
# each namedtuple has six attributes: directory, filename, time, date, etc
flashair_files = command.list_files()  # list files in /DCIM/100__TSB by default
special_files = command.list_files(remote_dir="/DCIM/my_special_folder")

# get an integer count of files in a certain dir
n_files = command.count_files(remote_dir="/DCIM")  # count in specific directory
```

Files listed by FlashAir are converted to a `namedtuple` with
attributes `filename, directory, path, size, attribute, datetime`,
where `size` is in bytes, `attribute` shows file permissions and so on,
and `datetime` is a `datetime` object from the `arrow` library.
Filters can inspect any of these tuple parameters.

```python
# here we cull any RAW files (.raw or .cr2), files of a certain name,
# and files created after some arrow datetime
# you can combine any number of filters
some_date = arrow.get("1987-04-02 11:33:03")  # arrow datetimes supported
filter_date = lambda f: f.datetime > some_date  # after my birthday
filter_raw = lambda f: not f.filename.lower().endswith(".raw", ".cr2")
filter_name = lambda f: f.filename.lower()startswith("IMG_08")
certain_files = command.list_files(filter_raw, filter_name, filter_date)
for f in certain_files:
    print("{:s}: {:0.2f} MB (created {:s})".format(
        f.filename, f.size / 10**6, f.datetime.humanize()))
```

### Example 2: using file synchronization functions

The `sync` module contains functions for syncing files UP to FlashAir
and DOWN from FlashAir to your local filesystem.

```python
from tfatool import sync

# Sync files as a one-off action
# here we sync the most recent files sorted by (file.date, file.time)
sync.up_by_time(count=10)  # uploads 10 most recent files (in CWD by default)
sync.down_by_time(count=15, local_dir="/home/tad/Pictures")

# Sync specific files selected from files list
from tfatool import command
camille_filter = lambda f: "camille" in f.filename().lower()  # certain filename
jpeg_filter = lambda f: f.filename.lower().endswith(".jpg")  # only JPEGs
size_filter = lambda f: f.size < (5 * (10 ** 6))  # only files < 5 MB
camille_photos = command.list_files(camille_filter, jpeg_filter, size_filter)
sync.down_by_files(camille_photos, local_dir="/home/tad/Pictures/camille")
```

### Example 3A: watching for newly created files

The `tfatool.sync` module contains three generator functions for
monitoring your FlashAir device and your local filesystem for
newly created fiiles. File monitoring can work in one of three ways:

1. watch for new files in a remote FlashAir directory and
   sync them to a local directory
2. watch for new files in a local directory and
   sync them to a remote FlashAir location
3. watch for new files in *both* local and remote locations
   and synchronize them both

Download remote files as they appear with `down_by_arrival`:

```python
import time
from tfatool import sync

# generates tuples like ("down", {fileinfo, fileinfo...})
to_download = sync.down_by_arrival()

# consuming the generator downloads available files
for direction, pending_download in to_download:
    if not pending_download:
        time.sleep(0.5)  # nothing to download
```

Use `up_by_arrival` to upload local files as they appear.
Note that with any of these functions you can pass
specific local and remote directories.

```python
# generates tuples like ("up", {fileinfo, fileinfo...})
to_upload = sync.up_by_arrival(local_dir="/special/place",
                               remote_dir="/DCIM")
...
```

Finally, use `up_down_by_arrival` to perform a *bidirectional*
sync of the local and remote directories. Note that file filters
can be applied to any of these generators.

```python
filter_jpg = lambda f: f.filename.endswith(".jpg")
# generates tuples like ("up", {fileinfo,...}) for pending uploads
# and ("down", {fileinfo...}) for pending downloads
to_upload_or_download = sync.up_down_by_arrival(filter_jpg)
```

### Example 3B: watching for newly created files *in a separate thread*

The `tfatool.sync.Monitor` object watches for new files in your
FlashAir device and/or your local filesystem with a separate thread.

Uploading new files in the background:

```python
from tfatool import sync

monitor = sync.Monitor(local_dir="/home/tad/Pictures/new",
                       remote_dir="/DCIM")
monitor.sync_up()  # start upload thread
# ... do something else
monitor.stop()  # prompt thread to stop
monitor.join()  # wait for thread to stop
```

Downloads work the same way, but with the `Monitor.sync_down` method.
Sync bidirectionally with `Monitor.sync_both`.

### Example 4: sending config changes via a POST to *config.cgi*

The `tfatool.config` module is an abstraction of FlashAir's `config.cgi`.
To change config parameters, construct a dictionary of parameter
names (`tfatool.info.Config` Enum types) and values.

```python
from tfatool.config import post, config
from tfatool.info import Config

params = {
    Config.app_info: "special application info",
    Config.wifi_timeout: 3600,  # one-hour WiFi timeout
    Config.wifi_ssid: "SUPER FUN PHOTO ZONE",
    Config.timezone: -11,  # somewhere in the USA, for example
}
```

Finally, prep the parameters for URL construction and send the request.
The `tfatool.config.config` function will raise `AssertionError`
if any value is out of bounds (e.g. if the WiFi timeout is < 60 s).
These prepped parameters can then be sent to FlashAir via an
HTTP POST using `tfatool.config.post`.

```python
prepped_params = config(params)
response = post(prepped_params)
```

# Installation

Requires `requests`, `tqdm`, `arrow`, `tabulate`, and `python3.4+`.

Install with your system's Python3:

```
python3.5 -m pip install tfatool
```

Or into a virtualenv:

```
virtualenv -p python3.5 env/
source env/bin/activate
pip install tfatool
```

