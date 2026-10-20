
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st


DB_PATH = (
    Path(__file__).resolve().parents[1]
    / "paysense_analytics.duckdb"
)


def render_dbt_kpis():
    st.header("dbt-Powered Product KPIs")

    st.caption(
        "Source: mart_product_kpis | "
        "Baseline: Jan 2017–Jul 2018 | "
        "Delivered, reviewed orders"
    )

    if not DB_PATH.exists():
        st.error(
            "Analytics database not found. "
            "Run the dbt pipeline first."
        )
        return

    with duckdb.connect(
        str(DB_PATH),
        read_only=True
    ) as con:
        df = con.execute("""
            SELECT *
            FROM main.mart_product_kpis
            ORDER BY order_month
        """).df()

    if df.empty:
        st.warning("No KPI data available.")
        return

    df["order_month"] = pd.to_datetime(
        df["order_month"]
    )

    total_orders = int(df["total_orders"].sum())

    low_rating_rate = (
        df["low_rating_pct"]
        .mul(df["total_orders"])
        .sum()
        / total_orders
    )

    late_delivery_rate = (
        df["late_delivery_pct"]
        .mul(df["total_orders"])
        .sum()
        / total_orders
    )

    avg_order_value = (
        df["avg_order_value"]
        .mul(df["total_orders"])
        .sum()
        / total_orders
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Orders", f"{total_orders:,}")
    col2.metric("Low ratings", f"{low_rating_rate:.2f}%")
    col3.metric("Late deliveries", f"{late_delivery_rate:.2f}%")
    col4.metric("Avg. order value", f"R${avg_order_value:,.2f}")

    st.subheader("Monthly Customer Experience")

    fig = px.line(
        df,
        x="order_month",
        y=["low_rating_pct", "late_delivery_pct"],
        labels={
            "order_month": "Purchase month",
            "value": "Rate (%)",
            "variable": "KPI"
        }
    )

    fig.update_layout(
        template="plotly_white",
        legend_title_text="Metric",
        hovermode="x unified"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    with st.expander("Explore the monthly data"):
        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True
        )

    st.caption(
        "Overall rates are weighted by monthly order counts. "
        "These are observational metrics, not causal effects."
    )
