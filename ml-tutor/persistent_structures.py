import pickle
from collections import defaultdict
from pathlib import Path
from threading import Lock
from typing import TypeVar, Generic, Set, Dict

from .utils import data_path, Singleton

K = TypeVar("K")
T = TypeVar("T")


class FileLockRegistry(metaclass=Singleton):
    def __init__(self):
        self._lock = Lock()
        self._file_locks = defaultdict(Lock)

    def get_lock(self, file_name: Path) -> Lock:
        with self._lock:
            lock = self._file_locks[file_name]
        return lock


class PersistentDict(Dict[K, T], Generic[K, T]):
    def __init__(self, file_name: str):
        super().__init__()
        self._file_lock = FileLockRegistry()
        self._file_path = data_path() / file_name
        self._load()

    def save(self):
        with self._file_lock.get_lock(file_name=self._file_path):
            with open(self._file_path, "wb") as f:
                pickle.dump(dict(self), f)

    def _load(self):
        if self._file_path.exists():
            with self._file_lock.get_lock(file_name=self._file_path):
                with open(self._file_path, "rb") as f:
                    self.update(pickle.load(f))
        else:
            self.clear()


class PersistentSet(Set[T], Generic[T]):
    def __init__(self, file_name: str):
        super().__init__()
        self._file_lock = FileLockRegistry()
        self._file_path = data_path() / file_name
        self._load()

    def save(self):
        with self._file_lock.get_lock(file_name=self._file_path):
            with open(self._file_path, "wb") as f:
                pickle.dump(set(self), f)

    def _load(self):
        if self._file_path.exists():
            with self._file_lock.get_lock(file_name=self._file_path):
                with open(self._file_path, "rb") as f:
                    self.update(pickle.load(f))
        else:
            self.clear()
