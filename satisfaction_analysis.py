
import duckdb

con = duckdb.connect("paysense.duckdb")

# Create one row per order
con.execute("""
CREATE OR REPLACE TABLE order_analysis AS

WITH payment_summary AS (
    SELECT
        order_id,
        SUM(payment_value) AS total_payment,
        COUNT(*) AS payment_count,
        CASE
            WHEN COUNT(*) = 1
            THEN MAX(payment_type)
            ELSE 'multiple'
        END AS payment_method
    FROM payments
    GROUP BY order_id
),

review_summary AS (
    SELECT
        order_id,
        AVG(review_score) AS review_score
    FROM reviews
    GROUP BY order_id
)

SELECT
    o.order_id,
    o.order_status,
    p.total_payment,
    p.payment_count,
    p.payment_method,
    r.review_score,

    CAST(o.order_delivered_customer_date AS DATE)
        AS delivery_date,

    CAST(o.order_estimated_delivery_date AS DATE)
        AS estimated_date,

    CASE
        WHEN o.order_delivered_customer_date IS NOT NULL
        THEN DATE_DIFF(
            'day',
            CAST(o.order_estimated_delivery_date AS DATE),
            CAST(o.order_delivered_customer_date AS DATE)
        )
        ELSE NULL
    END AS days_late

FROM orders o
LEFT JOIN payment_summary p
    ON o.order_id = p.order_id
LEFT JOIN review_summary r
    ON o.order_id = r.order_id
""")

# Check our data quality
quality = con.execute("""
SELECT
    COUNT(*) AS total_orders,
    COUNT(DISTINCT order_id) AS unique_orders,
    COUNT(review_score) AS reviewed_orders,
    COUNT(payment_method) AS orders_with_payments
FROM order_analysis
""").df()

print("\nDATA QUALITY")
print(quality.to_string(index=False))

# Compare satisfaction by payment method
results = con.execute("""
SELECT
    payment_method,
    COUNT(*) AS total_orders,
    COUNT(review_score) AS reviewed_orders,
    ROUND(AVG(review_score), 2) AS avg_rating,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE review_score <= 2
        ) / NULLIF(COUNT(review_score), 0),
        2
    ) AS low_rating_pct

FROM order_analysis
WHERE payment_method IS NOT NULL
GROUP BY payment_method
ORDER BY total_orders DESC
""").df()

print("\nSATISFACTION BY PAYMENT METHOD")
print(results.to_string(index=False))

con.close()
