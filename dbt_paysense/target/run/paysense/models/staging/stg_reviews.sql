
  
  create view "paysense_analytics"."main"."stg_reviews__dbt_tmp" as (
    -- PaySense: Clean customer reviews
-- One row per review record

SELECT
    review_id,
    order_id,
    CAST(review_score AS INTEGER)
        AS review_score,
    CAST(review_creation_date AS TIMESTAMP)
        AS review_created_at,
    CAST(review_answer_timestamp AS TIMESTAMP)
        AS review_answered_at

FROM read_csv_auto(
    '../data/raw/olist_order_reviews_dataset.csv'
)
  );
