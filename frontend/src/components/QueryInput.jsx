import React from 'react';

const PRESET_EXAMPLES = [
  'Compare PostgreSQL and MongoDB for a startup SaaS application.',
  'Analyze monolithic vs microservices architecture for an early-stage fintech.',
  'Design an event-driven data pipeline using Kafka and PostgreSQL.',
];

export function QueryInput({ query, setQuery, onSubmit, isLoading }) {
  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      if (!isLoading && query.trim()) {
        onSubmit();
      }
    }
  };

  return (
    <div className="query-card">
      <div className="card-label">
        <span>Business or Technical Query</span>
        <div className="examples-row">
          <span className="example-tag">Quick prompts:</span>
          {PRESET_EXAMPLES.map((example, i) => (
            <button
              key={i}
              type="button"
              className="example-btn"
              onClick={() => setQuery(example)}
              disabled={isLoading}
            >
              {example.slice(0, 24)}...
            </button>
          ))}
        </div>
      </div>

      <textarea
        className="query-input"
        placeholder="Enter your query here (e.g., 'Compare PostgreSQL and MongoDB for a startup SaaS application')..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isLoading}
        rows={4}
      />

      <div className="query-footer">
        <span className="hotkey-hint">Press Ctrl+Enter to submit</span>
        <button
          className="btn-primary"
          onClick={onSubmit}
          disabled={isLoading || !query.trim()}
        >
          {isLoading ? (
            <>
              <div className="spinner" />
              <span>Agents Collaborating...</span>
            </>
          ) : (
            <span>Run Workflow</span>
          )}
        </button>
      </div>
    </div>
  );
}
