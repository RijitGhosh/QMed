def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.get_json()["data"]["status"] == "ok"


def test_error_format_and_404(client):
    r = client.get("/api/nope")
    body = r.get_json()
    assert r.status_code == 404 and body["success"] is False and "code" in body["error"]


def test_protected_endpoints_require_auth(client):
    for path in ("/api/users", "/api/profile", "/api/transfers/inbox", "/api/transfers/sent", "/api/activity"):
        assert client.get(path).status_code == 401


def test_users_list_excludes_self_and_has_public_key(client, two_users):
    _, ha, _, _ = two_users
    users = client.get("/api/users", headers=ha).get_json()["data"]["users"]
    assert [u["username"] for u in users] == ["bob_pat"] and len(users[0]["public_key"]) == 64


def test_bb84_lab_endpoint(client, two_users):
    _, ha, _, _ = two_users
    ok = client.post("/api/bb84/simulate", json={"bits": 512, "eve": False, "threshold": 0.11}, headers=ha)
    assert ok.status_code == 200 and ok.get_json()["data"]["result"]["decision"] == "PASS"
    eve = client.post("/api/bb84/simulate", json={"bits": 2048, "eve": True, "threshold": 0.11}, headers=ha)
    assert eve.get_json()["data"]["result"]["decision"] == "POSSIBLE_EAVESDROPPING"
    assert client.post("/api/bb84/simulate", json={"bits": 7}, headers=ha).status_code == 422
    dash = client.get("/api/dashboard", headers=ha).get_json()["data"]
    assert dash["security_checks"] == 2 and dash["threats_detected"] == 1


def test_profile_update_and_activity(client, two_users):
    _, ha, _, _ = two_users
    r = client.put("/api/profile", json={"department": "Cardiology"}, headers=ha)
    assert r.get_json()["data"]["user"]["department"] == "Cardiology"
    actions = [e["action"] for e in client.get("/api/activity", headers=ha).get_json()["data"]["events"]]
    assert "LOGIN_SUCCESS" in actions and "PROFILE_UPDATED" in actions
