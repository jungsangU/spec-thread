"""Atomic writes for the existing Baseline files."""
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import yaml

from .baseline import BaselineLoader, mapping, project_path

SCHEMA_VERSION = 1


def read_document(root, name):
    path = project_path(root, f".specify/baseline/{name}")
    return mapping(yaml.load(path.read_text(encoding="utf-8"), Loader=BaselineLoader), name)


def write_document(root, name, data):
    path = project_path(root, f".specify/baseline/{name}")
    if path != root.resolve() / ".specify/baseline" / name:
        raise ValueError("Baseline 관리 파일은 심볼릭 링크를 사용할 수 없습니다")
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            yaml.safe_dump(data, stream, allow_unicode=True, sort_keys=False)
            stream.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
