"""LLM Engine: Uses Google Gemini with Groq as fallback to convert natural language to multi-chart SQL."""

import os
import re
import json
import google.generativeai as genai
from groq import Groq

# Configure the APIs
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

SYSTEM_PROMPT = """You are an expert data analyst and SQL engineer. Your job is to convert a natural language business question into one or more SQL queries, each with an appropriate visualization.

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

=== CHART TYPE SELECTION RULES ===
- time-based x_axis (month, quarter, date, year) → "line" or "area"
- comparing discrete categories → "bar"
- parts-of-whole with 6 or fewer categories → "pie"
- NEVER use "pie" if categories > 6
- two numeric axes → "scatter"

=== QUERY DECOMPOSITION RULES ===
- Simple one metric + one dimension → 1 chart
- "and also" / "as well as" / "along with" → 2+ independent charts
- "impact of X on Y" → scatter + bar (2 charts)
- "trend + breakdown" → line + bar (2 charts)
- "compare X by Y across Z" → grouped bar with `group_by` set; return ALL rows, never filter down

=== HIGHLIGHT RULE ===
- If the user says "highlight top" or "flag best", add a boolean column using a window function:
  CASE WHEN total_revenue = MAX(total_revenue) OVER (PARTITION BY customer_region) THEN 1 ELSE 0 END AS is_top
  NEVER filter rows when highlighting. Show everything, just mark the top.

=== STRICT SQL RULES ===
1. ONLY use columns that exist in the schema above. NEVER invent columns.
2. Always use the table name `amazon_sales`.
3. For date operations, use SQLite date functions like strftime().
4. For monthly aggregation: strftime('%Y-%m', order_date) as month
5. For quarterly aggregation:
   CASE WHEN CAST(strftime('%m', order_date) AS INTEGER) BETWEEN 1 AND 3 THEN 'Q1'
        WHEN CAST(strftime('%m', order_date) AS INTEGER) BETWEEN 4 AND 6 THEN 'Q2'
        WHEN CAST(strftime('%m', order_date) AS INTEGER) BETWEEN 7 AND 9 THEN 'Q3'
        WHEN CAST(strftime('%m', order_date) AS INTEGER) BETWEEN 10 AND 12 THEN 'Q4'
   END as quarter
6. For "revenue" or "sales", always use SUM(total_revenue).
7. Always alias aggregated columns with readable names (e.g., total_sales, avg_price).
8. Use ROUND() for all floating point results.

=== OUTPUT FORMAT ===
Respond ONLY with a valid JSON object. No markdown, no code blocks, no explanation. Just raw JSON:

{
  "can_answer": true,
  "explanation": "A clear overall explanation of what you're showing (1-2 sentences).",
  "charts": [
    {
      "sql": "SELECT ...",
      "chart_type": "line | bar | pie | scatter | area",
      "title": "Descriptive Chart Title",
      "x_axis": "column_name",
      "y_axis": "column_name",
      "group_by": "column_name or null",
      "insight": "One sentence key takeaway from this chart."
    }
  ]
}

If the question CANNOT be answered from the available data, return:
{
  "can_answer": false,
  "explanation": "Reason why this cannot be answered.",
  "charts": []
}
"""


def build_dynamic_system_prompt(schema_prompt: str) -> str:
    """Build a complete multi-chart system prompt from a dynamic schema description."""
    return f"""You are an expert data analyst and SQL engineer. Convert the user's natural language question into one or more SQL queries with appropriate visualizations.

You have access to the following table:

{schema_prompt}

=== CHART TYPE SELECTION RULES ===
- time-based x_axis → "line" or "area"
- comparing discrete categories → "bar"
- parts-of-whole, ≤6 categories → "pie"
- NEVER "pie" if categories > 6
- two numeric axes → "scatter"

=== QUERY DECOMPOSITION RULES ===
- Simple: 1 chart. "and also" / "as well as" / "trend + breakdown" → 2+ independent charts.
- "compare X by Y across Z" → grouped bar, group_by set.

=== STRICT RULES ===
1. ONLY use columns in the schema above.
2. Always alias aggregated columns with readable names.
3. Use ROUND() for floats. Use SQLite strftime() for dates.
4. If cannot answer: set can_answer = false, charts = [].

=== OUTPUT FORMAT (raw JSON only, no markdown) ===
{{
  "can_answer": true,
  "explanation": "...",
  "charts": [
    {{
      "sql": "SELECT ...",
      "chart_type": "line | bar | pie | scatter | area",
      "title": "Chart Title",
      "x_axis": "column_name",
      "y_axis": "column_name",
      "group_by": null,
      "insight": "One sentence key takeaway."
    }}
  ]
}}
"""


def _wrap_legacy_result(result: dict) -> dict:
    """Backward compatibility: wrap old single-sql format into new multi-chart format."""
    if "sql" in result and "charts" not in result:
        result["charts"] = [
            {
                "sql": result.get("sql", ""),
                "chart_type": "bar",
                "title": "Query Result",
                "x_axis": "",
                "y_axis": "",
                "group_by": None,
                "insight": result.get("explanation", ""),
            }
        ]
    return result


def _parse_llm_response(response_text: str) -> dict:
    """Robustly parse LLM JSON response, stripping markdown if present."""
    response_text = re.sub(r"```json\s*", "", response_text)
    response_text = re.sub(r"```\s*", "", response_text)
    response_text = response_text.strip()
    return json.loads(response_text)


