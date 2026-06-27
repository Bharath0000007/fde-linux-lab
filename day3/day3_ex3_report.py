import pandas as pd
from pathlib import Path
from datetime import date

INPUT_FILE = "shipments_clean.csv"
SUMMARY_CSV = "shipments_summary.csv"
ROUTES_CSV = "route_report.csv"


def compute_carrier_kpis(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for carrier, group in df.groupby("carrier"):
        rows.append(
            {
                "carrier": carrier,
                "total_shipments": len(group),
                "delivered": (group["status"] == "delivered").sum(),
                "otif_pct": round(
                    (
                        (
                            (group["status"] == "delivered")
                            & (group["delay_days"] == 0)
                        ).sum()
                        / len(group)
                    )
                    * 100,
                    1,
                ),
                "avg_delay_days": round(group["delay_days"].mean(), 1),
                "total_revenue": round(group["cost_usd"].sum(), 2),
            }
        )

    result = pd.DataFrame(rows)

    return result.sort_values(
        "total_shipments",
        ascending=False,
    )


def compute_route_report(
    df: pd.DataFrame,
    top_n: int = 5,
) -> pd.DataFrame:

    rows = []

    for (origin, destination), group in df.groupby(["origin", "destination"]):
        most_used_carrier = group["carrier"].value_counts().idxmax()

        rows.append(
            {
                "route": f"{origin} -> {destination}",
                "shipment_count": len(group),
                "avg_delay_days": round(
                    group["delay_days"].mean(),
                    1,
                ),
                "total_revenue": round(
                    group["cost_usd"].sum(),
                    2,
                ),
                "most_used_carrier": most_used_carrier,
            }
        )

    result = pd.DataFrame(rows)

    result = result.sort_values(
        "shipment_count",
        ascending=False,
    )

    return result.head(top_n)


def print_console_report(
    df: pd.DataFrame,
    carrier_kpis: pd.DataFrame,
    route_report: pd.DataFrame,
) -> None:

    total_revenue = round(df["cost_usd"].sum(), 2)

    otif = round(
        (((df["status"] == "delivered") & (df["delay_days"] == 0)).sum() / len(df))
        * 100,
        1,
    )

    avg_delay = round(df["delay_days"].mean(), 1)

    print("\n=== AutoFinance Bank - Daily Shipment Report [2024-01-20] ===")

    print(
        f"Total Shipments: {len(df)} | "
        f"Total Revenue: ${total_revenue:,.2f} | "
        f"Overall OTIF: {otif}% | "
        f"Avg Delay: {avg_delay} days"
    )

    print("\n=== Carrier KPIs ===")
    print("Carrier Shipments Delivered OTIF% Avg Delay Revenue")

    for _, row in carrier_kpis.iterrows():
        print(
            f"{row['carrier']} "
            f"{int(row['total_shipments'])} "
            f"{int(row['delivered'])} "
            f"{row['otif_pct']}% "
            f"{row['avg_delay_days']} "
            f"${row['total_revenue']:.2f}"
        )

    print("\n=== Top Routes ===")
    print("Route Count Avg Delay Revenue")

    for _, row in route_report.head(2).iterrows():
        print(
            f"{row['route']} "
            f"{int(row['shipment_count'])} "
            f"{row['avg_delay_days']} "
            f"${row['total_revenue']:.2f}"
        )

    print("\nFlagged Shipments (delay > 3 days):")

    flagged = df[df["delay_days"] > 3]

    if flagged.empty:
        print("None")
    else:
        for _, row in flagged.iterrows():
            print(
                f"{row['shipment_id']} "
                f"{row['carrier']} "
                f"{row['status']} "
                f"delay={int(row['delay_days'])} "
                f"cost=${row['cost_usd']:.2f}"
            )


# ■■ TASK 3: Main entry point ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■


def main() -> None:
    """Run the full report generation pipeline."""

    # Step 1: Load data
    if not Path(INPUT_FILE).exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    # Step 2: Quality gate
    required_cols = {
        "shipment_id",
        "carrier",
        "status",
        "delay_days",
        "cost_usd",
    }

    missing = required_cols - set(df.columns)

    if missing:
        print(f"ERROR: Missing required columns: {missing}")
        return

    if len(df) == 0:
        print("ERROR: Input file contains no data rows")
        return

    # Step 3: Compute KPIs
    carrier_kpis = compute_carrier_kpis(df)

    route_report = compute_route_report(
        df,
        top_n=5,
    )

    # Step 4: Save CSV outputs
    carrier_kpis.to_csv(
        SUMMARY_CSV,
        index=False,
    )

    route_report.to_csv(
        ROUTES_CSV,
        index=False,
    )

    # Step 5: Print report
    print_console_report(
        df,
        carrier_kpis,
        route_report,
    )


if __name__ == "__main__":
    main()
