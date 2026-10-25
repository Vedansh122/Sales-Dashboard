import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from data_utils import (
    load_uploaded_file, profile_data, preprocess_data,
    statistical_summary, detect_sales_columns
)

st.set_page_config(
    page_title="Sales Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 Sales Analysis Dashboard")
st.caption("Upload, validate, clean, explore, and visualize sales data.")

with st.sidebar:
    st.header("Data")
    uploaded_file = st.file_uploader(
        "Upload a dataset",
        type=["csv", "xlsx", "json"],
        help="Supported formats: CSV, Excel (.xlsx), and JSON."
    )
    st.divider()
    st.caption("You can also explore the included sample dataset after uploading it.")

if uploaded_file is None:
    st.info("Upload a CSV, XLSX, or JSON file to begin.")
    st.markdown("""
    **Expected sales columns for all five KPIs**
    - Order ID
    - Sales
    - Profit
    - Quantity

    Column matching is case-insensitive. If your file uses different names, the
    dashboard will ask you to map the required fields.
    """)
    st.stop()

try:
    raw_df = load_uploaded_file(uploaded_file)
except Exception as exc:
    st.error(f"Could not read this file: {exc}")
    st.stop()

if raw_df.empty:
    st.error("The uploaded file has no rows. Please upload a non-empty dataset.")
    st.stop()

st.subheader("1. Data validation")
profile = profile_data(raw_df)
a, b, c, d = st.columns(4)
a.metric("Rows", f"{profile['rows']:,}")
b.metric("Columns", f"{profile['columns']:,}")
c.metric("Duplicate records", f"{profile['duplicate_rows']:,}")
d.metric("Cells with missing values", f"{profile['missing_cells']:,}")

with st.expander("Column names and data types", expanded=True):
    st.dataframe(profile["column_profile"], use_container_width=True, hide_index=True)

with st.expander("Preview uploaded data"):
    st.dataframe(raw_df.head(20), use_container_width=True)

st.subheader("2. Preprocessing")
with st.expander("Choose cleaning options", expanded=True):
    left, right = st.columns(2)
    with left:
        missing_strategy = st.selectbox(
            "Handle missing values",
            ["Keep as-is", "Drop rows with missing values", "Fill numeric with median and text with mode"],
            index=2
        )
    with right:
        duplicate_strategy = st.selectbox(
            "Handle duplicate records",
            ["Keep duplicates", "Remove exact duplicate rows"],
            index=1
        )
    normalize_text = st.checkbox("Trim extra spaces in text columns", value=True)
    parse_dates = st.checkbox("Convert likely date columns to dates", value=True)

try:
    df = preprocess_data(
        raw_df,
        missing_strategy=missing_strategy,
        duplicate_strategy=duplicate_strategy,
        normalize_text=normalize_text,
        parse_dates=parse_dates,
    )
except Exception as exc:
    st.error(f"Preprocessing failed: {exc}")
    st.stop()

st.success(f"Preprocessing complete: {len(raw_df):,} original rows → {len(df):,} rows.")
if df.empty:
    st.warning("No records remain after preprocessing. Change the cleaning options.")
    st.stop()

st.subheader("3. Map sales fields")
mapping_options = list(df.columns)
defaults = detect_sales_columns(df)
map1, map2, map3, map4 = st.columns(4)

def mapping_select(label, suggested, key):
    index = mapping_options.index(suggested) if suggested in mapping_options else 0
    return st.selectbox(label, mapping_options, index=index, key=key)

with map1:
    order_col = mapping_select("Order ID column", defaults.get("order_id"), "order_col")
with map2:
    sales_col = mapping_select("Sales column", defaults.get("sales"), "sales_col")
with map3:
    profit_col = mapping_select("Profit column", defaults.get("profit"), "profit_col")
with map4:
    quantity_col = mapping_select("Quantity column", defaults.get("quantity"), "quantity_col")

# Numeric conversion is performed on selected KPI columns; invalid values become missing.
for col in [sales_col, profit_col, quantity_col]:
    df[col] = pd.to_numeric(
        df[col].astype(str).str.replace(",", "", regex=False).str.replace("$", "", regex=False),
        errors="coerce"
    ).replace([np.inf, -np.inf], np.nan)

valid_kpi = df[[sales_col, profit_col, quantity_col]].notna().all(axis=1)
if not valid_kpi.all():
    st.warning(f"{int((~valid_kpi).sum())} row(s) have invalid or missing values in selected numeric KPI fields. They are excluded from KPI calculations and charts.")
analysis_df = df.loc[valid_kpi].copy()
if analysis_df.empty:
    st.error("The selected Sales, Profit, and Quantity columns do not contain usable numeric data.")
    st.stop()

