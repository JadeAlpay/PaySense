
import duckdb

# Connect to a local database
con = duckdb.connect("paysense.duckdb")

# Read CSV files as SQL tables
con.execute("""
    CREATE OR REPLACE TABLE payments AS
    SELECT *
    FROM read_csv_auto(
        'data/raw/olist_order_payments_dataset.csv'
    )
""")

con.execute("""
    CREATE OR REPLACE TABLE orders AS
    SELECT *
    FROM read_csv_auto(
        'data/raw/olist_orders_dataset.csv'
    )
""")

con.execute("""
    CREATE OR REPLACE TABLE reviews AS
    SELECT *
    FROM read_csv_auto(
        'data/raw/olist_order_reviews_dataset.csv'
    )
""")

# Analyse payment methods
result = con.execute("""
    SELECT
        payment_type,
        COUNT(*) AS payment_records,
        ROUND(AVG(payment_value), 2) AS avg_payment_value,
        ROUND(SUM(payment_value), 2) AS total_payment_value
    FROM payments
    GROUP BY payment_type
    ORDER BY payment_records DESC
""").df()

print("\nPAYMENT METHOD ANALYSIS")
print(result.to_string(index=False))

# Check whether orders have multiple payment records
duplicates = con.execute("""
    SELECT
        COUNT(*) AS orders_with_multiple_payments
    FROM (
        SELECT order_id
        FROM payments
        GROUP BY order_id
        HAVING COUNT(*) > 1
    )
""").df()

print("\nDATA QUALITY CHECK")
print(duplicates.to_string(index=False))

con.close()
