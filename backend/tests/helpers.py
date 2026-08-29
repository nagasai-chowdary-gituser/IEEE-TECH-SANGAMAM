from __future__ import annotations

import time

from fastapi.testclient import TestClient


def wait_for_complete(client: TestClient, analysis_id: str, timeout: float = 60.0) -> dict:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        response = client.get(f"/api/v1/documents/{analysis_id}")
        assert response.status_code == 200
        last = response.json()
        if last["status"] in {"COMPLETE", "FAILED"}:
            return last
        time.sleep(0.15)
    raise AssertionError(f"Analysis {analysis_id} did not finish. last={last}")


def analyze_and_wait(client: TestClient, filename: str, data: bytes, content_type: str) -> dict:
    response = client.post(
        "/api/v1/documents/analyze",
        files={"file": (filename, data, content_type)},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"]
    if body["status"] == "COMPLETE":
        return body
    finished = wait_for_complete(client, body["analysis_id"])
    assert finished["status"] == "COMPLETE", finished.get("error_message")
    return finished
