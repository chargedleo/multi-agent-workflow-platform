import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Dashboard } from './components/dashboard/Dashboard';
import { QueryInput } from './components/QueryInput';
import { WorkflowResult } from './components/WorkflowResult';
import { RunDetailModal } from './components/RunDetailModal';
import { DocumentManager } from './components/DocumentManager';
import { PendingApprovals } from './components/PendingApprovals';
import { EvaluationConsole } from './components/evaluation/EvaluationConsole';
import {
  fetchHealth,
  fetchWorkflowStats,
  executeWorkflow,
  fetchWorkflowRuns,
  fetchWorkflowRunDetail,
  fetchDocuments,
  fetchPendingApprovals,
} from './services/api';
import './App.css';

export function App() {
  // Navigation tabs: 'dashboard', 'query', 'approvals', 'documents'
  const [activeNavTab, setActiveNavTab] = useState('dashboard');

  // Backend Health state
  const [healthInfo, setHealthInfo] = useState({ status: 'checking', database: 'unknown' });

  // Query Runner state
  const [query, setQuery] = useState('Compare the advantages and disadvantages of PostgreSQL and MongoDB for a startup SaaS application.');
  const [result, setResult] = useState(null);
  const [isLoadingQuery, setIsLoadingQuery] = useState(false);
  const [queryError, setQueryError] = useState(null);

  // Executive Dashboard Stats state
  const [stats, setStats] = useState({
    total_runs: 0,
    active_runs: 0,
    awaiting_approval: 0,
    completed_runs: 0,
    failed_runs: 0,
    rejected_runs: 0,
    avg_duration_ms: null,
  });
  const [isStatsLoading, setIsStatsLoading] = useState(false);

  // Filterable Workflow Runs Table state
  const [runs, setRuns] = useState([]);
  const [totalRuns, setTotalRuns] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [isRunsLoading, setIsRunsLoading] = useState(false);

  // Run detail modal state
  const [selectedRunDetail, setSelectedRunDetail] = useState(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);

  // Pending Approvals queue state
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [isApprovalsLoading, setIsApprovalsLoading] = useState(false);

  // Documents state
  const [documents, setDocuments] = useState([]);
  const [isDocsLoading, setIsDocsLoading] = useState(false);

  // Auto-refresh polling & Page Visibility state
  const [autoRefreshInterval, setAutoRefreshInterval] = useState(10); // in seconds, 0 = off
  const [isPausedDueToVisibility, setIsPausedDueToVisibility] = useState(false);
  const timerRef = useRef(null);

  // 1. Fetch Backend Health
  const checkHealth = useCallback(async () => {
    try {
      const data = await fetchHealth();
      setHealthInfo(data);
    } catch (err) {
      setHealthInfo({ status: 'offline', database: 'unreachable' });
    }
  }, []);

  // 2. Fetch Aggregated Workflow Stats
  const loadStats = useCallback(async () => {
    setIsStatsLoading(true);
    try {
      const data = await fetchWorkflowStats();
      setStats(data);
    } catch (err) {
      console.warn('Failed to load workflow stats:', err);
    } finally {
      setIsStatsLoading(false);
    }
  }, []);

  // 3. Fetch Filtered Workflow Runs
  const loadRuns = useCallback(async (p = page, ps = pageSize, stat = statusFilter, search = searchQuery) => {
    setIsRunsLoading(true);
    try {
      const data = await fetchWorkflowRuns(p, ps, stat, search);
      setRuns(data.items || []);
      setTotalRuns(data.total || 0);
    } catch (err) {
      console.warn('Failed to load workflow runs:', err);
    } finally {
      setIsRunsLoading(false);
    }
  }, [page, pageSize, statusFilter, searchQuery]);

  // 4. Fetch Pending Approvals
  const loadPendingApprovals = useCallback(async () => {
    setIsApprovalsLoading(true);
    try {
      const data = await fetchPendingApprovals();
      setPendingApprovals(data.items || []);
    } catch (err) {
      console.warn('Failed to load pending approvals:', err);
    } finally {
      setIsApprovalsLoading(false);
    }
  }, []);

  // 5. Fetch Ingested Documents
  const loadDocuments = useCallback(async () => {
    setIsDocsLoading(true);
    try {
      const data = await fetchDocuments(1, 50);
      setDocuments(data.items || []);
    } catch (err) {
      console.warn('Failed to load documents:', err);
    } finally {
      setIsDocsLoading(false);
    }
  }, []);

  // Refresh all dashboard data
  const handleRefreshAll = useCallback(async () => {
    await Promise.all([
      checkHealth(),
      loadStats(),
      loadRuns(page, pageSize, statusFilter, searchQuery),
      loadPendingApprovals(),
    ]);
  }, [checkHealth, loadStats, loadRuns, page, pageSize, statusFilter, searchQuery, loadPendingApprovals]);

  // Inspect run details
  const handleSelectRun = async (runId) => {
    setIsDetailLoading(true);
    try {
      const detail = await fetchWorkflowRunDetail(runId);
      setSelectedRunDetail(detail);
    } catch (err) {
      console.error(`Failed to load details for run ${runId}:`, err);
    } finally {
      setIsDetailLoading(false);
    }
  };

  // Execute workflow from Query Runner
  const handleRunWorkflow = async () => {
    if (!query.trim()) return;

    setIsLoadingQuery(true);
    setQueryError(null);

    try {
      const data = await executeWorkflow(query);
      setResult(data);
      // Immediately refresh stats, runs, and pending approvals
      await handleRefreshAll();
    } catch (err) {
      setQueryError(err.message || 'An error occurred while executing the multi-agent workflow.');
      setResult(null);
    } finally {
      setIsLoadingQuery(false);
    }
  };

  // Handle approval decision from modal or cards
  const handleApprovalDone = async (updatedData) => {
    if (updatedData) {
      setResult(updatedData);
    }
    await handleRefreshAll();
  };

  // Pagination & Filter Handlers
  const handlePageChange = (newPage) => {
    setPage(newPage);
    loadRuns(newPage, pageSize, statusFilter, searchQuery);
  };

  const handlePageSizeChange = (newSize) => {
    setPageSize(newSize);
    setPage(1);
    loadRuns(1, newSize, statusFilter, searchQuery);
  };

  const handleStatusFilterChange = (newStatus) => {
    setStatusFilter(newStatus);
    setPage(1);
    loadRuns(1, pageSize, newStatus, searchQuery);
  };

  const handleSearchChange = (newSearch) => {
    setSearchQuery(newSearch);
    setPage(1);
    loadRuns(1, pageSize, statusFilter, newSearch);
  };

  // Initial load
  useEffect(() => {
    checkHealth();
    loadStats();
    loadRuns(1, pageSize, statusFilter, searchQuery);
    loadPendingApprovals();
    loadDocuments();
  }, []);

  // Visibility detection & auto-refresh polling
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        setIsPausedDueToVisibility(true);
      } else {
        setIsPausedDueToVisibility(false);
        // Refresh immediately upon returning to the window
        handleRefreshAll();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [handleRefreshAll]);

  // Polling timer
  useEffect(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    if (autoRefreshInterval > 0 && !isPausedDueToVisibility) {
      timerRef.current = setInterval(() => {
        handleRefreshAll();
      }, autoRefreshInterval * 1000);
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [autoRefreshInterval, isPausedDueToVisibility, handleRefreshAll]);

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="header-top">
          <div className="header-title-group">
            <div className="logo-badge">M</div>
            <div>
              <h1 className="header-title">Multi-Agent AI Workflow Automation Platform</h1>
              <span className="header-subtitle-text">
                Autonomous LangGraph Orchestration • PostgreSQL Persistence • FAISS RAG • MCP Tools • HITL Control
              </span>
            </div>
          </div>
          <div className="header-badges">
            <span className="badge badge-milestone">Milestone 9B • Evaluation Console & Release</span>
            <span className={`badge badge-status ${healthInfo.status !== 'healthy' ? 'disconnected' : ''}`}>
              <span className="status-dot"></span>
              API: {healthInfo.status}
            </span>
          </div>
        </div>

        {/* Global Navigation Tabs */}
        <nav className="main-nav-tabs">
          <button
            className={`nav-tab-btn ${activeNavTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveNavTab('dashboard')}
          >
            Monitoring Dashboard
          </button>
          <button
            className={`nav-tab-btn ${activeNavTab === 'query' ? 'active' : ''}`}
            onClick={() => setActiveNavTab('query')}
          >
            Query Runner
          </button>
          <button
            className={`nav-tab-btn ${activeNavTab === 'approvals' ? 'active' : ''}`}
            onClick={() => setActiveNavTab('approvals')}
          >
            Approvals Queue
            {pendingApprovals.length > 0 && (
              <span className="nav-tab-badge">{pendingApprovals.length}</span>
            )}
          </button>
          <button
            className={`nav-tab-btn ${activeNavTab === 'documents' ? 'active' : ''}`}
            onClick={() => setActiveNavTab('documents')}
          >
            Knowledge Base
            {documents.length > 0 && (
              <span className="nav-tab-badge-subtle">{documents.length}</span>
            )}
          </button>
          <button
            className={`nav-tab-btn ${activeNavTab === 'evaluations' ? 'active' : ''}`}
            onClick={() => setActiveNavTab('evaluations')}
          >
            Evaluation Console
          </button>
        </nav>
      </header>

      {/* Main Tabbed Views */}
      <main className="main-content-area">
        {/* TAB 1: Monitoring Dashboard */}
        {activeNavTab === 'dashboard' && (
          <Dashboard
            stats={stats}
            isStatsLoading={isStatsLoading}
            runs={runs}
            totalRuns={totalRuns}
            page={page}
            pageSize={pageSize}
            statusFilter={statusFilter}
            searchQuery={searchQuery}
            isRunsLoading={isRunsLoading}
            autoRefreshInterval={autoRefreshInterval}
            isPausedDueToVisibility={isPausedDueToVisibility}
            pendingApprovals={pendingApprovals}
            onPageChange={handlePageChange}
            onPageSizeChange={handlePageSizeChange}
            onStatusFilterChange={handleStatusFilterChange}
            onSearchChange={handleSearchChange}
            onAutoRefreshChange={setAutoRefreshInterval}
            onSelectRun={handleSelectRun}
            onRefreshAll={handleRefreshAll}
            onNavigateToApprovals={() => setActiveNavTab('approvals')}
          />
        )}

        {/* TAB 2: Query Runner */}
        {activeNavTab === 'query' && (
          <div className="query-runner-view">
            <QueryInput
              query={query}
              setQuery={setQuery}
              onSubmit={handleRunWorkflow}
              isLoading={isLoadingQuery}
            />

            {queryError && (
              <div className="error-banner">
                <div>
                  <strong>Error:</strong> {queryError}
                </div>
              </div>
            )}

            <WorkflowResult
              result={result}
              onApprovalDone={handleApprovalDone}
            />
          </div>
        )}

        {/* TAB 3: Approvals Queue */}
        {activeNavTab === 'approvals' && (
          <div className="approvals-view">
            <PendingApprovals
              pendingApprovals={pendingApprovals}
              isLoading={isApprovalsLoading}
              onSelectApproval={handleSelectRun}
              onRefresh={loadPendingApprovals}
            />
          </div>
        )}

        {/* TAB 4: Knowledge Base (Documents) */}
        {activeNavTab === 'documents' && (
          <div className="documents-view">
            <DocumentManager
              documents={documents}
              isLoading={isDocsLoading}
              onRefresh={loadDocuments}
            />
          </div>
        )}

        {/* TAB 5: Evaluation Console (Milestone 9B) */}
        {activeNavTab === 'evaluations' && (
          <div className="evaluations-view">
            <EvaluationConsole />
          </div>
        )}
      </main>

      {/* Run Detail Inspection Modal */}
      {selectedRunDetail && (
        <RunDetailModal
          run={selectedRunDetail}
          onClose={() => setSelectedRunDetail(null)}
          onApprovalDone={handleApprovalDone}
        />
      )}

      {/* Loading overlay for run detail */}
      {isDetailLoading && (
        <div className="loading-toast">Loading run details from PostgreSQL...</div>
      )}

      {/* App Footer */}
      <footer className="app-footer">
        Portfolio Platform Architecture — Milestone 9B: Evaluation Console, End-to-End Verification & Portfolio Release
      </footer>
    </div>
  );
}

export default App;
