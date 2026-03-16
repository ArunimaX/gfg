"""Chart type selection logic based on query results and SQL analysis."""

import re


def select_chart_type(sql: str, columns: list[str], rows: list[list], user_query: str = "") -> list[dict]:
    """
    Analyze the SQL query, result columns, and data to recommend chart types.
    Returns a list of chart suggestions with metadata.
    """
    sql_lower = sql.lower()
    query_lower = user_query.lower()
    num_rows = len(rows)
    num_cols = len(columns)

    charts = []

    # Detect column types from data
    date_cols = []
    numeric_cols = []
    categorical_cols = []

    for i, col in enumerate(columns):
        col_lower = col.lower()
        sample_values = [row[i] for row in rows[:20] if i < len(row) and row[i] is not None]

        if not sample_values:
            continue

        # Check if date column
        if col_lower in ("order_date", "date", "month", "year", "quarter") or \
           any(re.match(r"^\d{4}-\d{2}", str(v)) for v in sample_values[:3]):
            date_cols.append(col)
        # Check if numeric
        elif all(_is_numeric(v) for v in sample_values[:5]):
            numeric_cols.append(col)
        else:
            categorical_cols.append(col)

    # --- Chart Selection Rules ---

    # Rule 0: Single Row + Numeric Values -> KPI Card
    if num_rows == 1 and numeric_cols:
        charts.append({
            "type": "kpi",
            "title": _generate_title(columns, "Summary"),
            "xKey": None,
            "yKeys": numeric_cols,
            "description": "High-level metrics summary",
        })

    # Rule 1: Time series data → Line Chart
    if date_cols and numeric_cols and num_rows > 1:
        charts.append({
            "type": "line",
            "title": _generate_title(columns, "Trend"),
            "xKey": date_cols[0],
            "yKeys": numeric_cols[:3],
            "pivotCol": categorical_cols[0] if categorical_cols else None,
            "description": "Time series trend visualization",
        })

    # Rule 2: Categorical + Numeric → Bar Chart
    if categorical_cols and numeric_cols:
        charts.append({
            "type": "bar",
            "title": _generate_title(columns, "Comparison"),
            "xKey": categorical_cols[0],
            "yKeys": numeric_cols[:3],
            "pivotCol": categorical_cols[1] if len(categorical_cols) > 1 else None,
            "description": "Category comparison",
        })

    # Rule 3: Part of whole / proportions → Pie Chart
    if (len(categorical_cols) == 1 and len(numeric_cols) == 1 and num_rows <= 15) or \
       any(kw in query_lower for kw in ["proportion", "share", "percentage", "breakdown", "distribution of"]):
        charts.append({
            "type": "pie",
            "title": _generate_title(columns, "Distribution"),
            "nameKey": categorical_cols[0] if categorical_cols else columns[0],
            "valueKey": numeric_cols[0] if numeric_cols else columns[-1],
            "description": "Proportional breakdown",
        })

    # Rule 4: If we have only numeric data with many rows → Area Chart
    if date_cols and numeric_cols and num_rows > 10:
        charts.append({
            "type": "area",
            "title": _generate_title(columns, "Area Trend"),
            "xKey": date_cols[0],
            "yKeys": numeric_cols[:2],
            "pivotCol": categorical_cols[0] if categorical_cols else None,
            "description": "Area trend visualization",
        })

    # Rule 5: Keywords suggesting specific charts
    if any(kw in query_lower for kw in ["top", "highest", "lowest", "ranking", "best", "worst"]):
        if not any(c["type"] == "bar" for c in charts):
            x_key = categorical_cols[0] if categorical_cols else columns[0]
            y_keys = numeric_cols[:2] if numeric_cols else [columns[-1]]
            charts.append({
                "type": "bar",
                "title": _generate_title(columns, "Ranking"),
                "xKey": x_key,
                "yKeys": y_keys,
                "pivotCol": categorical_cols[1] if categorical_cols and len(categorical_cols) > 1 else None,
                "description": "Ranking comparison",
            })

    # Fallback: if no charts determined, use bar chart
    if not charts:
        x_key = columns[0]
        y_keys = [c for c in columns[1:] if c != x_key][:3]
        if not y_keys:
            y_keys = columns[:1]
        charts.append({
            "type": "bar",
            "title": _generate_title(columns, "Results"),
            "xKey": x_key,
            "yKeys": y_keys,
            "pivotCol": None,
            "description": "Query results visualization",
        })

    # Limit to best 2 charts to avoid clutter
    # Prefer diversity of chart types
    seen_types = set()
    unique_charts = []
    for chart in charts:
        if chart["type"] not in seen_types:
            unique_charts.append(chart)
            seen_types.add(chart["type"])
        if len(unique_charts) >= 2:
            break

    return unique_charts


def _is_numeric(value) -> bool:
    """Check if a value is numeric."""
    if isinstance(value, (int, float)):
        return True
    try:
        float(str(value))
        return True
    except (ValueError, TypeError):
        return False


def _generate_title(columns: list[str], chart_kind: str) -> str:
    """Generate a human-readable chart title from columns."""
    clean_cols = [col.replace("_", " ").title() for col in columns[:3]]
    if len(clean_cols) == 1:
        return f"{clean_cols[0]} {chart_kind}"
    elif len(clean_cols) == 2:
        return f"{clean_cols[0]} vs {clean_cols[1]}"
    else:
        return f"{clean_cols[0]} by {clean_cols[1]} — {chart_kind}"
