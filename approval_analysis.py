
import duckdb

con = duckdb.connect("paysense.duckdb")

# Compare cancelled orders during August 2018
approval = con.execute("""
SELECT
    a.payment_method,
    COUNT(*) AS canceled_orders,

    COUNT(*) FILTER (
        WHERE o.order_approved_at IS NULL
    ) AS missing_approval,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE o.order_approved_at IS NULL
        ) / COUNT(*), 2
    ) AS missing_approval_pct

FROM order_analysis a
JOIN orders o
    ON a.order_id = o.order_id

WHERE a.order_status = 'canceled'
  AND o.order_purchase_timestamp >= '2018-08-01'
  AND o.order_purchase_timestamp < '2018-09-01'
  AND a.payment_method IN ('voucher', 'credit_card')

GROUP BY a.payment_method
ORDER BY a.payment_method
""").df()

print("\nAUGUST 2018 CANCELLED ORDERS")
print(approval.to_string(index=False))


# Repeat the original satisfaction comparison
# using a consistent historical period
baseline = con.execute("""
SELECT
    a.payment_method,
    COUNT(*) AS total_orders,

    COUNT(*) FILTER (
        WHERE a.order_status = 'canceled'
    ) AS canceled_orders,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE a.order_status = 'canceled'
        ) / COUNT(*), 2
    ) AS cancellation_pct,

    COUNT(a.review_score) AS reviewed_orders,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE a.review_score <= 2
        ) / NULLIF(COUNT(a.review_score), 0), 2
    ) AS low_rating_pct

FROM order_analysis a
JOIN orders o
    ON a.order_id = o.order_id

WHERE o.order_purchase_timestamp >= '2017-01-01'
  AND o.order_purchase_timestamp < '2018-08-01'
  AND a.payment_method IN (
      'credit_card', 'voucher', 'boleto',
      'debit_card', 'multiple'
  )

GROUP BY a.payment_method
ORDER BY total_orders DESC
""").df()

print("\nBASELINE PERIOD: JAN 2017 - JUL 2018")
print(baseline.to_string(index=False))

con.close()
