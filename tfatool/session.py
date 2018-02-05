from contextlib import contextmanager
from typing import NamedTuple, Tuple, Callable

from .info import URL, DEFAULT_REMOTE_DIR


class _Session(NamedTuple):
    url: str = URL  # device URL (http://flashair by default)
    remote_dir: str = DEFAULT_REMOTE_DIR  # /DCIM/100__TSB by default
    local_dir: str = "."  # local directory for sychronizing files
    filters: Tuple[Callable] = ()


class Session:
    """Context-mutable wrapper for the _Session namedtuple"""

    def __init__(self, *args, **kwargs):
        """Creates a _Session namedtuple. See _Session
        docs for detailed signature."""
        self._session = _Session(*args, **kwargs)

    @property
    def url(self):
        return self._session.url

    @property
    def remote_dir(self):
        return self._session.remote_dir

    @property
    def local_dir(self):
        return self._session.local_dir

    @property
    def filters(self):
        return self._session.filters

    @contextmanager
    def added_filters(self, *filters: Tuple[Callable]):
        """Filter with the given callables within a context manager.
        Applies existing filters in addition to these new ones.

        >>> sesh = session.Session(url="http://hork",
        ...                        filters=(lamda f: f.size > 3e6,))
        >>> with sesh.also_filtered(lambda f: f.name.endswith("jpg"):
        ...     local_large_jpgs = sync.list_local_files(sesh)
        >>> local_large_files = sync.list_local_files(sesh)
        """
        old_session = self._session
        try:
            self._session = old_session._replace(
                filters=filters + old_session.filters)
            yield
        finally:
            self._session = old_session

    @contextmanager
    def filtered(self, *filters: Tuple[Callable]):
        """Filter with the given callables within a context manager

        >>> sesh = session.Session(url="http://hork",
        ...                        filters=(lamda f: f.size > 3e6,))
        >>> with sesh.filtered(lambda f: f.name.endswith("jpg"):
        ...     local_jpgs = sync.list_local_files(sesh)
        >>> local_large_files = sync.list_local_files(sesh)
        """
        old_session = self._session
        try:
            self._session = self._session._replace(filters=filters)
            yield
        finally:
            self._session = old_session

    @contextmanager
    def transferring_to(self, local_dir: str = None,
                        remote_dir: str = None, url: str = None):
        """Temporarily transfer to a different local dir, remote dir,
        and/or FlashAir device URL within a context manager.

        >>> sesh = session.Session(url="http://device0")
        >>> with sesh.transferring_to(url="http://device1"):
        ...     for _, new_file in sync.up_by_arrival(sesh):
        ...         ...  # this new file is going to http://device1
        >>> for _, new_file in sync.up_by_arrival(sesh):
        ...     ...  # this new file is going to http://device0
        """
        old_session = self._session
        try:
            local = (local_dir if local_dir is not None else
                     old_session.local_dir)
            remote = (remote_dir if remote_dir is not None else
                      old_session.remote_dir)
            self._session = self._session._replace(
                local_dir=local, remote_dir=remote)
            yield
        finally:
            self._session = old_session
