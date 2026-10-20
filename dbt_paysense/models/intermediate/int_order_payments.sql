
-- Aggregate payments to one row per order

SELECT
    order_id,
    COUNT(*) AS payment_count,
    SUM(payment_amount) AS total_payment,

    CASE
        WHEN COUNT(*) = 1
            THEN MAX(payment_method)
        ELSE 'multiple'
    END AS payment_method,

    MAX(installments) AS max_installments

FROM {{ ref('stg_payments') }}

GROUP BY order_id