def _validate_result(result: dict) -> dict:
    """Ensure the result has the required top-level keys."""
    if "can_answer" not in result:
        result["can_answer"] = bool(result.get("charts") or result.get("sql"))
    if "charts" not in result:
        result = _wrap_legacy_result(result)
    if "explanation" not in result:
        result["explanation"] = ""
    return result


def init_gemini():
    """Initialize the Gemini API client."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please set it with: set GEMINI_API_KEY=your_api_key"
        )
    genai.configure(api_key=api_key)


def generate_sql_with_groq(user_query: str, conversation_history: list = None, table_name: str = "amazon_sales", custom_schema: str = None, custom_system_prompt: str | None = None) -> dict:
    """
    Fallback: Use Groq API to generate multi-chart SQL when Gemini fails.
    """
    groq_api_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY not available for fallback")

    client = Groq(api_key=groq_api_key)

    system = custom_system_prompt if custom_system_prompt else SYSTEM_PROMPT
    if custom_schema and not custom_system_prompt:
        system += f"\n\nADDITIONAL TABLE:\n{custom_schema}\nUse table name: {table_name}"

    # Add conversation history
    history_context = ""
    if conversation_history:
        history_context = "\n\nPREVIOUS CONVERSATION:\n"
        for entry in conversation_history[-5:]:
            history_context += f"User asked: {entry.get('query', '')}\n"
            history_context += f"SQL generated: {entry.get('sql', '')}\n\n"
        history_context += "The user may be asking a follow-up question that builds on the previous queries.\n"

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system + history_context},
                {"role": "user", "content": user_query},
            ],
            temperature=0.1,
            max_tokens=2048,
        )

        response_text = response.choices[0].message.content.strip()
        result = _parse_llm_response(response_text)
        result = _validate_result(result)

        # Fix table name in all chart SQLs
        if table_name != "amazon_sales":
            for chart in result.get("charts", []):
                sql = chart.get("sql", "")
                if "amazon_sales" in sql:
                    chart["sql"] = sql.replace("amazon_sales", table_name)

        return result

    except json.JSONDecodeError:
        return {
            "can_answer": False,
            "explanation": "Failed to parse Groq response as JSON.",
            "charts": [],
        }
    except Exception as e:
        return {
            "can_answer": False,
            "explanation": f"Error communicating with Groq API: {str(e)}",
            "charts": [],
        }


def generate_sql(user_query: str, conversation_history: list = None, table_name: str = "amazon_sales", custom_schema: str = None, custom_system_prompt: str | None = None) -> dict:
    """
    Convert a natural language query to multi-chart SQL specs using Gemini with Groq fallback.

    Returns:
        dict with keys: can_answer, explanation, charts (list of chart specs)
    """

    # Try Gemini first
    try:
        init_gemini()

        # Find an available model
        model_name = "gemini-2.0-flash"
        try:
            available_models = [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
            preferred_models = [
                "models/gemini-2.5-flash",
                "models/gemini-2.0-flash",
                "models/gemini-2.0-flash-lite",
                "models/gemini-1.5-flash",
                "models/gemini-1.5-pro",
            ]
            for pref in preferred_models:
                if pref in available_models:
                    model_name = pref.split("/")[-1]
                    break
        except Exception:
            pass  # fallback to default if list_models fails

        model = genai.GenerativeModel(model_name)

        # Build the system context
        system = custom_system_prompt if custom_system_prompt else SYSTEM_PROMPT
        if custom_schema and not custom_system_prompt:
            system += f"\n\nADDITIONAL TABLE:\n{custom_schema}\nUse table name: {table_name}"

        # Add conversation history for follow-up questions
        history_context = ""
        if conversation_history:
            history_context = "\n\nPREVIOUS CONVERSATION:\n"
            for entry in conversation_history[-5:]:
                history_context += f"User asked: {entry.get('query', '')}\n"
                history_context += f"SQL generated: {entry.get('sql', '')}\n\n"
            history_context += (
                "The user may be asking a follow-up question that builds on the previous queries. "
                "If they say things like 'now filter', 'only show', 'change to', etc., modify the previous query accordingly.\n"
            )

        full_prompt = system + history_context + f"\n\nUser question: {user_query}"
        response = model.generate_content(full_prompt)
        response_text = response.text.strip()

        result = _parse_llm_response(response_text)
        result = _validate_result(result)

        # Fix table name in all chart SQLs
        if table_name != "amazon_sales":
            for chart in result.get("charts", []):
                sql = chart.get("sql", "")
                if "amazon_sales" in sql:
                    chart["sql"] = sql.replace("amazon_sales", table_name)

        return result

    except Exception as gemini_error:
        print(f"⚠️ Gemini API failed: {str(gemini_error)}")
        print("🔄 Attempting fallback to Groq API...")

        try:
            result = generate_sql_with_groq(user_query, conversation_history, table_name, custom_schema, custom_system_prompt)
            print("✅ Successfully generated SQL using Groq fallback")
            return result
        except Exception as groq_error:
            print(f"❌ Groq fallback also failed: {str(groq_error)}")
            return {
                "can_answer": False,
                "explanation": f"Both Gemini and Groq APIs failed. Gemini: {str(gemini_error)}. Groq: {str(groq_error)}",
                "charts": [],
            }
