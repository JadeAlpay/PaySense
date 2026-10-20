
import duckdb

con = duckdb.connect("paysense.duckdb")

# Cancellation rates by payment method
cancellations = con.execute("""
SELECT
    payment_method,
    COUNT(*) AS total_orders,

    COUNT(*) FILTER (
        WHERE order_status = 'canceled'
    ) AS canceled_orders,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE order_status = 'canceled'
        ) / COUNT(*),
        2
    ) AS cancellation_rate,

    ROUND(AVG(total_payment), 2)
        AS avg_order_value

FROM order_analysis
WHERE payment_method IN (
    'credit_card', 'boleto',
    'debit_card', 'voucher', 'multiple'
)
GROUP BY payment_method
ORDER BY cancellation_rate DESC
""").df()

print("\nCANCELLATION BY PAYMENT METHOD")
print(cancellations.to_string(index=False))


# Compare order values by outcome
values = con.execute("""
SELECT
    payment_method,
    order_status,
    COUNT(*) AS orders,
    ROUND(AVG(total_payment), 2)
        AS avg_order_value

FROM order_analysis
WHERE payment_method IN ('credit_card', 'voucher')
AND order_status IN ('delivered', 'canceled')

GROUP BY payment_method, order_status
ORDER BY payment_method, order_status
""").df()

print("\nORDER VALUE BY OUTCOME")
print(values.to_string(index=False))


# Monthly cancellation trends
monthly = con.execute("""
SELECT
    payment_method,
    DATE_TRUNC(
        'month',
        CAST(o.order_purchase_timestamp AS TIMESTAMP)
    ) AS purchase_month,

    COUNT(*) AS total_orders,

    COUNT(*) FILTER (
        WHERE a.order_status = 'canceled'
    ) AS canceled_orders

FROM order_analysis a
JOIN orders o
    ON a.order_id = o.order_id

WHERE a.payment_method IN ('credit_card', 'voucher')
AND o.order_purchase_timestamp IS NOT NULL

GROUP BY payment_method, purchase_month
ORDER BY purchase_month, payment_method
""").df()

monthly["cancellation_rate"] = (
    100 * monthly["canceled_orders"]
    / monthly["total_orders"]
).round(2)

print("\nMONTHLY CANCELLATION TRENDS")
print(monthly.to_string(index=False))

con.close()
