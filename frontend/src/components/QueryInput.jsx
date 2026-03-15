import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Sparkles, Upload } from 'lucide-react';

const EXAMPLE_PROMPTS = [
  "Show total sales by region",
  "Which product category generated the highest revenue?",
  "Show monthly sales trend for 2023",
  "Compare payment methods by total revenue",
  "What is the average discount by product category?",
  "Show quarterly revenue breakdown",
  "Top 5 products by quantity sold",
  "Show average rating by category",
];

export default function QueryInput({ onSubmit, isLoading, conversationHistory }) {
  const [query, setQuery] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    if (!isLoading && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isLoading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
      setQuery('');
    }
  };

  const handleExampleClick = (prompt) => {
    if (!isLoading) {
      onSubmit(prompt);
    }
  };

  return (
    <div className="query-input-container">
      <form onSubmit={handleSubmit} className="query-form">
        <div className="input-wrapper">
          <Sparkles className="input-icon" size={20} />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a business question... e.g., 'Show monthly sales trend for 2023'"
            className="query-input"
            disabled={isLoading}
          />
          <button
            type="submit"
            className="submit-btn"
            disabled={!query.trim() || isLoading}
          >
            {isLoading ? (
              <Loader2 className="spin" size={20} />
            ) : (
              <Send size={20} />
            )}
          </button>
        </div>
      </form>

      {conversationHistory.length === 0 && (
        <div className="examples-section">
          <p className="examples-label">Try one of these example queries:</p>
          <div className="examples-grid">
            {EXAMPLE_PROMPTS.map((prompt, i) => (
              <button
                key={i}
                className="example-chip"
                onClick={() => handleExampleClick(prompt)}
                disabled={isLoading}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      {isLoading && (
        <div className="loading-banner">
          <Loader2 className="spin" size={18} />
          <span>Analyzing your question and generating dashboard...</span>
        </div>
      )}
    </div>
  );
}
