from safewatch_api.services.blob_storage import parse_blob_uri, safe_blob_name


def test_parse_blob_uri_splits_container_and_blob_name() -> None:
    assert parse_blob_uri("blob://evidence-documents/uploads/permit.pdf") == (
        "evidence-documents",
        "uploads/permit.pdf",
    )


def test_safe_blob_name_keeps_uploads_prefix_and_sanitizes_filename() -> None:
    blob_name = safe_blob_name("Permit Demo 001.pdf")

    assert blob_name.startswith("uploads/")
    assert blob_name.endswith("-Permit-Demo-001.pdf")
