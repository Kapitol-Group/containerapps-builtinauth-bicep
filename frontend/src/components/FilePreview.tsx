import React, { useEffect, useRef, useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import type { PDFDocumentProxy, PDFPageProxy, PageViewport } from 'pdfjs-dist';
import { TenderFile } from '../types';
import { filesApi } from '../services/api';
import './FilePreview.css';

// Configure PDF.js worker - use the bundled worker
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.mjs',
  import.meta.url
).toString();

interface FilePreviewProps {
  file: TenderFile | null;
  tenderId?: string;
}

const FilePreview: React.FC<FilePreviewProps> = ({ file, tenderId }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [pageNum, setPageNum] = useState(1);
  const [numPages, setNumPages] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scale, setScale] = useState(1.0);
  const pdfDocRef = useRef<PDFDocumentProxy | null>(null);
  const renderTaskRef = useRef<any>(null);

  useEffect(() => {
    if (file && tenderId && isPdfFile(file)) {
      loadPdf();
    } else {
      // Clean up when no file is selected or file is not a PDF
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
        renderTaskRef.current = null;
      }
      if (pdfDocRef.current) {
        pdfDocRef.current.destroy();
        pdfDocRef.current = null;
      }
      setNumPages(0);
      setPageNum(1);
      setError(null);
    }

    return () => {
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
        renderTaskRef.current = null;
      }
      if (pdfDocRef.current) {
        pdfDocRef.current.destroy();
        pdfDocRef.current = null;
      }
    };
  }, [file, tenderId]);

  useEffect(() => {
    if (pdfDocRef.current && numPages > 0 && canvasRef.current) {
      // Use setTimeout to ensure render happens after any state updates
      setTimeout(() => {
        renderPage(pageNum);
      }, 0);
    }
  }, [pageNum, scale, numPages]);

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
      const arrayBuffer = await blob.arrayBuffer();

      // Clean up previous PDF if exists
      if (pdfDocRef.current) {
        await pdfDocRef.current.destroy();
      }

      // Load the PDF
      const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
      const pdf = await loadingTask.promise;
      
      pdfDocRef.current = pdf;
      setNumPages(pdf.numPages);
      setPageNum(1);
      setLoading(false);
      
      // The useEffect will handle rendering when numPages/pageNum updates
      // No need to manually call renderPage here
    } catch (err) {
      console.error('Error loading PDF:', err);
      setError('Failed to load PDF file');
      setLoading(false);
    }
  };

  const renderPage = async (num: number) => {
    if (!pdfDocRef.current || !canvasRef.current) return;

    // Cancel any ongoing render task
    if (renderTaskRef.current) {
      renderTaskRef.current.cancel();
      renderTaskRef.current = null;
    }

    try {
      const page = await pdfDocRef.current.getPage(num);
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');
      
      if (!context) return;

      const viewport = page.getViewport({ scale });
      
      // Set canvas dimensions
      canvas.height = viewport.height;
      canvas.width = viewport.width;

      // Clear the canvas before rendering
      context.clearRect(0, 0, canvas.width, canvas.height);

      // Render the page
      const renderContext = {
        canvasContext: context,
        viewport: viewport,
      };

      const renderTask = page.render(renderContext as any);
      renderTaskRef.current = renderTask;
      
      await renderTask.promise;
      renderTaskRef.current = null;
    } catch (err: any) {
      // Ignore cancellation errors
      if (err?.name === 'RenderingCancelledException') {
        console.log('Render cancelled');
        return;
      }
      console.error('Error rendering page:', err);
      setError('Failed to render PDF page');
    }
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
    <div className="file-preview" ref={containerRef}>
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
        {!loading && !error && (
          <div className="canvas-container">
            <canvas ref={canvasRef} />
          </div>
        )}
      </div>
    </div>
  );
};

export default FilePreview;
