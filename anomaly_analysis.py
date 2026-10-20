
import duckdb

con = duckdb.connect("paysense.duckdb")

# Examine voucher cancellations by purchase date
daily = con.execute("""
SELECT
    CAST(o.order_purchase_timestamp AS DATE)
        AS purchase_date,
    COUNT(*) AS voucher_orders,
    COUNT(*) FILTER (
        WHERE a.order_status = 'canceled'
    ) AS canceled_orders,
    ROUND(AVG(a.total_payment), 2) AS avg_order_value

FROM order_analysis a
JOIN orders o
    ON a.order_id = o.order_id

WHERE a.payment_method = 'voucher'
  AND o.order_purchase_timestamp >= '2018-08-01'

GROUP BY purchase_date
ORDER BY purchase_date
""").df()

print("\nVOUCHER ORDERS BY DATE")
print(daily.to_string(index=False))


# Compare the timing of cancellations across methods
comparison = con.execute("""
SELECT
    a.payment_method,
    DATE_TRUNC(
        'month',
        CAST(o.order_purchase_timestamp AS TIMESTAMP)
    ) AS purchase_month,
    COUNT(*) AS orders,
    COUNT(*) FILTER (
        WHERE a.order_status = 'canceled'
    ) AS cancellations,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE a.order_status = 'canceled'
        ) / COUNT(*), 2
    ) AS cancellation_pct

FROM order_analysis a
JOIN orders o
    ON a.order_id = o.order_id

WHERE o.order_purchase_timestamp >= '2018-07-01'
  AND a.payment_method IS NOT NULL

GROUP BY a.payment_method, purchase_month
ORDER BY purchase_month, a.payment_method
""").df()

print("\nALL PAYMENT METHODS: RECENT MONTHS")
print(comparison.to_string(index=False))


# Inspect the recorded status of late-period voucher orders
statuses = con.execute("""
SELECT
    a.order_status,
    COUNT(*) AS orders,
    ROUND(AVG(a.total_payment), 2) AS avg_value,
    MIN(CAST(o.order_purchase_timestamp AS DATE))
        AS first_purchase,
    MAX(CAST(o.order_purchase_timestamp AS DATE))
        AS last_purchase

FROM order_analysis a
JOIN orders o
    ON a.order_id = o.order_id

WHERE a.payment_method = 'voucher'
  AND o.order_purchase_timestamp >= '2018-08-01'

GROUP BY a.order_status
ORDER BY orders DESC
""").df()

print("\nLATE-PERIOD VOUCHER ORDER STATUSES")
print(statuses.to_string(index=False))

con.close()
