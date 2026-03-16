import {
    LineChart, Line,
    BarChart, Bar,
    PieChart, Pie, Cell,
    AreaChart, Area,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer,
} from 'recharts';

const COLORS = [
    '#3B7A3B', '#5DA25D', '#2D5A2D', '#7DBF7D',
    '#4A6B4A', '#8FBC8F', '#6B8F6B', '#C4A84B',
    '#2B4F2B', '#A0C49D', '#3D6B3D', '#D4C9B5',
];

const CHART_COLORS = {
    primary: '#3B7A3B',
    secondary: '#5DA25D',
    tertiary: '#7DBF7D',
    quaternary: '#8FBC8F',
};

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

export default function ChartRenderer({ chart, data }) {
    if (!data || data.length === 0) return null;

    const { type, title, xKey, yKeys, nameKey, valueKey } = chart;

    const renderChart = () => {
        switch (type) {
            case 'line':
                return (
                    <ResponsiveContainer width="100%" height={380}>
                        <LineChart data={data} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
                            <defs>
                                {(yKeys || []).map((key, i) => (
                                    <linearGradient key={key} id={`lineGrad${i}`} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor={COLORS[i % COLORS.length]} stopOpacity={1} />
                                        <stop offset="100%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.6} />
                                    </linearGradient>
                                ))}
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(107,143,107,0.15)" />
                            <XAxis dataKey={xKey} tick={{ fill: '#9BAA9B', fontSize: 12 }} axisLine={{ stroke: '#4A6B4A' }} />
                            <YAxis tick={{ fill: '#9BAA9B', fontSize: 12 }} axisLine={{ stroke: '#4A6B4A' }} tickFormatter={formatValue} />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend wrapperStyle={{ color: '#D4C9B5' }} />
                            {(yKeys || []).map((key, i) => (
                                <Line
                                    key={key}
                                    type="monotone"
                                    dataKey={key}
                                    stroke={COLORS[i % COLORS.length]}
                                    strokeWidth={2.5}
                                    dot={{ r: 3, fill: COLORS[i % COLORS.length] }}
                                    activeDot={{ r: 6, strokeWidth: 2 }}
                                />
                            ))}
                        </LineChart>
                    </ResponsiveContainer>
                );

            case 'bar':
                return (
                    <ResponsiveContainer width="100%" height={380}>
                        <BarChart data={data} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
                            <defs>
                                {(yKeys || []).map((key, i) => (
                                    <linearGradient key={key} id={`barGrad${i}`} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.9} />
                                        <stop offset="100%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.5} />
                                    </linearGradient>
                                ))}
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(107,143,107,0.15)" />
                            <XAxis dataKey={xKey} tick={{ fill: '#9BAA9B', fontSize: 12 }} axisLine={{ stroke: '#4A6B4A' }} />
                            <YAxis tick={{ fill: '#9BAA9B', fontSize: 12 }} axisLine={{ stroke: '#4A6B4A' }} tickFormatter={formatValue} />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend wrapperStyle={{ color: '#D4C9B5' }} />
                            {(yKeys || []).map((key, i) => (
                                <Bar
                                    key={key}
                                    dataKey={key}
                                    fill={`url(#barGrad${i})`}
                                    radius={[6, 6, 0, 0]}
                                    maxBarSize={60}
                                />
                            ))}
                        </BarChart>
                    </ResponsiveContainer>
                );

            case 'pie':
                return (
                    <ResponsiveContainer width="100%" height={380}>
                        <PieChart>
                            <Pie
                                data={data}
                                dataKey={valueKey || yKeys?.[0] || 'value'}
                                nameKey={nameKey || xKey || 'name'}
                                cx="50%"
                                cy="50%"
                                outerRadius={140}
                                innerRadius={60}
                                paddingAngle={3}
                                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(1)}%)`}
                                labelLine={{ stroke: '#6B8F6B' }}
                            >
                                {data.map((_, i) => (
                                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip content={<CustomTooltip />} />
                            <Legend wrapperStyle={{ color: '#D4C9B5' }} />
                        </PieChart>
                    </ResponsiveContainer>
                );

            case 'area':
                return (
                    <ResponsiveContainer width="100%" height={380}>
                        <AreaChart data={data} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
                            <defs>
                                {(yKeys || []).map((key, i) => (
                                    <linearGradient key={key} id={`areaGrad${i}`} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.4} />
                                        <stop offset="100%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.05} />
                                    </linearGradient>
                                ))}
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(107,143,107,0.15)" />
                            <XAxis dataKey={xKey} tick={{ fill: '#9BAA9B', fontSize: 12 }} axisLine={{ stroke: '#4A6B4A' }} />
                            <YAxis tick={{ fill: '#9BAA9B', fontSize: 12 }} axisLine={{ stroke: '#4A6B4A' }} tickFormatter={formatValue} />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend wrapperStyle={{ color: '#D4C9B5' }} />
                            {(yKeys || []).map((key, i) => (
                                <Area
                                    key={key}
                                    type="monotone"
                                    dataKey={key}
                                    stroke={COLORS[i % COLORS.length]}
                                    fill={`url(#areaGrad${i})`}
                                    strokeWidth={2}
                                />
                            ))}
                        </AreaChart>
                    </ResponsiveContainer>
                );

            default:
                return <p className="no-chart">Unsupported chart type: {type}</p>;
        }
    };

    return (
        <div className="chart-card">
            <div className="chart-header">
                <h3 className="chart-title">{title || 'Query Results'}</h3>
                <span className="chart-badge">{type.toUpperCase()}</span>
            </div>
            {renderChart()}
        </div>
    );
}
