# PaySense — Data Dictionary

## Source tables

- **Orders:** `olist_orders_dataset.csv`; source order identifier, customer identifier, status, purchase, approval, actual delivery and estimated delivery timestamps.
- **Payments:** `olist_order_payments_dataset.csv`; payment-level rows, including sequence, type, instalments and BRL amount. **Not one row per order.**
- **Reviews:** `olist_order_reviews_dataset.csv`; review-level rows including review ID, order ID, score and timestamps. **Not guaranteed to be one row per order.**

## dbt staging models

| Model | Grain | Key fields |
| --- | --- | --- |
| `stg_orders` | one row per order | `order_id`, `customer_id`, `order_status`, `purchased_at`, `approved_at`, `delivered_at`, `estimated_delivery_at` |
| `stg_payments` | one row per payment record | `order_id`, `payment_sequence`, `payment_method`, `installments`, `payment_amount` |
| `stg_reviews` | one row per review record | `review_id`, `order_id`, `review_score`, `review_created_at`, `review_answered_at` |

## dbt intermediate models

**`int_order_payments`** (one row per order):

- `payment_count`: number of payment records.
- `total_payment`: sum of `payment_amount` (BRL).
- `payment_method`: method if one payment record; `multiple` if more than one record.
- `max_installments`: maximum instalment count among payment records.

**`int_order_reviews`** (one row per order):

- `review_count`: number of review records.
- `review_score`: arithmetic mean of available review scores for an order.

## Final model: `fct_order_experience`

**Grain:** exactly one row per order, including orders without review or payment data.

| Column | Meaning |
| --- | --- |
| `order_id` | Unique identifier for each order |
| `customer_id` | Customer identifier in Olist data |
| `order_status` | Status such as delivered or canceled |
| `purchased_at` | Purchase timestamp |
| `approved_at` | Recorded payment approval timestamp (nullable) |
| `delivered_at` | Actual delivery timestamp (nullable) |
| `estimated_delivery_at` | Estimated delivery timestamp |
| `payment_method` | Single payment method, `multiple`, or null |
| `payment_count` | Number of payment rows attached to order |
| `total_payment` | Total payments summed over rows (BRL) |
| `max_installments` | Largest instalment count attached to order |
| `review_score` | Mean recorded review score for order; null if unreviewed |
| `review_count` | Count of review records, null when none were joined |
| `low_rating` | True when mean score <= 2; false when reviewed and > 2; null if unreviewed |
| `days_late` | DuckDB `DATE_DIFF('day', estimated_delivery_date, actual_delivery_date)`; negative is early, positive is late |
| `late_delivery` | True when actual delivery calendar date exceeds estimated delivery date; null if missing date |

**Important implementation nuance:** The main Streamlit loader calculates `late_delivery` as `days_late > 0`, which is aligned with the date-based definition. Review and payment nulls are excluded by relevant dashboard filters rather than filled with zero.

## Monthly mart: `mart_product_kpis`

**Grain:** one row per purchase month, January 2017–July 2018.

**Eligible population:** delivered orders with recorded review score, delivery delay and payment total.

| Column | Definition |
| --- | --- |
| `order_month` | Calendar month of purchase |
| `total_orders` | Count of eligible orders |
| `avg_review_score` | Average order-level review score |
| `low_rating_pct` | Percent of eligible orders with average review score <= 2 |
| `late_delivery_pct` | Percent of eligible orders with `days_late > 0` |
| `avg_order_value` | Mean summed order payment (BRL) |

**Aggregation caution:** Overall percentages must be weighted by `total_orders`, not computed as an unweighted mean of 19 monthly percentages. In the validated baseline, the simple monthly average low-rating rate was **12.39%**, while the overall order-weighted rate was **12.99%**.
