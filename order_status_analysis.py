
import duckdb

con = duckdb.connect("paysense.duckdb")

# 1. Compare order statuses across payment methods
status = con.execute("""
SELECT
    payment_method,
    order_status,
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
WHERE payment_method IN ('credit_card', 'voucher')
GROUP BY payment_method, order_status
ORDER BY payment_method, total_orders DESC
""").df()

print("\nORDER STATUS BY PAYMENT METHOD")
print(status.to_string(index=False))


# 2. Compare orders with and without delivery dates
delivery_missing = con.execute("""
SELECT
    payment_method,

    CASE
        WHEN delivery_date IS NULL
        THEN 'No delivery date'
        ELSE 'Has delivery date'
    END AS delivery_record,

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
WHERE payment_method IN ('credit_card', 'voucher')
GROUP BY payment_method, delivery_record
ORDER BY payment_method, delivery_record
""").df()

print("\nSATISFACTION BY DELIVERY RECORD")
print(delivery_missing.to_string(index=False))

con.close()
