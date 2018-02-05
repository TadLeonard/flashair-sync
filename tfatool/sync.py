import logging
import os
import threading
import time

from enum import Enum
from functools import partial
from pathlib import Path
from typing import List, Dict, Optional, Iterable
from urllib.parse import urljoin

import arrow
import requests
import tqdm

from . import command, upload
from .info import RawFileInfo, SimpleFileInfo, FileInfo
from .session import Session

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Python 3.4 compatibility via scandir backport
if hasattr(os, "scandir"):
    scandir = os.scandir
else:
    import scandir
    scandir = scandir.scandir


class Direction(str, Enum):
    up = "upload"  # upload direction
    down = "download"  # download direction


#####################################
# Synchronizing newly created files

class Monitor:
    """Synchronizes newly created files TO or FROM FlashAir
    in separate threads"""

    def __init__(self, session: Session = Session()):
        self.session = session
        self.running = threading.Event()
        self.thread = None

    def _run(self, method):
        assert self.thread is None
        self.running.set()
        self.thread = threading.Thread(target=self._run_sync, args=(method,))
        self.thread.start()

    def _run_sync(self, method):
        files = method(self.session)
        while self.running.is_set():
            _, new = next(files)
            if not new:
                time.sleep(0.3)

    def sync_both(self):
        self._run(up_down_by_arrival)

    def sync_up(self):
        self._run(up_by_arrival)

    def sync_down(self):
        self._run(down_by_arrival)

    def stop(self):
        self.running.clear()

    def join(self):
        if self.thread:
            self.thread.join()
        self.thread = None


def up_down_by_arrival(session: Session = Session()):
    """Monitors a local directory and a remote FlashAir directory and
    generates sets of new files to be uploaded or downloaded.
    Sets to upload are generated in a tuple
    like (Direction.up, {...}), while download sets to download
    are generated in a tuple like (Direction.down, {...}). The generator yields
    before each upload or download actually takes place."""
    local_dir = session.local_dir
    remote_dir = session.remote_dir
    local_monitor = watch_local_files(session)
    remote_monitor = watch_remote_files(session)
    _, lfile_set = next(local_monitor)
    _, rfile_set = next(remote_monitor)
    _notify_sync_ready(len(lfile_set), local_dir, remote_dir)
    _notify_sync_ready(len(rfile_set), remote_dir, local_dir)
    processed = set()
    for new_local, new_remote in zip(local_monitor, remote_monitor):
        new_local, local_set = new_local
        local_arrivals = {f for f in new_local if
                          f.filename not in processed}
        yield Direction.up, local_arrivals
        if local_arrivals:
            processed.update(f.filename for f in local_arrivals)
            _notify_sync(Direction.up, local_arrivals)
            up_by_files(local_arrivals, remote_dir)
            _notify_sync_ready(len(local_set), local_dir, remote_dir)
        new_remote, remote_set = new_remote
        remote_arrivals = {f for f in new_remote if
                           f.filename not in processed}
        yield Direction.down, remote_arrivals
        if remote_arrivals:
            processed.update(f.filename for f in remote_arrivals)
            _notify_sync(Direction.down, remote_arrivals)
            yield Direction.down, remote_arrivals
            down_by_files(remote_arrivals, session)
            _notify_sync_ready(len(remote_set), remote_dir, local_dir)


def up_by_arrival(session: Session = Session()):
    """Monitors a local directory and
    generates sets of new files to be uploaded to FlashAir.
    Sets to upload are generated in a tuple like (Direction.up, {...}).
    The generator yields before each upload actually takes place."""
    local_dir = session.local_dir
    remote_dir = session.remote_dir
    local_monitor = watch_local_files(session)
    _, file_set = next(local_monitor)
    _notify_sync_ready(len(file_set), session.local_dir, remote_dir)
    for new_arrivals, file_set in local_monitor:
        # where new_arrivals is possibly empty
        yield Direction.up, new_arrivals
        if new_arrivals:
            _notify_sync(Direction.up, new_arrivals)
            up_by_files(new_arrivals, remote_dir)
            _notify_sync_ready(len(file_set), local_dir, remote_dir)


def down_by_arrival(session: Session = Session()):
    """Monitors a remote FlashAir directory and generates sets of
    new files to be downloaded from FlashAir.
    Sets to download are generated in a tuple like (Direction.down, {...}).
    The generator yields AFTER each download actually takes place."""
    local_dir = session.local_dir
    remote_dir = session.remote_dir
    remote_monitor = watch_remote_files(session)
    _, file_set = next(remote_monitor)
    _notify_sync_ready(len(file_set), remote_dir, local_dir)
    for new_arrivals, file_set in remote_monitor:
        if new_arrivals:
            _notify_sync(Direction.down, new_arrivals)
            down_by_files(new_arrivals, session)
            _notify_sync_ready(len(file_set), remote_dir, local_dir)
        yield Direction.down, new_arrivals


