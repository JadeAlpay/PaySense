
-- PaySense: Monthly product KPI mart
-- Grain: one row per purchase month
-- Baseline: January 2017 through July 2018
-- Population: delivered orders with a review and
-- a recorded delivery date

WITH baseline AS (

    SELECT
        DATE_TRUNC('month', purchased_at)
            AS order_month,
        order_id,
        review_score,
        total_payment,
        days_late

    FROM {{ ref('fct_order_experience') }}

    WHERE purchased_at >= '2017-01-01'
      AND purchased_at < '2018-08-01'
      AND order_status = 'delivered'
      AND review_score IS NOT NULL
      AND days_late IS NOT NULL
      AND total_payment IS NOT NULL
),

monthly_kpis AS (

    SELECT
        order_month,

        COUNT(*) AS total_orders,

        AVG(review_score)
            AS avg_review_score,

        100.0 * AVG(
            CASE WHEN review_score <= 2
                THEN 1.0 ELSE 0.0 END
        ) AS low_rating_pct,

        100.0 * AVG(
            CASE WHEN days_late > 0
                THEN 1.0 ELSE 0.0 END
        ) AS late_delivery_pct,

        AVG(total_payment)
            AS avg_order_value

    FROM baseline
    GROUP BY order_month
)

SELECT *
FROM monthly_kpis
ORDER BY order_month
