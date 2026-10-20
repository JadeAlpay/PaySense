
-- Aggregate reviews to one row per order

SELECT
    order_id,
    COUNT(*) AS review_count,
    AVG(review_score) AS review_score

FROM {{ ref('stg_reviews') }}

GROUP BY order_id
