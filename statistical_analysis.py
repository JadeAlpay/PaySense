
import duckdb
import numpy as np
from scipy.stats import norm

con = duckdb.connect("paysense.duckdb")

data = con.execute("""
    SELECT
        a.payment_method,
        COUNT(*) AS reviewed_orders,
        COUNT(*) FILTER (
            WHERE a.review_score <= 2
        ) AS low_ratings
    FROM order_analysis a
    JOIN orders o ON a.order_id = o.order_id
    WHERE o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp < '2018-08-01'
      AND a.payment_method IN ('voucher', 'credit_card')
      AND a.review_score IS NOT NULL
    GROUP BY a.payment_method
""").df().set_index("payment_method")

v = data.loc["voucher"]
c = data.loc["credit_card"]

n1, x1 = int(v["reviewed_orders"]), int(v["low_ratings"])
n2, x2 = int(c["reviewed_orders"]), int(c["low_ratings"])

p1 = x1 / n1
p2 = x2 / n2
difference = p1 - p2

# Two-proportion z-test (null: equal proportions)
pooled = (x1 + x2) / (n1 + n2)
se_null = np.sqrt(
    pooled * (1 - pooled) * (1/n1 + 1/n2)
)

z = difference / se_null
p_value = 2 * norm.sf(abs(z))

# Unadjusted Wald confidence interval for difference
se_diff = np.sqrt(
    p1 * (1-p1)/n1 + p2 * (1-p2)/n2
)

ci_low = difference - 1.96 * se_diff
ci_high = difference + 1.96 * se_diff

print("\nSTATISTICAL ANALYSIS")
print(f"Voucher low-rating rate: {p1:.2%}")
print(f"Credit-card low-rating rate: {p2:.2%}")
print(f"Difference: {difference*100:.2f} pp")
print(f"Z-statistic: {z:.3f}")
print(f"P-value: {p_value:.4f}")
print(
    f"95% CI for difference: "
    f"[{ci_low*100:.2f}, {ci_high*100:.2f}] pp"
)

if p_value < 0.05:
    print("\nResult: Statistically significant at 5%.")
else:
    print("\nResult: Not statistically significant at 5%.")

con.close()
