import React from 'react';

export function WorkflowResult({ result }) {
  if (!result) return null;

  const { request_id, answer, key_points, confidence, sources, errors } = result;
  const confidencePercent = Math.round((confidence || 0) * 100);

  return (
    <div className="result-card">
      <div className="result-header">
        <div className="result-title-group">
          <h2 className="result-title">Workflow Result</h2>
          {request_id && (
            <span className="req-badge" title="Unique Request ID">
              ID: {request_id}
            </span>
          )}
        </div>

        <div className="confidence-box">
          <span className="confidence-label">Confidence</span>
          <span className="confidence-val">{confidencePercent}%</span>
        </div>
      </div>

      {errors && errors.length > 0 && (
        <div className="error-banner">
          <div>
            <strong>Warnings / Non-fatal errors recorded:</strong>
            <ul style={{ paddingLeft: '1.25rem', marginTop: '0.25rem' }}>
              {errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div className="answer-section">
        <div className="section-label">Synthesized Response</div>
        <div className="answer-body">{answer}</div>
      </div>

      {key_points && key_points.length > 0 && (
        <div className="key-points-section">
          <div className="section-label">Executive Key Points</div>
          <div className="key-points-grid">
            {key_points.map((point, idx) => (
              <div key={idx} className="key-point-item">
                <span className="key-point-bullet">•</span>
                <span>{point}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {sources && sources.length > 0 && (
        <div className="sources-section">
          <div className="section-label">
            Grounding Evidence & Citations ({sources.length})
          </div>
          <div className="sources-grid">
            {sources.map((src, idx) => (
              <div key={idx} className="source-card">
                <div className="source-card-header">
                  <div className="source-title-group">
                    <span className="source-icon">📄</span>
                    <strong className="source-doc-name">{src.filename || 'Document'}</strong>
                    {src.page_number && (
                      <span className="source-page-badge">Page {src.page_number}</span>
                    )}
                  </div>
                  {src.similarity_score != null && (
                    <span className="source-score-badge">
                      Similarity: {(src.similarity_score * 100).toFixed(1)}%
                    </span>
                  )}
                </div>
                {src.snippet && (
                  <p className="source-snippet">
                    "{src.snippet}"
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
