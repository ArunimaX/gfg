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


import uuid
import datetime

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Original amazon_sales table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS amazon_sales (
        order_id INTEGER PRIMARY KEY,
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
    ''')

    # Chat Sessions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        active_table TEXT NOT NULL
    )
    ''')

    # Chat Messages table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_messages (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        sql_query TEXT,
        result_summary TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
    )
    ''')

    conn.commit()

    # Check if we need to load the initial dataset
    cursor.execute("SELECT COUNT(*) FROM amazon_sales")
    if cursor.fetchone()[0] == 0:
        csv_path = os.path.join(get_data_dir(), "amazon_sales_report.csv")
        if os.path.exists(csv_path):
            try:
                _load_initial_csv(conn, cursor, csv_path)
            except Exception as e:
                print(f"Failed to load initial CSV: {e}")
        else:
            print(f"Warning: Initial CSV not found at {csv_path}")

def create_chat_session(user_id: str, title: str, active_table: str) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    session_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO chat_sessions (id, user_id, title, created_at, active_table) VALUES (?, ?, ?, ?, ?)",
        (session_id, user_id, title, now, active_table)
    )
    conn.commit()
    return session_id

def add_chat_message(session_id: str, role: str, content: str, sql_query: str | None = None, result_summary: str | None = None):
    conn = get_connection()
    cursor = conn.cursor()
    message_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO chat_messages (id, session_id, role, content, sql_query, result_summary, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (message_id, session_id, role, content, sql_query, result_summary, now)
    )
    conn.commit()

def get_user_sessions(user_id: str) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, created_at, active_table FROM chat_sessions WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    return [dict(row) for row in cursor.fetchall()]

def get_session_messages(session_id: str, user_id: str) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    # Verify owner
    cursor.execute("SELECT user_id FROM chat_sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    if not row or row["user_id"] != user_id:
        raise ValueError("Session not found or forbidden")

    cursor.execute(
        "SELECT role, content, sql_query, result_summary, created_at FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,)
    )
    return [dict(r) for r in cursor.fetchall()]

def _load_initial_csv(conn: sqlite3.Connection, cursor: sqlite3.Cursor, csv_path: str):
    """Helper to load the initial Amazon Sale Report CSV into the amazon_sales table."""
    print(f"Loading initial data from {csv_path}...")
    
    # Clean and read CSV
    clean_text = clean_csv_content(csv_path)
    reader = csv.reader(io.StringIO(clean_text))
    header = next(reader)  # Skip header

    # Map CSV headers to table columns (case-insensitive, handle spaces/underscores)
    # CSV headers: order_id,Date,Status,Fulfilment,Sales Channel ,ship-service-level,Style,SKU,Category,Size,ASIN,Courier Status,Qty,Currency,Amount,ship-city,ship-state,ship-postal-code,ship-country,promotion-ids,B2B,Fulfilled by
    # Table columns: order_id,date,status,fulfilment,sales_channel,ship_service_level,style,sku,category,size,asin,courier_status,qty,currency,amount,ship_city,ship_state,ship_postal_code,ship_country,promotion_ids,b2b,fulfilled_by
    
    # Create a mapping from cleaned CSV header to its index
    csv_header_map = {h.strip().lower().replace(' ', '_').replace('-', '_'): i for i, h in enumerate(header)}

    # Define the order of columns for insertion
    insert_cols = [
        "order_id", "date", "status", "fulfilment", "sales_channel",
        "ship_service_level", "style", "sku", "category", "size",
        "asin", "courier_status", "qty", "currency", "amount",
        "ship_city", "ship_state", "ship_postal_code", "ship_country",
        "promotion_ids", "b2b", "fulfilled_by"
    ]
    
    # Ensure all required columns are present in the CSV
    if not all(col in csv_header_map for col in insert_cols):
        missing_cols = [col for col in insert_cols if col not in csv_header_map]
        raise ValueError(f"CSV is missing required columns for amazon_sales table: {missing_cols}")

    insert_sql = f"INSERT INTO amazon_sales ({', '.join(insert_cols)}) VALUES ({', '.join(['?'] * len(insert_cols))})"

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
    # Safety: only allow SELECT statements (including CTEs that start with WITH)
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
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
    """Load an uploaded CSV string into a new SQLite table with smart type detection."""
    conn = get_connection()
    cursor = conn.cursor()

    reader = csv.reader(io.StringIO(csv_content))
    header = next(reader)

    # Clean column names
    clean_cols = [col.strip().replace(" ", "_").replace("-", "_").lower() for col in header]

    # Read all rows first for type detection
    all_rows = [row for row in reader if len(row) == len(clean_cols)]

    # Detect column types from sample data
    import re as _re
    col_types = []
    for col_idx in range(len(clean_cols)):
        samples = [r[col_idx].strip() for r in all_rows[:100] if col_idx < len(r) and r[col_idx].strip()]
        if not samples:
            col_types.append("TEXT")
            continue
        # Check date
        if all(_re.match(r"^\d{4}-\d{2}-\d{2}", s) for s in samples[:10]):
            col_types.append("TEXT")  # Store dates as TEXT for SQLite date functions
        # Check integer
        elif all(_re.match(r"^-?\d+$", s) for s in samples[:10]):
            col_types.append("INTEGER")
        # Check float
        elif all(_re.match(r"^-?\d+\.?\d*$", s) for s in samples[:10]):
            col_types.append("REAL")
        else:
            col_types.append("TEXT")

    # Drop existing table
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

    # Create table with detected types
    col_defs = ", ".join([f'"{col}" {typ}' for col, typ in zip(clean_cols, col_types)])
    cursor.execute(f"CREATE TABLE {table_name} ({col_defs})")

    # Cast rows to proper types and insert
    def cast_value(val, typ):
        val = val.strip()
        if not val:
            return None
        try:
            if typ == "INTEGER":
                return int(val)
            elif typ == "REAL":
                return float(val)
        except (ValueError, TypeError):
            pass
        return val

    typed_rows = [
        tuple(cast_value(row[i], col_types[i]) for i in range(len(clean_cols)))
        for row in all_rows
    ]

    placeholders = ", ".join(["?"] * len(clean_cols))
    insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
    cursor.executemany(insert_sql, typed_rows)
    conn.commit()

    # Build schema info for LLM
    schema_prompt = _build_schema_prompt(table_name, clean_cols, col_types, cursor)

    return {
        "table_name": table_name,
        "columns": clean_cols,
        "col_types": col_types,
        "row_count": len(typed_rows),
        "schema_prompt": schema_prompt,
    }


def _build_schema_prompt(table_name: str, columns: list, col_types: list, cursor) -> str:
    """Build a dynamic LLM system prompt section for a table."""
    lines = [f"TABLE: {table_name}", "COLUMNS:"]
    for col, typ in zip(columns, col_types):
        # Get distinct values for TEXT columns (categorical)
        extra = ""
        if typ == "TEXT":
            try:
                cursor.execute(f'SELECT DISTINCT "{col}" FROM {table_name} LIMIT 15')
                vals = [str(r[0]) for r in cursor.fetchall() if r[0]]
                if vals and len(vals) <= 12:
                    extra = f" — Values: {', '.join(vals)}"
                elif vals:
                    extra = f" — e.g. {', '.join(vals[:5])}"
            except Exception:
                pass
        elif typ in ("INTEGER", "REAL"):
            try:
                cursor.execute(f'SELECT MIN("{col}"), MAX("{col}") FROM {table_name}')
                mn, mx = cursor.fetchone()
                if mn is not None:
                    extra = f" — Range: {mn} to {mx}"
            except Exception:
                pass
        lines.append(f"  - {col} ({typ}){extra}")

    # Row count
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        lines.append(f"\nTotal rows: {count}")
    except Exception:
        pass

    return "\n".join(lines)


def get_dynamic_table_info(table_name: str) -> dict:
    """Get schema info about any table in the database."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = []
    col_names = []
    col_types = []
    for row in cursor.fetchall():
        columns.append({"name": row[1], "type": row[2]})
        col_names.append(row[1])
        col_types.append(row[2])

    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]

    # Get distinct values for TEXT columns
    distinct_values = {}
    for col_info in columns:
        if col_info["type"] == "TEXT":
            try:
                cursor.execute(f'SELECT DISTINCT "{col_info["name"]}" FROM {table_name} ORDER BY "{col_info["name"]}" LIMIT 15')
                vals = [row[0] for row in cursor.fetchall() if row[0]]
                if vals:
                    distinct_values[col_info["name"]] = vals
            except Exception:
                pass

    # Build schema prompt
    schema_prompt = _build_schema_prompt(table_name, col_names, col_types, cursor)

    return {
        "table_name": table_name,
        "columns": columns,
        "row_count": count,
        "distinct_values": distinct_values,
        "schema_prompt": schema_prompt,
    }


def get_dataset_capabilities(table_name: str = "amazon_sales") -> dict:
    """
    Return what the dataset CAN answer — used for smart error recovery.
    Returns column names, categorical values, date ranges, and suggested queries.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]

    # Row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]

    # Categorical values
    categories = {}
    for col in columns:
        try:
            cursor.execute(f'SELECT DISTINCT "{col}" FROM {table_name} LIMIT 10')
            vals = [str(r[0]) for r in cursor.fetchall() if r[0] is not None]
            # Only include if it's truly categorical (not too many unique values)
            if 2 <= len(vals) <= 10:
                categories[col] = vals
        except Exception:
            pass

    # Date range
    date_range = None
    for col in columns:
        try:
            cursor.execute(f'SELECT MIN("{col}"), MAX("{col}") FROM {table_name}')
            mn, mx = cursor.fetchone()
            if mn and isinstance(mn, str) and len(mn) >= 10 and mn[4] == '-':
                date_range = {"column": col, "min": mn, "max": mx}
                break
        except Exception:
            pass

    # Generate smart suggestions based on actual schema
    suggestions = []
    numeric_cols = []
    text_cols = []
    for col in columns:
        try:
            cursor.execute(f'SELECT typeof("{col}") FROM {table_name} LIMIT 1')
            t = cursor.fetchone()[0]
            if t in ("integer", "real"):
                numeric_cols.append(col)
            elif t == "text" and col in categories:
                text_cols.append(col)
        except Exception:
            pass

    if numeric_cols and text_cols:
        suggestions.append(f"Show total {numeric_cols[0].replace('_', ' ')} by {text_cols[0].replace('_', ' ')}")
    if len(text_cols) >= 2 and numeric_cols:
        suggestions.append(f"Compare {text_cols[0].replace('_', ' ')} by {numeric_cols[0].replace('_', ' ')}")
    if date_range and numeric_cols:
        suggestions.append(f"Show monthly trend of {numeric_cols[0].replace('_', ' ')}")
    if numeric_cols:
        suggestions.append(f"What is the average {numeric_cols[-1].replace('_', ' ')}?")
    if text_cols:
        suggestions.append(f"Show distribution across {text_cols[-1].replace('_', ' ')}")

    # Keep top 5
    suggestions = suggestions[:5]

    return {
        "table_name": table_name,
        "columns": columns,
        "row_count": row_count,
        "categories": categories,
        "date_range": date_range,
        "suggestions": suggestions,
    }


def get_all_tables() -> list:
    """Return a list of all user tables in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]
