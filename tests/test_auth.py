from server.security import hash_password, verify_password
from tests.conftest import PASSWORD, login, register


def test_register_and_login(client):
    assert register(client, "carol").status_code == 201
    data, _ = login(client, "carol")
    assert data["token"] and data["user"]["username"] == "carol"


def test_login_by_email(client):
    register(client, "dave")
    r = client.post("/api/auth/login", json={"identifier": "dave@example.com", "password": PASSWORD})
    assert r.status_code == 200


def test_invalid_password(client):
    register(client, "erin")
    r = client.post("/api/auth/login", json={"identifier": "erin", "password": "Wrong123"})
    assert r.status_code == 401 and r.get_json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_duplicates(client):
    register(client, "frank")
    assert register(client, "frank", email="other@example.com").status_code == 409
    assert register(client, "frank2", email="frank@example.com").status_code == 409


def test_weak_password_and_bad_email(client):
    assert register(client, "gina", password="abc").status_code == 422
    assert register(client, "gina", email="not-an-email").status_code == 422


def test_password_hash_verification():
    h, salt = hash_password("Str0ngPass")
    assert PASSWORD not in h and verify_password("Str0ngPass", h, salt) and not verify_password("x", h, salt)
    assert hash_password("Str0ngPass")[1] != salt  # random salts


def test_logout_invalidates_token(client):
    register(client, "hank")
    _, h = login(client, "hank")
    assert client.get("/api/profile", headers=h).status_code == 200
    assert client.post("/api/auth/logout", headers=h).status_code == 200
    assert client.get("/api/profile", headers=h).status_code == 401


def test_distinct_tokens_and_bad_tokens(client):
    register(client, "ivy")
    (d1, _), (d2, _) = login(client, "ivy"), login(client, "ivy")
    assert d1["token"] != d2["token"]
    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/profile", headers={"Authorization": "Bearer bad!"}).status_code == 401


def test_invalid_json(client):
    r = client.post("/api/auth/login", data="nope", content_type="application/json")
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "INVALID_JSON"
