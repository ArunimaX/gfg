import { useState } from 'react';
import { Database, Code, Table, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';
import ChartRenderer from './ChartRenderer';

export default function Dashboard({ result }) {
    const [showSQL, setShowSQL] = useState(false);
    const [showTable, setShowTable] = useState(false);

    if (!result) return null;

    const { success, sql, explanation, columns, rows, row_count, charts, error } = result;

    // Convert rows to objects for Recharts
    const chartData = rows?.map(row => {
        const obj = {};
        columns?.forEach((col, i) => {
            // Try to parse numeric values
            const val = row[i];
            const num = Number(val);
            obj[col] = isNaN(num) || val === null || val === '' ? val : num;
        });
        return obj;
    }) || [];

    if (!success) {
        return (
            <div className="dashboard-error">
                <AlertCircle size={24} />
                <p>{error || 'Something went wrong. Please try again.'}</p>
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
        </div>
    );
}
