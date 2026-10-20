
-- PaySense: Clean payment records
-- One row per payment record, not per order

SELECT
    order_id,
    CAST(payment_sequential AS INTEGER)
        AS payment_sequence,
    LOWER(TRIM(payment_type))
        AS payment_method,
    CAST(payment_installments AS INTEGER)
        AS installments,
    CAST(payment_value AS DOUBLE)
        AS payment_amount

FROM read_csv_auto(
    '../data/raw/olist_order_payments_dataset.csv'
)
