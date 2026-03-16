import { useState, useEffect } from 'react';
import { Database, Code, Table, ChevronDown, ChevronUp, AlertCircle, Sparkles, Loader2, ArrowRight, Lightbulb, RefreshCw } from 'lucide-react';
import ChartRenderer from './ChartRenderer';

const API_URL = 'http://localhost:8000';

/* ─── Follow-up Suggestions ─── */
function FollowUpSuggestions({ result, conversationHistory, onFollowUp }) {
    const [suggestions, setSuggestions] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!result?.success || !result?.query) return;

        const fetchSuggestions = async () => {
            setLoading(true);
            try {
                const res = await fetch(`${API_URL}/api/follow-ups`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: result.query,
                        sql: result.sql || '',
                        explanation: result.explanation || '',
                        columns: result.columns || [],
                        conversation_history: conversationHistory || [],
                    }),
                });
                const data = await res.json();
                if (data.success && Array.isArray(data.suggestions)) {
                    setSuggestions(data.suggestions);
                }
            } catch {
                // Silently fail — follow-ups are optional
            } finally {
                setLoading(false);
            }
        };

        fetchSuggestions();
    }, [result?.query]);

    if (loading) {
        return (
            <div className="followup-section followup-loading">
                <Loader2 className="spin" size={14} />
                <span>Generating follow-up suggestions...</span>
            </div>
        );
    }

    if (!suggestions.length) return null;

    return (
        <div className="followup-section">
            <div className="followup-header">
                <Sparkles size={14} />
                <span>You might also want to ask:</span>
            </div>
            <div className="followup-chips">
                {suggestions.map((s, i) => (
                    <button
                        key={i}
                        className="followup-chip"
                        onClick={() => onFollowUp(s)}
                    >
                        <ArrowRight size={13} className="followup-chip-icon" />
                        {s}
                    </button>
                ))}
            </div>
        </div>
    );
}

/* ─── AI Insights Card ─── */
function InsightsCard({ result }) {
    const [insights, setInsights] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!result?.success || !result?.rows?.length) return;

        const fetchInsights = async () => {
            setLoading(true);
            try {
                const res = await fetch(`${API_URL}/api/insights`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: result.query,
                        columns: result.columns || [],
                        rows: result.rows?.slice(0, 30) || [],
                        explanation: result.explanation || '',
                    }),
                });
                const data = await res.json();
                if (data.success && Array.isArray(data.insights)) {
                    setInsights(data.insights);
                }
            } catch {
                // Silently fail — insights are optional
            } finally {
                setLoading(false);
            }
        };

        fetchInsights();
    }, [result?.query]);

    if (loading) {
        return (
            <div className="insights-card insights-loading">
                <Loader2 className="spin" size={15} />
                <span>Generating AI insights...</span>
            </div>
        );
    }

    if (!insights.length) return null;

    return (
        <div className="insights-card">
            <div className="insights-header">
                <Lightbulb size={16} />
                <span>Key Insights</span>
            </div>
            <ul className="insights-list">
                {insights.map((insight, i) => (
                    <li key={i} className="insight-item">{insight}</li>
                ))}
            </ul>
        </div>
    );
}

/* ─── Dashboard Component ─── */
export default function Dashboard({ result, conversationHistory, onFollowUp }) {
    const [showSQL, setShowSQL] = useState(false);
    const [showTable, setShowTable] = useState(false);

    if (!result) return null;

    const { success, sql, explanation, columns, rows, row_count, charts, error, suggestions } = result;

    // Convert rows to objects for Recharts
    const chartData = rows?.map(row => {
        const obj = {};
        columns?.forEach((col, i) => {
            const val = row[i];
            const num = Number(val);
            obj[col] = isNaN(num) || val === null || val === '' ? val : num;
        });
        return obj;
    }) || [];

    if (!success) {
        return (
            <div className="dashboard-error-container">
                <div className="dashboard-error">
                    <AlertCircle size={24} />
                    <p>{error || 'Something went wrong. Please try again.'}</p>
                </div>
                {/* Smart error recovery: show dataset suggestions */}
                {suggestions && suggestions.length > 0 && (
                    <div className="error-suggestions">
                        <div className="error-suggestions-header">
                            <RefreshCw size={14} />
                            <span>Try one of these instead:</span>
                        </div>
                        <div className="error-suggestion-chips">
                            {suggestions.map((s, i) => (
                                <button
                                    key={i}
                                    className="error-suggestion-chip"
                                    onClick={() => onFollowUp(s)}
                                >
                                    <ArrowRight size={13} />
                                    {s}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className="dashboard">
            {/* Explanation */}
            {explanation && (
                <div className="explanation-card">
                    <Database size={18} />
                    <p>{explanation}</p>
                </div>
            )}

            {/* SQL Toggle */}
            {sql && (
                <div className="sql-section">
                    <button className="toggle-btn" onClick={() => setShowSQL(!showSQL)}>
                        <Code size={16} />
                        <span>Generated SQL</span>
                        {showSQL ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                    {showSQL && (
                        <pre className="sql-code">{sql}</pre>
                    )}
                </div>
            )}

            {/* Charts */}
            {charts && charts.length > 0 && (
                <div className="charts-grid">
                    {charts.map((chart, i) => (
                        <ChartRenderer key={i} chart={chart} data={chartData} />
                    ))}
                </div>
            )}

            {/* AI Insights */}
            <InsightsCard result={result} />

            {/* Data Table Toggle */}
            {columns && columns.length > 0 && (
                <div className="table-section">
                    <button className="toggle-btn" onClick={() => setShowTable(!showTable)}>
                        <Table size={16} />
                        <span>Data Table ({row_count} rows)</span>
                        {showTable ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                    {showTable && (
                        <div className="data-table-wrapper">
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        {columns.map((col, i) => (
                                            <th key={i}>{col.replace(/_/g, ' ')}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {rows.slice(0, 100).map((row, ri) => (
                                        <tr key={ri}>
                                            {row.map((cell, ci) => (
                                                <td key={ci}>
                                                    {typeof cell === 'number'
                                                        ? cell.toLocaleString()
                                                        : cell ?? '—'}
                                                </td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {rows.length > 100 && (
                                <p className="table-note">Showing first 100 of {row_count} rows</p>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* Follow-up Suggestions */}
            <FollowUpSuggestions
                result={result}
                conversationHistory={conversationHistory}
                onFollowUp={onFollowUp}
            />
        </div>
    );
}
