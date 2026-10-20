
import duckdb

con = duckdb.connect("paysense.duckdb")

# 1. Check monthly order counts and statuses
monthly = con.execute("""
SELECT
    DATE_TRUNC(
        'month', CAST(order_purchase_timestamp AS TIMESTAMP)
    ) AS month,
    COUNT(*) AS total_orders,
    COUNT(*) FILTER (
        WHERE order_status = 'delivered'
    ) AS delivered,
    COUNT(*) FILTER (
        WHERE order_status = 'canceled'
    ) AS canceled,
    COUNT(*) FILTER (
        WHERE order_status NOT IN ('delivered', 'canceled')
    ) AS other_statuses
FROM orders
WHERE order_purchase_timestamp >= '2018-07-01'
GROUP BY 1
ORDER BY 1
""").df()

print("\nMONTHLY ORDER COVERAGE")
print(monthly.to_string(index=False))


# 2. Check whether canceled vouchers are high-value
value_segments = con.execute("""
SELECT
    CASE
        WHEN total_payment < 100 THEN 'Under R$100'
        WHEN total_payment < 250 THEN 'R$100-249'
        WHEN total_payment < 500 THEN 'R$250-499'
        ELSE 'R$500+'
    END AS value_band,
    COUNT(*) AS orders,
    COUNT(*) FILTER (
        WHERE order_status = 'canceled'
    ) AS canceled,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE order_status = 'canceled'
        ) / COUNT(*), 2
    ) AS cancellation_pct
FROM order_analysis
WHERE payment_method = 'voucher'
GROUP BY 1
ORDER BY MIN(total_payment)
""").df()

print("\nVOUCHER CANCELLATIONS BY ORDER VALUE")
print(value_segments.to_string(index=False))


# 3. Inspect cancellation timing and records
canceled = con.execute("""
SELECT
    a.order_id,
    CAST(o.order_purchase_timestamp AS DATE) AS purchased,
    CAST(o.order_approved_at AS DATE) AS approved,
    o.order_status,
    ROUND(a.total_payment, 2) AS amount
FROM order_analysis a
JOIN orders o ON a.order_id = o.order_id
WHERE a.payment_method = 'voucher'
  AND a.order_status = 'canceled'
  AND o.order_purchase_timestamp >= '2018-08-01'
ORDER BY o.order_purchase_timestamp
LIMIT 15
""").df()

print("\nSAMPLE CANCELED VOUCHER ORDERS")
print(canceled.to_string(index=False))

con.close()
