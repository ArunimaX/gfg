"""Database module: loads CSV into SQLite and executes queries safely."""

import sqlite3
import csv
import io
import os
from .utils import clean_csv_content, get_data_dir

DB_PATH = os.path.join(get_data_dir(), "sales.db")

_connection = None


def get_connection() -> sqlite3.Connection:
    """Get or create the SQLite connection."""
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
    return _connection


def init_db(csv_path: str = None):
    """
    Load CSV data into SQLite. Strips binary preamble if present.
    Creates the amazon_sales table with proper types.
    """
    if csv_path is None:
        csv_path = os.path.join(get_data_dir(), "Amazon Sales.csv")

    conn = get_connection()
    cursor = conn.cursor()

    # Drop existing table
    cursor.execute("DROP TABLE IF EXISTS amazon_sales")

    # Create table with proper schema
    cursor.execute("""
        CREATE TABLE amazon_sales (
            order_id INTEGER,
            order_date TEXT,
            product_id INTEGER,
            product_category TEXT,
            price REAL,
            discount_percent REAL,
            quantity_sold INTEGER,
            customer_region TEXT,
            payment_method TEXT,
            rating REAL,
            review_count INTEGER,
            discounted_price REAL,
            total_revenue REAL
        )
    """)

    # Clean and read CSV
    clean_text = clean_csv_content(csv_path)
    reader = csv.reader(io.StringIO(clean_text))
    header = next(reader)  # Skip header

    # Insert data
    insert_sql = """
        INSERT INTO amazon_sales 
        (order_id, order_date, product_id, product_category, price,
         discount_percent, quantity_sold, customer_region, payment_method,
         rating, review_count, discounted_price, total_revenue)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    rows_inserted = 0
    batch = []
    for row in reader:
        if len(row) < 13:
            continue
        try:
            parsed = (
                int(row[0]),           # order_id
                row[1].strip(),        # order_date
                int(row[2]),           # product_id
                row[3].strip(),        # product_category
                float(row[4]),         # price
                float(row[5]),         # discount_percent
                int(row[6]),           # quantity_sold
                row[7].strip(),        # customer_region
                row[8].strip(),        # payment_method
                float(row[9]),         # rating
                int(row[10]),          # review_count
                float(row[11]),        # discounted_price
                float(row[12]),        # total_revenue
            )
            batch.append(parsed)
            if len(batch) >= 1000:
                cursor.executemany(insert_sql, batch)
                rows_inserted += len(batch)
                batch = []
        except (ValueError, IndexError):
            continue

    if batch:
        cursor.executemany(insert_sql, batch)
        rows_inserted += len(batch)

    conn.commit()

    # Create useful indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_date ON amazon_sales(order_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON amazon_sales(product_category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_region ON amazon_sales(customer_region)")
    conn.commit()

    print(f"✅ Loaded {rows_inserted} rows into amazon_sales table")
    return rows_inserted


def execute_query(sql: str) -> dict:
    """
    Execute a read-only SQL query and return results as a dict.
    Returns: {"columns": [...], "rows": [[...], ...], "row_count": int}
    """
    # Safety: only allow SELECT statements
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed for safety.")

    dangerous_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "ATTACH"]
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            raise ValueError(f"Query contains forbidden keyword: {keyword}")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql)
    
    columns = [description[0] for description in cursor.description]
    rows = [list(row) for row in cursor.fetchall()]

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }


def get_table_info() -> dict:
    """Get schema info about the amazon_sales table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(amazon_sales)")
    columns = []
    for row in cursor.fetchall():
        columns.append({
            "name": row[1],
            "type": row[2],
        })
    
    cursor.execute("SELECT COUNT(*) FROM amazon_sales")
    count = cursor.fetchone()[0]

    # Get distinct values for categorical columns
    categorical_cols = ["product_category", "customer_region", "payment_method"]
    distinct_values = {}
    for col in categorical_cols:
        cursor.execute(f"SELECT DISTINCT {col} FROM amazon_sales ORDER BY {col}")
        distinct_values[col] = [row[0] for row in cursor.fetchall()]

    # Get date range
    cursor.execute("SELECT MIN(order_date), MAX(order_date) FROM amazon_sales")
    date_range = cursor.fetchone()

    return {
        "table_name": "amazon_sales",
        "columns": columns,
        "row_count": count,
        "distinct_values": distinct_values,
        "date_range": {"min": date_range[0], "max": date_range[1]},
    }


def load_uploaded_csv(csv_content: str, table_name: str = "uploaded_data") -> dict:
    """Load an uploaded CSV string into a new SQLite table."""
    conn = get_connection()
    cursor = conn.cursor()

    reader = csv.reader(io.StringIO(csv_content))
    header = next(reader)

    # Clean column names
    clean_cols = [col.strip().replace(" ", "_").replace("-", "_").lower() for col in header]

    # Drop existing table
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

    # Create table (all TEXT initially)
    col_defs = ", ".join([f'"{col}" TEXT' for col in clean_cols])
    cursor.execute(f"CREATE TABLE {table_name} ({col_defs})")

    # Insert data
    placeholders = ", ".join(["?"] * len(clean_cols))
    insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"

    rows = []
    for row in reader:
        if len(row) == len(clean_cols):
            rows.append(row)

    cursor.executemany(insert_sql, rows)
    conn.commit()

    return {
        "table_name": table_name,
        "columns": clean_cols,
        "row_count": len(rows),
    }
