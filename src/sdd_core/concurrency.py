"""Short cooperative metadata locks, separate from long integration ownership."""
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from threading import RLock, local
import hashlib
import os
import time

_local = local()
_threads = {}
_guard = RLock()


def runtime_path(root):
    root = Path(root).resolve()
    key = hashlib.sha256(os.path.normcase(str(root)).encode()).hexdigest()
    # A project sibling, never copied as project content and never put in Git.
    import json
    marker=root/'.specify/spec-thread.json'
    setting=json.loads(marker.read_text(encoding='utf-8')).get('development',{}).get('runtime_root') if marker.is_file() else None
    if setting and not Path(setting).is_absolute():raise ValueError('Runtime 경로는 절대 경로여야 합니다')
    base=Path(setting).expanduser().resolve() if setting else root.parent/'.spec-thread-runtime'
    if base.is_relative_to(root) or root.is_relative_to(base):
        raise ValueError('Runtime은 원본 프로젝트 밖의 별도 관리 디렉터리여야 합니다')
    return base/key


@contextmanager
def project_lock(root, name='metadata', *, timeout=30):
    root=Path(root).resolve()
    folder = (root.parent/'.spec-thread-locks'/hashlib.sha256(os.path.normcase(str(root)).encode()).hexdigest()
              if name=='metadata' else runtime_path(root))
    if folder.is_symlink() or folder.parent.is_symlink():
        raise ValueError('Runtime Lock 경로는 심볼릭 링크를 허용하지 않습니다')
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = folder / (name + '.lock')
    key = str(path)
    with _guard:
        thread_lock = _threads.setdefault(key, RLock())
    with thread_lock:
        held = getattr(_local, 'held', {})
        if key in held:
            yield
            return
        flags = os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(path, flags, 0o600)
        stream = os.fdopen(fd, 'r+b')
        started = time.monotonic()
        try:
            if os.name == 'nt':
                import msvcrt
                if os.fstat(fd).st_size == 0:
                    stream.write(b'\0');stream.flush()
                def acquire():
                    stream.seek(0);msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                def release():
                    stream.seek(0);msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                def acquire():fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                def release():fcntl.flock(fd, fcntl.LOCK_UN)
            while True:
                try:
                    acquire();break
                except (BlockingIOError, PermissionError, OSError):
                    if time.monotonic()-started >= timeout:
                        raise ValueError(f'프로젝트 {name} Lock 사용 중입니다')
                    time.sleep(.02)
            _local.held = {**held, key: True}
            try:yield
            finally:
                _local.held = held
                release()
        finally:
            stream.close()


def metadata_transaction(function):
    @wraps(function)
    def run(root, *args, **kwargs):
        with project_lock(root):
            return function(root, *args, **kwargs)
    return run
