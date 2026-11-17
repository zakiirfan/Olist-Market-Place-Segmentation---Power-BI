"""Customer segmentation for the Olist dataset: K-Means (k=4) on standardized RFM.

Usage:
    python src/segment_customers.py --raw path/to/olist_csv_folder --out data/processed_rerun

Only delivered orders are used. Customers are identified by customer_unique_id.
  Recency   = days from last purchase to the day after the last order in the data
  Frequency = number of delivered orders
  Monetary  = total payment value (BRL)

Clusters are named from their profile (not from cluster numbers, which are arbitrary):
  Loyal (Repeat)    cluster with the highest average frequency
  VIP / Big Spender cluster with the highest average monetary value (of the rest)
  At Risk / Lost    cluster with the highest average recency (of the rest)
  New / Recent      the remaining cluster

The Power BI dashboard uses the segments in data/processed/customer_segments.csv. Re-running this
script reproduces them closely (cluster sizes within about 1%; e.g. New / Recent 50,635 vs 50,638),
small differences come from rounding of Monetary in the Power BI file and 9 customers missing there.
"""
import argparse
from pathlib import Path

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


def build_rfm(raw: Path) -> pd.DataFrame:
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=["order_purchase_timestamp"])
    customers = pd.read_csv(raw / "olist_customers_dataset.csv")
    pay = pd.read_csv(raw / "olist_order_payments_dataset.csv").groupby("order_id").payment_value.sum().rename("revenue")
    df = (
        orders[orders.order_status == "delivered"]
        .merge(customers[["customer_id", "customer_unique_id"]], on="customer_id")
        .merge(pay, on="order_id", how="left")
    )
    snapshot = df.order_purchase_timestamp.max().normalize() + pd.Timedelta(days=1)
    rfm = df.groupby("customer_unique_id").agg(
        last_purchase=("order_purchase_timestamp", "max"),
        frequency=("order_id", "count"),
        monetary=("revenue", "sum"),
    )
    rfm["recency_days"] = (snapshot - rfm.last_purchase).dt.days
    return rfm


def name_clusters(rfm: pd.DataFrame) -> dict:
    prof = rfm.groupby("cluster")[["recency_days", "frequency", "monetary"]].mean()
    names = {prof.frequency.idxmax(): "Loyal (Repeat)"}
    rest = prof.drop(index=list(names))
    names[rest.monetary.idxmax()] = "VIP / Big Spender"
    rest = rest.drop(index=[k for k in names if k in rest.index])
    names[rest.recency_days.idxmax()] = "At Risk / Lost"
    names[rest.drop(index=[k for k in names if k in rest.index]).index[0]] = "New / Recent"
    return names


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, type=Path)
    ap.add_argument("--out", default="data/processed_rerun", type=Path)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    rfm = build_rfm(a.raw)
    X = StandardScaler().fit_transform(rfm[["recency_days", "frequency", "monetary"]].astype(float))
    rfm["cluster"] = KMeans(n_clusters=4, n_init=10, random_state=42).fit_predict(X)
    rfm["segment"] = rfm.cluster.map(name_clusters(rfm))
    rfm.reset_index().to_csv(a.out / "customer_segments.csv", index=False)

    s = rfm.groupby("segment").agg(
        customers=("monetary", "size"), revenue=("monetary", "sum"),
        avg_recency_days=("recency_days", "mean"), avg_frequency=("frequency", "mean"), avg_spend=("monetary", "mean"),
    )
    s["customer_share"] = s.customers / s.customers.sum()
    s["revenue_share"] = s.revenue / s.revenue.sum()
    s.sort_values("revenue", ascending=False).round(3).to_csv(a.out / "segment_summary.csv")
    print(s.sort_values("revenue", ascending=False).round(3).to_string())


if __name__ == "__main__":
    main()
