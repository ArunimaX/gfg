"""FastAPI backend for the Conversational AI BI Dashboard."""

import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

import traceback
import json as json_mod
import re
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from .database import (
    init_db,
    get_all_tables,
    load_uploaded_csv,
    get_dynamic_table_info,
    get_dataset_capabilities,
    create_chat_session,
    add_chat_message,
    get_user_sessions,
    get_session_messages,
    execute_query,
)
from .llm_engine import generate_sql, generate_sql_with_groq, build_dynamic_system_prompt
from .chart_selector import select_chart_type
from .auth import verify_token

app = FastAPI()

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize the database on startup
@app.on_event("startup")
def startup_event():
    init_db()
    # Triggered reload to load .env 

_schema_cache = {}

# Request Models
class QueryRequest(BaseModel):
    query: str
    conversation_history: List[Dict[str, str]] = []
    table_name: str = "amazon_sales"
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    success: bool
    sql: Optional[str] = None
    explanation: Optional[str] = None
    columns: Optional[List[str]] = None
    rows: Optional[List[list]] = None
    row_count: Optional[int] = None
    charts: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    suggestions: List[str] = []
    session_id: Optional[str] = None

class FollowUpRequest(BaseModel):
    query: str
    columns: List[str]
    explanation: Optional[str] = None
    conversation_history: List[Dict[str, str]] = []

class InsightsRequest(BaseModel):
    query: str
    columns: List[str]
    rows: List[list]
    explanation: Optional[str] = None


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "message": "AI BI Dashboard API is running"}


@app.get("/api/schema")
async def schema(user_id: str = Depends(verify_token)):
    """Get the current database schema."""
    try:
        info = get_dynamic_table_info("amazon_sales")
        return {"success": True, "schema": info}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/tables")
async def list_tables(user_id: str = Depends(verify_token)):
    """List all available tables in the database."""
    try:
        tables = get_all_tables()
        result = []
        for t in tables:
            try:
                info = get_dynamic_table_info(t)
                result.append({
                    "name": t,
                    "columns": [c["name"] for c in info["columns"]],
                    "row_count": info["row_count"],
                })
            except Exception:
                result.append({"name": t, "columns": [], "row_count": 0})
        return {"success": True, "tables": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/sessions")
async def get_sessions(user_id: str = Depends(verify_token)):
    """List all past chat sessions for the authenticated user."""
    try:
        sessions = get_user_sessions(user_id)
        return {"success": True, "sessions": sessions}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/sessions/{session_id}")
async def get_session_history(session_id: str, user_id: str = Depends(verify_token)):
    """Get messages for a specific session."""
    try:
        messages = get_session_messages(session_id, user_id)
        return {"success": True, "messages": messages}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest, user_id: str = Depends(verify_token)):
    """
    Process a natural language query:
    1. Send to Gemini LLM to generate SQL
    2. Execute SQL on SQLite
    3. Select appropriate chart types
    4. Return structured results with smart error recovery
    """
    try:
        session_id = request.session_id
        if not session_id:
            title = request.query[:50] + "..." if len(request.query) > 50 else request.query
            session_id = create_chat_session(user_id, title, request.table_name)
            request.session_id = session_id

        # Determine if we need a custom system prompt for non-default tables
        custom_system_prompt = None
        if request.table_name != "amazon_sales":
            if request.table_name in _schema_cache:
                custom_system_prompt = _schema_cache[request.table_name]
            else:
                # Try to build one dynamically
                try:
                    info = get_dynamic_table_info(request.table_name)
                    custom_system_prompt = build_dynamic_system_prompt(info["schema_prompt"])
                    _schema_cache[request.table_name] = custom_system_prompt
                except Exception:
                    pass

        # Step 1: Generate SQL from natural language
        llm_result = generate_sql(
            user_query=request.query,
            conversation_history=request.conversation_history,
            table_name=request.table_name,
            custom_system_prompt=custom_system_prompt,
        )

        if not llm_result.get("can_answer", False):
            explanation_text = llm_result.get("explanation", "")
            error_msg = "Sorry, the available dataset does not contain information to answer this question."

            # Surface actual API errors to the user instead of masking them
            if "Error" in explanation_text or "Failed" in explanation_text:
                error_msg = explanation_text

            # Smart error recovery: suggest what the dataset CAN answer
            suggestions = []
            try:
                caps = get_dataset_capabilities(request.table_name)
                suggestions = caps.get("suggestions", [])
            except Exception:
                pass

            return QueryResponse(
                success=False,
                explanation=explanation_text,
                error=error_msg,
                suggestions=suggestions,
            )

        sql = llm_result["sql"]
        if not sql:
            # Smart error recovery here too
            suggestions = []
            try:
                caps = get_dataset_capabilities(request.table_name)
                suggestions = caps.get("suggestions", [])
            except Exception:
                pass
            return QueryResponse(
                success=False,
                error="The AI could not generate a valid SQL query for your question.",
                suggestions=suggestions,
            )

        # Step 2: Execute SQL
        try:
            result = execute_query(sql)
        except Exception as e:
            error_msg = str(e)
            return QueryResponse(
                success=False,
                sql=sql,
                explanation=llm_result.get("explanation", ""),
                error=f"SQL execution error: {error_msg}. Please try rephrasing your question.",
            )

        # Step 3: Select chart types
        charts = select_chart_type(
            sql=sql,
            columns=result["columns"],
            rows=result["rows"],
            user_query=request.query,
        )

        add_chat_message(
            session_id=session_id,
            role="user",
            content=request.query
        )
        add_chat_message(
            session_id=session_id,
            role="assistant",
            content=llm_result.get("explanation", "Here is your data."),
            sql_query=sql,
            result_summary=f"Found {result['row_count']} rows."
        )

        return QueryResponse(
            success=True,
            sql=sql,
            explanation=llm_result.get("explanation", ""),
            columns=result["columns"],
            rows=result["rows"],
            row_count=result["row_count"],
            charts=charts,
            session_id=session_id,
        )

    except Exception as e:
        traceback.print_exc()
        return QueryResponse(
            success=False,
            error=f"An unexpected error occurred: {str(e)}",
        )


