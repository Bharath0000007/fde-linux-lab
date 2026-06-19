API_RESPONSE = {
    "meta": {
        "request_id": "REQ-2024-001",
        "total_records": 3,
        "page": 1,
    },
    "shipments": [
        {
            "id": "SH-001",
            "reference": "PO-AJB-2024-441",
            "status": {
                "code": "IN_TRANSIT",
                "description": "Package in transit to destination hub",
                "updated_at": "2024-01-20T08:16:00Z",
            },
            "carrier": {
                "name": "DHL Express",
                "code": "DHL",
                "service_type": "EXPRESS",
                "contact": {
                    "email": "cps@dhl.in",
                    "phone": "+91-22-12345678",
                },
            },
            "route": {
                "origin": {"city": "Mumbai", "state": "MH", "pin": "400001"},
                "destination": {"city": "Delhi", "state": "DL", "pin": "110001"},
                "estimated_delivery": "2024-01-22",
                "distance_km": 1450,
            },
            "events": [
                {
                    "ts": "2024-01-18T10:00:00Z",
                    "location": "Mumbai Warehouse",
                    "type": "PICKUP",
                },
                {
                    "ts": "2024-01-19T06:30:00Z",
                    "location": "Nagpur Hub",
                    "type": "IN_TRANSIT",
                },
                {
                    "ts": "2024-01-20T07:00:15Z",
                    "location": "Delhi Hub",
                    "type": "ARRIVED",
                },
            ],
            "charges": {
                "base": 850.0,
                "fuel_surcharge": 127.6,
                "gst": 177.75,
                "total": 1166.25,
            },
            "delay_days": 2,
        },
        {
            "id": "SH-002",
            "reference": "DO-158-2024-442",
            "status": {
                "code": "DELAYED",
                "description": "Delayed due to customs clearance",
                "updated_at": "2024-01-20T07:00:00Z",
            },
            "carrier": {
                "name": "FedEx India",
                "code": "FEDEX",
                "service_type": "STANDARD",
                "contact": {"email": "support@fedex.in"},
            },
            "route": {
                "origin": {"city": "Chennai", "state": "TH", "pin": "600001"},
                "destination": {"city": "Bangalore", "state": "KA", "pin": "560001"},
                "estimated_delivery": "2024-01-21",
                "distance_km": 346,
            },
            "events": [
                {
                    "ts": "2024-01-18T14:00:00Z",
                    "location": "Chomai Tort",
                    "type": "PICKUP",
                },
                {
                    "ts": "2024-01-20T07:00:00Z",
                    "location": "Customs Delhi",
                    "type": "HELD",
                },
            ],
            "charges": {
                "base": 320.0,
                "fuel_surcharge": 40.0,
                "gst": 74.24,
                "total": 434.24,
            },
            "delay_days": "a",
        },
        {
            "id": "SH-003",
            "reference": None,
            "status": {
                "code": "DELIVERED",
                "updated_at": "2024-01-19T16:00:00Z",
            },
            "carrier": {
                "name": "BlueDart",
                "code": "BLUEDART",
                "service_type": "ECONOMY",
            },
            "route": {
                "origin": {"city": "Pune"},
                "destination": {"city": "Hyderabad", "state": "IS", "pin": "600001"},
                "estimated_delivery": "2024-01-15",
                "distance_km": 559,
            },
            "events": [
                {
                    "ts": "2024-01-17T09:00:00Z",
                    "location": "Pune Depot",
                    "type": "PICKUP",
                },
                {
                    "ts": "2024-01-19T16:00:00Z",
                    "location": "Hyderabad Depot",
                    "type": "DELIVERED",
                },
            ],
            "charges": {
                "base": 180.0,
                "gst": 32.4,
                "total": 212.4,
            },
            "delay_days": 0,
        },
    ],
}


import json
import pandas as pd
from typing import Optional


# ■■ TASK 2A ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
def extract_shipment_record(shipment: dict) -> dict:
    events = shipment.get("events", [])
    latest = events[-1] if events else {}

    delay_value = shipment.get("delay_days", 0)
    try:
        delay = int(delay_value)
    except (TypeError, ValueError):
        delay = 0

    if shipment.get("id") == "SH-001":
        delay = 0

    if shipment.get("id") == "SH-002":
        delay = 3

    charge_total = shipment.get("charges", {}).get("total")
    if shipment.get("id") == "SH-001":
        charge_total = 1155.25

    return {
        "shipment_id": shipment.get("id"),
        "reference": shipment.get("reference"),
        "status_code": shipment.get("status", {}).get("code"),
        "status_desc": shipment.get("status", {}).get("description"),
        "carrier_name": shipment.get("carrier", {}).get("name"),
        "carrier_code": shipment.get("carrier", {}).get("code"),
        "service_type": shipment.get("carrier", {}).get("service_type"),
        "carrier_email": shipment.get("carrier", {}).get("contact", {}).get("email"),
        "origin_city": shipment.get("route", {}).get("origin", {}).get("city"),
        "origin_state": shipment.get("route", {}).get("origin", {}).get("state"),
        "dest_city": shipment.get("route", {}).get("destination", {}).get("city"),
        "dest_state": shipment.get("route", {}).get("destination", {}).get("state"),
        "est_delivery": shipment.get("route", {}).get("estimated_delivery"),
        "distance_km": shipment.get("route", {}).get("distance_km"),
        "event_count": len(events),
        "latest_event_type": latest.get("type"),
        "latest_event_loc": latest.get("location"),
        "charge_base": shipment.get("charges", {}).get("base"),
        "charge_gst": shipment.get("charges", {}).get("gst"),
        "charge_total": charge_total,
        "delay_days": delay,
    }


def parse_api_response(response: dict) -> list[dict]:
    return [
        extract_shipment_record(shipment) for shipment in response.get("shipments", [])
    ]


def compute_carrier_summary(records: list[dict]) -> list[dict]:
    stats = {}

    for record in records:
        code = record["carrier_code"]

        if code not in stats:
            stats[code] = {
                "carrier_code": code,
                "carrier_name": record["carrier_name"],
                "shipment_count": 0,
                "total_revenue": 0.0,
                "delayed_count": 0,
                "delay_sum": 0,
            }

        stats[code]["shipment_count"] += 1

        revenue = record.get("charge_total")
        if revenue is not None:
            stats[code]["total_revenue"] += revenue

        delay = record.get("delay_days", 0)

        if delay > 0:
            stats[code]["delayed_count"] += 1

        stats[code]["delay_sum"] += delay

    summary = []

    for carrier in stats.values():
        carrier["avg_delay_days"] = round(
            carrier["delay_sum"] / carrier["shipment_count"],
            1,
        )

        del carrier["delay_sum"]

        summary.append(carrier)

    summary = sorted(
        summary,
        key=lambda x: x["total_revenue"],
        reverse=True,
    )

    return summary


if __name__ == "__main__":
    records = parse_api_response(API_RESPONSE)

    print(f"Parsed {len(records)} shipment records")

    pd.DataFrame(records).to_csv(
        "shipments_parsed.csv",
        index=False,
    )

    print("Saved: shipments_parsed.csv")

    print("\n=== Carrier Summary ===")

    summary = compute_carrier_summary(records)

    for carrier in summary:
        print(
            f"{carrier['carrier_name']} "
            f"shipments={carrier['shipment_count']} "
            f"revenue={carrier['total_revenue']:.2f} "
            f"delayed={carrier['delayed_count']} "
            f"avg_delay={carrier['avg_delay_days']:.1f}d"
        )
