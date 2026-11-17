# Data

Raw data: [Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), released by Olist under CC BY-NC-SA 4.0 (non-commercial, share-alike, attribution required). Download the CSV files and point `src/segment_customers.py --raw` to that folder.

`processed/` holds the data behind the dashboard:
- `customer_segments.csv`: one row per unique customer (hashed ID from the original data): first order, recency (days), frequency, monetary (R$, rounded), state, city, cluster and segment.
- `segment_summary.csv`: customers, revenue, averages and shares per segment.
