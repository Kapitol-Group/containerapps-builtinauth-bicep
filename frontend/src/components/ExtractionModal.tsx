import React, { useState, useRef, useEffect } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import { TenderFile, TitleBlockCoords } from '../types';
import { uipathApi, filesApi } from '../services/api';
import './CreateTenderModal.css';
import './ExtractionModal.css';

// Configure PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.mjs',
  import.meta.url
).toString();

interface ExtractionModalProps {
  tenderId: string;
  files: TenderFile[];
  onClose: () => void;
  onSubmit: () => void;
}

const ExtractionModal: React.FC<ExtractionModalProps> = ({ tenderId, files, onClose, onSubmit }) => {
  const [discipline, setDiscipline] = useState('Architectural');
  const [coords, setCoords] = useState<TitleBlockCoords>({ x: 0, y: 0, width: 100, height: 50 });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showRegionSelector, setShowRegionSelector] = useState(false);
  const [isLoadingPdf, setIsLoadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pdfDocRef = useRef<PDFDocumentProxy | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPoint, setStartPoint] = useState<{ x: number; y: number } | null>(null);
  const [currentRect, setCurrentRect] = useState<TitleBlockCoords | null>(null);
  const [pdfScale, setPdfScale] = useState(1.0);
  const renderTaskRef = useRef<any>(null);
  const animationFrameRef = useRef<number | null>(null);
  const offscreenCanvasRef = useRef<HTMLCanvasElement | null>(null); // Store rendered PDF

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
      }
      if (pdfDocRef.current) {
        pdfDocRef.current.destroy();
      }
    };
  }, []);

  const loadPdfPreview = async () => {
    if (files.length === 0) {
      setPdfError('No files selected');
      return;
    }

    console.log('[ExtractionModal] loadPdfPreview start');
    setIsLoadingPdf(true);
    setPdfError(null);

    try {
      // Load the first PDF file for preview
      const firstPdfFile = files.find(f => 
        f.content_type?.toLowerCase().includes('pdf') || 
        f.name.toLowerCase().endsWith('.pdf')
      );

      if (!firstPdfFile) {
        setPdfError('No PDF files selected');
        setIsLoadingPdf(false);
        console.log('[ExtractionModal] no PDF file found');
        return;
      }

      const blob = await filesApi.download(tenderId, firstPdfFile.path);
      const arrayBuffer = await blob.arrayBuffer();

      if (pdfDocRef.current) {
        console.log('[ExtractionModal] destroying existing pdfDocRef');
        await pdfDocRef.current.destroy();
      }

      const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
      const pdf = await loadingTask.promise;
      pdfDocRef.current = pdf;

      console.log('[ExtractionModal] PDF loaded, showing canvas');
      setIsLoadingPdf(false);
      
      // Render after canvas becomes visible (after React re-renders)
      setTimeout(() => {
        console.log('[ExtractionModal] rendering page 1');
        renderPdfPage(1, true);  // Skip overlay on initial load
      }, 0);
    } catch (err) {
      console.error('Error loading PDF:', err);
      setPdfError('Failed to load PDF preview');
      setIsLoadingPdf(false);
    }
  };

  const drawSelectionOverlay = (rect?: TitleBlockCoords) => {
    const canvas = canvasRef.current;
    const offscreen = offscreenCanvasRef.current;
    if (!canvas || !offscreen) return;

    const context = canvas.getContext('2d');
    if (!context) return;

    // First, copy the stored PDF image to the main canvas
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.drawImage(offscreen, 0, 0);

    // Then draw the selection rectangle on top
    const rectToDraw = rect || currentRect;
    if (rectToDraw && rectToDraw.width > 0 && rectToDraw.height > 0) {
      context.strokeStyle = '#0078d4';
      context.lineWidth = 3;
      context.fillStyle = 'rgba(0, 120, 212, 0.2)';
      context.fillRect(rectToDraw.x, rectToDraw.y, rectToDraw.width, rectToDraw.height);
      context.strokeRect(rectToDraw.x, rectToDraw.y, rectToDraw.width, rectToDraw.height);
    } else if (coords && coords.width > 100 && coords.height > 50) {
      // Only draw saved coords if they're not the default values
      const displayCoords = {
        x: coords.x * pdfScale,
        y: coords.y * pdfScale,
        width: coords.width * pdfScale,
        height: coords.height * pdfScale,
      };
      context.strokeStyle = '#28a745';
      context.lineWidth = 3;
      context.fillStyle = 'rgba(40, 167, 69, 0.2)';
      context.fillRect(displayCoords.x, displayCoords.y, displayCoords.width, displayCoords.height);
      context.strokeRect(displayCoords.x, displayCoords.y, displayCoords.width, displayCoords.height);
    }
  };

  const renderPdfPage = async (pageNum: number, skipOverlay: boolean = false) => {
    if (!pdfDocRef.current || !canvasRef.current) return;

    if (renderTaskRef.current) {
      console.log('[ExtractionModal] cancelling pending render task');
      renderTaskRef.current.cancel();
    }

    try {
      const page = await pdfDocRef.current.getPage(pageNum);
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');

      if (!context) return;

      // Calculate scale to fit the available space
      const viewport = page.getViewport({ scale: 1.0 });
      const containerWidth = canvas.parentElement?.clientWidth ?? 0;
      console.log('[ExtractionModal] renderPdfPage containerWidth', containerWidth);

      // If the container hasn't laid out yet, retry on the next frame
      if (containerWidth < 50) {
        // Avoid piling up retries if component unmounted
        if (showRegionSelector) {
          console.log('[ExtractionModal] container width too small, retrying render');
          requestAnimationFrame(() => renderPdfPage(pageNum, skipOverlay));
        }
        return;
      }

      const scale = Math.min((containerWidth - 40) / viewport.width, 2.0);
      setPdfScale(scale);
      console.log('[ExtractionModal] renderPdfPage scale', scale);

      const scaledViewport = page.getViewport({ scale });

      canvas.height = scaledViewport.height;
      canvas.width = scaledViewport.width;

      // Create offscreen canvas to store the PDF image
      if (!offscreenCanvasRef.current) {
        offscreenCanvasRef.current = document.createElement('canvas');
      }
      const offscreen = offscreenCanvasRef.current;
      offscreen.width = canvas.width;
      offscreen.height = canvas.height;
      const offscreenCtx = offscreen.getContext('2d');
      if (!offscreenCtx) return;

      offscreenCtx.clearRect(0, 0, offscreen.width, offscreen.height);

      // Render to offscreen canvas
      const renderTask = page.render({
        canvasContext: offscreenCtx,
        viewport: scaledViewport,
      } as any);

      renderTaskRef.current = renderTask;
      await renderTask.promise;
      renderTaskRef.current = null;
      console.log('[ExtractionModal] render task complete');
      
      // Always copy offscreen to main canvas
      context.clearRect(0, 0, canvas.width, canvas.height);
      context.drawImage(offscreen, 0, 0);
      
      // Draw selection overlay if not initial load
      if (!skipOverlay && (currentRect || coords)) {
        drawSelectionOverlay();
      }
    } catch (err: any) {
      if (err?.name !== 'RenderingCancelledException') {
        console.error('Error rendering PDF:', err);
      }
    }
  };

  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setIsDrawing(true);
    setStartPoint({ x, y });
    setCurrentRect(null);
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing || !startPoint || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    const width = currentX - startPoint.x;
    const height = currentY - startPoint.y;

    const newRect = {
      x: width >= 0 ? startPoint.x : currentX,
      y: height >= 0 ? startPoint.y : currentY,
      width: Math.abs(width),
      height: Math.abs(height),
    };
    
    // Store current rect for mouseUp
    setCurrentRect(newRect);
    
    // Draw immediately without waiting for state update to avoid flicker
    drawSelectionOverlay(newRect);
  };

  const handleCanvasMouseUp = () => {
    if (!isDrawing) return;
    
    setIsDrawing(false);
    
    if (currentRect && currentRect.width > 10 && currentRect.height > 10) {
      // Convert canvas coordinates to PDF coordinates
      const pdfCoords = {
        x: Math.round(currentRect.x / pdfScale),
        y: Math.round(currentRect.y / pdfScale),
        width: Math.round(currentRect.width / pdfScale),
        height: Math.round(currentRect.height / pdfScale),
      };
      setCoords(pdfCoords);
      // Keep currentRect for green overlay display
    } else {
      // Clear if too small
      setCurrentRect(null);
    }
    setStartPoint(null);
  };

  const drawSelection = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const context = canvas.getContext('2d');
    if (!context) return;

    // Redraw the PDF page first
    if (pdfDocRef.current) {
      renderPdfPage(1);
    }
  };

  useEffect(() => {
    // Clean up - no longer needed since we draw directly in mousemove
  }, [currentRect, showRegionSelector]);

  // Load PDF when region selector becomes visible
  useEffect(() => {
    if (showRegionSelector && canvasRef.current && !pdfDocRef.current) {
      console.log('[ExtractionModal] showRegionSelector effect trigger');
      loadPdfPreview();
    }
  }, [showRegionSelector]);

  const handleOpenRegionSelector = () => {
    console.log('[ExtractionModal] opening region selector');
    setShowRegionSelector(true);
    // Wait for modal to render and canvas to be available
    setTimeout(() => {
      if (canvasRef.current) {
        console.log('[ExtractionModal] delayed loadPdfPreview call');
        loadPdfPreview();
      }
    }, 200);
  };

  const handleCloseRegionSelector = () => {
    setShowRegionSelector(false);
    if (renderTaskRef.current) {
      renderTaskRef.current.cancel();
    }
    if (pdfDocRef.current) {
      pdfDocRef.current.destroy();
      pdfDocRef.current = null;
    }
  };

  const handleResetSelection = () => {
    console.log('[ExtractionModal] resetting selection');
    setCoords({ x: 0, y: 0, width: 100, height: 50 });
    setCurrentRect(null);
    drawSelection();
  };

  const handleSubmit = async () => {
    try {
      setIsSubmitting(true);
      await uipathApi.queueExtraction(
        tenderId,
        files.map(f => f.path),
        discipline,
        coords
      );
      onSubmit();
    } catch (error) {
      console.error('Failed to queue extraction:', error);
      alert('Failed to queue extraction. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Queue Extraction</h2>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>
        
        <div className="form-group">
          <label>Selected Files ({files.length})</label>
          <div style={{ maxHeight: '150px', overflowY: 'auto', padding: '0.5rem', background: '#f5f5f5', borderRadius: '4px' }}>
            {files.map(file => (
              <div key={file.path} style={{ padding: '0.25rem 0', fontSize: '0.9rem' }}>
                • {file.name}
              </div>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label>Discipline</label>
          <select value={discipline} onChange={(e) => setDiscipline(e.target.value)}>
            <option>Architectural</option>
            <option>Structural</option>
            <option>Mechanical</option>
            <option>Electrical</option>
          </select>
        </div>
        
        <div className="form-group">
          <label>Title Block Region</label>
          <button 
            type="button"
            className="btn-secondary" 
            onClick={handleOpenRegionSelector}
            style={{ width: '100%', marginTop: '0.5rem' }}
          >
            {coords.width > 0 && coords.height > 0 
              ? `Selected: ${coords.width}×${coords.height}px at (${coords.x}, ${coords.y})`
              : 'Select Title Block Region'}
          </button>
        </div>

        {showRegionSelector && (
          <div className="region-selector-modal" onClick={handleCloseRegionSelector}>
            <div className="region-selector-content" onClick={(e) => e.stopPropagation()}>
              <div className="region-selector-header">
                <h3>Select Title Block Region</h3>
                <button className="close-btn" onClick={handleCloseRegionSelector}>&times;</button>
              </div>
              
              <div className="region-selector-body">
                {isLoadingPdf && <div className="loading">Loading PDF preview...</div>}
                {pdfError && <div className="error">{pdfError}</div>}
                
                {!isLoadingPdf && !pdfError && (
                  <>
                    <p className="instruction">
                      Click and drag on the PDF preview to select the title block region
                    </p>
                    <div className="canvas-wrapper">
                      <canvas
                        ref={canvasRef}
                        onMouseDown={handleCanvasMouseDown}
                        onMouseMove={handleCanvasMouseMove}
                        onMouseUp={handleCanvasMouseUp}
                        onMouseLeave={handleCanvasMouseUp}
                        style={{ cursor: 'crosshair' }}
                      />
                    </div>
                    {coords.width > 0 && coords.height > 0 && (
                      <div className="selection-info">
                        Selected region: {coords.width} × {coords.height} px at ({coords.x}, {coords.y})
                      </div>
                    )}
                  </>
                )}
              </div>
              
              <div className="region-selector-footer">
                <button className="btn-secondary" onClick={handleResetSelection}>
                  Reset Selection
                </button>
                <button className="btn-primary" onClick={handleCloseRegionSelector}>
                  Confirm Selection
                </button>
              </div>
            </div>
          </div>
        )}
        
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </button>
          <button className="btn-primary" onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Submitting...' : 'Submit'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExtractionModal;