###################################################
# Sync ONCE in the DOWN (from FlashAir) direction

def down_by_all(session: Session = Session()):
    files = command.list_files(session)
    down_by_files(files, session)


def down_by_files(to_sync: List[FileInfo],
                  session: Session = Session()):
    """Sync a given list of files from `command.list_files`
    to `session.local_dir` dir"""
    for fileinfo in to_sync:
        _sync_remote_file(fileinfo, session)


def down_by_time(session: Session = Session(), count=1):
    """Sync most recent file by date, time attribues"""
    files = command.list_files(session)
    most_recent = sorted(files, key=lambda f: f.datetime)
    to_sync = most_recent[-count:]
    _notify_sync(Direction.down, to_sync)
    down_by_files(to_sync[::-1], session)


def down_by_name(session: Session = Session(), count=1):
    """Sync files whose filename attribute is highest in alphanumeric order"""
    files = command.list_files(session)
    greatest = sorted(files, key=lambda f: f.filename)
    to_sync = greatest[-count:]
    _notify_sync(Direction.down, to_sync)
    down_by_files(to_sync[::-1], session)


def _sync_remote_file(remote_file_info: FileInfo, session: Session):
    local_dir = session.local_dir
    local = Path(local_dir, remote_file_info.filename)
    local_name = str(local)
    remote_size = remote_file_info.size
    if local.exists():
        local_size = local.stat().st_size
        if local.stat().st_size == remote_size:
            logger.info(
                "Skipping '{}': already exists locally".format(local_name))
        else:
            logger.warning(
                "Removing {}: local size {} != remote size {}".format(
                    local_name, local_size, remote_size))
            os.remove(local_name)
            _stream_to_file(local_name, remote_file_info, session)
    else:
        _stream_to_file(local_name, remote_file_info, session)


def _stream_to_file(local_name, fileinfo, session):
    logger.info("Copying remote file {} to {}".format(
                fileinfo.path, local_name))
    streaming_file = _get_file(fileinfo, session)
    _write_file_safely(local_name, fileinfo, streaming_file)


def _get_file(fileinfo, session):
    url = urljoin(session.url, fileinfo.path)
    logger.info("Requesting file: {}".format(url))
    return requests.get(url, stream=True)


def _write_file_safely(local_path, fileinfo, response):
    """attempts to stream a remote file into a local file object,
    removes the local file if it's interrupted by any error"""
    try:
        _write_file(local_path, fileinfo, response)
    except BaseException as e:
        logger.warning("{} interrupted writing {} -- "
                       "cleaning up partial file".format(
                           e.__class__.__name__, local_path))
        os.remove(local_path)
        raise e


def _write_file(local_path, fileinfo, response):
    start = time.time()
    pbar_size = fileinfo.size / (5 * 10**5)
    pbar = tqdm.tqdm(total=int(pbar_size))
    if response.status_code == 200:
        with open(local_path, "wb") as outfile:
            for chunk in response.iter_content(5*10**5):
                progress = len(chunk) / (5 * 10**5)
                _update_pbar(pbar, progress)
                outfile.write(chunk)
    else:
        raise requests.RequestException("Expected status code 200")
    pbar.close()
    duration = time.time() - start
    logger.info("Wrote {} in {:0.2f} s ({:0.2f} MB, {:0.2f} MB/s)".format(
                fileinfo.filename, duration, fileinfo.size / 10 ** 6,
                fileinfo.size / (duration * 10 ** 6)))


def _update_pbar(pbar, val):
    update_val = max(int(val), 1)
    try:
        pbar.update(update_val)
    except Exception as e:
        # oh, c'mon TQDM, progress bars shouldn't crash software
        logger.debug("TQDM progress bar error: {}({})".format(
                     e.__class__.__name__, e))


###########################################
# Local and remote file watcher-generators

def watch_local_files(session: Session = Session()):
    list_local = partial(list_local_files, session)
    old_files = new_files = set(list_local())
    while True:
        yield new_files - old_files, new_files
        old_files = new_files
        new_files = set(list_local())


