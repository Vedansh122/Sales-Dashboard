import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from data_utils import (
    load_uploaded_file, profile_data, preprocess_data,
    statistical_summary, detect_sales_columns
)

st.set_page_config(
    page_title="SalesPulse | Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Design system ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

:root {
  --ink: #172033;
  --muted: #667085;
  --line: #e8edf4;
  --panel: #ffffff;
  --canvas: #f5f7fb;
  --accent: #635bff;
  --teal: #10a89a;
}
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: var(--canvas); color: var(--ink); }
.block-container { max-width: 1440px; padding-top: 1.6rem; padding-bottom: 3rem; }
[data-testid="stSidebar"] { background: #111827; border-right: 1px solid #202a3b; }
[data-testid="stSidebar"] * { color: #e5e7eb; }
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
  background: #1f2937; border: 1px dashed #64748b; border-radius: 14px;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
  color: #111827; background: #ffffff;
}
[data-testid="stSidebar"] hr { border-color: #374151; }
h1, h2, h3 { font-family: 'Manrope', sans-serif !important; letter-spacing: -0.035em; color: #172033; }
h1 { font-size: 2.25rem !important; font-weight: 800 !important; }
h2 { font-size: 1.35rem !important; font-weight: 750 !important; }
h3 { font-size: 1.05rem !important; font-weight: 700 !important; }
[data-testid="stMetric"] {
  background: var(--panel); border: 1px solid var(--line); border-radius: 18px;
  padding: 18px 20px; box-shadow: 0 4px 18px rgba(24, 39, 75, .035);
}
[data-testid="stMetricLabel"] { color: #667085 !important; font-size: .84rem !important; font-weight: 600 !important; }
[data-testid="stMetricValue"] { color: #172033 !important; font-family: 'Manrope', sans-serif; font-size: 1.65rem !important; font-weight: 800 !important; }
[data-testid="stMetricDelta"] { font-size: .78rem !important; }
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: #fff; border: 1px solid var(--line); border-radius: 18px;
  padding: 16px 18px; box-shadow: 0 4px 18px rgba(24, 39, 75, .025);
}
div[data-testid="stExpander"] { background: #fff; border: 1px solid var(--line); border-radius: 14px; }
.stButton > button, .stDownloadButton > button {
  border-radius: 10px; border: 1px solid #d8dcef; font-weight: 600;
}
.stButton > button[kind="primary"] { background: var(--accent); border-color: var(--accent); }
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
[data-testid="stPlotlyChart"] { background: #fff; border: 1px solid var(--line); border-radius: 16px; padding: 8px; }
[data-testid="stFileUploader"] { border-radius: 14px; }
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
  border-radius: 10px; border-color: #dce2ed;
}
div[data-testid="stAlert"] { border-radius: 12px; }
.hero {
  background: linear-gradient(120deg, #171f3b 0%, #39358b 58%, #635bff 100%);
  padding: 28px 32px; border-radius: 22px; color: white; margin: 0 0 24px 0;
  box-shadow: 0 12px 28px rgba(56, 53, 139, .16);
}
.hero .eyebrow { color: #c7d2fe; text-transform: uppercase; letter-spacing: .13em; font-size: .72rem; font-weight: 700; }
.hero h1 { color: #fff !important; margin: 7px 0 6px 0; font-size: 2.2rem !important; }
.hero p { color: #e0e7ff; margin: 0; font-size: .98rem; }
.section-label {
  color: #635bff; font-size: .72rem; font-weight: 800; letter-spacing: .12em;
  text-transform: uppercase; margin-bottom: 4px;
}
.small-muted { color: #667085; font-size: .87rem; }
.status-pill {
 display: inline-block; padding: 5px 10px; border-radius: 100px;
 background: #e7f8f4; color: #087f70; font-size: .75rem; font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

def section_heading(kicker, title, subtitle=None):
    st.markdown(f'<div class="section-label">{kicker}</div>', unsafe_allow_html=True)
    st.subheader(title)
    if subtitle:
        st.markdown(f'<div class="small-muted">{subtitle}</div>', unsafe_allow_html=True)

def money(value):
    return f"${value:,.2f}"

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("""
    <div style="padding:8px 4px 18px 4px">
      <div style="font-size:1.55rem;font-weight:800;font-family:Manrope,sans-serif;color:#fff">◈ SalesPulse</div>
      <div style="font-size:.78rem;color:#9ca3af;margin-top:3px">SALES INTELLIGENCE</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### Workspace")
    uploaded_file = st.file_uploader(
        "Import your dataset",
        type=["csv", "xlsx", "json"],
        help="Supported formats: CSV, Excel (.xlsx), JSON."
    )
    st.caption("CSV · XLSX · JSON")
    st.divider()
    st.markdown("### How to use")
    st.markdown("1. Upload a sales file\n2. Review data quality\n3. Choose cleaning options\n4. Filter and explore KPIs")
    st.divider()
    st.markdown('<div style="font-size:.75rem;color:#9ca3af">SALES PULSE · DATA WORKSPACE</div>', unsafe_allow_html=True)

# ---------- Welcome state ----------
if uploaded_file is None:
    st.markdown("""
    <div class="hero">
      <div class="eyebrow">Sales analytics workspace</div>
      <h1>Turn raw data into clear decisions.</h1>
      <p>Validate your dataset, clean inconsistencies, track business KPIs and explore interactive visual insights.</p>
    </div>
    """, unsafe_allow_html=True)
    section_heading("GET STARTED", "Your analytics, all in one place",
                    "Upload a CSV, Excel, or JSON file from the sidebar to open your dashboard.")
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.markdown("### ◫  Data quality")
            st.markdown("Inspect dataset size, column types, missing values, and duplicate records before analysis.")
    with col2:
        with st.container(border=True):
            st.markdown("### ⚙  Smart preprocessing")
            st.markdown("Handle missing values, remove duplicate rows, normalize text, and parse dates.")
    with col3:
        with st.container(border=True):
            st.markdown("### ↗  Performance insights")
            st.markdown("Track five sales KPIs and use interactive filters and charts to explore your data.")
    st.info("For the five sales KPIs, map columns for Order ID, Sales, Profit, and Quantity after uploading.")
    st.stop()

# ---------- Load and validate ----------
try:
    raw_df = load_uploaded_file(uploaded_file)
except Exception as exc:
    st.error(f"Unable to read this file. Check the format and try again. Details: {exc}")
    st.stop()

if raw_df.empty:
    st.error("This file contains no rows. Please upload a non-empty dataset.")
    st.stop()

st.markdown(f"""
<div class="hero">
  <div class="eyebrow">Overview / {uploaded_file.name}</div>
  <h1>Sales performance dashboard</h1>
  <p>Explore performance, understand data quality, and uncover patterns across your sales records.</p>
</div>
""", unsafe_allow_html=True)

profile = profile_data(raw_df)
section_heading("01 / DATA QUALITY", "Dataset health",
                "A quick overview of the uploaded file before cleaning.")
q1, q2, q3, q4 = st.columns(4)
q1.metric("Total records", f"{profile['rows']:,}")
q2.metric("Columns detected", f"{profile['columns']:,}")
q3.metric("Duplicate rows", f"{profile['duplicate_rows']:,}")
q4.metric("Missing cells", f"{profile['missing_cells']:,}")

with st.expander("View column profile and raw data preview", expanded=False):
    tab_profile, tab_preview = st.tabs(["Column profile", "Data preview"])
    with tab_profile:
        st.dataframe(profile["column_profile"], use_container_width=True, hide_index=True)
    with tab_preview:
        st.dataframe(raw_df.head(25), use_container_width=True, hide_index=True)

# ---------- Preprocessing ----------
section_heading("02 / PREPROCESSING", "Prepare your data",
                "Select cleaning rules. The dashboard recalculates from the original upload each time.")
with st.container(border=True):
    p1, p2 = st.columns(2)
    with p1:
        missing_strategy = st.selectbox(
            "Missing-value strategy",
            ["Fill numeric with median and text with mode", "Keep as-is", "Drop rows with missing values"],
            index=0
        )
        normalize_text = st.toggle("Trim spaces and normalize blank text", value=True)
    with p2:
        duplicate_strategy = st.selectbox(
            "Duplicate records",
            ["Remove exact duplicate rows", "Keep duplicates"],
            index=0
        )
        parse_dates = st.toggle("Parse likely date columns", value=True)

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

change = len(raw_df) - len(df)
st.success(f"Cleaning complete · {len(df):,} rows available · {max(change, 0):,} rows removed.")
if df.empty:
    st.warning("No rows remain after cleaning. Change the cleaning options.")
    st.stop()

# ---------- Field mapping ----------
section_heading("03 / FIELD MAPPING", "Connect your sales fields",
                "Suggested matches are selected automatically. Confirm the columns before reading the KPIs.")
mapping_options = list(df.columns)
defaults = detect_sales_columns(df)

def mapping_select(label, suggested, key):
    index = mapping_options.index(suggested) if suggested in mapping_options else 0
    return st.selectbox(label, mapping_options, index=index, key=key)

with st.container(border=True):
    map1, map2, map3, map4 = st.columns(4)
    with map1:
        order_col = mapping_select("Order ID", defaults.get("order_id"), "order_col")
    with map2:
        sales_col = mapping_select("Sales amount", defaults.get("sales"), "sales_col")
    with map3:
        profit_col = mapping_select("Profit amount", defaults.get("profit"), "profit_col")
    with map4:
        quantity_col = mapping_select("Quantity sold", defaults.get("quantity"), "quantity_col")

for col in [sales_col, profit_col, quantity_col]:
    df[col] = pd.to_numeric(
        df[col].astype(str).str.replace(",", "", regex=False).str.replace("$", "", regex=False),
        errors="coerce"
    ).replace([np.inf, -np.inf], np.nan)

valid_kpi = df[[order_col, sales_col, profit_col, quantity_col]].notna().all(axis=1)
if not valid_kpi.all():
    st.warning(f"{int((~valid_kpi).sum())} row(s) with missing or invalid KPI values will be excluded from KPI calculations.")
analysis_df = df.loc[valid_kpi].copy()
if analysis_df.empty:
    st.error("The selected fields do not contain enough valid data to calculate KPIs.")
    st.stop()

# ---------- Filters ----------
section_heading("04 / EXPLORE", "Filters",
                "Use the filters to focus every KPI and visualization on the records that matter.")
base_df = analysis_df.copy()
filter_columns = [c for c in ["Region", "Category", "Segment", "Ship Mode", "State", "City", "Country"] if c in base_df.columns]
with st.container(border=True):
    filter_cols = st.columns(3)
    selected_filters = {}
    if filter_columns:
        for i, col in enumerate(filter_columns[:6]):
            with filter_cols[i % 3]:
                values = sorted(base_df[col].dropna().astype(str).unique().tolist())
                selected_filters[col] = st.multiselect(
                    f"{col}", values, default=values, key=f"filter_{col}"
                )
        for col, values in selected_filters.items():
            analysis_df = analysis_df[analysis_df[col].astype(str).isin(values)]
    else:
        st.info("No common categorical fields were detected in this dataset.")

date_col_candidates = [
    c for c in analysis_df.columns
    if "date" in str(c).lower() and pd.api.types.is_datetime64_any_dtype(analysis_df[c])
]
if date_col_candidates:
    dc1, dc2 = st.columns([1, 2])
    with dc1:
        chosen_date_col = st.selectbox("Date field", date_col_candidates)
    dates = analysis_df[chosen_date_col].dropna()
    if not dates.empty:
        with dc2:
            date_range = st.date_input(
                "Date range",
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
    st.warning("No records match these filters. Clear one or more selections.")
    st.stop()

# ---------- KPI cards ----------
total_sales = analysis_df[sales_col].sum()
total_profit = analysis_df[profit_col].sum()
total_orders = analysis_df[order_col].nunique(dropna=True)
total_quantity = analysis_df[quantity_col].sum()
profit_margin = (total_profit / total_sales * 100) if total_sales else 0.0

section_heading("05 / PERFORMANCE", "Business at a glance",
                f"Calculated from {len(analysis_df):,} filtered records.")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total sales", money(total_sales), help="Sum of the selected sales column.")
k2.metric("Total profit", money(total_profit), help="Sum of the selected profit column.")
k3.metric("Total orders", f"{total_orders:,}", help="Count of unique Order IDs.")
k4.metric("Quantity sold", f"{total_quantity:,.0f}", help="Sum of the selected quantity column.")
k5.metric("Profit margin", f"{profit_margin:.2f}%", help="Total profit divided by total sales.")

# ---------- Charts ----------
section_heading("06 / VISUAL ANALYTICS", "Explore the numbers",
                "Hover over chart elements for details. Use the Plotly controls to zoom, pan, or save a chart.")
chart1, chart2 = st.columns(2)

if "Category" in analysis_df.columns:
    category_summary = analysis_df.groupby("Category", dropna=False).agg(
        Sales=(sales_col, "sum"), Profit=(profit_col, "sum")
    ).reset_index()
    fig = px.bar(
        category_summary, x="Category", y=["Sales", "Profit"], barmode="group",
        title="Sales & profit by category", labels={"value": "Amount", "variable": "Metric"},
        color_discrete_sequence=["#635bff", "#10a89a"]
    )
    fig.update_layout(template="plotly_white", margin=dict(l=16, r=16, t=58, b=16),
                      legend_title_text="", font=dict(family="DM Sans", color="#344054"))
    with chart1:
        st.plotly_chart(fig, use_container_width=True)
else:
    with chart1:
        st.info("A Category field is needed for this chart.")

if "Region" in analysis_df.columns:
    region_summary = analysis_df.groupby("Region", dropna=False).agg(Sales=(sales_col, "sum")).reset_index()
    fig = px.pie(
        region_summary, names="Region", values="Sales", hole=0.62,
        title="Sales mix by region", color_discrete_sequence=["#635bff", "#10a89a", "#f59e0b", "#f472b6", "#60a5fa"]
    )
    fig.update_traces(textposition="outside", textinfo="percent+label")
    fig.update_layout(template="plotly_white", margin=dict(l=16, r=16, t=58, b=16),
                      font=dict(family="DM Sans", color="#344054"), showlegend=False)
    with chart2:
        st.plotly_chart(fig, use_container_width=True)
else:
    with chart2:
        st.info("A Region field is needed for this chart.")

date_cols = [
    c for c in analysis_df.columns
    if "date" in str(c).lower() and pd.api.types.is_datetime64_any_dtype(analysis_df[c])
]
if date_cols:
    trend = analysis_df.dropna(subset=[date_cols[0]]).copy()
    if not trend.empty:
        trend["Period"] = trend[date_cols[0]].dt.to_period("M").astype(str)
        trend_summary = trend.groupby("Period", as_index=False).agg(
            Sales=(sales_col, "sum"), Profit=(profit_col, "sum")
        )
        fig = px.line(
            trend_summary, x="Period", y=["Sales", "Profit"], markers=True,
            title="Monthly sales & profit trend",
            labels={"value": "Amount", "variable": "Metric"},
            color_discrete_sequence=["#635bff", "#10a89a"]
        )
        fig.update_layout(template="plotly_white", margin=dict(l=16, r=16, t=58, b=16),
                          legend_title_text="", font=dict(family="DM Sans", color="#344054"))
        st.plotly_chart(fig, use_container_width=True)
else:
    fig = px.scatter(
        analysis_df, x=sales_col, y=profit_col, size=quantity_col,
        title="Sales vs profit relationship",
        labels={sales_col: "Sales", profit_col: "Profit", quantity_col: "Quantity"},
        color_discrete_sequence=["#635bff"], hover_data=[order_col]
    )
    fig.update_layout(template="plotly_white", margin=dict(l=16, r=16, t=58, b=16),
                      font=dict(family="DM Sans", color="#344054"))
    st.plotly_chart(fig, use_container_width=True)

# ---------- Details and export ----------
section_heading("07 / DATA DETAILS", "Statistical summary",
                "Descriptive statistics for the selected sales metrics.")
with st.container(border=True):
    summary = statistical_summary(analysis_df, numeric_columns=[sales_col, profit_col, quantity_col])
    st.dataframe(summary, use_container_width=True, hide_index=True)

with st.expander("View filtered records", expanded=False):
    st.caption(f"{len(analysis_df):,} rows · {len(analysis_df.columns):,} columns")
    st.dataframe(analysis_df, use_container_width=True, hide_index=True)
    csv_bytes = analysis_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered data as CSV", data=csv_bytes,
        file_name="filtered_sales_data.csv", mime="text/csv"
    )

st.markdown("""
<div style="text-align:center;padding:24px 0 4px 0;color:#98a2b3;font-size:.78rem">
  SALESPULSE ANALYTICS · BUILT WITH STREAMLIT & PLOTLY
</div>
""", unsafe_allow_html=True)
