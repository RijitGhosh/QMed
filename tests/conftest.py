import random
import pytest

from server.app import create_app
from server.config import Settings
from client.encryption import new_account_keys

PASSWORD = "Str0ngPass"


@pytest.fixture()
def app(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", storage_dir=tmp_path / "storage", log_dir=tmp_path / "logs",
                        database_url=f"sqlite:///{(tmp_path / 'qmed.db').as_posix()}", testing=True,
                        secret_key="test-secret", max_file_bytes=200_000)
    return create_app(settings)


@pytest.fixture()
def client(app):
    return app.test_client()


def register(client, username, role="Doctor", password=PASSWORD, email=None):
    pub, blob = new_account_keys(password)
    return client.post("/api/auth/register", json={
        "full_name": username.title(), "username": username, "email": email or f"{username}@example.com",
        "password": password, "role": role, "public_key": pub, "encrypted_private_key": blob})


def login(client, username, password=PASSWORD):
    r = client.post("/api/auth/login", json={"identifier": username, "password": password})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()["data"]
    return d, {"Authorization": f"Bearer {d['token']}"}


@pytest.fixture()
def two_users(client):
    register(client, "alice_doc", "Doctor")
    register(client, "bob_pat", "Patient")
    a, ha = login(client, "alice_doc")
    b, hb = login(client, "bob_pat")
    return a, ha, b, hb
