
import duckdb
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

con = duckdb.connect("paysense.duckdb")

# Use the baseline period and delivered orders
df = con.execute("""
SELECT
    a.payment_method,
    a.review_score,
    a.total_payment,
    a.days_late
FROM order_analysis a
JOIN orders o ON a.order_id = o.order_id
WHERE o.order_purchase_timestamp >= '2017-01-01'
  AND o.order_purchase_timestamp < '2018-08-01'
  AND a.order_status = 'delivered'
  AND a.review_score IS NOT NULL
  AND a.days_late IS NOT NULL
  AND a.total_payment >= 0
  AND a.payment_method IN (
      'credit_card', 'voucher', 'boleto',
      'debit_card', 'multiple'
  )
""").df()

con.close()

# Create variables
df["low_rating"] = (df["review_score"] <= 2).astype(int)
df["late_delivery"] = (df["days_late"] > 0).astype(int)
df["log_order_value"] = np.log1p(df["total_payment"])

print("\nMODEL DATA")
print("Orders analysed:", len(df))
print("Low ratings:", df["low_rating"].sum())

# Logistic regression
# Credit card is the reference payment method
model = smf.logit(
    formula="""
        low_rating ~
        late_delivery +
        log_order_value +
        C(payment_method, Treatment(reference="credit_card"))
    """,
    data=df
).fit(disp=False)

# Convert coefficients into odds ratios
results = pd.DataFrame({
    "odds_ratio": np.exp(model.params),
    "ci_lower": np.exp(model.conf_int()[0]),
    "ci_upper": np.exp(model.conf_int()[1]),
    "p_value": model.pvalues
})

print("\nLOGISTIC REGRESSION RESULTS")
print(results.round(4).to_string())

print("\nMODEL CONVERGED:", model.mle_retvals["converged"])
