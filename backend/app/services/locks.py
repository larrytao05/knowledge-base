import threading
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

sync_lock = threading.Lock()

_path_locks: dict[Path, threading.Lock] = defaultdict(threading.Lock)
_path_locks_guard = threading.Lock()


@contextmanager
def path_lock(path: Path) -> Iterator[None]:
    with _path_locks_guard:
        lock = _path_locks[path]
    with lock:
        yield
