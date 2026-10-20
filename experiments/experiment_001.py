
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import (
    confint_proportions_2indep,
    proportion_effectsize,
    proportions_ztest,
)

# ----------------------------------
# 1. Experiment configuration
# ----------------------------------

SEED = 42
CONTROL_RATE = 0.30
TREATMENT_RATE = 0.25

ALPHA = 0.05
POWER = 0.80

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(SEED)

# ----------------------------------
# 2. Required sample size
# ----------------------------------

effect_size = abs(
    proportion_effectsize(
        CONTROL_RATE,
        TREATMENT_RATE
    )
)

power_analysis = NormalIndPower()

n_per_group = int(np.ceil(
    power_analysis.solve_power(
        effect_size=effect_size,
        alpha=ALPHA,
        power=POWER,
        ratio=1.0,
        alternative="two-sided"
    )
))

print("\nEXPERIMENT DESIGN")
print("Assumed control rate:", f"{CONTROL_RATE:.1%}")
print("Target treatment rate:", f"{TREATMENT_RATE:.1%}")
print("Power:", f"{POWER:.0%}")
print("Significance level:", ALPHA)
print("Required participants per group:", n_per_group)
print("Total participants:", n_per_group * 2)

# ----------------------------------
# 3. Generate a simulated experiment
# ----------------------------------

n_total = n_per_group * 2

# Exact 50/50 assignment, shuffled randomly
assignment = np.array(
    ["control"] * n_per_group
    + ["treatment"] * n_per_group
)
rng.shuffle(assignment)

# Simulated outcome:
# 1 = low rating, 0 = not low rating
probabilities = np.where(
    assignment == "control",
    CONTROL_RATE,
    TREATMENT_RATE
)

low_rating = rng.binomial(1, probabilities)

experiment = pd.DataFrame({
    "customer_id": np.arange(1, n_total + 1),
    "group": assignment,
    "low_rating": low_rating
})

experiment.to_csv(
    RESULTS_DIR / "experiment_001_customers.csv",
    index=False
)

# ----------------------------------
# 4. Summarise outcomes
# ----------------------------------

summary = (
    experiment.groupby("group")
    .agg(
        participants=("customer_id", "count"),
        low_ratings=("low_rating", "sum"),
        low_rating_rate=("low_rating", "mean")
    )
    .reset_index()
)

summary.to_csv(
    RESULTS_DIR / "experiment_001_summary.csv",
    index=False
)

print("\nEXPERIMENT RESULTS")
print(summary.to_string(index=False))

control = summary.set_index("group").loc["control"]
treatment = summary.set_index("group").loc["treatment"]

n_control = int(control["participants"])
n_treatment = int(treatment["participants"])

x_control = int(control["low_ratings"])
x_treatment = int(treatment["low_ratings"])

p_control = x_control / n_control
p_treatment = x_treatment / n_treatment

# Negative = improvement in treatment
difference = p_treatment - p_control

# ----------------------------------
# 5. Statistical hypothesis test
# ----------------------------------

z_stat, p_value = proportions_ztest(
    count=[x_treatment, x_control],
    nobs=[n_treatment, n_control],
    alternative="two-sided"
)

ci_lower, ci_upper = confint_proportions_2indep(
    count1=x_treatment,
    nobs1=n_treatment,
    count2=x_control,
    nobs2=n_control,
    compare="diff",
    method="newcomb",
    alpha=ALPHA
)

# Allocation sanity check
allocation_p = binomtest(
    n_treatment,
    n_total,
    p=0.5
).pvalue

print("\nSTATISTICAL TEST")
print(f"Control rate: {p_control:.2%}")
print(f"Treatment rate: {p_treatment:.2%}")
print(f"Difference: {difference * 100:.2f} pp")
print(f"Z-statistic: {z_stat:.3f}")
print(f"P-value: {p_value:.4f}")
print(
    "95% CI: "
    f"[{ci_lower * 100:.2f}, "
    f"{ci_upper * 100:.2f}] pp"
)
print(f"Allocation check p-value: {allocation_p:.4f}")

if ci_upper < 0:
    conclusion = "Evidence of a reduction in low ratings."
elif ci_lower > 0:
    conclusion = "Evidence of an increase in low ratings."
else:
    conclusion = "Inconclusive treatment effect."

print("\nINTERPRETATION")
print(conclusion)
print(
    "SIMULATED DATA ONLY. "
    "This is not evidence of a real product improvement."
)

# ----------------------------------
# 6. Save metrics for the dashboard
# ----------------------------------

metrics = pd.DataFrame([{
    "experiment_id": "EXP-001",
    "data_type": "SIMULATED",
    "seed": SEED,
    "control_rate": p_control,
    "treatment_rate": p_treatment,
    "effect_pp": difference * 100,
    "ci_lower_pp": ci_lower * 100,
    "ci_upper_pp": ci_upper * 100,
    "p_value": p_value,
    "n_control": n_control,
    "n_treatment": n_treatment,
    "conclusion": conclusion
}])

metrics.to_csv(
    RESULTS_DIR / "experiment_001_metrics.csv",
    index=False
)

print("\nResults saved to:", RESULTS_DIR)
