# Conversational AI for Instant Business Intelligence Dashboards

An AI-powered web application where non-technical users can type natural language business questions and instantly generate interactive dashboards with charts and insights.

## Architecture

```
User Prompt → React Frontend → FastAPI Backend → Gemini LLM → SQL Query
                                                                  ↓
              Dashboard ← Recharts ← JSON Response ← SQLite Database
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Charts | Recharts |
| Backend | Python FastAPI |
| LLM | Google Gemini (gemini-1.5-flash) |
| Database | SQLite |

## Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))

### 1. Clone & Install Backend

```bash
cd gfg

# Install Python dependencies
pip install -r requirements.txt

# Set your Gemini API key
set GEMINI_API_KEY=your_api_key_here    # Windows
# export GEMINI_API_KEY=your_api_key_here  # macOS/Linux
```

### 2. Start Backend

```bash
cd gfg
uvicorn backend.main:app --reload --port 8000
```

The backend will automatically:
- Load the Amazon Sales CSV into SQLite
- Start serving on http://localhost:8000
- API docs available at http://localhost:8000/docs

### 3. Install & Start Frontend

```bash
cd gfg/frontend
npm install
npm run dev
```

Frontend runs on http://localhost:5173

### 4. Open the App

Navigate to **http://localhost:5173** in your browser and start asking questions!

## Example Prompts

Try these queries to test the system:

1. **"Show total sales by region"**
   → Bar chart comparing revenue across regions

2. **"Which product category generated the highest revenue?"**
   → Bar chart ranking categories by revenue

3. **"Show monthly sales trend for 2023"**
   → Line chart with monthly revenue over time

4. **"Compare payment methods by total revenue"**
   → Bar + pie chart of payment method distribution

5. **"What is the average discount percentage by product category?"**
   → Bar chart of average discounts per category

6. **"Show quarterly revenue breakdown for 2022"**
   → Bar chart with Q1-Q4 revenue

7. **"Top 5 products by quantity sold"**
   → Ranked bar chart

8. **"Show average rating by category"**
   → Bar chart of product ratings

### Follow-up Questions

The system supports conversational follow-ups:

```
You: "Show sales by region"
You: "Now filter this to only show Asia"
You: "Break that down by product category"
```

## Features

- **Natural Language Queries** — Type business questions in plain English
- **Automatic Chart Selection** — AI selects the best chart type (line, bar, pie, area)
- **Interactive Charts** — Hover tooltips, legends, responsive sizing
- **SQL Transparency** — View the generated SQL query
- **Data Table** — Expandable data table with results
- **Follow-up Questions** — Conversational context for related queries
- **CSV Upload** — Upload your own CSV files and query them instantly
- **Error Handling** — Clear error messages for unsupported queries
- **Dark Mode UI** — Premium dark-themed interface with glassmorphism effects

## Dataset

**Amazon Sales Dataset** — 50,000 e-commerce transactions with 13 columns:

| Column | Type | Description |
|---|---|---|
| order_id | Integer | Unique transaction ID |
| order_date | Date | YYYY-MM-DD format (2022–2023) |
| product_id | Integer | Product identifier |
| product_category | Text | Books, Fashion, Sports, Electronics, Home & Kitchen |
| price | Float | Original price per unit |
| discount_percent | Integer | Discount % applied |
| quantity_sold | Integer | Units purchased |
| customer_region | Text | North America, Asia, Europe, etc. |
| payment_method | Text | UPI, Credit Card, Debit Card, etc. |
| rating | Float | Product rating (0–5.0) |
| review_count | Integer | Number of reviews |
| discounted_price | Float | Price after discount |
| total_revenue | Float | discounted_price × quantity_sold |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/query` | Process natural language query |
| GET | `/api/schema` | Get database schema |
| POST | `/api/upload-csv` | Upload a CSV file |
| GET | `/api/health` | Health check |
| GET | `/api/example-prompts` | Get example prompts |
