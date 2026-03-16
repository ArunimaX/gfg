import {
    LineChart, Line,
    BarChart, Bar, Cell,
    PieChart, Pie,
    AreaChart, Area,
    ScatterChart, Scatter,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer, ZAxis,
} from 'recharts';

const PALETTE = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#f472b6', '#34d399'];
const HIGHLIGHT_COLOR = '#f59e0b';
const DEFAULT_COLOR = '#6366f1';

function formatValue(value) {
    if (typeof value !== 'number') return value;
    if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
    return value % 1 !== 0 ? value.toFixed(2) : value;
}

function CustomTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null;
    return (
        <div className="custom-tooltip">
            <p className="tooltip-label">{label}</p>
            {payload.map((entry, i) => (
                <p key={i} className="tooltip-value" style={{ color: entry.color }}>
                    {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
                </p>
            ))}
        </div>
    );
}

export default function ChartRenderer({ chart }) {
    const { chart_type, title, x_axis, y_axis, group_by, insight, data = [], columns = [], error } = chart;

    // ── Error card ─────────────────────────────────────────────────────────────
    if (error) {
        return (
            <div className="chart-card chart-error-card">
                <div className="chart-header">
                    <h3 className="chart-title">{title || 'Chart'}</h3>
                    <span className="chart-badge" style={{ background: 'rgba(248,113,113,0.2)', color: '#f87171' }}>ERROR</span>
                </div>
                <p style={{ color: '#f87171', fontSize: '0.9rem', padding: '12px 0' }}>{error}</p>
            </div>
        );
    }

    if (!data || data.length === 0) {
        return (
            <div className="chart-card">
                <div className="chart-header">
                    <h3 className="chart-title">{title || 'Chart'}</h3>
                    <span className="chart-badge">NO DATA</span>
                </div>
                <p style={{ color: '#64748b', fontSize: '0.9rem', padding: '20px 0', textAlign: 'center' }}>No data returned for this chart.</p>
            </div>
        );
    }

    const xKey = x_axis || (columns[0] ?? Object.keys(data[0])[0]);
    const yKey = y_axis || (columns[1] ?? Object.keys(data[0])[1]);
    const hasHighlight = data.some(d => d.is_top !== undefined);

    // ── Derive group keys (for grouped bar/line/area) ─────────────────────────
    let groupKeys = [];
    let groupData = data;
    if (group_by) {
        const uniqueGroups = [...new Set(data.map(d => d[group_by]))].filter(Boolean);
        groupKeys = uniqueGroups;

        // Pivot if the data is in long format (each row has group_by value)
        const pivotMap = new Map();
        data.forEach(row => {
            const xVal = row[xKey];
            if (!pivotMap.has(xVal)) pivotMap.set(xVal, { [xKey]: xVal });
            const entry = pivotMap.get(xVal);
            entry[row[group_by]] = row[yKey];
        });
        groupData = Array.from(pivotMap.values());
    }

    const renderChart = () => {
        switch (chart_type) {

            // ── LINE ────────────────────────────────────────────────────────────
            case 'line':
                return (
                    <ResponsiveContainer width="100%" height={360}>
                        <LineChart data={group_by ? groupData : data} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
                            <defs>
                                {(group_by ? groupKeys : [yKey]).map((key, i) => (
                                    <linearGradient key={key} id={`lineG${i}`} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor={PALETTE[i % PALETTE.length]} stopOpacity={1} />
                                        <stop offset="100%" stopColor={PALETTE[i % PALETTE.length]} stopOpacity={0.6} />
                                    </linearGradient>
                                ))}
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                            <XAxis dataKey={xKey} tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#334155' }} />
                            <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#334155' }} tickFormatter={formatValue} />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend wrapperStyle={{ color: '#cbd5e1' }} />
                            {(group_by ? groupKeys : [yKey]).map((key, i) => (
                                <Line key={key} type="monotone" dataKey={key} stroke={PALETTE[i % PALETTE.length]}
                                    strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 6 }} />
                            ))}
                        </LineChart>
                    </ResponsiveContainer>
                );

            // ── BAR ─────────────────────────────────────────────────────────────
            case 'bar':
                if (group_by) {
                    // Grouped bar - multiple <Bar> components
                    return (
                        <ResponsiveContainer width="100%" height={360}>
                            <BarChart data={groupData} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                                <XAxis dataKey={xKey} tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#334155' }} />
                                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#334155' }} tickFormatter={formatValue} />
                                <Tooltip content={<CustomTooltip />} />
                                <Legend wrapperStyle={{ color: '#cbd5e1' }} />
                                {groupKeys.map((key, i) => (
                                    <Bar key={key} dataKey={key} fill={PALETTE[i % PALETTE.length]} radius={[4, 4, 0, 0]} maxBarSize={40} />
                                ))}
                            </BarChart>
                        </ResponsiveContainer>
                    );
                }
                // Simple bar with optional is_top highlight
                return (
                    <ResponsiveContainer width="100%" height={360}>
                        <BarChart data={data} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
                            <defs>
                                <linearGradient id="barGrad0" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor={DEFAULT_COLOR} stopOpacity={0.9} />
                                    <stop offset="100%" stopColor={DEFAULT_COLOR} stopOpacity={0.5} />
                                </linearGradient>
                                <linearGradient id="barGradHL" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor={HIGHLIGHT_COLOR} stopOpacity={0.95} />
                                    <stop offset="100%" stopColor={HIGHLIGHT_COLOR} stopOpacity={0.6} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                            <XAxis dataKey={xKey} tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#334155' }} />
                            <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#334155' }} tickFormatter={formatValue} />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend wrapperStyle={{ color: '#cbd5e1' }} />
                            <Bar dataKey={yKey} radius={[6, 6, 0, 0]} maxBarSize={60}>
                                {data.map((entry, index) => (
                                    <Cell
                                        key={index}
                                        fill={hasHighlight && entry.is_top === 1 ? 'url(#barGradHL)' : 'url(#barGrad0)'}
                                    />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                );

            // ── PIE ─────────────────────────────────────────────────────────────
            case 'pie':
                return (
                    <ResponsiveContainer width="100%" height={360}>
                        <PieChart>
                            <Pie
                                data={data}
                                dataKey={yKey}
                                nameKey={xKey}
                                cx="50%"
                                cy="50%"
                                outerRadius={140}
                                innerRadius={60}
                                paddingAngle={3}
                                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(1)}%)`}
                                labelLine={{ stroke: '#64748b' }}
                            >
                                {data.map((_, i) => (
                                    <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                                ))}
                            </Pie>
                            <Tooltip content={<CustomTooltip />} />
                            <Legend wrapperStyle={{ color: '#cbd5e1' }} />
                        </PieChart>
                    </ResponsiveContainer>
                );

            // ── AREA ────────────────────────────────────────────────────────────
            case 'area':
                return (
                    <ResponsiveContainer width="100%" height={360}>
                        <AreaChart data={group_by ? groupData : data} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
                            <defs>
                                {(group_by ? groupKeys : [yKey]).map((key, i) => (
                                    <linearGradient key={key} id={`areaG${i}`} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor={PALETTE[i % PALETTE.length]} stopOpacity={0.4} />
                                        <stop offset="100%" stopColor={PALETTE[i % PALETTE.length]} stopOpacity={0.05} />
                                    </linearGradient>
                                ))}
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                            <XAxis dataKey={xKey} tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#334155' }} />
                            <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#334155' }} tickFormatter={formatValue} />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend wrapperStyle={{ color: '#cbd5e1' }} />
                            {(group_by ? groupKeys : [yKey]).map((key, i) => (
                                <Area key={key} type="monotone" dataKey={key}
                                    stroke={PALETTE[i % PALETTE.length]}
                                    fill={`url(#areaG${i})`} strokeWidth={2} />
                            ))}
                        </AreaChart>
                    </ResponsiveContainer>
                );

            // ── SCATTER ─────────────────────────────────────────────────────────
            case 'scatter': {
                // Normalize data: ensure x and y are numeric
                const scatterData = data.map(d => ({
                    [xKey]: typeof d[xKey] === 'number' ? d[xKey] : parseFloat(d[xKey]) || 0,
                    [yKey]: typeof d[yKey] === 'number' ? d[yKey] : parseFloat(d[yKey]) || 0,
                    ...d,
                }));
                return (
                    <ResponsiveContainer width="100%" height={360}>
                        <ScatterChart margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                            <XAxis dataKey={xKey} type="number" name={xKey} tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#334155' }} tickFormatter={formatValue} label={{ value: xKey, position: 'bottom', fill: '#94a3b8', fontSize: 12 }} />
                            <YAxis dataKey={yKey} type="number" name={yKey} tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#334155' }} tickFormatter={formatValue} />
                            <ZAxis range={[60, 60]} />
                            <Tooltip cursor={{ strokeDasharray: '3 3' }} content={<CustomTooltip />} />
                            <Legend wrapperStyle={{ color: '#cbd5e1' }} />
                            <Scatter name={`${xKey} vs ${yKey}`} data={scatterData} fill={PALETTE[0]} fillOpacity={0.8} />
                        </ScatterChart>
                    </ResponsiveContainer>
                );
            }

            // ── KPI ─────────────────────────────────────────────────────────────
            case 'kpi': {
                const numericKeys = columns.filter(col =>
                    data.length > 0 && typeof data[0][col] === 'number'
                );
                return (
                    <div className="kpi-grid">
                        {numericKeys.map((key, i) => {
                            const val = data[0][key];
                            return (
                                <div key={key} className="kpi-card-inner">
                                    <div className="kpi-label">{key.replace(/_/g, ' ').toUpperCase()}</div>
                                    <div className="kpi-value" style={{ color: PALETTE[i % PALETTE.length] }}>
                                        {typeof val === 'number' && val % 1 !== 0
                                            ? val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                                            : val?.toLocaleString()}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                );
            }

            default:
                return <p className="no-chart" style={{ color: '#64748b', textAlign: 'center', padding: '20px' }}>Unsupported chart type: {chart_type}</p>;
        }
    };

    const badgeStyle = {
        kpi: { background: 'rgba(99,102,241,0.2)', color: '#a78bfa' },
        line: { background: 'rgba(6,182,212,0.15)', color: '#06b6d4' },
        area: { background: 'rgba(16,185,129,0.15)', color: '#10b981' },
        bar: { background: 'rgba(99,102,241,0.12)', color: '#818cf8' },
        pie: { background: 'rgba(245,158,11,0.15)', color: '#f59e0b' },
        scatter: { background: 'rgba(239,68,68,0.12)', color: '#f87171' },
    };

    return (
        <div className="chart-card">
            <div className="chart-header">
                <h3 className="chart-title">{title || 'Query Results'}</h3>
                <span className="chart-badge" style={badgeStyle[chart_type] || {}}>
                    {(chart_type || 'chart').toUpperCase()}
                </span>
            </div>
            {insight && (
                <div className="chart-insight">
                    <span className="insight-dot">💡</span>
                    {insight}
                </div>
            )}
            {renderChart()}
        </div>
    );
}