st.subheader("4. Interactive filters")
filter_cols = st.columns(3)
filter_columns = [c for c in ["Region", "Category", "Segment", "Ship Mode", "State", "City", "Country"] if c in analysis_df.columns]
if filter_columns:
    selected_filters = {}
    for i, col in enumerate(filter_columns[:6]):
        with filter_cols[i % 3]:
            values = sorted(analysis_df[col].dropna().astype(str).unique().tolist())
            selected_filters[col] = st.multiselect(f"Filter by {col}", values, default=values, key=f"filter_{col}")
    for col, values in selected_filters.items():
        analysis_df = analysis_df[analysis_df[col].astype(str).isin(values)]
else:
    st.info("No common categorical fields were detected, so category filters are unavailable.")

date_col_candidates = [c for c in analysis_df.columns if "date" in str(c).lower() and pd.api.types.is_datetime64_any_dtype(analysis_df[c])]
if date_col_candidates:
    chosen_date_col = st.selectbox("Date range column", date_col_candidates)
    dates = analysis_df[chosen_date_col].dropna()
    if not dates.empty:
        date_range = st.date_input(
            "Select date range",
            value=(dates.min().date(), dates.max().date()),
            min_value=dates.min().date(),
            max_value=dates.max().date(),
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            analysis_df = analysis_df[
                analysis_df[chosen_date_col].notna()
                & (analysis_df[chosen_date_col].dt.date >= start_date)
                & (analysis_df[chosen_date_col].dt.date <= end_date)
            ]

if analysis_df.empty:
    st.warning("No records match the selected filters. Change or clear the filters.")
    st.stop()

total_sales = analysis_df[sales_col].sum()
total_profit = analysis_df[profit_col].sum()
total_orders = analysis_df[order_col].nunique(dropna=True)
total_quantity = analysis_df[quantity_col].sum()
profit_margin = (total_profit / total_sales * 100) if total_sales else 0.0

st.subheader("5. Key performance indicators")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Sales", f"${total_sales:,.2f}")
k2.metric("Total Profit", f"${total_profit:,.2f}")
k3.metric("Total Orders", f"{total_orders:,}")
k4.metric("Total Quantity Sold", f"{total_quantity:,.0f}")
k5.metric("Profit Margin", f"{profit_margin:.2f}%")

st.subheader("6. Interactive visualizations")
chart1, chart2 = st.columns(2)

if "Category" in analysis_df.columns:
    category_summary = analysis_df.groupby("Category", dropna=False).agg(
        Sales=(sales_col, "sum"), Profit=(profit_col, "sum")
    ).reset_index()
    with chart1:
        fig = px.bar(category_summary, x="Category", y=["Sales", "Profit"],
                     barmode="group", title="Sales and Profit by Category",
                     labels={"value": "Amount", "variable": "Metric"})
        st.plotly_chart(fig, use_container_width=True)
else:
    with chart1:
        st.info("A Category column is needed for the category chart.")

if "Region" in analysis_df.columns:
    region_summary = analysis_df.groupby("Region", dropna=False).agg(
        Sales=(sales_col, "sum")
    ).reset_index()
    with chart2:
        fig = px.pie(region_summary, names="Region", values="Sales",
                     title="Sales Share by Region", hole=0.35)
        st.plotly_chart(fig, use_container_width=True)
else:
    with chart2:
        st.info("A Region column is needed for the region chart.")

date_cols = [c for c in analysis_df.columns if "date" in str(c).lower() and pd.api.types.is_datetime64_any_dtype(analysis_df[c])]
if date_cols:
    date_choice = st.selectbox("Trend date column", date_cols, key="trend_date")
    trend = analysis_df.dropna(subset=[date_choice]).copy()
    if not trend.empty:
        trend["Period"] = trend[date_choice].dt.to_period("M").astype(str)
        trend_summary = trend.groupby("Period", as_index=False).agg(
            Sales=(sales_col, "sum"), Profit=(profit_col, "sum")
        )
        fig = px.line(trend_summary, x="Period", y=["Sales", "Profit"],
                      markers=True, title="Monthly Sales and Profit Trend",
                      labels={"value": "Amount", "variable": "Metric"})
        st.plotly_chart(fig, use_container_width=True)
else:
    # Fallback visualization for datasets without a recognized date column.
    numeric_cols = analysis_df.select_dtypes(include="number").columns.tolist()
    if len(numeric_cols) >= 2:
        fig = px.scatter(analysis_df, x=sales_col, y=profit_col,
                         size=quantity_col, title="Sales vs Profit (bubble size = quantity)")
        st.plotly_chart(fig, use_container_width=True)

st.subheader("7. Statistical summary")
summary = statistical_summary(analysis_df, numeric_columns=[sales_col, profit_col, quantity_col])
st.dataframe(summary, use_container_width=True)

st.subheader("8. Filtered data")
st.caption(f"Showing {len(analysis_df):,} records after cleaning and filters.")
st.dataframe(analysis_df, use_container_width=True, hide_index=True)
csv_bytes = analysis_df.to_csv(index=False).encode("utf-8")
st.download_button("Download filtered data as CSV", data=csv_bytes,
                   file_name="filtered_sales_data.csv", mime="text/csv")
