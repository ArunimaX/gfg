"""Utility functions for data cleaning and schema extraction."""

import os
import re
import csv
import io


def get_data_dir():
    """Get the path to the data directory."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def clean_csv_content(filepath: str) -> str:
    """
    Read a CSV file and strip any binary preamble (e.g., macOS webarchive prefix).
    Returns clean CSV text content starting from the actual header row.
    """
    with open(filepath, "rb") as f:
        raw = f.read()

    text = raw.decode("utf-8", errors="replace")

    # Try to find the header row by looking for known column patterns
    # Strategy: find 'order_id' or first line with many comma-separated fields
    header_patterns = ["order_id", "Order_ID", "ORDER_ID"]
    
    for pattern in header_patterns:
        idx = text.find(pattern)
        if idx >= 0:
            # Found header - extract from this point
            clean_text = text[idx:]
            # Normalize line endings
            clean_text = clean_text.replace("\r\n", "\n").replace("\r", "\n")
            # Remove any trailing binary garbage and non-printable lines
            lines = clean_text.split("\n")
            clean_lines = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                # Check if line has printable content
                printable_ratio = sum(1 for c in stripped if c.isprintable()) / max(len(stripped), 1)
                if printable_ratio > 0.9:
                    clean_lines.append(stripped)
            return "\n".join(clean_lines)

    # Fallback: if no known header found, try to detect CSV structure
    lines = text.split("\n")
    for i, line in enumerate(lines):
        fields = line.split(",")
        if len(fields) >= 5:
            # This might be the header or first data row
            remaining = "\n".join(lines[i:])
            return remaining.strip()

    return text


def extract_schema_from_csv(filepath: str) -> dict:
    """
    Extract column names, sample values, and inferred types from a CSV file.
    Returns a dict with columns info for LLM context.
    """
    clean_text = clean_csv_content(filepath)
    reader = csv.reader(io.StringIO(clean_text))
    header = next(reader)

    # Read sample rows
    sample_rows = []
    for i, row in enumerate(reader):
        if i >= 5:
            break
        sample_rows.append(row)

    columns = []
    for col_idx, col_name in enumerate(header):
        col_info = {
            "name": col_name.strip(),
            "sample_values": [row[col_idx].strip() for row in sample_rows if col_idx < len(row)],
        }
        # Infer type
        samples = col_info["sample_values"]
        if all(re.match(r"^\d{4}-\d{2}-\d{2}$", s) for s in samples if s):
            col_info["type"] = "DATE"
        elif all(re.match(r"^-?\d+$", s) for s in samples if s):
            col_info["type"] = "INTEGER"
        elif all(re.match(r"^-?\d+\.?\d*$", s) for s in samples if s):
            col_info["type"] = "REAL"
        else:
            col_info["type"] = "TEXT"
        columns.append(col_info)

    return {"table_name": "amazon_sales", "columns": columns}


def get_schema_prompt(schema: dict) -> str:
    """Generate a schema description string for the LLM prompt."""
    lines = [f"Table: {schema['table_name']}", "Columns:"]
    for col in schema["columns"]:
        samples = ", ".join(col["sample_values"][:3])
        lines.append(f"  - {col['name']} ({col['type']}) — e.g. {samples}")
    return "\n".join(lines)


DATA_DICTIONARY = """
Dataset: Amazon E-commerce Sales Transactional Log

Columns:
- order_id (INTEGER): Unique identifier for each sales transaction. Range: 1–49997
- order_date (DATE, YYYY-MM-DD): Date the transaction was completed. Range: 2022 to 2023
- product_id (INTEGER): Unique identifier for the purchased item.
- product_category (TEXT): Product department — Books, Fashion, Sports, Electronics, Home & Kitchen
- price (REAL): Original base price per unit before discount.
- discount_percent (INTEGER): Percentage discount applied (e.g. 10, 20).
- quantity_sold (INTEGER): Number of units purchased in the order.
- customer_region (TEXT): Geographical area of buyer — North America, Asia, Europe, etc.
- payment_method (TEXT): Payment instrument — UPI, Credit Card, Debit Card, Net Banking, etc.
- rating (REAL): Product rating out of 5.0.
- review_count (INTEGER): Total user reviews for the product.
- discounted_price (REAL): Price per unit after discount.
- total_revenue (REAL): Final transaction value = discounted_price × quantity_sold.
"""
