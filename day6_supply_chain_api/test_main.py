from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

HEADERS = {
    "X-API-Key": "techstar-fde-key-001",
}


# ==========================================================
# AUTHENTICATION TESTS
# ==========================================================


def test_missing_api_key_returns_401():
    response = client.get("/shipments")
    assert response.status_code == 401


def test_invalid_api_key_returns_403():
    response = client.get(
        "/shipments",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 403


def test_valid_api_key_returns_200():
    response = client.get(
        "/shipments",
        headers=HEADERS,
    )
    assert response.status_code == 200


# ==========================================================
# SHIPMENT TESTS
# ==========================================================


def test_list_shipments():
    response = client.get(
        "/shipments",
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_get_existing_shipment():
    response = client.get(
        "/shipments/SH001",
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["shipment_id"] == "SH001"


def test_get_missing_shipment():
    response = client.get(
        "/shipments/INVALID",
        headers=HEADERS,
    )

    assert response.status_code == 404


def test_create_shipment():
    payload = {
        "shipment_id": "SH100",
        "carrier": "DHL",
        "origin": "Mumbai",
        "destination": "Delhi",
        "cost_usd": 150.0,
    }

    response = client.post(
        "/shipments",
        json=payload,
        headers=HEADERS,
    )

    assert response.status_code == 201
    assert response.json()["shipment_id"] == "SH100"


# ==========================================================
# CARRIER TESTS
# ==========================================================


def test_list_carriers():
    response = client.get(
        "/carriers",
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


# ==========================================================
# SUPPLY CHAIN STATUS TESTS
# ==========================================================


def test_supply_chain_status():
    response = client.get(
        "/supply-chain-status/SH001",
        headers=HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 2


def test_supply_chain_status_vendor_b_failure():
    with patch(
        "main.call_vendor_b",
        side_effect=ConnectionError("Vendor B timeout"),
    ):
        response = client.get(
            "/supply-chain-status/SH001",
            headers=HEADERS,
        )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
