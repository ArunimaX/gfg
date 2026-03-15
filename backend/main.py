"""FastAPI backend for the Conversational AI BI Dashboard."""

import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

import traceback
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .database import init_db, execute_query, get_table_info, load_uploaded_csv
from .llm_engine import generate_sql
from .chart_selector import select_chart_type

app = FastAPI(
    title="AI BI Dashboard API",
    description="Convert natural language queries to interactive dashboards",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    conversation_history: list[dict] = []
    table_name: str = "amazon_sales"


class QueryResponse(BaseModel):
    success: bool
    sql: str = ""
    explanation: str = ""
    columns: list[str] = []
    rows: list[list] = []
    row_count: int = 0
    charts: list[dict] = []
    error: str = ""


@app.on_event("startup")
async def startup():
    """Load CSV data into SQLite on startup."""
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        traceback.print_exc()


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "message": "AI BI Dashboard API is running"}


@app.get("/api/schema")
async def schema():
    """Get the current database schema."""
    try:
        info = get_table_info()
        return {"success": True, "schema": info}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Process a natural language query:
    1. Send to Gemini LLM to generate SQL
    2. Execute SQL on SQLite
    3. Select appropriate chart types
    4. Return structured results
    """
    try:
        # Step 1: Generate SQL from natural language
        llm_result = generate_sql(
            user_query=request.query,
            conversation_history=request.conversation_history,
            table_name=request.table_name,
        )

        if not llm_result.get("can_answer", False):
            explanation_text = llm_result.get("explanation", "")
            error_msg = "Sorry, the available dataset does not contain information to answer this question."
            
            # Surface actual API errors to the user instead of masking them
            if "Error" in explanation_text or "Failed" in explanation_text:
                error_msg = explanation_text
                
            return QueryResponse(
                success=False,
                explanation=explanation_text,
                error=error_msg,
            )

        sql = llm_result["sql"]
        if not sql:
            return QueryResponse(
                success=False,
                error="The AI could not generate a valid SQL query for your question.",
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

        return QueryResponse(
            success=True,
            sql=sql,
            explanation=llm_result.get("explanation", ""),
            columns=result["columns"],
            rows=result["rows"],
            row_count=result["row_count"],
            charts=charts,
        )

    except Exception as e:
        traceback.print_exc()
        return QueryResponse(
            success=False,
            error=f"An unexpected error occurred: {str(e)}",
        )


@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Upload a CSV file and make it queryable."""
    try:
        content = await file.read()
        csv_text = content.decode("utf-8", errors="replace")

        # Use filename (without extension) as table name
        table_name = file.filename.rsplit(".", 1)[0] if file.filename else "uploaded_data"
        table_name = table_name.replace(" ", "_").replace("-", "_").lower()

        result = load_uploaded_csv(csv_text, table_name)

        return {
            "success": True,
            "message": f"Uploaded {result['row_count']} rows into table '{result['table_name']}'",
            "table_name": result["table_name"],
            "columns": result["columns"],
            "row_count": result["row_count"],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/example-prompts")
async def example_prompts():
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
