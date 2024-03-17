from pathlib import Path

from .constants import DATA_FOLDER_NAME


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def project_root() -> Path:
    path = Path(__file__).parent
    return path


def data_path() -> Path:
    path = project_root() / DATA_FOLDER_NAME
    if not path.exists():
        path.mkdir()
    return path
