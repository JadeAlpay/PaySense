
-- PaySense: Staging model for orders

SELECT
    order_id,
    customer_id,
    order_status,

    CAST(
        order_purchase_timestamp AS TIMESTAMP
    ) AS purchased_at,

    CAST(
        order_approved_at AS TIMESTAMP
    ) AS approved_at,

    CAST(
        order_delivered_customer_date AS TIMESTAMP
    ) AS delivered_at,

    CAST(
        order_estimated_delivery_date AS TIMESTAMP
    ) AS estimated_delivery_at

FROM read_csv_auto(
    '../data/raw/olist_orders_dataset.csv'
)
