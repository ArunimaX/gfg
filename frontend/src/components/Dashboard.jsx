import { useState, useEffect } from 'react';
import { Database, Code, Table, ChevronDown, ChevronUp, AlertCircle, Sparkles, Loader2, ArrowRight, Lightbulb, RefreshCw } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import ChartRenderer from './ChartRenderer';

const API_URL = 'http://localhost:8000';

/* ─── Follow-up Suggestions ─── */
function FollowUpSuggestions({ result, conversationHistory, onFollowUp }) {
    const [suggestions, setSuggestions] = useState([]);
    const [loading, setLoading] = useState(false);
    const { getToken } = useAuth();

    useEffect(() => {
        if (!result?.success || !result?.query) return;

        const fetchSuggestions = async () => {
            setLoading(true);
            try {
                const token = await getToken();
                const res = await fetch(`${API_URL}/api/follow-ups`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        query: result.query,
                        sql: result.sql || '',
                        explanation: result.explanation || '',
                        columns: result.charts?.[0]?.columns || [],
                        conversation_history: conversationHistory || [],
                    }),
                });
                const data = await res.json();
                if (data.success && Array.isArray(data.suggestions)) {
                    setSuggestions(data.suggestions);
                }
            } catch {
                // Silently fail
            } finally {
                setLoading(false);
            }
        };

        fetchSuggestions();
    }, [result?.query, getToken, conversationHistory]);

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
                    <button key={i} className="followup-chip" onClick={() => onFollowUp(s)}>
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
    const { getToken } = useAuth();

    // Flatten all rows from all charts for insights
    const firstChart = result?.charts?.[0];
    const allRows = firstChart?.data?.slice(0, 30).map(d => Object.values(d)) || [];
    const cols = firstChart?.columns || [];

    useEffect(() => {
        if (!result?.success || !allRows.length) return;

        const fetchInsights = async () => {
            setLoading(true);
            try {
                const token = await getToken();
                const res = await fetch(`${API_URL}/api/insights`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        query: result.query,
                        columns: cols,
                        rows: allRows,
                        explanation: result.explanation || '',
                    }),
                });
                const data = await res.json();
                if (data.success && Array.isArray(data.insights)) {
                    setInsights(data.insights);
                }
            } catch {
                // Silently fail
            } finally {
                setLoading(false);
            }
        };

        fetchInsights();
    }, [result?.query, getToken]);

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

/* ─── Collapsible Data Table for one chart ─── */
function ChartDataTable({ chart }) {
    const [show, setShow] = useState(false);
    if (!chart.columns?.length || !chart.data?.length) return null;

    const handleDownloadCSV = () => {
        const headers = chart.columns.join(',');
        const rows = chart.data.map(row => 
            chart.columns.map(col => {
                let cell = row[col];
                // Escape quotes and commas
                if (typeof cell === 'string') {
                    cell = `"${cell.replace(/"/g, '""')}"`;
                }
                return cell ?? '';
            }).join(',')
        );
        const csvContent = [headers, ...rows].join('\n');
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', `${chart.title || 'export'}_data.csv`.replace(/\s+/g, '_').toLowerCase());
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    return (
        <div className="table-section">
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <button className="toggle-btn" onClick={() => setShow(!show)} style={{ flex: 1 }}>
                    <Table size={16} />
                    <span>Data Table ({chart.data.length} rows)</span>
                    {show ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
                {show && (
                    <button 
                        className="toggle-btn" 
                        onClick={handleDownloadCSV}
                        style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', borderColor: 'rgba(16, 185, 129, 0.2)' }}
                        title="Download as CSV"
                    >
                        <span>Download CSV</span>
                    </button>
                )}
            </div>
            {show && (
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead>
                            <tr>{chart.columns.map((col, i) => (
                                <th key={i}>{col.replace(/_/g, ' ')}</th>
                            ))}</tr>
                        </thead>
                        <tbody>
                            {chart.data.slice(0, 100).map((row, ri) => (
                                <tr key={ri}>
                                    {chart.columns.map((col, ci) => (
                                        <td key={ci}>
                                            {typeof row[col] === 'number'
                                                ? row[col].toLocaleString()
                                                : row[col] ?? '—'}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {chart.data.length > 100 && (
                        <p className="table-note">Showing first 100 of {chart.data.length} rows</p>
                    )}
                </div>
            )}
        </div>
    );
}

/* ─── Dashboard Component ─── */
export default function Dashboard({ result, conversationHistory, onFollowUp }) {
    const [showSQL, setShowSQL] = useState(false);

    if (!result) return null;

    const { success, sql, explanation, charts, error, suggestions } = result;

    if (!success) {
        return (
            <div className="dashboard-error-container">
                <div className="dashboard-error">
                    <AlertCircle size={24} />
                    <p>{error || 'Something went wrong. Please try again.'}</p>
                </div>
                {suggestions && suggestions.length > 0 && (
                    <div className="error-suggestions">
                        <div className="error-suggestions-header">
                            <RefreshCw size={14} />
                            <span>Try one of these instead:</span>
                        </div>
                        <div className="error-suggestion-chips">
                            {suggestions.map((s, i) => (
                                <button key={i} className="error-suggestion-chip" onClick={() => onFollowUp(s)}>
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

            {/* SQL Toggle (combined) */}
            {sql && (
                <div className="sql-section">
                    <button className="toggle-btn" onClick={() => setShowSQL(!showSQL)}>
                        <Code size={16} />
                        <span>Generated SQL ({charts?.length || 1} quer{charts?.length === 1 ? 'y' : 'ies'})</span>
                        {showSQL ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                    {showSQL && <pre className="sql-code">{sql}</pre>}
                </div>
            )}

            {/* Multi-chart grid */}
            {charts && charts.length > 0 && (
                <div className="charts-grid">
                    {charts.map((chart, i) => (
                        <div key={i} className="chart-with-table">
                            <ChartRenderer chart={chart} />
                            <ChartDataTable chart={chart} />
                        </div>
                    ))}
                </div>
            )}

            {/* AI Insights (from first chart data) */}
            <InsightsCard result={result} />

            {/* Follow-up Suggestions */}
            <FollowUpSuggestions
                result={result}
                conversationHistory={conversationHistory}
                onFollowUp={onFollowUp}
            />
        </div>
    );
}
