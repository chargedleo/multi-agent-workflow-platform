import React, { useState, useEffect } from 'react';
import { fetchEvaluationDatasets, startEvaluation } from '../../services/api';

/**
 * Launch form for scheduling benchmark evaluation runs.
 * Supports metric_only and integration modes against versioned fixtures.
 */
export function EvaluationLaunchForm({ onRunStarted, activeRunningRun }) {
  const [datasets, setDatasets] = useState([]);
  const [isLoadingDatasets, setIsLoadingDatasets] = useState(false);
  const [datasetError, setDatasetError] = useState(null);

  // Form fields
  const [selectedDataset, setSelectedDataset] = useState('benchmark_v1');
  const [mode, setMode] = useState('metric_only');
  const [maxConcurrency, setMaxConcurrency] = useState(4);
  const [timeoutPerCase, setTimeoutPerCase] = useState(30.0);

  // Submission state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function loadDatasets() {
      setIsLoadingDatasets(true);
      setDatasetError(null);
      try {
        const data = await fetchEvaluationDatasets();
        if (isMounted) {
          setDatasets(data || []);
          if (data && data.length > 0 && !data.some((d) => d.name === selectedDataset)) {
            setSelectedDataset(data[0].name);
          }
        }
      } catch (err) {
        if (isMounted) {
          setDatasetError(err.message || 'Failed to load benchmark datasets');
        }
      } finally {
        if (isMounted) setIsLoadingDatasets(false);
      }
    }
    loadDatasets();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isSubmitting || activeRunningRun) return;

    setIsSubmitting(true);
    setFormError(null);

    try {
      const payload = {
        dataset_name: selectedDataset,
        mode,
        max_concurrency: Number(maxConcurrency),
        timeout_per_case_seconds: Number(timeoutPerCase),
      };
      const createdRun = await startEvaluation(payload);
      if (onRunStarted) {
        onRunStarted(createdRun);
      }
    } catch (err) {
      setFormError(err.message || 'Failed to start benchmark evaluation');
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedMeta = datasets.find((d) => d.name === selectedDataset);

  return (
    <div className="eval-panel">
      <div className="eval-panel-header">
        <div className="eval-panel-title">
          <span>🚀</span> Launch Benchmark Evaluation
        </div>
        {selectedMeta && (
          <div className="eval-panel-actions">
            <span className="eval-badge eval-badge-mode">
              v{selectedMeta.version} • {selectedMeta.case_count} Cases
            </span>
          </div>
        )}
      </div>

      {formError && (
        <div className="error-banner">
          <strong>Launch Error:</strong> {formError}
        </div>
      )}

      {datasetError && (
        <div className="error-banner">
          <strong>Dataset Load Warning:</strong> {datasetError}
        </div>
      )}

      <form className="eval-form" onSubmit={handleSubmit}>
        {/* Dataset Selection */}
        <div className="eval-form-group">
          <label className="eval-form-label" htmlFor="eval-dataset-select">
            Benchmark Dataset
          </label>
          <select
            id="eval-dataset-select"
            className="eval-form-select"
            value={selectedDataset}
            onChange={(e) => setSelectedDataset(e.target.value)}
            disabled={isSubmitting || isLoadingDatasets || !!activeRunningRun}
          >
            {datasets.map((d) => (
              <option key={d.name} value={d.name}>
                {d.name} (v{d.version} — {d.case_count} cases)
              </option>
            ))}
            {datasets.length === 0 && (
              <option value="benchmark_v1">benchmark_v1 (Default)</option>
            )}
          </select>
          {selectedMeta && (
            <span className="eval-form-helper">
              {selectedMeta.description || 'Verified ground-truth benchmark suite.'}
            </span>
          )}
        </div>

        {/* Execution Mode */}
        <div className="eval-form-group">
          <label className="eval-form-label" htmlFor="eval-mode-select">
            Evaluation Execution Mode
          </label>
          <select
            id="eval-mode-select"
            className="eval-form-select"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            disabled={isSubmitting || !!activeRunningRun}
          >
            <option value="metric_only">
              Metric Only (Deterministic, High-Speed Offline Fixtures)
            </option>
            <option value="integration">
              Integration Mode (Live FAISS Retriever & Pipeline)
            </option>
          </select>
          <span className="eval-form-helper">
            {mode === 'metric_only'
              ? 'Evaluates retrieval and quality using precomputed ground truth in ~50ms.'
              : 'Executes actual live FAISS vector search against ingested corpus.'}
          </span>
        </div>

        {/* Max Concurrency */}
        <div className="eval-form-group">
          <label className="eval-form-label" htmlFor="eval-concurrency-input">
            Max Concurrency (1–16 workers)
          </label>
          <input
            id="eval-concurrency-input"
            type="number"
            className="eval-form-input"
            min={1}
            max={16}
            value={maxConcurrency}
            onChange={(e) => setMaxConcurrency(e.target.value)}
            disabled={isSubmitting || !!activeRunningRun}
          />
          <span className="eval-form-helper">
            Bounded asynchronous semaphore to protect database & memory.
          </span>
        </div>

        {/* Timeout per case */}
        <div className="eval-form-group">
          <label className="eval-form-label" htmlFor="eval-timeout-input">
            Timeout Per Case (seconds)
          </label>
          <input
            id="eval-timeout-input"
            type="number"
            className="eval-form-input"
            min={1}
            max={120}
            step={0.5}
            value={timeoutPerCase}
            onChange={(e) => setTimeoutPerCase(e.target.value)}
            disabled={isSubmitting || !!activeRunningRun}
          />
          <span className="eval-form-helper">
            Isolates slow cases without aborting the broader evaluation run.
          </span>
        </div>

        {/* Submit Button Row */}
        <div className="eval-form-group" style={{ gridColumn: '1 / -1', marginTop: '0.5rem' }}>
          <button
            type="submit"
            className="eval-btn"
            disabled={isSubmitting || !!activeRunningRun || datasets.length === 0}
          >
            {isSubmitting ? (
              <>
                <span className="eval-active-spinner"></span>
                <span>Initializing Evaluation Run...</span>
              </>
            ) : activeRunningRun ? (
              <>
                <span className="eval-active-spinner"></span>
                <span>Evaluation in Progress ({activeRunningRun.id.slice(0, 8)})...</span>
              </>
            ) : (
              <>
                <span>▶</span>
                <span>Execute Benchmark Run</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
