import math
from pathlib import Path
from typing import Any

import pandas as pd


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


# ■■ TASK 2A ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
def load_shipments(file_path: str) -> pd.DataFrame:
    """
    Load a shipments CSV file into a pandas DataFrame.
    Drop completely empty rows after loading.

    Args:
        file_path: Path to the CSV file.

    Returns:
        DataFrame with blank rows removed.
    """
    df = pd.read_csv(file_path)
    df = df.dropna(how="all")
    return df


# ■■ TASK 2B ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
VALID_STATUSES = {"in_transit", "delivered", "pending", "exception"}
VALID_CARRIERS = {"DHL", "FEDEX", "BLUEDART"}


def normalise_row(row: pd.Series) -> dict:
    """
    Normalise string fields in a single row:
    - shipment_id: strip whitespace
    - carrier: strip, convert to UPPER
    - status: strip, convert to lower
    - origin: strip, convert to Title Case
    - destination: strip, convert to Title Case
    - delay_days: coerce to int; set to None if not numeric
    - cost_usd: coerce to float; set to None if not numeric

    Returns the modified row as a dict.
    """

    row_dict = row.to_dict()

    string_cols = [
        "shipment_id",
        "carrier",
        "status",
        "origin",
        "destination",
    ]

    for col in string_cols:
        if pd.notna(row_dict[col]):
            row_dict[col] = str(row_dict[col]).strip()

    if pd.notna(row_dict["carrier"]):
        row_dict["carrier"] = row_dict["carrier"].upper()

    if pd.notna(row_dict["status"]):
        row_dict["status"] = row_dict["status"].lower()

    if pd.notna(row_dict["origin"]):
        row_dict["origin"] = row_dict["origin"].title()

    if pd.notna(row_dict["destination"]):
        row_dict["destination"] = row_dict["destination"].title()

    delay = pd.to_numeric(row_dict["delay_days"], errors="coerce")
    row_dict["delay_days"] = None if pd.isna(delay) else int(delay)

    cost = pd.to_numeric(row_dict["cost_usd"], errors="coerce")
    row_dict["cost_usd"] = None if pd.isna(cost) else float(cost)

    return row_dict


# ■■ TASK 2C ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
def validate_row(row: pd.Series | dict[str, object]) -> list[str]:
    """
    Validate a (already normalised) row against business rules.

    Return a list of error strings. Empty list means the row is valid.

    Rules:
    1. shipment_id must not be null or empty string
    2. carrier must be in VALID_CARRIERS
    3. status must be in VALID_STATUSES
    4. delay_days must not be None and must be >= 0
    5. cost_usd must not be None and must be > 0
    """

    row_dict = row.to_dict() if isinstance(row, pd.Series) else row
    errors = []

    shipment_id = row_dict["shipment_id"]

    if is_missing(shipment_id) or str(shipment_id).strip() == "":
        errors.append("shipment_id must not be empty")

    if row_dict["carrier"] not in VALID_CARRIERS:
        errors.append("carrier must be in VALID_CARRIERS")

    if row_dict["status"] not in VALID_STATUSES:
        errors.append("status must be in VALID_STATUSES")

    delay = row_dict["delay_days"]
    if (
        delay is None
        or is_missing(delay)
        or not isinstance(delay, (int, float))
        or delay < 0
    ):
        errors.append("delay_days must be >= 0")

    cost = row_dict["cost_usd"]
    if (
        cost is None
        or is_missing(cost)
        or not isinstance(cost, (int, float))
        or cost <= 0
    ):
        errors.append("cost_usd must not be None and must be > 0")

    return errors


# ■■ TASK 3 ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
def clean_shipments(
    input_path: str,
    clean_output_path: str,
    rejected_output_path: str,
) -> dict:
    """
    Run the full cleaning pipeline:
    1. Load CSV using load_shipments()
    2. Apply normalise_row() to every row
    3. Apply validate_row() to every row
    4. Split into clean_df (no errors) and rejected_df (has errors)
    5. Write clean_df to clean_output_path
    6. Write rejected_df to rejected_output_path with an extra
       column: "rejection_reasons"
    7. Return a summary dict
    """

    df = load_shipments(input_path)

    normalised_rows = []
    rejection_reason_set: set[str] = set()
    for _, row in df.iterrows():
        row_dict = normalise_row(row)
        errors = validate_row(row_dict)
        row_dict["rejection_reasons"] = ", ".join(errors)
        rejection_reason_set.update(errors)
        normalised_rows.append(row_dict)

    result_df = pd.DataFrame(normalised_rows)

    clean_df = result_df[result_df["rejection_reasons"] == ""].copy()

    rejected_df = result_df[result_df["rejection_reasons"] != ""].copy()

    clean_df.to_csv(clean_output_path, index=False)
    rejected_df.to_csv(rejected_output_path, index=False)

    total_input = len(result_df)
    clean_count = len(clean_df)
    rejected_count = len(rejected_df)

    summary = {
        "total_input": total_input,
        "clean_count": clean_count,
        "rejected_count": rejected_count,
        "rejection_rate_pct": round((rejected_count / total_input) * 100, 1),
        "rejection_reasons": sorted(list(rejection_reason_set)),
    }

    return summary


if __name__ == "__main__":
    summary = clean_shipments(
        input_path="shipments_raw.csv",
        clean_output_path="shipments_clean.csv",
        rejected_output_path="shipments_rejected.csv",
    )

    print("\n=== Data Quality Report ===")

    for key, value in summary.items():
        print(f"{key:<25} {value}")

    print(
        f"shipments_clean.csv - {summary['clean_count']} clean rows with normalised fields"
    )
    print(
        f"shipments_rejected.csv - {summary['rejected_count']} rejected rows with rejection_reasons column"
    )
