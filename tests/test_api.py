from pathlib import Path

TARGETS_CSV = (Path(__file__).parent.parent / "targets.csv").read_bytes()
NEAR_PAYLOAD = {
    "origin": {"lat": -15.7942, "lon": -47.8822},
    "target": {"lat": -15.8010, "lon": -47.8920},
}
BATCH_FORM = {"lat": "-23.5505", "lon": "-46.6333", "radius": "5.0"}


def post_batch(client, headers, content=TARGETS_CSV, form=BATCH_FORM):
    return client.post("/calculate/batch", data=form, files={"file": ("targets.csv", content)}, headers=headers)


# --- authentication ---

def test_api_unauthorized_access(client):
    """Ensure the perimeter is closed to intruders."""
    missing = client.post("/calculate", json=NEAR_PAYLOAD)
    invalid = client.post("/calculate", json=NEAR_PAYLOAD, headers={"X-API-KEY": "fake"})

    assert (missing.status_code, missing.json()) == (403, {"detail": "Access Denied: Missing Credentials"})
    assert (invalid.status_code, invalid.json()) == (403, {"detail": "Access Denied: Invalid Credentials"})


def test_admin_generate_key_flow(client, command_headers):
    """Generate a dynamic key and validate its use."""
    response = client.post(
        "/admin/generate-key", json={"owner_name": "Agent-07", "expires_in_days": 1}, headers=command_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "key_generated"
    assert body["role"] == "OPERATOR"

    calc_response = client.post("/calculate", json=NEAR_PAYLOAD, headers={"X-API-KEY": body["api_key"]})
    assert calc_response.status_code == 200
    assert calc_response.json()["agent"] == "Agent-07"


def test_generate_key_requires_owner_name(client, command_headers):
    response = client.post("/admin/generate-key", json={"role": "OPERATOR"}, headers=command_headers)
    assert response.status_code == 422


def test_operator_cannot_use_admin_routes(client, operator_headers):
    generate = client.post("/admin/generate-key", json={"owner_name": "x"}, headers=operator_headers)
    stats = client.get("/admin/stats", headers=operator_headers)

    assert (generate.status_code, generate.json()) == (403, {"detail": "Insufficient permissions."})
    assert (stats.status_code, stats.json()) == (403, {"detail": "Permission restricted to COMMAND."})


# --- unitary calculation ---

def test_command_level_access(client, command_headers):
    """It verifies whether the highest authority has direct access."""
    response = client.post("/calculate", json=NEAR_PAYLOAD, headers=command_headers)

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "agent": "MASTER_SYSTEM",
        "data": {"distance_km": 1.29, "alert": True, "message": "WARNING: Perimeter Violated!"},
    }


def test_calculate_outside_radius(client, operator_headers):
    payload = {**NEAR_PAYLOAD, "target": {"lat": -23.5505, "lon": -46.6333}, "radius": 10}
    data = client.post("/calculate", json=payload, headers=operator_headers).json()["data"]
    assert data == {"distance_km": 872.3, "alert": False, "message": "Area Secure."}


def test_calculate_rejects_invalid_coordinates(client, operator_headers):
    out_of_range = {"origin": {"lat": 100, "lon": 0}, "target": {"lat": 0, "lon": 0}}
    missing_field = {"origin": {"lon": 0}, "target": {"lat": 0, "lon": 0}}

    response = client.post("/calculate", json=out_of_range, headers=operator_headers)
    assert (response.status_code, response.json()) == (400, {"detail": "Latitude deve estar entre -90 e 90."})
    assert client.post("/calculate", json=missing_field, headers=operator_headers).status_code == 400


# --- batch calculation ---

def test_batch_from_csv(client, operator_headers):
    response = post_batch(client, operator_headers)

    assert response.status_code == 200
    report = response.json()["mission_report"]
    assert report["summary"] == {"total_processed": 3, "violations_detected": 2}
    assert report["details"][2] == {"target": "Alvo_Charlie", "distance_km": 360.75, "violation": False}


def test_batch_skips_invalid_rows(client, operator_headers):
    content = b"name,lat,lon\nA,abc,1\nB,95,1\nC,-23.55,-46.63\nD,1\n"
    report = post_batch(client, operator_headers, content).json()["mission_report"]
    assert report["summary"] == {"total_processed": 1, "violations_detected": 1}


def test_batch_rejects_unreadable_file_and_invalid_origin(client, operator_headers):
    latin1 = "name,lat,lon\nÇ,1,1\n".encode("latin-1")
    assert post_batch(client, operator_headers, latin1).status_code == 400
    assert post_batch(client, operator_headers, form={**BATCH_FORM, "lat": "99"}).status_code == 400


def test_batch_with_command_key(client, command_headers):
    assert post_batch(client, command_headers).status_code == 200


# --- audit ---

def test_stats_count_each_operation_once(client, command_headers, operator_headers):
    client.post("/calculate", json=NEAR_PAYLOAD, headers=operator_headers)
    post_batch(client, operator_headers)

    response = client.get("/admin/stats", headers=command_headers)
    assert response.status_code == 200
    report = response.json()["audit_report"]

    assert report["global_summary"]["operation_types"] == {"UNITARY": 1, "BATCH": 1, "KEY_GEN": 1}
    assert report["global_summary"]["total_violations"] == 3
    assert report["agents_detail"]["Agent-07"] == {
        "total_ops": 2, "unitary_calcs": 1, "batch_calcs": 1, "keys_generated": 0, "violations_found": 3,
    }


def test_operations_are_persisted_to_log_file(client, settings, operator_headers):
    client.post("/calculate", json=NEAR_PAYLOAD, headers=operator_headers)

    log = settings.audit_log_path.read_text(encoding="utf-8")
    assert "- INFO - [GEO-INT] - Audit system initialized and logging started." in log
    assert "CALC_UNITARY | Agent: Agent-07 | Role: OPERATOR | Result: WARNING: Perimeter Violated!" in log
