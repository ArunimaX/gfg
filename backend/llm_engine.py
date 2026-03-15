"""LLM Engine: Uses Google Gemini to convert natural language to SQL."""

import os
import re
import json
import google.generativeai as genai

# Configure the API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

SYSTEM_PROMPT = """You are an expert SQL analyst. You convert natural language business questions into SQLite SQL queries.

You have access to a single table called `amazon_sales` with the following schema:

TABLE: amazon_sales
COLUMNS:
  - order_id (INTEGER) — Unique transaction identifier (1–49997)
  - order_date (TEXT) — Transaction date in YYYY-MM-DD format (range: 2022 to 2023)
  - product_id (INTEGER) — Unique product identifier
  - product_category (TEXT) — Product department. Values: Books, Fashion, Sports, Electronics, Home & Kitchen
  - price (REAL) — Original base price per unit before discount
  - discount_percent (REAL) — Percentage discount applied (e.g. 10, 20, 30)
  - quantity_sold (INTEGER) — Number of units purchased in the order
  - customer_region (TEXT) — Buyer's geographical area. Values: North America, Asia, Europe, South America, Africa, Oceania
  - payment_method (TEXT) — Payment instrument. Values: UPI, Credit Card, Debit Card, Net Banking, PayPal
  - rating (REAL) — Product rating out of 5.0
  - review_count (INTEGER) — Total user reviews for the product
  - discounted_price (REAL) — Price per unit after discount
  - total_revenue (REAL) — Final transaction value = discounted_price × quantity_sold

RULES:
1. ONLY use columns that exist in the schema above. NEVER invent columns.
2. Always use the table name `amazon_sales`.
3. For date operations, use SQLite date functions like strftime().
4. For monthly aggregation, use strftime('%Y-%m', order_date) as month.
5. For quarterly aggregation, use:
   CASE 
     WHEN CAST(strftime('%m', order_date) AS INTEGER) BETWEEN 1 AND 3 THEN 'Q1'
     WHEN CAST(strftime('%m', order_date) AS INTEGER) BETWEEN 4 AND 6 THEN 'Q2'
     WHEN CAST(strftime('%m', order_date) AS INTEGER) BETWEEN 7 AND 9 THEN 'Q3'
     WHEN CAST(strftime('%m', order_date) AS INTEGER) BETWEEN 10 AND 12 THEN 'Q4'
   END as quarter
6. For "revenue" or "sales", use SUM(total_revenue).
7. For "top" or "highest", use ORDER BY ... DESC LIMIT.
8. When the user says "region", use customer_region.
9. When the user says "category", use product_category.
10. Return ONLY a JSON object with these keys:
    - "sql": the SQL query string
    - "explanation": a brief explanation of what the query does
    - "can_answer": true/false (false if the question cannot be answered from this dataset)
11. If the question cannot be answered from the available data, set "can_answer" to false and explain why.
12. Always alias aggregated columns with readable names (e.g., total_sales, avg_price).
13. Use ROUND() for floating point results.

Respond ONLY with valid JSON. No markdown, no code blocks, just raw JSON.
"""


def init_gemini():
    """Initialize the Gemini API client."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please set it with: set GEMINI_API_KEY=your_api_key"
        )
    genai.configure(api_key=api_key)


def generate_sql(user_query: str, conversation_history: list[dict] = None, table_name: str = "amazon_sales", custom_schema: str = None) -> dict:
    """
    Convert a natural language query to SQL using Gemini.
    
    Args:
        user_query: The user's natural language question
        conversation_history: List of previous {query, sql} dicts for follow-ups
        table_name: Target table name
        custom_schema: Optional custom schema for uploaded CSVs
    
    Returns:
        dict with keys: sql, explanation, can_answer
    """
    init_gemini()

    # Find an available model since different API keys have different access
    model_name = "gemini-1.5-flash"
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        preferred_models = ["models/gemini-1.5-flash", "models/gemini-1.5-pro", "models/gemini-pro"]
        for pref in preferred_models:
            if pref in available_models:
                model_name = pref.split("/")[-1]
                break
    except Exception:
        pass # fallback to default if list_models fails

    model = genai.GenerativeModel(model_name)

    # Build the prompt
    messages = []

    # System context
    system = SYSTEM_PROMPT
    if custom_schema:
        system += f"\n\nADDITIONAL TABLE:\n{custom_schema}\nUse table name: {table_name}"

    # Add conversation history for follow-up questions
    history_context = ""
    if conversation_history:
        history_context = "\n\nPREVIOUS CONVERSATION:\n"
        for entry in conversation_history[-5:]:  # Last 5 exchanges
            history_context += f"User asked: {entry.get('query', '')}\n"
            history_context += f"SQL generated: {entry.get('sql', '')}\n\n"
        history_context += "The user may be asking a follow-up question that builds on the previous queries. "
        history_context += "If they say things like 'now filter', 'only show', 'change to', etc., modify the previous query accordingly.\n"

    full_prompt = system + history_context + f"\n\nUser question: {user_query}"

    try:
        response = model.generate_content(full_prompt)
        response_text = response.text.strip()

        # Clean up response - remove markdown code blocks if present
        response_text = re.sub(r"```json\s*", "", response_text)
        response_text = re.sub(r"```\s*", "", response_text)
        response_text = response_text.strip()

        result = json.loads(response_text)

        # Validate required keys
        if "sql" not in result:
            result["sql"] = ""
        if "explanation" not in result:
            result["explanation"] = "Query generated successfully."
        if "can_answer" not in result:
            result["can_answer"] = bool(result["sql"])

        # Replace table name if custom
        if table_name != "amazon_sales" and "amazon_sales" in result.get("sql", ""):
            result["sql"] = result["sql"].replace("amazon_sales", table_name)

        return result

    except json.JSONDecodeError as e:
        # Try to extract SQL from non-JSON response
        sql_match = re.search(r"(SELECT\s+.+?)(?:\n\n|$)", response_text, re.IGNORECASE | re.DOTALL)
        if sql_match:
            return {
                "sql": sql_match.group(1).strip(),
                "explanation": "Query extracted from response.",
                "can_answer": True,
            }
        return {
            "sql": "",
            "explanation": f"Failed to parse LLM response: {str(e)}",
            "can_answer": False,
        }
    except Exception as e:
        return {
            "sql": "",
            "explanation": f"Error communicating with Gemini API: {str(e)}",
            "can_answer": False,
        }