def watch_remote_files(session: Session = Session()):
    command.memory_changed(session)  # clear change status to start
    list_remote = partial(command.list_files, session)
    old_files = new_files = set(list_remote())
    while True:
        yield new_files - old_files, new_files
        old_files = new_files
        if command.memory_changed(session):
            new_files = set(list_remote())


#####################################################
# Synchronize ONCE in the UP direction (to FlashAir)

def up_by_all(session: Session = Session(), count: Optional[int] = None):
    files = list(list_local_files(session))
    if count is not None:
        files = files[-count:]
    up_by_files(list(files), session=session)


def up_by_files(to_sync: List[FileInfo] = [],
                remote_files: Optional[Dict[str, FileInfo]] = None,
                session: Session = Session()):
    """Sync a given list of local files to `remote_dir` dir"""
    if remote_files is None:
        remote_files = command.map_files_raw(session)
    for local_file in to_sync:
        _sync_local_file(local_file, remote_files, session)


def up_by_time(session: Session = Session(), count=1):
    """Sync most recent file by date, time attribues"""
    remote_files = command.map_files_raw(session)
    local_files = list_local_files(session)
    most_recent = sorted(local_files, key=lambda f: f.datetime)
    to_sync = most_recent[-count:]
    _notify_sync(Direction.up, to_sync)
    up_by_files(session, to_sync[::-1], remote_files)


def up_by_name(session: Session = Session(), count=1):
    """Sync files whose filename attribute is highest in alphanumeric order"""
    remote_files = command.map_files_raw(session)
    local_files = list_local_files(session)
    greatest = sorted(local_files, key=lambda f: f.filename)
    to_sync = greatest[-count:]
    _notify_sync(Direction.up, to_sync)
    up_by_files(session, to_sync[::-1], remote_files)


def _sync_local_file(local_file_info: SimpleFileInfo,
                     remote_files: Dict[str, FileInfo],
                     session: Session = Session()):
    local_name = local_file_info.filename
    local_size = local_file_info.size
    if local_name in remote_files:
        remote_file_info = remote_files[local_name]
        remote_size = remote_file_info.size
        if local_size == remote_size:
            logger.info(
                "Skipping '{}' already exists on SD card".format(
                    local_name))
        else:
            logger.warning(
                "Removing remote file {}: "
                "local size {} != remote size {}".format(
                    local_name, local_size, remote_size))
            upload.delete_file(remote_file_info.path, session)
            _stream_from_file(local_file_info, session)
    else:
        _stream_from_file(session, local_file_info)


def _stream_from_file(fileinfo: SimpleFileInfo,
                      session: Session = Session()):
    logger.info("Uploading local file {} to {}".format(
                fileinfo.path, session.remote_dir))
    _upload_file_safely(fileinfo, session)


def _upload_file_safely(fileinfo: SimpleFileInfo,
                        session: Session = Session()):
    """attempts to upload a local file to FlashAir,
    tries to remove the remote file if interrupted by any error"""
    try:
        upload.upload_file(fileinfo.path, session)
    except BaseException as e:
        logger.warning("{} interrupted writing {} -- "
                       "cleaning up partial remote file".format(
                           e.__class__.__name__, fileinfo.path))
        upload.delete_file(fileinfo.path, session)
        raise e


def list_local_files(
        session: Session = Session()) -> Iterable[SimpleFileInfo]:
    all_entries = scandir(session.local_dir)
    file_entries = (e for e in all_entries if e.is_file())
    for entry in file_entries:
        stat = entry.stat()
        size = stat.st_size
        datetime = arrow.get(stat.st_mtime)
        path = str(Path(session.local_dir, entry.name))
        info = SimpleFileInfo(session.local_dir, entry.name, path,
                              size, datetime)
        if all(filt(info) for filt in session.filters):
            yield info


def list_local_files_raw(
        session: Session = Session()) -> Iterable[RawFileInfo]:
    all_entries = scandir(session.local_dir)
    all_files = (e for e in all_entries if e.is_file() and
                 all(filt(e) for filt in session.filters))
    for entry in all_files:
        path = str(Path(session.local_dir, entry.name))
        yield RawFileInfo(session.local_dir, entry.name, path,
                          entry.stat().st_size)


def _notify_sync(direction, files):
    logger.info("{:d} files to {:s}:\n{}".format(
        len(files), direction,
        "\n".join("  " + f.filename for f in files)))


def _notify_sync_ready(num_old_files, from_dir, to_dir):
    logger.info("Ready to sync new files from {} to {} "
                "({:d} existing files ignored)".format(
                    from_dir, to_dir, num_old_files))