@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...), user_id: str = Depends(verify_token)):
    """Upload a CSV file and make it queryable with auto-detected schema."""
    try:
        content = await file.read()
        csv_text = content.decode("utf-8", errors="replace")

        # Use filename (without extension) as table name
        table_name = file.filename.rsplit(".", 1)[0] if file.filename else "uploaded_data"
        table_name = table_name.replace(" ", "_").replace("-", "_").lower()

        result = load_uploaded_csv(csv_text, table_name)

        # Cache the dynamic system prompt for this table
        schema_prompt = result.get("schema_prompt", "")
        if schema_prompt:
            _schema_cache[table_name] = build_dynamic_system_prompt(schema_prompt)

        return {
            "success": True,
            "message": f"Uploaded {result['row_count']} rows into table '{result['table_name']}'",
            "table_name": result["table_name"],
            "columns": result["columns"],
            "col_types": result.get("col_types", []),
            "row_count": result["row_count"],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/example-prompts")
async def example_prompts(user_id: str = Depends(verify_token)):
    """Return example prompts for the user."""
    return {
        "prompts": [
            "Show total sales by region",
            "Which product category generated the highest revenue?",
            "Show monthly sales trend for 2023",
            "What is the average discount percentage by product category?",
            "Show the top 5 products by revenue",
            "Compare payment methods by total revenue",
            "Show quarterly revenue breakdown for 2022",
            "What is the average rating by product category?",
        ]
    }


@app.post("/api/follow-ups")
async def generate_follow_ups(request: FollowUpRequest, user_id: str = Depends(verify_token)):
    """Generate smart follow-up question suggestions based on the current query result."""
    try:
        import google.generativeai as genai

        columns_str = ", ".join(request.columns) if request.columns else "unknown"
        history_ctx = ""
        if request.conversation_history:
            recent = request.conversation_history[-3:]
            history_ctx = "Previous queries in this session:\n"
            for h in recent:
                history_ctx += f"- {h.get('query', '')}\n"

        prompt = f"""You are a helpful data analyst assistant. A user just queried a business dashboard and got results.

{history_ctx}
Current query: "{request.query}"
Result columns: {columns_str}
Explanation: {request.explanation or 'No explanation provided.'}

Generate exactly 3 concise, insightful follow-up questions the user might want to ask next to explore the data further.
These should be natural extensions or deeper dives based on what was just shown.
Return ONLY a JSON array of 3 strings, no markdown, no extra text. Example:
["Question 1?", "Question 2?", "Question 3?"]"""

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        text = text.strip()

        suggestions = json_mod.loads(text)
        if not isinstance(suggestions, list):
            raise ValueError("LLM did not return a list")
        suggestions = [str(s) for s in suggestions[:3]]

        return {"success": True, "suggestions": suggestions}

    except Exception as e:
        # Fallback: return generic suggestions related to the query
        fallback = [
            f"Break down '{request.query}' by product category",
            f"Compare this result across different customer regions",
            f"Show the trend over time for this analysis",
        ]
        return {"success": True, "suggestions": fallback}


@app.post("/api/insights")
async def generate_insights(request: InsightsRequest, user_id: str = Depends(verify_token)):
    """Generate AI-powered text insights from query results."""
    try:
        import google.generativeai as genai

        # Build a data summary from rows (limit to first 30 rows for the LLM)
        sample_rows = request.rows[:30] if request.rows else []
        data_summary = ""
        if request.columns and sample_rows:
            data_summary = f"Columns: {', '.join(request.columns)}\n"
            data_summary += "Data:\n"
            for row in sample_rows:
                row_str = " | ".join(str(v) for v in row)
                data_summary += f"  {row_str}\n"

        prompt = f"""You are a senior business analyst reviewing dashboard results. Analyze the data and provide exactly 3 concise, actionable insights.

User's question: "{request.query}"
{f'Query explanation: {request.explanation}' if request.explanation else ''}

{data_summary}

Rules:
- Each insight should be a single sentence, max 25 words.
- Focus on KEY FINDINGS: trends, outliers, notable comparisons, or business implications.
- Use specific numbers from the data when possible.
- Do NOT repeat the query or explain what the chart shows — provide NEW insight.
- Return ONLY a JSON array of 3 strings, no markdown. Example:
["Insight 1.", "Insight 2.", "Insight 3."]"""

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        text = text.strip()

        insights = json_mod.loads(text)
        if not isinstance(insights, list):
            raise ValueError("LLM did not return a list")
        insights = [str(s) for s in insights[:3]]

        return {"success": True, "insights": insights}

    except Exception as e:
        return {"success": False, "insights": [], "error": str(e)}
