
import duckdb

con = duckdb.connect("paysense.duckdb")

results = con.execute("""
WITH delivery_groups AS (
    SELECT
        a.order_id,
        a.review_score,
        a.days_late,

        CASE
            WHEN a.days_late <= 0
                THEN '0. On time or early'
            WHEN a.days_late BETWEEN 1 AND 3
                THEN '1. 1-3 days late'
            WHEN a.days_late BETWEEN 4 AND 7
                THEN '2. 4-7 days late'
            WHEN a.days_late BETWEEN 8 AND 14
                THEN '3. 8-14 days late'
            ELSE '4. Over 14 days late'
        END AS delay_group

    FROM order_analysis a
    JOIN orders o ON a.order_id = o.order_id

    WHERE o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp < '2018-08-01'
      AND a.order_status = 'delivered'
      AND a.review_score IS NOT NULL
      AND a.days_late IS NOT NULL
)

SELECT
    delay_group,
    COUNT(*) AS orders,
    ROUND(AVG(review_score), 2) AS avg_rating,

    COUNT(*) FILTER (
        WHERE review_score <= 2
    ) AS low_ratings,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE review_score <= 2
        ) / COUNT(*), 2
    ) AS low_rating_pct

FROM delivery_groups
GROUP BY delay_group
ORDER BY delay_group
""").df()

print("\nCUSTOMER SATISFACTION BY DELAY LENGTH")
print(results.to_string(index=False))

con.close()
