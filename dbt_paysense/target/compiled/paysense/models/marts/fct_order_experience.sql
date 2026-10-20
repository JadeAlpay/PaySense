-- Final analytical model
-- Grain: exactly one row per order

SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.purchased_at,
    o.approved_at,
    o.delivered_at,
    o.estimated_delivery_at,

    p.payment_method,
    p.payment_count,
    p.total_payment,
    p.max_installments,

    r.review_score,
    r.review_count,

    CASE
        WHEN r.review_score <= 2 THEN TRUE
        WHEN r.review_score IS NOT NULL THEN FALSE
        ELSE NULL
    END AS low_rating,

    CASE
        WHEN o.delivered_at IS NOT NULL
         AND o.estimated_delivery_at IS NOT NULL
        THEN DATE_DIFF(
            'day',
            CAST(o.estimated_delivery_at AS DATE),
            CAST(o.delivered_at AS DATE)
        )
        ELSE NULL
    END AS days_late,

    CASE
        WHEN o.delivered_at IS NOT NULL
         AND o.estimated_delivery_at IS NOT NULL
        THEN CAST(o.delivered_at AS DATE)
             > CAST(o.estimated_delivery_at AS DATE)
        ELSE NULL
    END AS late_delivery

FROM "paysense_analytics"."main"."stg_orders" o

LEFT JOIN "paysense_analytics"."main"."int_order_payments" p
    ON o.order_id = p.order_id

LEFT JOIN "paysense_analytics"."main"."int_order_reviews" r
    ON o.order_id = r.order_id