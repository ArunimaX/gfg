import { useState, useRef, useEffect } from 'react';
import { BarChart3, Upload, X, MessageSquare, Trash2, Database, History, LogIn } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, UserButton, useAuth } from '@clerk/clerk-react';
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
    const { getToken } = useAuth();
    
    // Add session management
    const [sessions, setSessions] = useState([]);
    const [activeSessionId, setActiveSessionId] = useState(null);
    const [sidebarOpen, setSidebarOpen] = useState(false);

    // Fetch sessions on load
    useEffect(() => {
        const fetchSessions = async () => {
            try {
                const token = await getToken();
                if (!token) return;
                
                const response = await fetch(`${API_URL}/api/sessions`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const data = await response.json();
                if (data.sessions) setSessions(data.sessions);
            } catch (err) {
                console.error("Failed to fetch sessions", err);
            }
        };
        fetchSessions();
    }, [getToken]);

    const handleQuery = async (query) => {
        setIsLoading(true);
        try {
            const token = await getToken();
            const response = await fetch(`${API_URL}/api/query`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    query,
                    conversation_history: conversationHistory,
                    table_name: activeTable,
                    session_id: activeSessionId
                }),
            });
            const data = await response.json();

            // Add to results
            setResults(prev => [...prev, { query, ...data }]);

            // Update conversation history
            if (data.success) {
                setConversationHistory(prev => [...prev, { query, sql: data.sql }]);
                if (data.session_id && data.session_id !== activeSessionId) {
                    setActiveSessionId(data.session_id);
                    // Optionally refresh sidebar here, or just prepend locally
                }
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
            const token = await getToken();
            const response = await fetch(`${API_URL}/api/upload-csv`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
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
        setActiveSessionId(null);
    };

    const switchToDefault = () => {
        setActiveTable('amazon_sales');
        setResults([]);
        setConversationHistory([]);
        setUploadStatus(null);
        setActiveSessionId(null);
    };

    const loadSession = async (sessionId, tableName) => {
        setIsLoading(true);
        setSidebarOpen(false);
        try {
            const token = await getToken();
            const response = await fetch(`${API_URL}/api/sessions/${sessionId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await response.json();
            
            if (data.messages) {
                setActiveSessionId(sessionId);
                setActiveTable(tableName);
                
                // Reconstruct results array (this is simplified, ideally we'd store full results in the DB)
                // For now, we'll just populate history so follow-ups work
                const history = [];
                const restoredResults = [];
                
                let currentQuery = "";
                for (const msg of data.messages) {
                    if (msg.role === 'user') {
                        currentQuery = msg.content;
                    } else if (msg.role === 'assistant') {
                        history.push({ query: currentQuery, sql: msg.sql_query });
                        restoredResults.push({
                            query: currentQuery,
                            success: true,
                            sql: msg.sql_query,
                            explanation: msg.content,
                            data: [], // Historical data rows missing in this simple schema
                            chart_config: null
                        });
                    }
                }
                setConversationHistory(history);
                setResults(restoredResults);
            }
        } catch (err) {
            console.error("Failed to load session", err);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="app">
            {/* Ambient background effects */}
            <div className="bg-gradient-orb orb-1" />
            <div className="bg-gradient-orb orb-2" />
            <div className="bg-gradient-orb orb-3" />

            <SignedOut>
                <div className="landing-page">
                    <div className="landing-content">
                        <div className="logo-icon" style={{ margin: '0 auto 24px', width: '64px', height: '64px' }}>
                            <BarChart3 size={32} />
                        </div>
                        <h1 className="app-title" style={{ fontSize: '2.5rem', marginBottom: '16px' }}>AI Business Intelligence</h1>
                        <p className="app-subtitle" style={{ fontSize: '1.2rem', marginBottom: '40px', maxWidth: '600px', margin: '0 auto 40px' }}>
                            Ask questions in plain English. Get instant interactive dashboards. Start making data-driven decisions today.
                        </p>
                        <SignInButton mode="modal">
                            <button className="submit-btn" style={{ width: 'auto', padding: '16px 32px', borderRadius: '30px', fontSize: '1.1rem', margin: '0 auto' }}>
                                <LogIn size={20} style={{ marginRight: '8px' }}/>
                                Sign In or Register
                            </button>
                        </SignInButton>
                    </div>
                </div>
            </SignedOut>

            <SignedIn>
                {/* Header */}
                <header className="header">
                <div className="header-content">
                    <div className="logo-section">
                        <button className="action-btn" onClick={() => setSidebarOpen(!sidebarOpen)} style={{ padding: '8px', border: 'none', background: 'transparent' }}>
                            <History size={20} />
                        </button>
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
                                <span className="hide-mobile">Clear</span>
                            </button>
                        )}
                        <UserButton afterSignOutUrl="/" />
                    </div>
                </div>
            </header>

            {/* Sidebar Overlay */}
            {sidebarOpen && (
                <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
            )}
            
            {/* Sidebar */}
            <div className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
                <div className="sidebar-header">
                    <h3>Chat History</h3>
                    <button className="close-sidebar" onClick={() => setSidebarOpen(false)}>
                        <X size={20} />
                    </button>
                </div>
                <div className="sidebar-content">
                    {sessions.length === 0 ? (
                        <p className="no-sessions">No previous sessions found.</p>
                    ) : (
                        sessions.map(session => (
                            <div 
                                key={session.id} 
                                className={`session-item ${activeSessionId === session.id ? 'active' : ''}`}
                                onClick={() => loadSession(session.id, session.active_table)}
                            >
                                <MessageSquare size={16} />
                                <div className="session-info">
                                    <span className="session-title">{session.title}</span>
                                    <span className="session-dataset">{session.active_table}</span>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

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
            </SignedIn>
        </div>
    );
}

export default App;
