import logging
import arrow

from pathlib import PurePosixPath
from collections import namedtuple
from typing import Dict, Iterable

from . import cgi
from .info import URL
from .info import WifiMode, WifiModeOnBoot, Operation
from .info import FileInfo, RawFileInfo
from .session import Session


logger = logging.getLogger(__name__)


##################
# command.cgi API


def map_files(session: Session = Session()) -> Dict[str, FileInfo]:
    files = list_files(session)
    return {f.filename: f for f in files}


def list_files(session: Session = Session()) -> Iterable[FileInfo]:
    response = _get(Operation.list_files,
                    session.url, DIR=session.remote_dir)
    files = _split_file_list(response.text)
    return (f for f in files if all(filt(f) for filt in session.filters))


def map_files_raw(
        session: Session = Session()) -> Dict[str, RawFileInfo]:
    files = list_files_raw(session)
    return {f.filename: f for f in files}


def list_files_raw(session: Session = Session()) -> Iterable[RawFileInfo]:
    response = _get(Operation.list_files,
                    session.url, DIR=session.remote_dir)
    files = _split_file_list_raw(response.text)
    return (f for f in files if all(filt(f) for filt in session.filters))


def count_files(session: Session = Session()) -> int:
    response = _get(Operation.count_files, session.url,
                    DIR=session.remote_dir)
    return int(response.text)


def memory_changed(session: Session = Session()) -> bool:
    """Returns True if memory has been written to, False otherwise"""
    response = _get(Operation.memory_changed, session.url)
    try:
        return int(response.text) == 1
    except ValueError:
        raise IOError("Likely no FlashAir connection, "
                      "memory changed CGI command failed")


def get_ssid(session: Session = Session()):
    return _get(Operation.get_ssid, session.url).text


def get_password(session: Session = Session()):
    return _get(Operation.get_password, session.url).text


def get_mac(session: Session = Session()):
    return _get(Operation.get_mac, session.url).text


def get_browser_lang(session: Session = Session()):
    return _get(Operation.get_browser_lang, session.url).text


def get_fw_version(session: Session = Session()):
    return _get(Operation.get_fw_version, session.url).text


def get_ctrl_image(session: Session = Session()):
    return _get(Operation.get_ctrl_image, session.url).text


def get_wifi_mode(session: Session = Session()) -> WifiMode:
    mode_value = int(_get(Operation.get_wifi_mode, session.url).text)
    all_modes = list(WifiMode) + list(WifiModeOnBoot)
    for mode in all_modes:
        if mode.value == mode_value:
            return mode
    raise ValueError("Uknown mode: {:d}".format(mode_value))


#####################
# API implementation

def _split_file_list(text: str) -> Iterable[FileInfo]:
    lines = text.split("\r\n")
    for line in lines:
        groups = line.split(",")
        if len(groups) == 6:
            directory, filename, *remaining = groups
            remaining = map(int, remaining)
            size, attr_val, date_val, time_val = remaining
            timeinfo = _decode_time(date_val, time_val)
            attribute = _decode_attribute(attr_val)
            path = str(PurePosixPath(directory, filename))
            yield FileInfo(directory, filename, path,
                           size, attribute, timeinfo)


def _split_file_list_raw(text: str) -> Iterable[RawFileInfo]:
    lines = text.split("\r\n")
    for line in lines:
        groups = line.split(",")
        if len(groups) == 6:
            directory, filename, size, *_ = groups
            path = str(PurePosixPath(directory, filename))
            yield RawFileInfo(directory, filename, path, int(size))


def _decode_time(date_val: int, time_val: int) -> arrow.Arrow:
    year = (date_val >> 9) + 1980  # 0-val is the year 1980
    month = (date_val & (0b1111 << 5)) >> 5
    day = date_val & 0b11111
    hour = time_val >> 11
    minute = ((time_val >> 5) & 0b111111)
    second = (time_val & 0b11111) * 2
    try:
        decoded = arrow.get(year, month, day, hour,
                            minute, second, tzinfo="local")
    except ValueError:
        year = max(1980, year)  # FAT32 doesn't go higher
        month = min(max(1, month), 12)
        day = max(1, day)
        decoded = arrow.get(year, month, day, hour, minute, second)
    return decoded


AttrInfo = namedtuple(
    "AttrInfo", "archive directly volume system_file hidden_file read_only")


def _decode_attribute(attr_val: int) -> AttrInfo:
    bit_positions = reversed(range(6))
    bit_flags = [bool(attr_val & (1 << bit)) for bit in bit_positions]
    return AttrInfo(*bit_flags)


########################################
# command.cgi request prepping, sending

def _get(operation: Operation, url=URL, **params):
    """HTTP GET of the FlashAir command.cgi entrypoint"""
    prepped_request = _prep_get(operation, url=url, **params)
    return cgi.send(prepped_request)


def _prep_get(operation: Operation, url=URL, **params):
    params.update(op=int(operation))  # op param required
    return cgi.prep_get(cgi.Entrypoint.command, url=url, **params)
