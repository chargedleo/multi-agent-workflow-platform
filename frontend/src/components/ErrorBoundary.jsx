import React from 'react';

/**
 * Production React Error Boundary.
 * Catches JavaScript errors anywhere in the child component tree,
 * logs the error, and displays a graceful fallback UI instead of crashing the whole app.
 */
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      errorMessage: error ? (error.message || String(error)) : 'An unexpected error occurred.',
    };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an unhandled error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, errorMessage: '' });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary-container" style={{ padding: '3rem 1.5rem', maxWidth: '650px', margin: '4rem auto' }}>
          <div className="card error-card" style={{ background: 'var(--card-bg, #1e293b)', border: '1px solid var(--danger-border, #ef4444)', borderRadius: '12px', padding: '2rem', textAlign: 'center', boxShadow: '0 10px 25px rgba(0,0,0,0.3)' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }} aria-hidden="true">⚠️</div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: '700', color: 'var(--text-primary, #f8fafc)', margin: '0 0 0.5rem 0' }}>
              Something Went Wrong
            </h2>
            <p style={{ color: 'var(--text-secondary, #94a3b8)', fontSize: '0.9rem', marginBottom: '1.5rem', lineHeight: '1.5' }}>
              An unexpected UI error occurred while rendering this view. Your workflow runs and database state remain safe in PostgreSQL.
            </p>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
              <button
                className="btn btn-primary"
                onClick={this.handleReset}
                style={{ background: 'var(--accent-primary, #6366f1)', color: '#fff', border: 'none', padding: '0.6rem 1.2rem', borderRadius: '6px', fontWeight: '600', cursor: 'pointer' }}
              >
                Try Again
              </button>
              <button
                className="btn btn-secondary"
                onClick={this.handleReload}
                style={{ background: 'rgba(51, 65, 85, 0.8)', color: 'var(--text-primary, #f8fafc)', border: '1px solid #475569', padding: '0.6rem 1.2rem', borderRadius: '6px', fontWeight: '600', cursor: 'pointer' }}
              >
                Reload App
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
