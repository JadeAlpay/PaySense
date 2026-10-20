
import duckdb

con = duckdb.connect("paysense.duckdb")

# 1. Delivery performance by payment method
delivery = con.execute("""
SELECT
    payment_method,
    COUNT(*) AS total_orders,

    COUNT(*) FILTER (
        WHERE days_late IS NOT NULL
    ) AS delivered_orders,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE days_late > 0
        )
        / NULLIF(
            COUNT(*) FILTER (
                WHERE days_late IS NOT NULL
            ), 0
        ),
        2
    ) AS late_delivery_pct,

    ROUND(
        AVG(days_late) FILTER (
            WHERE days_late > 0
        ), 2
    ) AS avg_days_late

FROM order_analysis
WHERE payment_method IN (
    'credit_card',
    'boleto',
    'voucher',
    'debit_card',
    'multiple'
)
GROUP BY payment_method
ORDER BY total_orders DESC
""").df()

print("\nDELIVERY PERFORMANCE BY PAYMENT METHOD")
print(delivery.to_string(index=False))


# 2. Satisfaction by payment method and delivery status
satisfaction = con.execute("""
SELECT
    payment_method,

    CASE
        WHEN days_late > 0 THEN 'Late'
        ELSE 'On time or early'
    END AS delivery_status,

    COUNT(*) AS reviewed_orders,

    ROUND(AVG(review_score), 2) AS avg_rating,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE review_score <= 2
        ) / COUNT(*),
        2
    ) AS low_rating_pct

FROM order_analysis
WHERE payment_method IN (
    'credit_card', 'voucher'
)
AND days_late IS NOT NULL
AND review_score IS NOT NULL

GROUP BY payment_method, delivery_status
ORDER BY payment_method, delivery_status
""").df()

print("\nSATISFACTION BY DELIVERY STATUS")
print(satisfaction.to_string(index=False))

con.close()
