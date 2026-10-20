
from pathlib import Path

import duckdb
import pandas as pd
import numpy as np


# Project folder
ROOT = Path(__file__).resolve().parents[1]

OLD_DB = ROOT / "paysense.duckdb"
NEW_DB = ROOT / "paysense_analytics.duckdb"


def load_data(database, query):
    """Run SQL and return a Pandas DataFrame."""
    with duckdb.connect(
        str(database),
        read_only=True
    ) as con:
        return con.execute(query).df()


old = load_data(
    OLD_DB,
    """
    SELECT
        order_id,
        payment_method,
        total_payment,
        review_score,
        days_late
    FROM order_analysis
    """
)

new = load_data(
    NEW_DB,
    """
    SELECT
        order_id,
        payment_method,
        total_payment,
        review_score,
        days_late
    FROM main.fct_order_experience
    """
)


# Rename columns so we can compare them
old = old.add_suffix("_old")
new = new.add_suffix("_new")

# Restore the common join key
old = old.rename(columns={"order_id_old": "order_id"})
new = new.rename(columns={"order_id_new": "order_id"})

# Join both datasets using order ID
comparison = old.merge(
    new,
    on="order_id",
    how="outer",
    indicator=True,
    validate="one_to_one"
)

print("\nPAYSENSE DATA RECONCILIATION")
print("=" * 45)

print("\nORDER COVERAGE")
print(comparison["_merge"].value_counts().to_string())

# Compare categorical payment methods
both = comparison[comparison["_merge"] == "both"].copy()

payment_matches = (
    both["payment_method_old"].fillna("__MISSING__")
    == both["payment_method_new"].fillna("__MISSING__")
)

# Compare numerical columns, treating paired nulls
# as equal and allowing minor floating-point differences.
def numeric_matches(column):
    return np.isclose(
        pd.to_numeric(
            both[f"{column}_old"], errors="coerce"
        ).to_numpy(dtype=float),
        pd.to_numeric(
            both[f"{column}_new"], errors="coerce"
        ).to_numpy(dtype=float),
        rtol=0,
        atol=1e-6,
        equal_nan=True
    )


print("\nFIELD-LEVEL VALIDATION")

checks = {
    "Payment method": payment_matches,
    "Total payment": numeric_matches("total_payment"),
    "Review score": numeric_matches("review_score"),
    "Days late": numeric_matches("days_late")
}

for label, matches in checks.items():
    passed = int(np.sum(matches))
    failed = len(matches) - passed

    print(
        f"{label}: {passed:,} matched, "
        f"{failed:,} mismatched"
    )

print("\nRECONCILIATION COMPLETE")
