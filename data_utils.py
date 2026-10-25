import json
from io import BytesIO
import pandas as pd


def load_uploaded_file(uploaded_file):
    """Load a CSV, XLSX, or JSON upload into a DataFrame."""
    name = uploaded_file.name.lower()
    raw = uploaded_file.getvalue()
    if name.endswith(".csv"):
        # Try common encodings while preserving a clear error if none work.
        last_error = None
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return pd.read_csv(BytesIO(raw), encoding=encoding)
            except Exception as exc:
                last_error = exc
        raise ValueError(f"CSV could not be parsed: {last_error}")
    if name.endswith(".xlsx"):
        return pd.read_excel(BytesIO(raw), engine="openpyxl")
    if name.endswith(".json"):
        try:
            return pd.read_json(BytesIO(raw))
        except ValueError:
            # Support newline-delimited JSON as a fallback.
            return pd.read_json(BytesIO(raw), lines=True)
    raise ValueError("Unsupported file type. Upload .csv, .xlsx, or .json.")


def profile_data(df):
    """Return dataset dimensions, duplicate count, missing count and column profile."""
    column_profile = pd.DataFrame({
        "Column": df.columns.astype(str),
        "Data Type": [str(dtype) for dtype in df.dtypes],
        "Missing Values": [int(df[col].isna().sum()) for col in df.columns],
        "Missing (%)": [
            round(float(df[col].isna().mean() * 100), 2) for col in df.columns
        ],
        "Unique Values": [int(df[col].nunique(dropna=True)) for col in df.columns],
    })
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_cells": int(df.isna().sum().sum()),
        "column_profile": column_profile,
    }


def preprocess_data(
    df,
    missing_strategy="Fill numeric with median and text with mode",
    duplicate_strategy="Remove exact duplicate rows",
    normalize_text=True,
    parse_dates=True,
):
    """Clean a copy of a DataFrame according to the chosen options."""
    cleaned = df.copy()

    if normalize_text:
        for col in cleaned.select_dtypes(include=["object", "string"]).columns:
            cleaned[col] = cleaned[col].map(
                lambda value: value.strip() if isinstance(value, str) else value
            )
            # Normalize blank strings to missing values.
            cleaned[col] = cleaned[col].replace(r"^\s*$", pd.NA, regex=True)

    if parse_dates:
        for col in cleaned.columns:
            if "date" in str(col).lower():
                parsed = pd.to_datetime(cleaned[col], errors="coerce")
                # Convert only if at least one value parsed successfully.
                if parsed.notna().any():
                    cleaned[col] = parsed

    if duplicate_strategy == "Remove exact duplicate rows":
        cleaned = cleaned.drop_duplicates()

    if missing_strategy == "Drop rows with missing values":
        cleaned = cleaned.dropna()
    elif missing_strategy == "Fill numeric with median and text with mode":
        for col in cleaned.columns:
            if pd.api.types.is_numeric_dtype(cleaned[col]):
                median = cleaned[col].median()
                if pd.notna(median):
                    cleaned[col] = cleaned[col].fillna(median)
            else:
                modes = cleaned[col].mode(dropna=True)
                if not modes.empty:
                    cleaned[col] = cleaned[col].fillna(modes.iloc[0])
    elif missing_strategy != "Keep as-is":
        raise ValueError(f"Unknown missing-value strategy: {missing_strategy}")

    return cleaned


def statistical_summary(df, numeric_columns=None):
    """Generate reusable descriptive statistics for numeric columns."""
    if numeric_columns is None:
        numeric_columns = df.select_dtypes(include="number").columns.tolist()
    usable = [col for col in numeric_columns if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
    if not usable:
        return pd.DataFrame({"Message": ["No numeric columns available for summary."]})
    summary = df[usable].describe().T.reset_index().rename(columns={"index": "Column"})
    summary["Median"] = [df[col].median() for col in usable]
    summary["Missing Values"] = [int(df[col].isna().sum()) for col in usable]
    return summary


def detect_sales_columns(df):
    """Guess common sales fields, using case-insensitive exact and partial matches."""
    normalized = {str(col).strip().lower(): col for col in df.columns}

    def choose(candidates):
        for candidate in candidates:
            if candidate in normalized:
                return normalized[candidate]
        for candidate in candidates:
            for low_name, original in normalized.items():
                if candidate in low_name:
                    return original
        return None

    return {
        "order_id": choose(["order id", "order_id", "order number", "order"]),
        "sales": choose(["sales", "revenue", "total sales", "amount"]),
        "profit": choose(["profit", "net profit", "earnings"]),
        "quantity": choose(["quantity", "qty", "units sold", "units"]),
    }
