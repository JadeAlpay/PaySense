"""Monthly product KPIs from the validated dbt mart."""
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = Path(__file__).resolve().parents[1] / "paysense_analytics.duckdb"


def render_dbt_kpis():
    st.header("Product KPIs")
    st.caption(
        "Monthly customer-experience metrics | "
        "January 2017–July 2018 | Delivered, reviewed orders"
    )

    if not DB_PATH.exists():
        st.error("Analytics database not found. Run the dbt pipeline first.")
        return

    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        df = con.execute("""
            SELECT *
            FROM main.mart_product_kpis
            ORDER BY order_month
        """).df()

    if df.empty:
        st.warning("No KPI data available.")
        return

    df["order_month"] = pd.to_datetime(df["order_month"])
    total_orders = int(df["total_orders"].sum())
    if total_orders == 0:
        st.warning("No orders available for these KPIs.")
        return

    # Weighted results: every order contributes equally to overall KPIs.
    low_rating_rate = (df["low_rating_pct"] * df["total_orders"]).sum() / total_orders
    late_delivery_rate = (df["late_delivery_pct"] * df["total_orders"]).sum() / total_orders
    avg_order_value = (df["avg_order_value"] * df["total_orders"]).sum() / total_orders

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Orders", f"{total_orders:,}")
    c2.metric("Low ratings", f"{low_rating_rate:.1f}%")
    c3.metric("Late deliveries", f"{late_delivery_rate:.1f}%")
    c4.metric("Avg. order value", f"R${avg_order_value:,.1f}")

    st.subheader("Monthly Customer Experience")
    plot_df = df.rename(columns={
        "low_rating_pct": "Low ratings",
        "late_delivery_pct": "Late deliveries",
    })
    fig = px.line(
        plot_df,
        x="order_month",
        y=["Low ratings", "Late deliveries"],
        markers=True,
        labels={"order_month": "Purchase month", "value": "Rate (%)", "variable": "Metric"},
        template="plotly_white",
    )
    fig.update_traces(hovertemplate="%{y:.1f}%<extra>%{fullData.name}</extra>")
    fig.update_layout(
        legend_title_text="Metric",
        hovermode="x unified",
        yaxis_tickformat=".1f",
        margin=dict(l=10, r=10, t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Explore the monthly data"):
        shown = df.rename(columns={
            "order_month": "Month",
            "total_orders": "Orders",
            "avg_review_score": "Avg. review",
            "low_rating_pct": "Low ratings (%)",
            "late_delivery_pct": "Late deliveries (%)",
            "avg_order_value": "Avg. order value (BRL)",
        })
        st.dataframe(
            shown.style.format({
                "Month": "{:%b %Y}",
                "Orders": "{:,.0f}",
                "Avg. review": "{:.1f}",
                "Low ratings (%)": "{:.1f}",
                "Late deliveries (%)": "{:.1f}",
                "Avg. order value (BRL)": "{:,.1f}",
            }),
            hide_index=True,
            use_container_width=True,
        )

    st.caption(
        "Overall rates are weighted by order counts. "
        "Historical associations do not establish causation."
    )