from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dbt_kpis import render_dbt_kpis

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="PaySense | Product Analytics",
    page_icon="💳",
    layout="wide",
)

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
    .stApp {
        background-color: #F6F8FB;
        color: #0F172A;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E5E7EB;
    }

    h1, h2, h3, h4 {
        color: #0F172A;
        letter-spacing: -0.02em;
    }

    .hero-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        color: white;
        padding: 1.4rem 1.5rem;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 1rem;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
    }

    .hero-subtitle {
        font-size: 0.95rem;
        color: rgba(255,255,255,0.82);
        margin-top: 0.4rem;
    }

    .metric-card {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 18px;
        padding: 1rem 1.1rem;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
        min-height: 115px;
    }

    .metric-label {
        font-size: 0.9rem;
        color: #64748B;
        margin-bottom: 0.4rem;
    }

    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.1;
    }

    .metric-caption {
        margin-top: 0.45rem;
        font-size: 0.82rem;
        color: #94A3B8;
    }

    .section-card {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 18px;
        padding: 1rem 1rem 0.5rem 1rem;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
        margin-bottom: 1rem;
    }

    .insight-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-left: 4px solid #2563EB;
        border-radius: 16px;
        padding: 1rem 1rem;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
        margin-bottom: 0.8rem;
    }

    .insight-title {
        font-size: 0.9rem;
        color: #64748B;
        margin-bottom: 0.35rem;
    }

    .insight-body {
        font-size: 1rem;
        color: #0F172A;
        line-height: 1.45;
    }

    .small-note {
        color: #64748B;
        font-size: 0.84rem;
    }

    div[data-testid="stMetric"] {
        background: white;
        border-radius: 16px;
        padding: 0.5rem;
        border: 1px solid #E5E7EB;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Constants
# -----------------------------
# Original database (keep during migration)
DB_PATH = Path(__file__).resolve().parents[1] / "paysense.duckdb"

# New validated dbt database
DBT_DB_PATH = Path(__file__).resolve().parents[1] / "paysense_analytics.duckdb"

PAYMENT_LABELS = {
    "credit_card": "Credit card",
    "boleto": "Boleto",
    "voucher": "Voucher",
    "debit_card": "Debit card",
    "multiple": "Multiple",
}

PAYMENT_ORDER = ["credit_card", "boleto", "debit_card", "multiple", "voucher"]

DELAY_ORDER = [
    "On time / early",
    "1–3 days late",
    "4–7 days late",
    "8–14 days late",
    "Over 14 days late",
]

PRIMARY = "#2563EB"
NAVY = "#0F172A"
TEAL = "#14B8A6"
SLATE = "#64748B"
RED = "#DC2626"
AMBER = "#F59E0B"

# -----------------------------
# Helpers
# -----------------------------
@st.cache_data
def load_data():
    # Main dashboard reads from the reconciled dbt fact table.
    con = duckdb.connect(str(DBT_DB_PATH), read_only=True)
    try:
        df = con.execute("""
            SELECT
                order_id,
                payment_method,
                order_status,
                review_score,
                total_payment,
                days_late,
                CAST(purchased_at AS DATE) AS purchase_date
            FROM main.fct_order_experience
            WHERE purchased_at >= '2017-01-01'
              AND purchased_at < '2018-08-01'
              AND order_status = 'delivered'
              AND review_score IS NOT NULL
              AND days_late IS NOT NULL
              AND payment_method IN (
                  'credit_card', 'boleto', 'voucher',
                  'debit_card', 'multiple'
              )
        """).df()
    finally:
        con.close()

    df["purchase_date"] = pd.to_datetime(df["purchase_date"])
    df["month"] = df["purchase_date"].dt.to_period("M").dt.to_timestamp()
    df["low_rating"] = (df["review_score"] <= 2).astype(int)
    df["late_delivery"] = (df["days_late"] > 0).astype(int)
    df["payment_label"] = df["payment_method"].map(PAYMENT_LABELS)
    df["log_order_value"] = np.log1p(df["total_payment"])

    def bucket_delay(days):
        if days <= 0:
            return "On time / early"
        elif days <= 3:
            return "1–3 days late"
        elif days <= 7:
            return "4–7 days late"
        elif days <= 14:
            return "8–14 days late"
        return "Over 14 days late"

    df["delay_group"] = df["days_late"].apply(bucket_delay)
    return df


def metric_card(label, value, caption):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_open(title, subtitle=None):
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def section_close():
    st.markdown("</div>", unsafe_allow_html=True)


def fmt_pct(x):
    return f"{x:.2f}%"


# -----------------------------
# Load + filters
# -----------------------------
df = load_data()

st.markdown("""
<div class="hero-card">
    <h1 style="margin:0;">PaySense</h1>
    <div class="hero-subtitle">
        Payment & customer experience analytics • Wise-style product analysis on real e-commerce data
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.title("PaySense")
st.sidebar.caption("Filters & controls")

min_date = df["purchase_date"].min().date()
max_date = df["purchase_date"].max().date()

date_range = st.sidebar.date_input(
    "Purchase date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

selected_methods = st.sidebar.multiselect(
    "Payment methods",
    options=PAYMENT_ORDER,
    default=PAYMENT_ORDER,
    format_func=lambda x: PAYMENT_LABELS[x],
)

min_value, max_value = float(df["total_payment"].min()), float(df["total_payment"].max())
value_range = st.sidebar.slider(
    "Order value range (BRL)",
    min_value=float(np.floor(min_value)),
    max_value=float(np.ceil(max_value)),
    value=(float(np.floor(min_value)), float(np.ceil(max_value))),
)

filtered = df[
    (df["purchase_date"].dt.date >= start_date)
    & (df["purchase_date"].dt.date <= end_date)
    & (df["payment_method"].isin(selected_methods))
    & (df["total_payment"] >= value_range[0])
    & (df["total_payment"] <= value_range[1])
].copy()

if filtered.empty:
    st.warning("No data matches the selected filters.")
    st.stop()

# -----------------------------
# KPI calculations
# -----------------------------
orders = len(filtered)
avg_rating = filtered["review_score"].mean()
low_rate = 100 * filtered["low_rating"].mean()
late_rate = 100 * filtered["late_delivery"].mean()
avg_order_value = filtered["total_payment"].mean()

low_count = int(filtered["low_rating"].sum())
late_count = int(filtered["late_delivery"].sum())

# -----------------------------
# KPI row
# -----------------------------
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    metric_card("Orders analysed", f"{orders:,}", "Delivered, reviewed orders")
with k2:
    metric_card("Average rating", f"{avg_rating:.2f}/5", "Mean review score")
with k3:
    metric_card("Low-rating rate", f"{low_rate:.2f}%", f"{low_count:,} orders rated 1–2")
with k4:
    metric_card("Late-delivery rate", f"{late_rate:.2f}%", f"{late_count:,} delayed deliveries")
with k5:
    metric_card("Avg order value", f"R${avg_order_value:,.2f}", "Average order payment")

st.markdown("")

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview",
    "Delivery Experience",
    "Payment Experience",
    "Insights",
    "Experimentation"
]
)

# -----------------------------
# Overview
# -----------------------------
with tab1:
    col_left, col_right = st.columns([1.65, 1])

    with col_left:
        section_open(
            "Monthly KPI trends",
            "Track satisfaction, delivery performance and order volume over time.",
        )

        trend = (
            filtered.groupby("month")
            .agg(
                orders=("order_id", "count"),
                avg_rating=("review_score", "mean"),
                low_rating_pct=("low_rating", lambda s: 100 * s.mean()),
                late_delivery_pct=("late_delivery", lambda s: 100 * s.mean()),
            )
            .reset_index()
        )

        metric_choice = st.radio(
            "Trend metric",
            ["Low-rating rate", "Late-delivery rate", "Average rating", "Order volume"],
            horizontal=True,
        )

        y_col_map = {
            "Low-rating rate": "low_rating_pct",
            "Late-delivery rate": "late_delivery_pct",
            "Average rating": "avg_rating",
            "Order volume": "orders",
        }

        color_map = {
            "Low-rating rate": RED,
            "Late-delivery rate": AMBER,
            "Average rating": PRIMARY,
            "Order volume": TEAL,
        }

        y_col = y_col_map[metric_choice]
        fig_trend = px.line(
            trend,
            x="month",
            y=y_col,
            markers=True,
            template="plotly_white",
        )
        fig_trend.update_traces(line_color=color_map[metric_choice], line_width=3, marker_size=7)
        fig_trend.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis_title="",
            yaxis_title="",
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        section_close()

    with col_right:
        section_open(
            "Top line product signals",
            "A quick summary of where customer pain is most visible."
        )

        delay_summary = (
            filtered.groupby("delay_group")
            .agg(
                orders=("order_id", "count"),
                low_ratings=("low_rating", "sum"),
                low_rating_pct=("low_rating", lambda s: 100 * s.mean()),
            )
            .reindex(DELAY_ORDER)
            .dropna()
            .reset_index()
        )

        worst_delay_row = delay_summary.sort_values("low_rating_pct", ascending=False).iloc[0]
        biggest_volume_row = delay_summary.sort_values("low_ratings", ascending=False).iloc[0]

        st.markdown(
            f"""
            <div class="insight-card">
                <div class="insight-title">Highest-risk delay segment</div>
                <div class="insight-body">
                    <b>{worst_delay_row['delay_group']}</b> has a
                    <b>{worst_delay_row['low_rating_pct']:.1f}% low-rating rate</b>.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="insight-card">
                <div class="insight-title">Largest source of negative experiences</div>
                <div class="insight-body">
                    <b>{biggest_volume_row['delay_group']}</b> contributes
                    <b>{int(biggest_volume_row['low_ratings']):,} low-rated orders</b>.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        payment_summary = (
            filtered.groupby("payment_method")
            .agg(
                orders=("order_id", "count"),
                low_rating_pct=("low_rating", lambda s: 100 * s.mean()),
            )
            .reset_index()
        )
        worst_payment = payment_summary.sort_values("low_rating_pct", ascending=False).iloc[0]

        st.markdown(
            f"""
            <div class="insight-card">
                <div class="insight-title">Highest low-rating payment segment</div>
                <div class="insight-body">
                    <b>{PAYMENT_LABELS[worst_payment['payment_method']]}</b> shows
                    <b>{worst_payment['low_rating_pct']:.1f}% low ratings</b>
                    in the current filter selection.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption(
            "These summaries are descriptive and reflect the selected filters. "
            "They do not establish causation."
        )
        section_close()

    lower_left, lower_right = st.columns(2)

    with lower_left:
        section_open(
            "Where low-rated orders come from",
            "This helps separate high-risk segments from high-volume segments."
        )

        source_fig = px.pie(
            delay_summary,
            names="delay_group",
            values="low_ratings",
            hole=0.58,
            template="plotly_white",
        )
        source_fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
        )
        st.plotly_chart(source_fig, use_container_width=True)
        section_close()

    with lower_right:
        section_open(
            "Order distribution by payment method",
            "Shows which payment methods dominate customer traffic."
        )

        pay_counts = (
            filtered.groupby("payment_label")
            .size()
            .reset_index(name="orders")
            .sort_values("orders", ascending=False)
        )

        fig_pay_mix = px.bar(
            pay_counts,
            x="payment_label",
            y="orders",
            text="orders",
            template="plotly_white",
            color_discrete_sequence=[PRIMARY],
        )
        fig_pay_mix.update_traces(textposition="outside")
        fig_pay_mix.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="",
            yaxis_title="",
        )
        st.plotly_chart(fig_pay_mix, use_container_width=True)
        section_close()

# -----------------------------
# Delivery Experience
# -----------------------------
with tab2:
    section_open(
        "Delivery delays & customer satisfaction",
        "Delivery performance is the strongest observed correlate of dissatisfaction in the project."
    )

    delay_summary = (
        filtered.groupby("delay_group")
        .agg(
            orders=("order_id", "count"),
            avg_rating=("review_score", "mean"),
            low_ratings=("low_rating", "sum"),
            low_rating_pct=("low_rating", lambda s: 100 * s.mean()),
        )
        .reindex(DELAY_ORDER)
        .dropna()
        .reset_index()
    )

    c1, c2 = st.columns(2)

    with c1:
        fig_delay_rate = px.bar(
            delay_summary,
            x="delay_group",
            y="low_rating_pct",
            text="low_rating_pct",
            template="plotly_white",
            color_discrete_sequence=[RED],
        )
        fig_delay_rate.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_delay_rate.update_layout(
            title="Low-rating rate by delay length",
            xaxis_title="",
            yaxis_title="Low-rating rate (%)",
            yaxis_range=[0, 100],
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig_delay_rate, use_container_width=True)

    with c2:
        fig_delay_volume = px.bar(
            delay_summary,
            x="delay_group",
            y="low_ratings",
            text="low_ratings",
            template="plotly_white",
            color_discrete_sequence=[AMBER],
        )
        fig_delay_volume.update_traces(textposition="outside")
        fig_delay_volume.update_layout(
            title="Number of low-rated orders by delay length",
            xaxis_title="",
            yaxis_title="Low-rated orders",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig_delay_volume, use_container_width=True)

    st.dataframe(
        delay_summary.rename(
            columns={
                "delay_group": "Delay group",
                "orders": "Orders",
                "avg_rating": "Average rating",
                "low_ratings": "Low-rated orders",
                "low_rating_pct": "Low-rating rate (%)",
            }
        ).round(2),
        use_container_width=True,
        hide_index=True,
    )
    section_close()

    section_open(
        "Interpretation",
        "Focus on what a product manager should do with the analysis."
    )

    st.markdown("""
- **On-time / early deliveries** still generate the largest absolute number of low-rated orders because they represent most order volume.
- **Late deliveries** create a much higher risk of dissatisfaction per customer.
- The most important product question is not only *“Which customers are unhappy?”* but also *“Where can intervention prevent the greatest amount of dissatisfaction?”*
- A realistic next step would be to test whether **proactive delay communication** reduces negative reviews among customers at risk of delayed delivery.
    """)
    section_close()

# -----------------------------
# Payment Experience
# -----------------------------
with tab3:
    section_open(
        "Payment experience",
        "Compare order volume, satisfaction and average value across payment methods."
    )

    payment_summary = (
        filtered.groupby(["payment_method", "payment_label"])
        .agg(
            orders=("order_id", "count"),
            avg_rating=("review_score", "mean"),
            low_rating_pct=("low_rating", lambda s: 100 * s.mean()),
            avg_order_value=("total_payment", "mean"),
            late_delivery_pct=("late_delivery", lambda s: 100 * s.mean()),
        )
        .reset_index()
    )

    payment_summary["payment_method"] = pd.Categorical(
        payment_summary["payment_method"],
        categories=PAYMENT_ORDER,
        ordered=True
    )
    payment_summary = payment_summary.sort_values("payment_method")

    left, right = st.columns(2)

    with left:
        fig_payment = px.bar(
            payment_summary,
            x="payment_label",
            y="low_rating_pct",
            text="low_rating_pct",
            template="plotly_white",
            color_discrete_sequence=[PRIMARY],
        )
        fig_payment.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_payment.update_layout(
            title="Low-rating rate by payment method",
            xaxis_title="",
            yaxis_title="Low-rating rate (%)",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig_payment, use_container_width=True)

    with right:
        fig_value = px.bar(
            payment_summary,
            x="payment_label",
            y="avg_order_value",
            text="avg_order_value",
            template="plotly_white",
            color_discrete_sequence=[TEAL],
        )
        fig_value.update_traces(texttemplate="R$%{text:.0f}", textposition="outside")
        fig_value.update_layout(
            title="Average order value by payment method",
            xaxis_title="",
            yaxis_title="Average order value (BRL)",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig_value, use_container_width=True)

    display_table = payment_summary[[
        "payment_label", "orders", "avg_rating",
        "low_rating_pct", "late_delivery_pct", "avg_order_value"
    ]].rename(columns={
        "payment_label": "Payment method",
        "orders": "Orders",
        "avg_rating": "Average rating",
        "low_rating_pct": "Low-rating rate (%)",
        "late_delivery_pct": "Late-delivery rate (%)",
        "avg_order_value": "Avg order value (BRL)",
    }).round(2)

    st.dataframe(display_table, use_container_width=True, hide_index=True)

    st.caption(
        "Earlier analysis showed that a late-period voucher anomaly distorted some initial conclusions. "
        "This dashboard uses a baseline analysis window (Jan 2017–Jul 2018) to support more stable comparisons."
    )
    section_close()

# -----------------------------
# Insights
# -----------------------------
  
with tab4:
    st.header("Product Intelligence")
    st.caption(
        "Statistical evidence, data quality and product decisions"
    )

    insights_tab, quality_tab = st.tabs([
        "📊 Statistical Insights",
        "🛡️ Data Quality Monitor"
    ])

    # ==========================================
    # UPGRADE 1: REGRESSION RESULTS
    # ==========================================
    with insights_tab:

        st.subheader("What predicts customer dissatisfaction?")

        st.info(
            "This statistical model covers 89,230 delivered and "
            "reviewed orders from Jan 2017 to Jul 2018. "
            "It is a fixed historical analysis and does not "
            "update with the dashboard's sidebar filters."
        )

        c1, c2, c3 = st.columns(3)

        c1.metric("Orders analysed", "89,230")
        c2.metric("Low-rated orders", "11,588")
        c3.metric("Model status", "Converged")

        st.markdown("### Adjusted odds ratios")

        # Results from your actual logistic regression
        regression = pd.DataFrame({
            "factor": [
                "Late delivery",
                "Voucher",
                "Order value (log scale)",
                "Multiple payments",
                "Debit card",
                "Boleto"
            ],
            "odds_ratio": [
                16.9128, 1.2757, 1.2440,
                1.0634, 0.9674, 0.9572
            ],
            "ci_lower": [
                15.9630, 1.0510, 1.2119,
                0.9401, 0.7985, 0.9064
            ],
            "ci_upper": [
                17.9191, 1.5486, 1.2770,
                1.2028, 1.1721, 1.0109
            ],
            "p_value": [
                0.0000, 0.0138, 0.0000,
                0.3286, 0.7350, 0.1163
            ]
        })

        regression["significant"] = (
            (regression["ci_lower"] > 1) |
            (regression["ci_upper"] < 1)
        )

        regression = regression.sort_values(
            "odds_ratio", ascending=True
        )

        colors = [
            TEAL if significant else SLATE
            for significant in regression["significant"]
        ]

        fig_reg = go.Figure()

        fig_reg.add_trace(go.Scatter(
            x=regression["odds_ratio"],
            y=regression["factor"],
            mode="markers",
            marker=dict(
                size=12,
                color=colors
            ),
            error_x=dict(
                type="data",
                symmetric=False,
                array=(
                    regression["ci_upper"]
                    - regression["odds_ratio"]
                ),
                arrayminus=(
                    regression["odds_ratio"]
                    - regression["ci_lower"]
                ),
                color=SLATE,
                thickness=2,
                width=5
            ),
            customdata=regression[
                ["ci_lower", "ci_upper", "p_value"]
            ].to_numpy(),
            hovertemplate=(
                "<b>%{y}</b>"
                "<br>Odds ratio: %{x:.2f}"
                "<br>95% CI: %{customdata[0]:.2f}"
                "–%{customdata[1]:.2f}"
                "<br>p-value: %{customdata[2]:.4f}"
                "<extra></extra>"
            )
        ))

        fig_reg.add_vline(
            x=1,
            line_dash="dash",
            line_color=SLATE,
            annotation_text="No difference"
        )

        fig_reg.update_layout(
            template="plotly_white",
            title="Odds of receiving a low customer rating",
            xaxis=dict(
                title="Adjusted odds ratio (log scale)",
                type="log",
                range=[-0.12, 1.4],
                tickvals=[1, 2, 5, 10, 20],
                ticktext=["1×", "2×", "5×", "10×", "20×"]
            ),
            yaxis_title="",
            height=410,
            margin=dict(l=10, r=20, t=65, b=30),
            showlegend=False
        )

        st.plotly_chart(
            fig_reg,
            use_container_width=True
        )

        st.caption(
            "Points represent odds ratios; horizontal lines "
            "show 95% confidence intervals. Teal indicates "
            "intervals excluding 1. Payment methods are "
            "compared with credit cards. The model adjusts "
            "for the displayed variables."
        )

        st.markdown("### Key analytical findings")

        a, b = st.columns(2)

        with a:
            st.success(
                "**Late delivery: OR 16.91**\n\n"
                "Late deliveries have approximately 16.9 "
                "times the odds of a low rating, holding "
                "payment method and order value constant.\n\n"
                "95% CI: 15.96–17.92."
            )

        with b:
            st.info(
                "**Voucher: OR 1.28**\n\n"
                "Voucher-only orders show approximately "
                "28% higher adjusted odds of a low rating "
                "than credit-card-only orders.\n\n"
                "95% CI: 1.05–1.55."
            )

        st.warning(
            "**Interpretation:** These are associations, "
            "not causal effects. Odds ratios are not the same "
            "as probability ratios. Order value is represented "
            "by log(1 + BRL amount), and additional unmeasured "
            "factors may influence satisfaction."
        )

        st.markdown("### Recommended product experiment")

        st.markdown("""
**Hypothesis:** Proactive delivery-delay notifications may
reduce customer dissatisfaction.

**Control:** Standard order-tracking experience.

**Treatment:** Proactive notifications with updated
delivery estimates and a support link.

**Primary KPI:** Low-rating rate among all randomised
customers identified as at risk of delay before treatment.

**Guardrails:** Support contact rate, complaint rate,
notification opt-outs and delivery completion.

**Decision:** Launch only if the experiment shows a
meaningful improvement without unacceptable guardrail
deterioration.
        """)

    # ==========================================
    # UPGRADE 2: DATA QUALITY MONITOR
    # ==========================================
    with quality_tab:

        st.subheader("Payment anomaly investigation")

        st.info(
            "This section queries the original dataset, "
            "including excluded months. It does not follow "
            "the dashboard's sidebar filters."
        )

        @st.cache_data
        def load_anomaly_data():
            con = duckdb.connect(
                str(DB_PATH), read_only=True
            )

            try:
                cancellation = con.execute("""
                    SELECT
                        a.payment_method,

                        COUNT(*) AS total_orders,

                        COUNT(*) FILTER (
                            WHERE a.order_status = 'canceled'
                        ) AS canceled_orders,

                        COUNT(*) FILTER (
                            WHERE o.order_purchase_timestamp >=
                                '2017-01-01'
                              AND o.order_purchase_timestamp <
                                '2018-08-01'
                        ) AS baseline_orders,

                        COUNT(*) FILTER (
                            WHERE a.order_status = 'canceled'
                              AND o.order_purchase_timestamp >=
                                '2017-01-01'
                              AND o.order_purchase_timestamp <
                                '2018-08-01'
                        ) AS baseline_canceled

                    FROM order_analysis a
                    JOIN orders o
                        ON a.order_id = o.order_id

                    WHERE a.payment_method IN (
                        'credit_card', 'voucher'
                    )

                    GROUP BY a.payment_method
                """).df()

                approval = con.execute("""
                    SELECT
                        a.payment_method,

                        COUNT(*) AS canceled_orders,

                        COUNT(*) FILTER (
                            WHERE o.order_approved_at IS NULL
                        ) AS missing_approval

                    FROM order_analysis a
                    JOIN orders o
                        ON a.order_id = o.order_id

                    WHERE a.order_status = 'canceled'
                      AND o.order_purchase_timestamp >=
                          '2018-08-01'
                      AND o.order_purchase_timestamp <
                          '2018-09-01'
                      AND a.payment_method IN (
                          'credit_card', 'voucher'
                      )

                    GROUP BY a.payment_method
                """).df()

                monthly = con.execute("""
                    SELECT
                        DATE_TRUNC(
                            'month',
                            CAST(
                                order_purchase_timestamp
                                AS TIMESTAMP
                            )
                        ) AS month,

                        COUNT(*) AS total_orders,

                        COUNT(*) FILTER (
                            WHERE order_status = 'delivered'
                        ) AS delivered,

                        COUNT(*) FILTER (
                            WHERE order_status = 'canceled'
                        ) AS canceled

                    FROM orders

                    WHERE order_purchase_timestamp >=
                        '2018-06-01'

                    GROUP BY 1
                    ORDER BY 1
                """).df()

                return cancellation, approval, monthly

            finally:
                con.close()

        cancellation, approval, monthly = load_anomaly_data()

        cancellation["full_rate"] = (
            100 * cancellation["canceled_orders"]
            / cancellation["total_orders"]
        )

        cancellation["baseline_rate"] = (
            100 * cancellation["baseline_canceled"]
            / cancellation["baseline_orders"]
        )

        voucher = cancellation[
            cancellation["payment_method"] == "voucher"
        ].iloc[0]

        card = cancellation[
            cancellation["payment_method"] == "credit_card"
        ].iloc[0]

        m1, m2, m3 = st.columns(3)

        m1.metric(
            "Voucher cancellation · Full",
            f"{voucher['full_rate']:.2f}%"
        )

        m2.metric(
            "Voucher cancellation · Baseline",
            f"{voucher['baseline_rate']:.2f}%"
        )

        m3.metric(
            "Card cancellation · Baseline",
            f"{card['baseline_rate']:.2f}%"
        )

        st.markdown("### Effect of the analysis window")

        comparison = cancellation.melt(
            id_vars="payment_method",
            value_vars=["full_rate", "baseline_rate"],
            var_name="period",
            value_name="cancellation_rate"
        )

        comparison["period"] = comparison["period"].map({
            "full_rate": "Full dataset",
            "baseline_rate": "Baseline period"
        })

        comparison["payment_method"] = (
            comparison["payment_method"].map(
                PAYMENT_LABELS
            )
        )

        fig_cancel = px.bar(
            comparison,
            x="payment_method",
            y="cancellation_rate",
            color="period",
            barmode="group",
            text="cancellation_rate",
            color_discrete_map={
                "Full dataset": RED,
                "Baseline period": TEAL
            },
            template="plotly_white",
            labels={
                "payment_method": "Payment method",
                "cancellation_rate": "Cancellation rate (%)",
                "period": "Period"
            }
        )

        fig_cancel.update_traces(
            texttemplate="%{text:.2f}%",
            textposition="outside"
        )

        fig_cancel.update_layout(
            height=380,
            margin=dict(l=10, r=10, t=20, b=30)
        )

        st.plotly_chart(
            fig_cancel,
            use_container_width=True
        )

        st.caption(
            "Baseline: Jan 2017–Jul 2018. "
            "Full dataset: all available observations. "
            "Different observation windows can change "
            "apparent payment-method performance."
        )

        st.markdown("### August 2018 approval anomaly")

        approval["missing_approval_pct"] = (
            100 * approval["missing_approval"]
            / approval["canceled_orders"]
        )

        st.dataframe(
            approval.rename(columns={
                "payment_method": "Payment method",
                "canceled_orders": "Cancelled orders",
                "missing_approval": "Missing approvals",
                "missing_approval_pct": "Missing (%)"
            }).round(2),
            hide_index=True,
            use_container_width=True
        )

        st.warning(
            "In August 2018, all 51 cancelled voucher-only "
            "orders lacked recorded approval timestamps, "
            "compared with 0 of 24 cancelled credit-card-only "
            "orders. Missing timestamps do not prove "
            "payment authorisation failure."
        )

        st.markdown("### Dataset coverage over time")

        monthly["month"] = pd.to_datetime(monthly["month"])

        fig_coverage = px.bar(
            monthly,
            x="month",
            y=["delivered", "canceled"],
            barmode="stack",
            color_discrete_map={
                "delivered": TEAL,
                "canceled": RED
            },
            labels={
                "value": "Number of orders",
                "month": "Purchase month",
                "variable": "Order status"
            },
            template="plotly_white"
        )

        fig_coverage.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=20, b=30)
        )

        st.plotly_chart(
            fig_coverage,
            use_container_width=True
        )

        st.caption(
            "This chart displays delivered and cancelled "
            "orders. Other order statuses are not shown."
        )

        st.markdown("### Data quality assessment")

        st.markdown("""
**Observed issues**

- Voucher cancellations increase sharply in August 2018.
- September and October contain very few orders.
- Cancelled voucher orders disproportionately lack recorded approval timestamps.
- The original payment-method comparison is sensitive to the selected analysis period.

**Analytical decision**

Use January 2017–July 2018 as the primary
comparison period while retaining the full
dataset for sensitivity analysis.

**Important limitation**

The dataset does not establish why voucher orders
were cancelled. The excluded period is anomalous,
not necessarily erroneous.

**Product implication**

Do not prioritise a voucher payment redesign solely
on the original cancellation statistics.
Investigate payment-processing records and
operational causes before proposing an intervention.
        """)

# ======================================
# EXPERIMENTATION — EXP-001
# ======================================

with tab5:
    st.header("Product Experimentation")
    st.caption(
        "EXP-001 | Proactive Delivery Notifications"
    )

    st.warning(
        "SIMULATED EXPERIMENT — These results demonstrate "
        "statistical methodology, not real customer impact."
    )

    results_path = (
        Path(__file__).resolve().parents[1]
        / "experiments"
        / "results"
    )

    metrics_file = (
        results_path / "experiment_001_metrics.csv"
    )

    summary_file = (
        results_path / "experiment_001_summary.csv"
    )

    if not metrics_file.exists() or not summary_file.exists():
        st.error(
            "Experiment results not found. Run: "
            "python experiments/experiment_001.py"
        )
    else:
        metrics = pd.read_csv(metrics_file).iloc[0]
        summary = pd.read_csv(summary_file)

        control = summary.loc[
            summary["group"] == "control"
        ].iloc[0]

        treatment = summary.loc[
            summary["group"] == "treatment"
        ].iloc[0]

        st.subheader("Experiment performance")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Control low-rating rate",
            f"{metrics['control_rate']:.2%}"
        )

        c2.metric(
            "Treatment low-rating rate",
            f"{metrics['treatment_rate']:.2%}"
        )

        c3.metric(
            "Absolute difference",
            f"{metrics['effect_pp']:+.2f} pp"
        )

        c4.metric(
            "P-value",
            f"{metrics['p_value']:.4f}"
        )

        st.divider()

        st.subheader("Control vs Treatment")

        summary["low_rating_pct"] = (
            summary["low_rating_rate"] * 100
        )

        fig = px.bar(
            summary,
            x="group",
            y="low_rating_pct",
            color="group",
            text="low_rating_pct",
            color_discrete_map={
                "control": SLATE,
                "treatment": TEAL
            },
            template="plotly_white",
        )

        fig.update_traces(
            texttemplate="%{text:.2f}%",
            textposition="outside"
        )

        fig.update_layout(
            yaxis_title="Low-rating rate (%)",
            xaxis_title="",
            yaxis_range=[0, 40],
            showlegend=False,
            height=400
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.subheader("Statistical evidence")

        st.write(
            f"**Observed treatment effect:** "
            f"{metrics['effect_pp']:+.2f} percentage points"
        )

        st.write(
            f"**95% confidence interval:** "
            f"[{metrics['ci_lower_pp']:.2f}, "
            f"{metrics['ci_upper_pp']:.2f}] pp"
        )

        st.write(
            f"**Two-sided p-value:** "
            f"{metrics['p_value']:.4f}"
        )

        st.write(
            f"**Sample size:** "
            f"{int(metrics['n_control']):,} control + "
            f"{int(metrics['n_treatment']):,} treatment"
        )

        st.info(str(metrics["conclusion"]))

        st.divider()

        st.subheader("Product decision")

        st.markdown("""

**Hypothesis**

Proactive delivery-delay notifications may reduce
negative customer experiences.

**Experiment design**

- Control: Standard order tracking
- Treatment: Proactive delay warning and revised ETA
- Primary outcome: Low-rating rate
- Assignment: Randomised 50/50

**Interpretation**

The simulated experiment produced a statistically
significant reduction in low ratings.

However, the data was generated with an assumed
treatment effect. No real product intervention
has been evaluated.

**Recommended next step**

Validate a delay-risk trigger, determine how reviews
will be collected consistently, and design a real
randomised controlled experiment.

**Decision**

Proceed to real-world experiment planning.
Do not recommend product rollout based on
simulated results alone.
        """)

        st.caption(
            "Experiment results are fixed and independent "
            "of the observational dashboard filters."
        )
# dbt-powered product KPIs
st.divider()
render_dbt_kpis()

st.markdown("---")
st.markdown(
    '<div class="small-note">PaySense uses the Olist public e-commerce dataset as a proxy product environment. '
    'All results shown are based on delivered, reviewed historical orders within the selected analysis window.</div>',
    unsafe_allow_html=True,
)
