import math
import os
import arrow

from functools import partial
from pathlib import PosixPath
from typing import Optional

from . import cgi
from .info import DEFAULT_REMOTE_DIR, DEFAULT_MASTERCODE, URL
from .info import WriteProtectMode, Upload, ResponseCode
from requests import RequestException, Request


def upload_file(local_path: str, url=URL, remote_dir=DEFAULT_REMOTE_DIR):
    set_write_protect(WriteProtectMode.on, url=url)
    set_upload_dir(remote_dir, url=url)
    set_creation_time(local_path, url=url)
    post_file(local_path, url=url)
    set_write_protect(WriteProtectMode.off, url=url)


def delete_file_in(remote_filepath: str, url: str = URL,
                   remote_dir: Optional[str] = DEFAULT_REMOTE_DIR):
    """
    Delete `remote_filepath` from the FlashAir device at `url`.
    If `remote_dir` is specified, the complete path to the resource to
    be deleted will be the joining of `remote_dir` and `remote_filepath`.
    By default, `remote_dir` is the FlashAir default directory,
    so the most common usage of this function is
    `delete_file_in("my_file.jpg")`.

    If `remote_dir` is None, `remote_filepath` will be used as the full path
    to the resource to be deleted.

    A note from the FlashAir docs:
    'Important: If you delete a directory, be sure that it does not
    contain child directories or files. If you delete a parent directory,
    its child directories and files may no longer be recognized by the
    file system.'
    """
    delete_request = _prep_delete_request(remote_filepath, url, remote_dir)
    response = cgi.send(delete_request)
    if response.text != ResponseCode.success:
        raise UploadError("Failed to delete file", response)
    return response


# Partially applied delete_file_in with no remote_dir
# Call this when you know the exact path of the file you're deleting
delete_file = partial(delete_file_in, remote_dir=None)


def _prep_delete_request(
        remote_filepath: str, url: str = URL,
        remote_dir: Optional[str] = DEFAULT_REMOTE_DIR) -> Request:
    if remote_dir is None:
        full_remote_path = remote_filepath
    else:
        full_remote_path = str(PosixPath(remote_dir, remote_filepath))
    return prep_post(url, **{Upload.delete: full_remote_path})


def set_write_protect(mode: WriteProtectMode, url=URL):
    response = get(url=url, **{Upload.write_protect: mode})
    if response.text != ResponseCode.success:
        raise UploadError("Failed to set write protect", response)
    return response


def set_upload_dir(remote_dir: str, url=URL):
    response = get(url=url, **{Upload.directory: remote_dir})
    if response.text != ResponseCode.success:
        raise UploadError("Failed to set upload directory", response)
    return response


def set_creation_time(local_path: str, url=URL):
    mtime = os.stat(local_path).st_mtime
    fat_time = _encode_time(mtime)
    encoded_time = _str_encode_time(fat_time)
    response = get(url=url, **{Upload.creation_time: encoded_time})
    if response.text != ResponseCode.success:
        raise UploadError("Failed to set creation time", response)
    return response


def post_file(local_path: str, url=URL):
    files = {local_path: open(local_path, "rb")}
    response = post(url=url, req_kwargs=dict(files=files))
    if response.status_code != 200:
        raise UploadError("Failed to post file", response)
    return response


def post(url=URL, req_kwargs=None, **params):
    prepped_request = prep_post(url, req_kwargs, **params)
    return cgi.send(prepped_request)


def get(url=URL, req_kwargs=None, **params):
    prepped_request = prep_get(url, req_kwargs, **params)
    return cgi.send(prepped_request)


def prep_req(prep_method, url=URL, req_kwargs=None, **params):
    req_kwargs = req_kwargs or {}
    params = {key.value: value for key, value in params.items()}
    return prep_method(url=url, req_kwargs=req_kwargs, **params)


prep_get = partial(prep_req, partial(cgi.prep_get, cgi.Entrypoint.upload))
prep_post = partial(prep_req, partial(cgi.prep_post, cgi.Entrypoint.upload))


def _str_encode_time(encoded_time: int):
    return "{0:#0{1}x}".format(encoded_time, 10)


def _encode_time(mtime: float):
    """Encode a mtime float as a 32-bit FAT time"""
    dt = arrow.get(mtime)
    dt = dt.to("local")
    date_val = ((dt.year - 1980) << 9) | (dt.month << 5) | dt.day
    secs = dt.second + dt.microsecond / 10**6
    time_val = (dt.hour << 11) | (dt.minute << 5) | math.floor(secs / 2)
    return (date_val << 16) | time_val


class UploadError(RequestException):
    def __init__(self, msg, response):
        self.msg = msg
        self.response = response

    def __str__(self):
        return "{}: {}".format(self.msg, self.response)

    __repr__ = __str__

