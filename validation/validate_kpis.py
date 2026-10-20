
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

SOURCES = {
    "Original": (
        ROOT / "paysense.duckdb",
        "order_analysis"
    ),
    "dbt": (
        ROOT / "paysense_analytics.duckdb",
        "main.fct_order_experience"
    )
}

results = []

for source, (database, table) in SOURCES.items():
    with duckdb.connect(
        str(database),
        read_only=True
    ) as con:

        # Attach the original orders table if necessary
        if source == "Original":
            query = """
        SELECT
            COUNT(*) AS orders,
            COUNT(a.review_score) AS reviewed_orders,

            ROUND(AVG(a.review_score), 4)
                AS avg_review_score,

            ROUND(
                100.0 * AVG(
                    CASE WHEN a.review_score <= 2
                        THEN 1.0 ELSE 0.0 END
                ), 4
            ) AS low_rating_pct,

            ROUND(
                100.0 * AVG(
                    CASE WHEN a.days_late > 0
                        THEN 1.0 ELSE 0.0 END
                ), 4
            ) AS late_delivery_pct,

            ROUND(AVG(a.total_payment), 4)
                AS avg_order_value

        FROM order_analysis AS a

        INNER JOIN orders AS o
            ON a.order_id = o.order_id

        WHERE o.order_purchase_timestamp >= '2017-01-01'
          AND o.order_purchase_timestamp < '2018-08-01'
          AND a.order_status = 'delivered'
          AND a.review_score IS NOT NULL
          AND a.days_late IS NOT NULL
          AND a.total_payment IS NOT NULL
    """
            ""
        else:
            query = f"""
                SELECT
                    COUNT(*) AS orders,
                    COUNT(review_score) AS reviewed_orders,
                    ROUND(AVG(review_score), 4)
                        AS avg_review_score,
                    ROUND(
                        100.0 * AVG(
                            CASE WHEN review_score <= 2
                                THEN 1.0 ELSE 0.0 END
                        ), 4
                    ) AS low_rating_pct,
                    ROUND(
                        100.0 * AVG(
                            CASE WHEN days_late > 0
                                THEN 1.0 ELSE 0.0 END
                        ), 4
                    ) AS late_delivery_pct,
                    ROUND(AVG(total_payment), 4)
                        AS avg_order_value
                FROM {table}
                WHERE purchased_at >= '2017-01-01'
                  AND purchased_at < '2018-08-01'
                  AND order_status = 'delivered'
                  AND review_score IS NOT NULL
                  AND days_late IS NOT NULL
                  AND total_payment IS NOT NULL
            """

        df = con.execute(query).df()
        df.insert(0, "source", source)
        results.append(df)

comparison = pd.concat(
    results,
    ignore_index=True
)

print("\nPAY SENSE KPI VALIDATION")
print(comparison.to_string(index=False))

old = comparison.iloc[0]
new = comparison.iloc[1]

print("\nKPI COMPARISON")

for column in comparison.columns[1:]:
    matches = abs(
        float(old[column]) - float(new[column])
    ) < 0.0001

    status = "PASS" if matches else "MISMATCH"

    print(f"{column}: {status}")
