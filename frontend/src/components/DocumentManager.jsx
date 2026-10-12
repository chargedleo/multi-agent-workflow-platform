import React, { useState, useRef } from 'react';
import { uploadDocument, deleteDocument } from '../services/api';

export function DocumentManager({ documents, isLoading, onRefresh }) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const result = await uploadDocument(file);
      setUploadSuccess(`Uploaded "${result.filename}" (${result.page_count} pages, ${result.chunk_count} chunks indexed).`);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      await onRefresh();
    } catch (err) {
      setUploadError(err.message || 'Failed to upload document.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docId, filename) => {
    if (!window.confirm(`Delete document "${filename}" and its vector embeddings?`)) {
      return;
    }

    setDeletingId(docId);
    try {
      await deleteDocument(docId);
      await onRefresh();
    } catch (err) {
      alert(`Failed to delete document: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="history-card document-manager-card">
      <div className="history-header">
        <div className="history-title-group">
          <h2 className="history-title">Document Knowledge Base (FAISS RAG)</h2>
          <span className="history-count-badge">
            {documents.length} {documents.length === 1 ? 'Document' : 'Documents'}
          </span>
        </div>

        <div className="header-actions">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,.txt,.md,.markdown"
            style={{ display: 'none' }}
            id="doc-file-input"
          />
          <label htmlFor="doc-file-input" className={`btn-primary ${isUploading ? 'disabled' : ''}`} style={{ cursor: isUploading ? 'not-allowed' : 'pointer' }}>
            {isUploading ? 'Uploading & Indexing...' : 'Upload Document'}
          </label>
          <button
            className="btn-text-action"
            onClick={onRefresh}
            disabled={isLoading || isUploading}
            title="Refresh documents list"
          >
            Refresh
          </button>
        </div>
      </div>

      {uploadSuccess && (
        <div className="success-banner" style={{ margin: '0.75rem 0' }}>
          {uploadSuccess}
        </div>
      )}

      {uploadError && (
        <div className="error-banner" style={{ margin: '0.75rem 0' }}>
          <strong>Upload Error:</strong> {uploadError}
        </div>
      )}

      <p className="doc-desc-text">
        Upload PDF, Markdown, or plain text documents. The system extracts text, segments it into overlapping chunks, computes embeddings, and indexes them into FAISS for semantic grounding in workflows.
      </p>

      {isLoading ? (
        <div className="empty-state">
          <div className="empty-title">Loading documents...</div>
        </div>
      ) : documents.length === 0 ? (
        <div className="empty-state">
          <div className="empty-title">No Documents Ingested</div>
          <p className="empty-subtext">
            Upload your first reference document (PDF, TXT, or MD) to enable retrieval-grounded multi-agent reasoning.
          </p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="history-table">
            <thead>
              <tr>
                <th>Document Name</th>
                <th>Format</th>
                <th>Size</th>
                <th>Pages</th>
                <th>Chunks</th>
                <th>Status</th>
                <th>Uploaded</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => {
                const statusClass = (doc.status || '').toLowerCase();
                const ext = doc.original_filename?.split('.').pop()?.toUpperCase() || 'FILE';
                return (
                  <tr key={doc.document_id}>
                    <td>
                      <div className="doc-name-cell">
                        <strong title={doc.original_filename}>{doc.original_filename}</strong>
                      </div>
                    </td>
                    <td>
                      <span className="mono-badge">{ext}</span>
                    </td>
                    <td>{formatFileSize(doc.file_size)}</td>
                    <td>{doc.page_count}</td>
                    <td>
                      <span className="chunk-badge">{doc.chunk_count} chunks</span>
                    </td>
                    <td>
                      <span className={`status-badge status-${statusClass}`}>
                        {doc.status}
                      </span>
                    </td>
                    <td className="time-cell">
                      {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn-delete"
                        onClick={() => handleDelete(doc.document_id, doc.original_filename)}
                        disabled={deletingId === doc.document_id}
                        title="Delete document and FAISS vectors"
                      >
                        {deletingId === doc.document_id ? 'Deleting...' : 'Delete'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
