import shutil
import uuid
from functools import lru_cache
from pathlib import Path

from app.config import get_settings


class Storage:
    # Files on local disk, one folder per user. The database only keeps the relative path.

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def save(self, user_id: uuid.UUID, filename: str, data: bytes) -> str:
        relative_path = f"{user_id}/{filename}"
        target = self.path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return relative_path

    def read(self, relative_path: str) -> bytes:
        return self.path(relative_path).read_bytes()

    def path(self, relative_path: str) -> Path:
        target = (self.root / relative_path).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError("path escapes the storage root")
        return target

    def delete(self, relative_path: str) -> None:
        self.path(relative_path).unlink(missing_ok=True)

    def delete_user(self, user_id: uuid.UUID) -> None:
        shutil.rmtree(self.path(str(user_id)), ignore_errors=True)


@lru_cache
def get_storage() -> Storage:
    return Storage(Path(get_settings().storage_dir))
