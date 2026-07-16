import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


import pytest


@pytest.fixture(autouse=True)
def clean_sf_env(monkeypatch):
    """Remove qualquer SF_*/CSV_DIR/HEADER_MAPPING_PATH residual do ambiente
    antes de cada teste, pra um teste nunca herdar env var de outro."""
    for key in list(__import__("os").environ):
        if key.startswith("SF_") or key in ("CSV_DIR", "HEADER_MAPPING_PATH"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def fake_auth():
    return {"access_token": "fake-token-123", "instance_url": "https://fake.my.salesforce.com"}
