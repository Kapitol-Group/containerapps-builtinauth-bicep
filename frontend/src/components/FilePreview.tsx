import React, { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { TenderFile } from '../types';
import { filesApi } from '../services/api';
import './FilePreview.css';

// Configure PDF.js worker - must be in same file as react-pdf components
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

interface FilePreviewProps {
  file: TenderFile | null;
  tenderId?: string;
}

const FilePreview: React.FC<FilePreviewProps> = ({ file, tenderId }) => {
  const [pageNum, setPageNum] = useState(1);
  const [numPages, setNumPages] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scale, setScale] = useState(1.0);
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);

  // Load PDF file when file or tenderId changes
  useEffect(() => {
    if (file && tenderId && isPdfFile(file)) {
      loadPdf();
    } else {
      // Clean up when no file is selected or file is not a PDF
      setPdfBlob(null);
      setNumPages(0);
      setPageNum(1);
      setError(null);
      setLoading(false);
    }
  }, [file, tenderId]);

  const isPdfFile = (file: TenderFile): boolean => {
    return file.content_type?.toLowerCase().includes('pdf') || 
           file.name.toLowerCase().endsWith('.pdf');
  };

  const loadPdf = async () => {
    if (!file || !tenderId) return;

    setLoading(true);
    setError(null);

    try {
      // Download the file as a blob
      const blob = await filesApi.download(tenderId, file.path);
      setPdfBlob(blob);
      setLoading(false);
    } catch (err) {
      console.error('Error loading PDF:', err);
      setError('Failed to load PDF file');
      setLoading(false);
      setPdfBlob(null);
    }
  };

  const onDocumentLoadSuccess = ({ numPages: nextNumPages }: { numPages: number }) => {
    setNumPages(nextNumPages);
    setPageNum(1);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('Error loading PDF document:', error);
    setError('Failed to load PDF document');
  };

  const nextPage = () => {
    if (pageNum < numPages) {
      setPageNum(pageNum + 1);
    }
  };

  const prevPage = () => {
    if (pageNum > 1) {
      setPageNum(pageNum - 1);
    }
  };

  const zoomIn = () => {
    setScale(prevScale => Math.min(prevScale + 0.25, 3.0));
  };

  const zoomOut = () => {
    setScale(prevScale => Math.max(prevScale - 0.25, 0.5));
  };

  const resetZoom = () => {
    setScale(1.0);
  };

  if (!file) {
    return (
      <div className="file-preview">
        <p>Select a file to preview</p>
      </div>
    );
  }

  if (!tenderId) {
    return (
      <div className="file-preview">
        <h3>{file.name}</h3>
        <p className="error">Tender ID is required for preview</p>
      </div>
    );
  }

  if (!isPdfFile(file)) {
    return (
      <div className="file-preview">
        <h3>{file.name}</h3>
        <p>Preview for {file.content_type}</p>
        <p className="placeholder">Preview is only available for PDF files</p>
      </div>
    );
  }

  return (
    <div className="file-preview">
      <div className="preview-header">
        <h3>{file.name}</h3>
        {numPages > 0 && (
          <div className="preview-controls">
            <div className="page-controls">
              <button onClick={prevPage} disabled={pageNum <= 1 || loading}>
                ← Prev
              </button>
              <span className="page-info">
                Page {pageNum} of {numPages}
              </span>
              <button onClick={nextPage} disabled={pageNum >= numPages || loading}>
                Next →
              </button>
            </div>
            <div className="zoom-controls">
              <button onClick={zoomOut} disabled={scale <= 0.5 || loading} title="Zoom Out">
                −
              </button>
              <button onClick={resetZoom} disabled={loading} title="Reset Zoom">
                {Math.round(scale * 100)}%
              </button>
              <button onClick={zoomIn} disabled={scale >= 3.0 || loading} title="Zoom In">
                +
              </button>
            </div>
          </div>
        )}
      </div>
      
      <div className="preview-content">
        {loading && <div className="loading">Loading PDF...</div>}
        {error && <div className="error">{error}</div>}
        {!loading && !error && pdfBlob && (
          <div className="pdf-document">
            <Document
              file={pdfBlob}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={<div className="loading">Loading document...</div>}
            >
              <Page
                pageNumber={pageNum}
                scale={scale}
                loading={<div className="loading">Loading page...</div>}
                renderAnnotationLayer={true}
                renderTextLayer={true}
              />
            </Document>
          </div>
        )}
      </div>
    </div>
  );
};

export default FilePreview;
