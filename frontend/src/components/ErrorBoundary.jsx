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
          <div className="card error-card" style={{ background: 'var(--bg-card, #ffffff)', border: '1px solid var(--border-color, #e5e5e5)', borderRadius: '8px', padding: '2rem', textAlign: 'center', boxShadow: 'var(--shadow-md)' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '1rem', color: 'var(--text-primary)' }} aria-hidden="true">■</div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: '700', fontFamily: 'var(--font-serif)', color: 'var(--text-primary, #111111)', margin: '0 0 0.5rem 0' }}>
              Something Went Wrong
            </h2>
            <p style={{ color: 'var(--text-secondary, #666666)', fontSize: '0.9rem', marginBottom: '1.5rem', lineHeight: '1.5' }}>
              An unexpected UI error occurred while rendering this view. Your workflow runs and database state remain safe in PostgreSQL.
            </p>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
              <button
                className="btn btn-primary"
                onClick={this.handleReset}
                style={{ background: 'var(--accent-primary, #111111)', color: '#fff', border: '1px solid #111111', padding: '0.6rem 1.2rem', borderRadius: '4px', fontWeight: '600', cursor: 'pointer' }}
              >
                Try Again
              </button>
              <button
                className="btn btn-secondary"
                onClick={this.handleReload}
                style={{ background: '#ffffff', color: 'var(--text-primary, #111111)', border: '1px solid var(--border-color, #d4d4d4)', padding: '0.6rem 1.2rem', borderRadius: '4px', fontWeight: '600', cursor: 'pointer' }}
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
