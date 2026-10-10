import { test, describe, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert';
import {
  fetchHealth,
  fetchWorkflowStats,
  executeWorkflow,
  fetchWorkflowRuns,
  fetchWorkflowRunDetail,
  fetchDocuments,
  fetchPendingApprovals,
  fetchEvaluationDatasets,
  fetchEvaluationRuns,
  fetchEvaluationRun,
  fetchEvaluationCaseResults,
  fetchEvaluationReport,
  startEvaluation,
  compareEvaluations,
} from '../src/services/api.js';

describe('Frontend API Service Layer Tests', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('Health and Workflow APIs', () => {
    test('fetchHealth returns status object on 200', async () => {
      globalThis.fetch = async (url) => {
        assert.ok(url.endsWith('/health'));
        return {
          ok: true,
          json: async () => ({ status: 'healthy', database: 'connected' }),
        };
      };

      const result = await fetchHealth();
      assert.strictEqual(result.status, 'healthy');
      assert.strictEqual(result.database, 'connected');
    });

    test('fetchHealth throws error on non-200 response', async () => {
      globalThis.fetch = async () => ({
        ok: false,
        status: 503,
      });

      await assert.rejects(
        async () => await fetchHealth(),
        /Health check failed with HTTP 503/
      );
    });

    test('executeWorkflow rejects empty query', async () => {
      await assert.rejects(
        async () => await executeWorkflow('   '),
        /Query cannot be empty/
      );
    });

    test('executeWorkflow sends query payload and returns result', async () => {
      globalThis.fetch = async (url, options) => {
        assert.ok(url.endsWith('/workflows'));
        assert.strictEqual(options.method, 'POST');
        const body = JSON.parse(options.body);
        assert.strictEqual(body.query, 'Test analysis query');
        return {
          ok: true,
          json: async () => ({
            request_id: 'test-req-123',
            answer: 'Mock response',
            confidence: 0.95,
          }),
        };
      };

      const res = await executeWorkflow('Test analysis query');
      assert.strictEqual(res.request_id, 'test-req-123');
      assert.strictEqual(res.confidence, 0.95);
    });
  });

  describe('Evaluation Console APIs (M9B)', () => {
    test('fetchEvaluationDatasets queries /evaluations/datasets', async () => {
      globalThis.fetch = async (url) => {
        assert.ok(url.endsWith('/evaluations/datasets'));
        return {
          ok: true,
          json: async () => [
            {
              name: 'benchmark_v1',
              version: '1.0.0',
              case_count: 35,
              checksum: '90967732a322...',
            },
          ],
        };
      };

      const datasets = await fetchEvaluationDatasets();
      assert.strictEqual(datasets.length, 1);
      assert.strictEqual(datasets[0].name, 'benchmark_v1');
      assert.strictEqual(datasets[0].case_count, 35);
    });

    test('fetchEvaluationRuns builds proper query params for pagination and filter', async () => {
      globalThis.fetch = async (url) => {
        const u = new URL(url, 'http://localhost');
        assert.strictEqual(u.pathname, '/api/v1/evaluations');
        assert.strictEqual(u.searchParams.get('page'), '2');
        assert.strictEqual(u.searchParams.get('page_size'), '10');
        assert.strictEqual(u.searchParams.get('dataset_name'), 'benchmark_v1');
        return {
          ok: true,
          json: async () => ({
            items: [{ id: 'run-1', status: 'COMPLETED' }],
            total: 1,
            page: 2,
            page_size: 10,
          }),
        };
      };

      const runs = await fetchEvaluationRuns(2, 10, 'benchmark_v1');
      assert.strictEqual(runs.total, 1);
      assert.strictEqual(runs.items[0].id, 'run-1');
    });

    test('fetchEvaluationRun requires valid runId', async () => {
      await assert.rejects(
        async () => await fetchEvaluationRun(''),
        /runId is required/
      );
    });

    test('fetchEvaluationRun retrieves run summary', async () => {
      globalThis.fetch = async (url) => {
        assert.ok(url.endsWith('/evaluations/run-xyz'));
        return {
          ok: true,
          json: async () => ({
            id: 'run-xyz',
            status: 'COMPLETED',
            duration_ms: 120.5,
          }),
        };
      };

      const run = await fetchEvaluationRun('run-xyz');
      assert.strictEqual(run.id, 'run-xyz');
      assert.strictEqual(run.status, 'COMPLETED');
    });

    test('fetchEvaluationCaseResults handles category filter and pagination', async () => {
      globalThis.fetch = async (url) => {
        const u = new URL(url, 'http://localhost');
        assert.strictEqual(u.pathname, '/api/v1/evaluations/run-xyz/results');
        assert.strictEqual(u.searchParams.get('category'), 'answerable');
        assert.strictEqual(u.searchParams.get('page'), '1');
        assert.strictEqual(u.searchParams.get('page_size'), '25');
        return {
          ok: true,
          json: async () => ({
            items: [{ case_id: 'case-001', category: 'answerable' }],
            total: 5,
            page: 1,
            page_size: 25,
          }),
        };
      };

      const cases = await fetchEvaluationCaseResults('run-xyz', 'answerable', 1, 25);
      assert.strictEqual(cases.items.length, 1);
      assert.strictEqual(cases.items[0].case_id, 'case-001');
    });

    test('fetchEvaluationReport downloads full machine-readable report', async () => {
      globalThis.fetch = async (url) => {
        assert.ok(url.endsWith('/evaluations/run-xyz/report'));
        return {
          ok: true,
          json: async () => ({
            report_version: '1.0.0',
            evaluation_run_id: 'run-xyz',
            summary: { mrr: 0.95 },
          }),
        };
      };

      const report = await fetchEvaluationReport('run-xyz');
      assert.strictEqual(report.report_version, '1.0.0');
      assert.strictEqual(report.summary.mrr, 0.95);
    });

    test('startEvaluation submits serialized benchmark configuration', async () => {
      globalThis.fetch = async (url, options) => {
        assert.ok(url.endsWith('/evaluations'));
        assert.strictEqual(options.method, 'POST');
        const body = JSON.parse(options.body);
        assert.strictEqual(body.dataset_name, 'benchmark_v1');
        assert.strictEqual(body.mode, 'integration');
        assert.strictEqual(body.max_concurrency, 8);
        assert.strictEqual(body.timeout_per_case_seconds, 45);
        return {
          ok: true,
          json: async () => ({
            id: 'new-run-id',
            status: 'PENDING',
            mode: 'integration',
          }),
        };
      };

      const created = await startEvaluation({
        dataset_name: 'benchmark_v1',
        mode: 'integration',
        max_concurrency: 8,
        timeout_per_case_seconds: 45,
      });

      assert.strictEqual(created.id, 'new-run-id');
      assert.strictEqual(created.status, 'PENDING');
    });

    test('startEvaluation propagates backend error message on failure', async () => {
      globalThis.fetch = async () => ({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Unknown dataset name specified' }),
      });

      await assert.rejects(
        async () => await startEvaluation({ dataset_name: 'non_existent' }),
        /Unknown dataset name specified/
      );
    });

    test('compareEvaluations validates input parameters and returns delta report', async () => {
      await assert.rejects(
        async () => await compareEvaluations('', 'run-2'),
        /Both baselineRunId and comparisonRunId are required/
      );

      globalThis.fetch = async (url, options) => {
        assert.ok(url.endsWith('/evaluations/compare'));
        assert.strictEqual(options.method, 'POST');
        const body = JSON.parse(options.body);
        assert.strictEqual(body.baseline_run_id, 'run-1');
        assert.strictEqual(body.comparison_run_id, 'run-2');
        return {
          ok: true,
          json: async () => ({
            baseline_run_id: 'run-1',
            comparison_run_id: 'run-2',
            summary_verdict: 'IMPROVED',
            improvements: ['mrr improved from 0.85 to 0.95'],
            regressions: [],
          }),
        };
      };

      const report = await compareEvaluations('run-1', 'run-2');
      assert.strictEqual(report.summary_verdict, 'IMPROVED');
      assert.strictEqual(report.improvements.length, 1);
    });
  });
});
