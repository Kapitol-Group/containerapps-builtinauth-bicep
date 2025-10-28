# Title Block Region Selection Tool

## Overview
An interactive PDF-based region selector that allows users to visually define the title block coordinates for extraction jobs in the Tender Management system.

## Features Implemented

### 📋 Core Functionality

1. **PDF Preview Loading**
   - Automatically loads the first PDF file from selected files
   - Renders the first page for region selection
   - Scales PDF to fit the modal window (max 800px width)

2. **Interactive Region Selection**
   - Click and drag to define rectangular region
   - Visual feedback with blue overlay during selection
   - Green overlay shows confirmed selection
   - Crosshair cursor for precision

3. **Coordinate Management**
   - Automatically converts canvas coordinates to PDF coordinates
   - Accounts for PDF scaling to maintain accuracy
   - Stores coordinates in pixels relative to original PDF dimensions

4. **Visual Feedback**
   - Real-time rectangle preview while dragging
   - Color-coded overlays:
     - **Blue** (`#0078d4`): Current selection being drawn
     - **Green** (`#28a745`): Confirmed saved selection
   - Display of selected region dimensions and position

5. **User Controls**
   - **Reset Selection**: Clear current selection and start over
   - **Confirm Selection**: Save selection and close modal
   - **Close**: Cancel without saving changes

## User Workflow

### Step 1: Open Extraction Modal
1. Select one or more PDF files in the tender
2. Click "Queue Extraction"
3. Extraction modal opens

### Step 2: Select Title Block Region
1. Click "Select Title Block Region" button
2. Region selector modal opens with PDF preview
3. Click and drag on the PDF to define the title block area
4. Selection rectangle appears with blue highlight
5. Release mouse to finalize selection
6. Selection turns green and coordinates are displayed

### Step 3: Confirm or Adjust
- **To adjust**: Click "Reset Selection" and draw again
- **To confirm**: Click "Confirm Selection"
- Coordinates are saved and modal closes

### Step 4: Submit Extraction Job
1. Review discipline selection
2. Review selected region coordinates
3. Click "Submit" to queue the extraction job

## Technical Implementation

### Components Modified

#### `ExtractionModal.tsx`
- Added PDF.js integration for rendering
- Implemented mouse event handlers for drawing
- Canvas-based selection with coordinate tracking
- Nested modal for region selector

#### `ExtractionModal.css` (New)
- Styled region selector modal (z-index: 2000)
- Canvas wrapper with scrolling support
- Instruction banner and selection info display
- Responsive design for various screen sizes

### Key Functions

```typescript
loadPdfPreview()      // Loads first PDF file for preview
renderPdfPage()       // Renders PDF page to canvas
handleCanvasMouseDown()  // Start selection
handleCanvasMouseMove()  // Update selection rectangle
handleCanvasMouseUp()    // Finalize selection
drawSelection()       // Draw selection overlay on canvas
```

### Coordinate System

The tool manages two coordinate systems:

1. **Canvas Coordinates**: Screen pixels on the displayed canvas
2. **PDF Coordinates**: Original PDF document pixels

**Conversion Formula**:
```typescript
pdfCoords = {
  x: canvasX / scale,
  y: canvasY / scale,
  width: canvasWidth / scale,
  height: canvasHeight / scale
}
```

This ensures coordinates remain accurate regardless of how the PDF is scaled for display.

## State Management

### Modal State
- `showRegionSelector`: Controls visibility of region selector
- `isLoadingPdf`: Loading state for PDF preview
- `pdfError`: Error message if PDF fails to load

### Selection State
- `isDrawing`: Whether user is currently drawing
- `startPoint`: Initial mouse position when drawing started
- `currentRect`: Current selection rectangle (canvas coords)
- `coords`: Saved coordinates (PDF coords)

### PDF State
- `pdfDocRef`: Reference to loaded PDF document
- `pdfScale`: Scale factor applied to PDF
- `renderTaskRef`: Current render task for cancellation

## Error Handling

1. **No PDF Files**: Shows error if no PDF files are selected
2. **Load Failure**: Displays error message if PDF fails to load
3. **Render Cancellation**: Properly handles cancelled render operations
4. **Cleanup**: Destroys PDF document and cancels renders on unmount

## UI/UX Features

### Visual Design
- **Nested Modal**: Region selector appears on top of extraction modal
- **Dark Overlay**: 70% opacity black background for focus
- **Instruction Banner**: Blue info banner with clear instructions
- **Selection Info**: Green success banner showing coordinates

### Accessibility
- Clear button labels
- Color-coded visual feedback
- Keyboard-friendly (can press Escape to close modals)
- Loading states prevent user confusion

### Responsive Behavior
- Canvas scrolls if PDF is larger than viewport
- Maximum modal size: 90vw × 90vh
- Maximum canvas display height: 60vh
- Scales PDF to fit available space

## Integration with Backend

The selected coordinates are sent to the UiPath API:

```typescript
await uipathApi.queueExtraction(
  tenderId,
  files.map(f => f.path),
  discipline,
  coords  // { x, y, width, height } in PDF pixels
);
```

## Default Coordinates

If user doesn't select a region, default coordinates are used:
```typescript
{ x: 0, y: 0, width: 100, height: 50 }
```

## Browser Compatibility

Works in all modern browsers that support:
- Canvas API
- Mouse events
- PDF.js library
- CSS Grid/Flexbox

## Performance Considerations

- Only loads first PDF file (not all selected files)
- Renders only first page (not entire document)
- Cancels previous render operations before starting new ones
- Cleans up PDF document when modal closes

## Future Enhancements

Potential improvements:
1. **Multi-page selection**: Select different regions on different pages
2. **Preset templates**: Common title block locations
3. **Fine-tune controls**: Arrow keys for pixel-perfect adjustment
4. **Zoom controls**: Zoom in/out on PDF preview
5. **Multiple regions**: Define header, footer, and title block separately
6. **Preview overlay**: Show what will be extracted
7. **Auto-detection**: ML-based title block detection
8. **Save templates**: Save commonly used selections
