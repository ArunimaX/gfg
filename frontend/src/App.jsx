import { useState, useRef } from 'react';
import { BarChart3, Upload, X, MessageSquare, Trash2, Database } from 'lucide-react';
import QueryInput from './components/QueryInput';
import Dashboard from './components/Dashboard';
import './App.css';

const API_URL = 'http://localhost:8000';

function App() {
    const [results, setResults] = useState([]);
    const [conversationHistory, setConversationHistory] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState(null);
    const [activeTable, setActiveTable] = useState('amazon_sales');
    const fileInputRef = useRef(null);
    const bottomRef = useRef(null);

    const handleQuery = async (query) => {
        setIsLoading(true);
        try {
            const response = await fetch(`${API_URL}/api/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query,
                    conversation_history: conversationHistory,
                    table_name: activeTable,
                }),
            });
            const data = await response.json();

            // Add to results
            setResults(prev => [...prev, { query, ...data }]);

            // Update conversation history
            if (data.success) {
                setConversationHistory(prev => [...prev, { query, sql: data.sql }]);
            }

            // Scroll to bottom
            setTimeout(() => {
                bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
            }, 100);
        } catch (err) {
            setResults(prev => [
                ...prev,
                {
                    query,
                    success: false,
                    error: 'Could not connect to the backend. Make sure the server is running on port 8000.',
                },
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleFileUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploadStatus({ loading: true, message: 'Uploading and analyzing schema...' });
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${API_URL}/api/upload-csv`, {
                method: 'POST',
                body: formData,
            });
            const data = await response.json();
            if (data.success) {
                setActiveTable(data.table_name);
                // Clear conversation history for new dataset
                setConversationHistory([]);
                setUploadStatus({
                    loading: false,
                    success: true,
                    message: `✅ ${data.message}. Schema auto-detected — you can now query this data.`,
                });
            } else {
                setUploadStatus({ loading: false, success: false, message: `❌ ${data.error}` });
            }
        } catch {
            setUploadStatus({ loading: false, success: false, message: '❌ Upload failed. Check server.' });
        }

        // Reset file input
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const clearHistory = () => {
        setResults([]);
        setConversationHistory([]);
    };

    const switchToDefault = () => {
        setActiveTable('amazon_sales');
        setResults([]);
        setConversationHistory([]);
        setUploadStatus(null);
    };

    return (
        <div className="app">
            {/* Ambient background effects */}
            <div className="bg-gradient-orb orb-1" />
            <div className="bg-gradient-orb orb-2" />
            <div className="bg-gradient-orb orb-3" />

            {/* Header */}
            <header className="header">
                <div className="header-content">
                    <div className="logo-section">
                        <div className="logo-icon">
                            <BarChart3 size={28} />
                        </div>
                        <div>
                            <h1 className="app-title">AI Business Intelligence</h1>
                            <p className="app-subtitle">Ask questions in plain English. Get instant dashboards.</p>
                        </div>
                    </div>
                    <div className="header-actions">
                        {/* Active dataset badge */}
                        {activeTable !== 'amazon_sales' && (
                            <button className="action-btn dataset-badge" onClick={switchToDefault}>
                                <Database size={14} />
                                <span>{activeTable}</span>
                                <X size={13} />
                            </button>
                        )}
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".csv"
                            onChange={handleFileUpload}
                            style={{ display: 'none' }}
                            id="csv-upload"
                        />
                        <button
                            className="action-btn upload-btn"
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <Upload size={16} />
                            <span>Upload CSV</span>
                        </button>
                        {results.length > 0 && (
                            <button className="action-btn clear-btn" onClick={clearHistory}>
                                <Trash2 size={16} />
                                <span>Clear</span>
                            </button>
                        )}
                    </div>
                </div>
            </header>

            {/* Upload status */}
            {uploadStatus && (
                <div className={`upload-banner ${uploadStatus.success ? 'success' : uploadStatus.loading ? 'loading' : 'error'}`}>
                    <span>{uploadStatus.message}</span>
                    <button onClick={() => setUploadStatus(null)} className="close-banner">
                        <X size={16} />
                    </button>
                </div>
            )}

            {/* Main content */}
            <main className="main-content">
                <div className="results-container">
                    {/* Welcome state */}
                    {results.length === 0 && !isLoading && (
                        <div className="welcome-section">
                            <div className="welcome-icon">
                                <MessageSquare size={48} />
                            </div>
                            <h2>What would you like to know?</h2>
                            <p>
                                {activeTable === 'amazon_sales'
                                    ? 'Ask any business question about Amazon sales data and get instant interactive charts and insights.'
                                    : `Your "${activeTable}" dataset is loaded. Ask any question about your data.`
                                }
                            </p>
                        </div>
                    )}

                    {/* Results */}
                    {results.map((result, i) => (
                        <div key={i} className="result-block">
                            <div className="user-query">
                                <MessageSquare size={16} />
                                <span>{result.query}</span>
                            </div>
                            <Dashboard
                                result={result}
                                conversationHistory={conversationHistory}
                                onFollowUp={handleQuery}
                            />
                        </div>
                    ))}

                    <div ref={bottomRef} />
                </div>

                {/* Query Input */}
                <div className="sticky-input-container">
                    <QueryInput
                        onSubmit={handleQuery}
                        isLoading={isLoading}
                        conversationHistory={conversationHistory}
                    />
                </div>
            </main>
        </div>
    );
}

export default App;
