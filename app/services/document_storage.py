"""Private document storage boundary.

Local filesystem storage is used for development and single-host deployments.
The API exposes storage keys only to backend services, never to clients.
"""

from pathlib import Path
from uuid import uuid4

from app.config import get_settings


class LocalDocumentStorage:
    def __init__(self, root: str | None = None):
        self.root = Path(root or get_settings().document_storage_path).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, company_id: int, extension: str, content: bytes) -> str:
        company_directory = self.root / str(company_id)
        company_directory.mkdir(parents=True, exist_ok=True)
        storage_key = f"{company_id}/{uuid4().hex}.{extension}"
        destination = (self.root / storage_key).resolve()
        if self.root not in destination.parents:
            raise ValueError("Invalid storage path")
        destination.write_bytes(content)
        return storage_key

    def resolve(self, storage_key: str) -> Path:
        path = (self.root / storage_key).resolve()
        if self.root not in path.parents or not path.is_file():
            raise FileNotFoundError("Stored document not found")
        return path

    def delete(self, storage_key: str | None) -> None:
        if not storage_key:
            return
        try:
            self.resolve(storage_key).unlink()
        except FileNotFoundError:
            return


_storage = None


def get_document_storage() -> LocalDocumentStorage:
    global _storage
    if _storage is None:
        _storage = LocalDocumentStorage()
    return _storage
