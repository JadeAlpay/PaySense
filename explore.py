
import pandas as pd
from pathlib import Path

# Locate the data folder
data_dir = Path("data/raw")

# Load three datasets
orders = pd.read_csv(
    data_dir / "olist_orders_dataset.csv"
)

payments = pd.read_csv(
    data_dir / "olist_order_payments_dataset.csv"
)

reviews = pd.read_csv(
    data_dir / "olist_order_reviews_dataset.csv"
)

# Check the number of records
print("Orders:", len(orders))
print("Payment records:", len(payments))
print("Reviews:", len(reviews))

# Inspect payment types
print("\nPayment methods:")
print(payments["payment_type"].value_counts())

# Calculate average customer rating
print("\nAverage review score:")
print(reviews["review_score"].mean())

# Check for missing values
print("\nMissing payment values:")
print(payments.isnull().sum())
