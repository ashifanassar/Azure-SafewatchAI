from urllib.parse import urlparse
from uuid import uuid4


class AzureBlobReader:
    def __init__(self, storage_account_name: str) -> None:
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        self.storage_account_name = storage_account_name
        account_url = f"https://{storage_account_name}.blob.core.windows.net"
        self.client = BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())

    def read(self, uri: str) -> bytes:
        container, blob_name = parse_blob_uri(uri)
        blob_client = self.client.get_blob_client(container=container, blob=blob_name)
        return blob_client.download_blob().readall()


class AzureBlobWriter:
    def __init__(self, storage_account_name: str) -> None:
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        self.storage_account_name = storage_account_name
        account_url = f"https://{storage_account_name}.blob.core.windows.net"
        self.client = BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())

    def upload(self, container: str, filename: str, content: bytes, content_type: str | None = None) -> str:
        from azure.storage.blob import ContentSettings

        blob_name = safe_blob_name(filename)
        blob_client = self.client.get_blob_client(container=container, blob=blob_name)
        blob_client.upload_blob(
            content,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type) if content_type else None,
        )
        return f"blob://{container}/{blob_name}"


def parse_blob_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "blob" or not parsed.netloc or not parsed.path:
        raise ValueError("Expected blob URI in the form blob://container/path/to/file")
    return parsed.netloc, parsed.path.lstrip("/")


def safe_blob_name(filename: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in ".-_" else "-" for char in filename.strip())
    cleaned = cleaned.strip(".-") or "evidence"
    return f"uploads/{uuid4()}-{cleaned}"
