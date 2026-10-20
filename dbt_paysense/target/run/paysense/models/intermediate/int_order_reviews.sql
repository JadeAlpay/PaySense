
  
  create view "paysense_analytics"."main"."int_order_reviews__dbt_tmp" as (
    -- Aggregate reviews to one row per order

SELECT
    order_id,
    COUNT(*) AS review_count,
    AVG(review_score) AS review_score

FROM "paysense_analytics"."main"."stg_reviews"

GROUP BY order_id
  );
