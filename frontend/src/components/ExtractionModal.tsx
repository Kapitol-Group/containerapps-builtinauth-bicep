import React, { useState, useRef, useEffect } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import {
  TenderFile,
  TitleBlockCoords,
  Tender,
  MFilesDocumentClass,
  MFilesQueueDefault,
  MFilesSearchField,
  MFilesPropertyValue,
  MFilesExtractionProperty,
} from '../types';
import { uipathApi, filesApi, tendersApi, sharepointApi, mfilesApi } from '../services/api';
import { getGraphApiToken, msalInstance } from '../authConfig';
import Dialog from './Dialog';
import './CreateTenderModal.css';
import './ExtractionModal.css';

// Configure PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.mjs',
  import.meta.url
).toString();

interface ExtractionModalProps {
  tenderId: string;
  tenderName?: string;
  files: TenderFile[];
  onClose: () => void;
  onSubmit: () => void;
}

// Known standard page sizes in PDF points (1 pt = 1/72 inch)
const KNOWN_PAGE_SIZES: Array<{ name: string; width: number; height: number }> = [
  { name: 'A0', width: 3370, height: 2384 },
  { name: 'A1', width: 2384, height: 1684 },
  { name: 'A2', width: 1684, height: 1191 },
  { name: 'A3', width: 1191, height: 842 },
  { name: 'A4', width: 842, height: 595 },
  { name: 'ANSI D', width: 2448, height: 1584 },
  { name: 'ANSI E', width: 3168, height: 2448 },
  { name: 'ARCH D', width: 2592, height: 1728 },
  { name: 'ARCH E', width: 3456, height: 2592 },
];

const PAGE_SIZE_TOLERANCE = 20; // PDF points (~7mm)

interface PageSizeInfo {
  fileName: string;
  width: number;
  height: number;
  error?: string;
}

interface MFilesFieldSelection {
  value: string;
  value_id: string;
  values: string[];
  value_ids: string[];
}

interface MFilesLookupMatchResult {
  matchedValue: MFilesPropertyValue | null;
  helperMessage: string;
}

const DEFAULT_MFILES_FIELD_SELECTION: MFilesFieldSelection = {
  value: '',
  value_id: '',
  values: [],
  value_ids: [],
};

function identifyPageSize(w: number, h: number): string {
  // Normalise to landscape (wider dimension first) for comparison
  const [wide, narrow] = w >= h ? [w, h] : [h, w];
  for (const size of KNOWN_PAGE_SIZES) {
    const [sWide, sNarrow] = size.width >= size.height
      ? [size.width, size.height]
      : [size.height, size.width];
    if (
      Math.abs(wide - sWide) <= PAGE_SIZE_TOLERANCE &&
      Math.abs(narrow - sNarrow) <= PAGE_SIZE_TOLERANCE
    ) {
      return size.name;
    }
  }
  return 'Custom';
}

function areSameSize(a: PageSizeInfo, b: PageSizeInfo): boolean {
  // Compare in both orientations
  const matchSame =
    Math.abs(a.width - b.width) <= PAGE_SIZE_TOLERANCE &&
    Math.abs(a.height - b.height) <= PAGE_SIZE_TOLERANCE;
  const matchFlipped =
    Math.abs(a.width - b.height) <= PAGE_SIZE_TOLERANCE &&
    Math.abs(a.height - b.width) <= PAGE_SIZE_TOLERANCE;
  return matchSame || matchFlipped;
}

function getMFilesDataType(field: MFilesSearchField): number {
  const parsed = Number(field.data_type);
  return Number.isFinite(parsed) ? parsed : -1;
}

function isLookupField(field: MFilesSearchField): boolean {
  const dataType = getMFilesDataType(field);
  return dataType === 9 || dataType === 10;
}

function isMultiSelectLookupField(field: MFilesSearchField): boolean {
  return getMFilesDataType(field) === 10;
}

function getSignedInUserDisplayName(): string {
  const activeAccount = msalInstance.getActiveAccount() || msalInstance.getAllAccounts()[0];
  return String(activeAccount?.name || activeAccount?.username || '').trim();
}

function getSelectionHasValue(field: MFilesSearchField, selection: MFilesFieldSelection): boolean {
  const dataType = getMFilesDataType(field);
  if (dataType === 10) {
    return selection.value_ids.length > 0 && selection.values.length > 0;
  }
  if (dataType === 9) {
    return Boolean(selection.value_id && selection.value.trim());
  }
  return Boolean(selection.value.trim());
}

function getResolvedCurrentUserValue(
  rule: MFilesQueueDefault | undefined,
  currentUserDisplayName: string,
): string {
  if (!rule || rule.rule_type !== 'current_user') {
    return '';
  }
  return String(rule.text_value || '').trim() || currentUserDisplayName.trim();
}

function getTextPrefillValue(rule: MFilesQueueDefault | undefined, currentUserDisplayName: string): string {
  if (!rule) {
    return '';
  }
  if (rule.rule_type === 'fixed_text') {
    return rule.text_value?.trim() || '';
  }
  if (rule.rule_type === 'current_user') {
    return getResolvedCurrentUserValue(rule, currentUserDisplayName);
  }
  return '';
}

function findLookupDefaultMatch(
  field: MFilesSearchField,
  rule: MFilesQueueDefault | undefined,
  values: MFilesPropertyValue[],
  currentUserDisplayName: string,
): MFilesLookupMatchResult {
  if (!rule) {
    return { matchedValue: null, helperMessage: '' };
  }

  const normalizedValues = values.map((item) => ({
    ...item,
    normalizedName: item.name.trim().toLowerCase(),
  }));

  const byId = (rule.lookup_value_id || '').trim();
  if (rule.rule_type === 'fixed_lookup') {
    if (byId) {
      const idMatch = values.find((item) => item.id === byId);
      if (idMatch) {
        return { matchedValue: idMatch, helperMessage: '' };
      }
    }

    const lookupName = (rule.lookup_value_name || '').trim().toLowerCase();
    if (!lookupName) {
      return { matchedValue: null, helperMessage: '' };
    }

    const nameMatch = normalizedValues.find((item) => item.normalizedName === lookupName);
    return {
      matchedValue: nameMatch || null,
      helperMessage: '',
    };
  }

  if (rule.rule_type === 'current_user') {
    const resolvedCurrentUserValue = getResolvedCurrentUserValue(rule, currentUserDisplayName);
    const displayValue = resolvedCurrentUserValue.trim().toLowerCase();
    if (!displayValue) {
      return { matchedValue: null, helperMessage: '' };
    }

    const nameMatch = normalizedValues.find((item) => item.normalizedName === displayValue);
    return {
      matchedValue: nameMatch || null,
      helperMessage: nameMatch
        ? ''
        : `No M-Files value matched the signed-in user "${resolvedCurrentUserValue}".`,
    };
  }

  if (!isLookupField(field)) {
    return { matchedValue: null, helperMessage: '' };
  }

  return { matchedValue: null, helperMessage: '' };
}

const ExtractionModal: React.FC<ExtractionModalProps> = ({ tenderId, tenderName, files, onClose, onSubmit }) => {
  const [destination, setDestination] = useState('');
  const [destinations, setDestinations] = useState<Array<{ name: string; path: string }>>([]);
  const [isLoadingDestinations, setIsLoadingDestinations] = useState(false);
  const [tenderType, setTenderType] = useState<'sharepoint' | 'mfiles'>('sharepoint');
  const [mfilesDocumentClass, setMfilesDocumentClass] = useState('');
  const [mfilesDocumentClasses, setMfilesDocumentClasses] = useState<MFilesDocumentClass[]>([]);
  const [isLoadingMfilesDocumentClasses, setIsLoadingMfilesDocumentClasses] = useState(false);
  const [mfilesDocumentClassesError, setMfilesDocumentClassesError] = useState('');
  const [isDocumentClassDropdownOpen, setIsDocumentClassDropdownOpen] = useState(false);
  const [documentClassFilter, setDocumentClassFilter] = useState('');
  const [mfilesMandatoryFields, setMfilesMandatoryFields] = useState<MFilesSearchField[]>([]);
  const [isLoadingMfilesMandatoryFields, setIsLoadingMfilesMandatoryFields] = useState(false);
  const [mfilesMandatoryFieldsError, setMfilesMandatoryFieldsError] = useState('');
  const [mfilesFieldValues, setMfilesFieldValues] = useState<Record<number, MFilesFieldSelection>>({});
  const [mfilesFieldTouchedById, setMfilesFieldTouchedById] = useState<Record<number, boolean>>({});
  const [mfilesDefaultHelperByFieldId, setMfilesDefaultHelperByFieldId] = useState<Record<number, string>>({});
  const [mfilesPropertyValuesByFieldId, setMfilesPropertyValuesByFieldId] = useState<Record<number, MFilesPropertyValue[]>>({});
  const [mfilesPropertyValuesLoadingByFieldId, setMfilesPropertyValuesLoadingByFieldId] = useState<Record<number, boolean>>({});
  const [mfilesPropertyValuesErrorByFieldId, setMfilesPropertyValuesErrorByFieldId] = useState<Record<number, string>>({});
  const [mfilesPropertyValueFilterByFieldId, setMfilesPropertyValueFilterByFieldId] = useState<Record<number, string>>({});
  const [openMultiSelectFieldId, setOpenMultiSelectFieldId] = useState<number | null>(null);
  const [coords, setCoords] = useState<TitleBlockCoords>({ x: 0, y: 0, width: 0, height: 0 });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showRegionSelector, setShowRegionSelector] = useState(false);
  const [isLoadingPdf, setIsLoadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [errorDialog, setErrorDialog] = useState<{ show: boolean; message: string }>({ show: false, message: '' });
  const [requiresTitleBlock, setRequiresTitleBlock] = useState(false);
  const [tender, setTender] = useState<Tender | null>(null);
  const [isCheckingPageSizes, setIsCheckingPageSizes] = useState(false);
  const [pageSizeWarning, setPageSizeWarning] = useState<string | null>(null);
  const [pageSizeCheckPassed, setPageSizeCheckPassed] = useState(false);
  
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pdfDocRef = useRef<PDFDocumentProxy | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPoint, setStartPoint] = useState<{ x: number; y: number } | null>(null);
  const [currentRect, setCurrentRect] = useState<TitleBlockCoords | null>(null);
  const [pdfScale, setPdfScale] = useState(1.0);
  const renderTaskRef = useRef<any>(null);
  const animationFrameRef = useRef<number | null>(null);
  const offscreenCanvasRef = useRef<HTMLCanvasElement | null>(null); // Store rendered PDF
  const mfilesFieldTouchedByIdRef = useRef<Record<number, boolean>>({});
  const isMFilesTender = tenderType === 'mfiles';
  const currentUserDisplayName = getSignedInUserDisplayName();

  useEffect(() => {
    mfilesFieldTouchedByIdRef.current = mfilesFieldTouchedById;
  }, [mfilesFieldTouchedById]);

  useEffect(() => {
    let cancelled = false;

    const loadTenderContext = async () => {
      setIsLoadingDestinations(true);
      setIsLoadingMfilesDocumentClasses(false);
      setMfilesDocumentClassesError('');
      setMfilesMandatoryFieldsError('');

      try {
        const tenderData = await tendersApi.get(tenderId);
        if (cancelled) {
          return;
        }

        setTender(tenderData);
        const resolvedTenderType = (tenderData.tender_type || 'sharepoint').toLowerCase() === 'mfiles'
          ? 'mfiles'
          : 'sharepoint';
        setTenderType(resolvedTenderType);

        if (resolvedTenderType === 'mfiles') {
          setDestinations([]);
          setDestination('');
          setIsDocumentClassDropdownOpen(false);
          setDocumentClassFilter('');
          setIsLoadingMfilesDocumentClasses(true);

          try {
            const classes = await mfilesApi.getDocumentClasses();
            if (cancelled) {
              return;
            }

            const normalizedClasses = classes.filter((item) => item?.name?.trim());
            setMfilesDocumentClasses(normalizedClasses);

            const drawingClass = normalizedClasses.find(
              (item) => item.name.trim().toLowerCase() === 'drawing'
            );
            const defaultClass = drawingClass?.name || normalizedClasses[0]?.name || 'Drawing';
            setMfilesDocumentClass(defaultClass);
          } catch (mfilesError: any) {
            if (!cancelled) {
              setMfilesDocumentClasses([{ id: 'Drawing', name: 'Drawing' }]);
              setMfilesDocumentClass('Drawing');
              setMfilesDocumentClassesError(mfilesError?.message || 'Failed to load M-Files document classes');
            }
          } finally {
            if (!cancelled) {
              setIsLoadingMfilesDocumentClasses(false);
            }
          }

          return;
        }

        if (!tenderData.output_library_id || !tenderData.output_folder_path) {
          console.warn('Tender missing output location configuration');
          setDestinations([]);
          setDestination('');
          return;
        }

        const accessToken = await getGraphApiToken('https://graph.microsoft.com');
        if (!accessToken) {
          console.error('Failed to get Graph API token');
          setDestinations([]);
          setDestination('');
          return;
        }

        const folders = await sharepointApi.listFolders(
          accessToken,
          tenderData.output_library_id,
          tenderData.output_folder_path
        );

        if (cancelled) {
          return;
        }

        setDestinations(folders.map(f => ({ name: f.name, path: f.path })));
        if (folders.length > 0) {
          setDestination(folders[0].name);
        } else {
          setDestination('');
        }
      } catch (error) {
        console.error('Failed to load destinations:', error);
        if (!cancelled) {
          setErrorDialog({
            show: true,
            message: 'Failed to load queue extraction settings. Please check tender configuration.'
          });
        }
      } finally {
        if (!cancelled) {
          setIsLoadingDestinations(false);
        }
      }
    };

    loadTenderContext();

    return () => {
      cancelled = true;
    };
  }, [tenderId]);

  useEffect(() => {
    if (!isMFilesTender || !mfilesDocumentClass.trim()) {
      return;
    }

    let cancelled = false;

    setMfilesMandatoryFields([]);
    setMfilesFieldValues({});
    setMfilesFieldTouchedById({});
    setMfilesDefaultHelperByFieldId({});
    setMfilesPropertyValuesByFieldId({});
    setMfilesPropertyValuesLoadingByFieldId({});
    setMfilesPropertyValuesErrorByFieldId({});
    setMfilesPropertyValueFilterByFieldId({});

    const timer = setTimeout(async () => {
      setIsLoadingMfilesMandatoryFields(true);
      setMfilesMandatoryFieldsError('');

      try {
        const fields = await mfilesApi.getSearchFields(mfilesDocumentClass.trim());
        if (cancelled) {
          return;
        }

        const mandatoryFields = fields.filter((field) => {
          if (typeof field.queue_required === 'boolean') {
            return field.queue_required;
          }
          return field.required && !field.system_auto_fill;
        });
        setMfilesMandatoryFields(mandatoryFields);

        setMfilesFieldValues((previous) => {
          const nextValues: Record<number, MFilesFieldSelection> = {};
          mandatoryFields.forEach((field) => {
            const existing = previous[field.id] || DEFAULT_MFILES_FIELD_SELECTION;
            const isLockedProjectField = field.name.trim().toLowerCase() === 'project' && Boolean(tender?.mfiles_project_name);
            const defaultTextValue = getTextPrefillValue(field.queue_default, currentUserDisplayName);

            if (isLockedProjectField) {
              nextValues[field.id] = { ...existing, value: tender?.mfiles_project_name || '' };
              return;
            }

            if (!isLookupField(field) && defaultTextValue) {
              nextValues[field.id] = { ...existing, value: defaultTextValue };
              return;
            }

            nextValues[field.id] = existing;
          });
          return nextValues;
        });

        setMfilesDefaultHelperByFieldId(() => {
          const nextHelpers: Record<number, string> = {};
          mandatoryFields.forEach((field) => {
            nextHelpers[field.id] = '';
          });
          return nextHelpers;
        });
      } catch (error: any) {
        if (!cancelled) {
          setMfilesMandatoryFields([]);
          setMfilesMandatoryFieldsError(error?.message || 'Failed to load mandatory M-Files properties');
        }
      } finally {
        if (!cancelled) {
          setIsLoadingMfilesMandatoryFields(false);
        }
      }
    }, 250);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [currentUserDisplayName, isMFilesTender, mfilesDocumentClass, tender?.mfiles_project_name]);

  useEffect(() => {
    if (!isMFilesTender || mfilesMandatoryFields.length === 0) {
      return;
    }

    let cancelled = false;

    const lookupFields = mfilesMandatoryFields.filter((field) => isLookupField(field));
    lookupFields.forEach((field) => {
      const fieldId = field.id;
      if (
        mfilesPropertyValuesByFieldId[fieldId] ||
        mfilesPropertyValuesLoadingByFieldId[fieldId]
      ) {
        return;
      }

      setMfilesPropertyValuesLoadingByFieldId((previous) => ({ ...previous, [fieldId]: true }));
      setMfilesPropertyValuesErrorByFieldId((previous) => ({ ...previous, [fieldId]: '' }));

      mfilesApi.getPropertyValues(fieldId)
        .then((values) => {
          if (cancelled) {
            return;
          }

          setMfilesPropertyValuesByFieldId((previous) => ({ ...previous, [fieldId]: values }));

          const isLockedProjectField = field.name.trim().toLowerCase() === 'project' && Boolean(tender?.mfiles_project_name);
          if (isLockedProjectField) {
            const matched = values.find((item) => item.name.trim().toLowerCase() === (tender?.mfiles_project_name || '').trim().toLowerCase());
            setMfilesFieldValues((previous) => ({
              ...previous,
              [fieldId]: {
                ...(previous[fieldId] || DEFAULT_MFILES_FIELD_SELECTION),
                value: tender?.mfiles_project_name || '',
                value_id: matched?.id || '',
                values: isMultiSelectLookupField(field) && matched ? [matched.name] : (previous[fieldId]?.values || []),
                value_ids: isMultiSelectLookupField(field) && matched ? [matched.id] : (previous[fieldId]?.value_ids || []),
              },
            }));
            setMfilesDefaultHelperByFieldId((previous) => ({
              ...previous,
              [fieldId]: '',
            }));
            return;
          }

          if (mfilesFieldTouchedByIdRef.current[fieldId]) {
            return;
          }

          const defaultRule = field.queue_default;
          const defaultMatch = findLookupDefaultMatch(field, defaultRule, values, currentUserDisplayName);
          const nextHelper = defaultMatch.helperMessage;
          setMfilesDefaultHelperByFieldId((previous) => ({
            ...previous,
            [fieldId]: nextHelper,
          }));

          if (!defaultMatch.matchedValue) {
            return;
          }

          const matchedValue = defaultMatch.matchedValue;

          setMfilesFieldValues((previous) => {
            const existing = previous[fieldId] || DEFAULT_MFILES_FIELD_SELECTION;
            if (getSelectionHasValue(field, existing)) {
              return previous;
            }

            if (isMultiSelectLookupField(field)) {
              return {
                ...previous,
                [fieldId]: {
                  ...existing,
                  value: matchedValue.name,
                  value_id: matchedValue.id,
                  values: [matchedValue.name],
                  value_ids: [matchedValue.id],
                },
              };
            }

            return {
              ...previous,
              [fieldId]: {
                ...existing,
                value: matchedValue.name,
                value_id: matchedValue.id,
                values: [],
                value_ids: [],
              },
            };
          });
        })
        .catch((error: any) => {
          if (!cancelled) {
            setMfilesPropertyValuesByFieldId((previous) => ({ ...previous, [fieldId]: [] }));
            setMfilesPropertyValuesErrorByFieldId((previous) => ({
              ...previous,
              [fieldId]: error?.message || 'Failed to load property values',
            }));
          }
        })
        .finally(() => {
          if (!cancelled) {
            setMfilesPropertyValuesLoadingByFieldId((previous) => ({ ...previous, [fieldId]: false }));
          }
        });
    });

    return () => {
      cancelled = true;
    };
  }, [currentUserDisplayName, isMFilesTender, mfilesMandatoryFields, tender?.mfiles_project_name]);

  // Check page sizes when title block processing is toggled on
  useEffect(() => {
    if (!requiresTitleBlock) {
      setPageSizeWarning(null);
      setPageSizeCheckPassed(false);
      return;
    }

    const pdfFiles = files.filter(
      f => f.content_type?.toLowerCase().includes('pdf') || f.name.toLowerCase().endsWith('.pdf')
    );

    // Nothing to compare with 0 or 1 PDF
    if (pdfFiles.length <= 1) {
      setPageSizeWarning(null);
      setPageSizeCheckPassed(pdfFiles.length === 1);
      return;
    }

    let cancelled = false;

    const checkPageSizes = async () => {
      setIsCheckingPageSizes(true);
      setPageSizeWarning(null);
      setPageSizeCheckPassed(false);

      const results: PageSizeInfo[] = [];

      const settled = await Promise.allSettled(
        pdfFiles.map(async (file): Promise<PageSizeInfo> => {
          const blob = await filesApi.download(tenderId, file.path);
          const arrayBuffer = await blob.arrayBuffer();
          const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
          const pdf = await loadingTask.promise;
          try {
            const page = await pdf.getPage(1);
            const viewport = page.getViewport({ scale: 1.0 });
            return { fileName: file.name, width: Math.round(viewport.width), height: Math.round(viewport.height) };
          } finally {
            pdf.destroy();
          }
        })
      );

      if (cancelled) return;

      for (const result of settled) {
        if (result.status === 'fulfilled') {
          results.push(result.value);
        } else {
          // Extract filename from the rejection if possible
          results.push({ fileName: '(unknown file)', width: 0, height: 0, error: 'Could not read page size' });
        }
      }

      // Also capture files that individually failed
      const errors = results.filter(r => r.error);
      const valid = results.filter(r => !r.error);

      // Group valid results by page size
      const groups: PageSizeInfo[][] = [];
      for (const info of valid) {
        let placed = false;
        for (const group of groups) {
          if (areSameSize(group[0], info)) {
            group.push(info);
            placed = true;
            break;
          }
        }
        if (!placed) {
          groups.push([info]);
        }
      }

      if (groups.length <= 1 && errors.length === 0) {
        setPageSizeCheckPassed(true);
        setIsCheckingPageSizes(false);
        return;
      }

      // Build warning message
      const parts: string[] = [];
      for (const group of groups) {
        const rep = group[0];
        const label = identifyPageSize(rep.width, rep.height);
        const fileNames = group.map(g => g.fileName).join(', ');
        parts.push(
          `${label} (${rep.width}×${rep.height} pts) — ${group.length} file${group.length > 1 ? 's' : ''}: ${fileNames}`
        );
      }
      for (const err of errors) {
        parts.push(`⚠ ${err.fileName}: ${err.error}`);
      }

      setPageSizeWarning(
        `Selected PDFs have different page sizes. The title block region may not align correctly on all files.\n\n${parts.join('\n')}`
      );
      setIsCheckingPageSizes(false);
    };

    checkPageSizes();

    return () => {
      cancelled = true;
    };
  }, [requiresTitleBlock, files, tenderId]);

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
      console.log('[ExtractionModal] PDF page original size', viewport.width, 'x', viewport.height);
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

      // Log canvas dimensions and scale for debugging
      console.log(`[ExtractionModal] Canvas size: ${canvas.width}x${canvas.height}, PDF viewport: ${scaledViewport.width}x${scaledViewport.height}, scale: ${scale}`);
      
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

  const updateMfilesFieldSelection = (
    fieldId: number,
    patch: Partial<MFilesFieldSelection>,
    options?: { markTouched?: boolean; clearHelper?: boolean },
  ) => {
    setMfilesFieldValues((previous) => ({
      ...previous,
      [fieldId]: {
        ...(previous[fieldId] || DEFAULT_MFILES_FIELD_SELECTION),
        ...patch,
      },
    }));

    if (options?.markTouched !== false) {
      setMfilesFieldTouchedById((previous) => ({
        ...previous,
        [fieldId]: true,
      }));
    }

    if (options?.clearHelper !== false) {
      setMfilesDefaultHelperByFieldId((previous) => ({
        ...previous,
        [fieldId]: '',
      }));
    }
  };

  useEffect(() => {
    if (openMultiSelectFieldId === null && !isDocumentClassDropdownOpen) {
      return;
    }

    const handleDocumentMouseDown = (event: MouseEvent) => {
      const target = event.target as Element | null;
      if (!target) {
        return;
      }

      const withinMultiSelectDropdown = target.closest(
        `[data-mfiles-multiselect-field-id="${openMultiSelectFieldId}"]`
      );
      const withinClassDropdown = target.closest('[data-mfiles-docclass-dropdown="true"]');

      if (!withinMultiSelectDropdown) {
        setOpenMultiSelectFieldId(null);
      }
      if (!withinClassDropdown) {
        setIsDocumentClassDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleDocumentMouseDown);
    return () => {
      document.removeEventListener('mousedown', handleDocumentMouseDown);
    };
  }, [openMultiSelectFieldId, isDocumentClassDropdownOpen]);

  const handleSubmit = async () => {
    try {
      setIsSubmitting(true);

      const selectedDocClass = mfilesDocumentClass.trim();
      const isSharePointExtraction = !isMFilesTender;
      let extractionCategory = destination;
      let mfilesPayloadClass: string | undefined;
      let mfilesPayloadProperties: MFilesExtractionProperty[] | undefined;

      if (isSharePointExtraction) {
        if (!destination) {
          setErrorDialog({ show: true, message: 'Please select a destination folder.' });
          setIsSubmitting(false);
          return;
        }
      } else {
        if (!selectedDocClass) {
          setErrorDialog({ show: true, message: 'Please select a document class.' });
          setIsSubmitting(false);
          return;
        }

        const missingFields: string[] = [];
        const properties: MFilesExtractionProperty[] = [];

        for (const field of mfilesMandatoryFields) {
          const selection = mfilesFieldValues[field.id] || DEFAULT_MFILES_FIELD_SELECTION;
          const dataType = getMFilesDataType(field);
          const propertyName = field.name.trim();
          const property: MFilesExtractionProperty = {
            property_id: field.id,
            property_name: propertyName,
            data_type: dataType >= 0 ? dataType : undefined,
            data_type_word: field.data_type_word,
          };

          if (dataType === 10) {
            if (selection.value_ids.length === 0 || selection.values.length === 0) {
              missingFields.push(propertyName);
              continue;
            }
            property.value_ids = selection.value_ids;
            property.values = selection.values;
          } else if (dataType === 9) {
            if (!selection.value_id || !selection.value.trim()) {
              missingFields.push(propertyName);
              continue;
            }
            property.value_id = selection.value_id;
            property.value = selection.value.trim();
          } else {
            if (!selection.value.trim()) {
              missingFields.push(propertyName);
              continue;
            }
            property.value = selection.value.trim();
          }

          properties.push(property);
        }

        if (missingFields.length > 0) {
          setErrorDialog({
            show: true,
            message: `Please complete all mandatory M-Files properties: ${missingFields.join(', ')}`
          });
          setIsSubmitting(false);
          return;
        }

        extractionCategory = selectedDocClass;
        mfilesPayloadClass = selectedDocClass;
        mfilesPayloadProperties = properties;
      }
      
      // Validate title block region if required
      if (requiresTitleBlock && (coords.x === 0 && coords.y === 0 && coords.width === 0 && coords.height === 0)) {
        setErrorDialog({ show: true, message: 'Please define a title block region before submitting.' });
        setIsSubmitting(false);
        return;
      }
      
      const batchName = `${extractionCategory} Batch ${new Date().toLocaleString()}`;
      
      // Submit extraction - backend returns immediately after creating batch
      await uipathApi.queueExtraction(
        tenderId,
        tenderName || tenderId,
        files.map(f => f.path),
        extractionCategory,
        coords,
        batchName,
        tender?.sharepoint_folder_path,
        tender?.output_folder_path,
        destinations.map(d => d.name),
        mfilesPayloadClass,
        mfilesPayloadProperties,
      );
      
      // Close modal immediately - batch is queued and processing in background
      onSubmit();
      
      // Show success message
      // Note: The parent component should show a toast/notification that the batch is processing
      console.log(`Batch "${batchName}" submitted successfully. Processing ${files.length} files in background.`);
      
    } catch (error) {
      console.error('Failed to queue extraction:', error);
      setErrorDialog({ show: true, message: 'Failed to queue extraction. Please try again.' });
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

        {!isMFilesTender ? (
          <div className="form-group">
            <label>Destination</label>
            {isLoadingDestinations ? (
              <select disabled>
                <option>Loading folders...</option>
              </select>
            ) : destinations.length > 0 ? (
              <select value={destination} onChange={(e) => setDestination(e.target.value)}>
                {destinations.map((dest) => (
                  <option key={dest.name} value={dest.name}>
                    {dest.name}
                  </option>
                ))}
              </select>
            ) : (
              <select disabled>
                <option>No destination folders available</option>
              </select>
            )}
          </div>
        ) : (
          <>
            <div className="form-group">
              <label htmlFor="mfiles-document-class">Document Class</label>
              <div
                className="mfiles-class-dropdown"
                data-mfiles-docclass-dropdown="true"
              >
                <button
                  id="mfiles-document-class"
                  type="button"
                  className="mfiles-multiselect-trigger mfiles-class-trigger"
                  onClick={() => {
                    if (!isSubmitting && !isLoadingMfilesDocumentClasses) {
                      setIsDocumentClassDropdownOpen((previous) => !previous);
                    }
                  }}
                  disabled={isSubmitting || isLoadingMfilesDocumentClasses}
                >
                  <span className="mfiles-multiselect-trigger-text">
                    {isLoadingMfilesDocumentClasses
                      ? 'Loading classes...'
                      : (mfilesDocumentClass || 'Select document class')}
                  </span>
                  <span className="mfiles-multiselect-trigger-caret">▾</span>
                </button>

                {isDocumentClassDropdownOpen && (
                  <div className="mfiles-multiselect-menu mfiles-class-menu">
                    <div className="mfiles-multiselect-search">
                      <input
                        type="text"
                        value={documentClassFilter}
                        onChange={(event) => setDocumentClassFilter(event.target.value)}
                        placeholder="Type to filter classes..."
                        autoFocus
                      />
                    </div>
                    {(() => {
                      const availableClasses = (
                        mfilesDocumentClasses.length > 0
                          ? mfilesDocumentClasses
                          : [{ id: 'Drawing', name: mfilesDocumentClass || 'Drawing' }]
                      );
                      const classFilterValue = documentClassFilter.trim().toLowerCase();
                      const filteredClasses = classFilterValue
                        ? availableClasses.filter((item) => item.name.toLowerCase().includes(classFilterValue))
                        : availableClasses;

                      if (filteredClasses.length === 0) {
                        return <div className="mfiles-multiselect-empty">No classes match your filter</div>;
                      }

                      return filteredClasses.map((item) => {
                        const isSelected = item.name === mfilesDocumentClass;
                        return (
                          <button
                            key={item.id}
                            type="button"
                            className={`mfiles-class-option ${isSelected ? 'is-selected' : ''}`}
                            onClick={() => {
                              setMfilesDocumentClass(item.name);
                              setIsDocumentClassDropdownOpen(false);
                              setDocumentClassFilter('');
                            }}
                          >
                            <span>{item.name}</span>
                            {isSelected && <span className="mfiles-class-selected-marker">✓</span>}
                          </button>
                        );
                      });
                    })()}
                  </div>
                )}
              </div>
              {mfilesDocumentClassesError && (
                <div className="mfiles-extraction-error">{mfilesDocumentClassesError}</div>
              )}
            </div>

            <div className="form-group">
              <label>Mandatory Properties</label>

              {isLoadingMfilesMandatoryFields ? (
                <div className="mfiles-extraction-helper">
                  Loading mandatory properties for "{mfilesDocumentClass.trim() || 'Drawing'}"...
                </div>
              ) : mfilesMandatoryFieldsError ? (
                <div className="mfiles-extraction-error">{mfilesMandatoryFieldsError}</div>
              ) : mfilesMandatoryFields.length === 0 ? (
                <div className="mfiles-extraction-helper">
                  No mandatory user-entered properties found for this document class.
                </div>
              ) : (
                <div className="mfiles-required-fields">
                  {mfilesMandatoryFields.map((field) => {
                    const selection = mfilesFieldValues[field.id] || DEFAULT_MFILES_FIELD_SELECTION;
                    const lookup = isLookupField(field);
                    const multiLookup = isMultiSelectLookupField(field);
                    const fieldDataTypeWord = (field.data_type_word || '').toLowerCase();
                    const propertyValues = mfilesPropertyValuesByFieldId[field.id] || [];
                    const loadingPropertyValues = Boolean(mfilesPropertyValuesLoadingByFieldId[field.id]);
                    const propertyValuesError = mfilesPropertyValuesErrorByFieldId[field.id];
                    const defaultHelperMessage = mfilesDefaultHelperByFieldId[field.id];
                    const isLockedProjectField = field.name.trim().toLowerCase() === 'project' && Boolean(tender?.mfiles_project_name);
                    const valueFilter = (mfilesPropertyValueFilterByFieldId[field.id] || '').trim().toLowerCase();
                    const filteredPropertyValues = valueFilter
                      ? propertyValues.filter((option) => option.name.toLowerCase().includes(valueFilter))
                      : propertyValues;

                    return (
                      <div key={field.id} className="mfiles-required-field">
                        <label htmlFor={`mfiles-field-${field.id}`}>
                          {field.name}
                          {isLockedProjectField ? ' (Inherited from tender project)' : ''}
                        </label>

                        {lookup ? (
                          multiLookup ? (
                            <div
                              className="mfiles-multiselect-dropdown"
                              data-mfiles-multiselect-field-id={field.id}
                            >
                              <button
                                id={`mfiles-field-${field.id}`}
                                type="button"
                                className="mfiles-multiselect-trigger"
                                onClick={() => {
                                  if (!isSubmitting && !loadingPropertyValues && !isLockedProjectField) {
                                    setOpenMultiSelectFieldId((previous) => previous === field.id ? null : field.id);
                                  }
                                }}
                                disabled={isSubmitting || loadingPropertyValues || isLockedProjectField}
                              >
                                <span className="mfiles-multiselect-trigger-text">
                                  {loadingPropertyValues
                                    ? 'Loading values...'
                                    : selection.values.length > 0
                                    ? selection.values.join(', ')
                                    : 'Select values'}
                                </span>
                                <span className="mfiles-multiselect-trigger-caret">▾</span>
                              </button>

                              {openMultiSelectFieldId === field.id && (
                                <div className="mfiles-multiselect-menu">
                                  <div className="mfiles-multiselect-search">
                                    <input
                                      type="text"
                                      value={mfilesPropertyValueFilterByFieldId[field.id] || ''}
                                      onChange={(event) => {
                                        const nextValue = event.target.value;
                                        setMfilesPropertyValueFilterByFieldId((previous) => ({
                                          ...previous,
                                          [field.id]: nextValue,
                                        }));
                                      }}
                                      placeholder="Type to filter values..."
                                      disabled={loadingPropertyValues}
                                    />
                                  </div>
                                  {loadingPropertyValues ? (
                                    <div className="mfiles-multiselect-empty">Loading values...</div>
                                  ) : filteredPropertyValues.length === 0 ? (
                                    <div className="mfiles-multiselect-empty">No values available</div>
                                  ) : (
                                    filteredPropertyValues.map((option) => {
                                      const isChecked = selection.value_ids.includes(option.id);
                                      return (
                                        <label key={`${option.id}-${option.name}`} className="mfiles-multiselect-option">
                                          <input
                                            type="checkbox"
                                            checked={isChecked}
                                            onChange={(event) => {
                                              const checked = event.target.checked;
                                              const currentIds = selection.value_ids || [];
                                              const currentValues = selection.values || [];
                                              if (checked) {
                                                updateMfilesFieldSelection(field.id, {
                                                  value_ids: [...currentIds, option.id],
                                                  values: [...currentValues, option.name],
                                                });
                                              } else {
                                                updateMfilesFieldSelection(field.id, {
                                                  value_ids: currentIds.filter((id) => id !== option.id),
                                                  values: currentValues.filter((name) => name !== option.name),
                                                });
                                              }
                                            }}
                                          />
                                          <span>{option.name}</span>
                                        </label>
                                      );
                                    })
                                  )}
                                </div>
                              )}
                            </div>
                          ) : (
                            <>
                              {!isLockedProjectField && (
                                <input
                                  type="text"
                                  value={mfilesPropertyValueFilterByFieldId[field.id] || ''}
                                  onChange={(event) => {
                                    const nextValue = event.target.value;
                                    setMfilesPropertyValueFilterByFieldId((previous) => ({
                                      ...previous,
                                      [field.id]: nextValue,
                                    }));
                                  }}
                                  placeholder="Type to filter values..."
                                  disabled={isSubmitting || loadingPropertyValues}
                                  className="mfiles-property-filter-input"
                                />
                              )}
                              <select
                                id={`mfiles-field-${field.id}`}
                                value={selection.value_id}
                                onChange={(event) => {
                                  const selectedId = event.target.value;
                                  const selectedValue = propertyValues.find((option) => option.id === selectedId);
                                  updateMfilesFieldSelection(field.id, {
                                    value_id: selectedId,
                                    value: selectedValue?.name || '',
                                    values: [],
                                    value_ids: [],
                                  });
                                }}
                                disabled={isSubmitting || loadingPropertyValues || isLockedProjectField}
                              >
                                <option value="">
                                  {loadingPropertyValues
                                    ? 'Loading values...'
                                    : propertyValuesError
                                      ? 'Failed to load values'
                                      : filteredPropertyValues.length > 0
                                        ? 'Select value'
                                        : 'No values available'}
                                </option>
                                {filteredPropertyValues.map((option) => (
                                  <option key={`${option.id}-${option.name}`} value={option.id}>
                                    {option.name}
                                  </option>
                                ))}
                              </select>
                            </>
                          )
                        ) : fieldDataTypeWord === 'boolean' ? (
                          <select
                            id={`mfiles-field-${field.id}`}
                            value={selection.value}
                            onChange={(event) => updateMfilesFieldSelection(field.id, {
                              value: event.target.value,
                              value_id: '',
                              values: [],
                              value_ids: [],
                            })}
                            disabled={isSubmitting || isLockedProjectField}
                          >
                            <option value="">Select value</option>
                            <option value="true">True</option>
                            <option value="false">False</option>
                          </select>
                        ) : fieldDataTypeWord === 'timestamp' ? (
                          <input
                            id={`mfiles-field-${field.id}`}
                            type="datetime-local"
                            value={selection.value}
                            onChange={(event) => updateMfilesFieldSelection(field.id, {
                              value: event.target.value,
                              value_id: '',
                              values: [],
                              value_ids: [],
                            })}
                            readOnly={isLockedProjectField}
                            disabled={isSubmitting}
                          />
                        ) : fieldDataTypeWord === 'integer' ? (
                          <input
                            id={`mfiles-field-${field.id}`}
                            type="number"
                            value={selection.value}
                            onChange={(event) => updateMfilesFieldSelection(field.id, {
                              value: event.target.value,
                              value_id: '',
                              values: [],
                              value_ids: [],
                            })}
                            readOnly={isLockedProjectField}
                            disabled={isSubmitting}
                          />
                        ) : fieldDataTypeWord === 'multilinetext' ? (
                          <textarea
                            id={`mfiles-field-${field.id}`}
                            value={selection.value}
                            onChange={(event) => updateMfilesFieldSelection(field.id, {
                              value: event.target.value,
                              value_id: '',
                              values: [],
                              value_ids: [],
                            })}
                            readOnly={isLockedProjectField}
                            disabled={isSubmitting}
                            className="mfiles-textarea"
                          />
                        ) : (
                          <input
                            id={`mfiles-field-${field.id}`}
                            type="text"
                            value={selection.value}
                            onChange={(event) => updateMfilesFieldSelection(field.id, {
                              value: event.target.value,
                              value_id: '',
                              values: [],
                              value_ids: [],
                            })}
                            readOnly={isLockedProjectField}
                            disabled={isSubmitting}
                          />
                        )}

                        {loadingPropertyValues && (
                          <div className="mfiles-extraction-helper">Loading values...</div>
                        )}
                        {defaultHelperMessage && (
                          <div className="mfiles-extraction-helper">{defaultHelperMessage}</div>
                        )}
                        {propertyValuesError && <div className="mfiles-extraction-error">{propertyValuesError}</div>}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </>
        )}
        
        <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input 
            type="checkbox" 
            id="requiresTitleBlock"
            checked={requiresTitleBlock} 
            onChange={(e) => setRequiresTitleBlock(e.target.checked)}
            style={{ cursor: 'pointer', width: '18px', height: '18px', margin: 0 }}
          />
          <label 
            htmlFor="requiresTitleBlock" 
            style={{ cursor: 'pointer', fontWeight: 'normal', margin: 0 }}
          >
            Requires Title Block Processing
          </label>
        </div>
        
        {requiresTitleBlock && isCheckingPageSizes && (
          <div className="page-size-checking">
            Checking page sizes across {files.filter(f => f.content_type?.toLowerCase().includes('pdf') || f.name.toLowerCase().endsWith('.pdf')).length} PDF files…
          </div>
        )}

        {requiresTitleBlock && !isCheckingPageSizes && pageSizeWarning && (
          <div className="page-size-warning">
            <strong>⚠ Page Size Mismatch</strong>
            {pageSizeWarning.split('\n').map((line, i) => (
              <span key={i}>{line}<br /></span>
            ))}
          </div>
        )}

        {requiresTitleBlock && !isCheckingPageSizes && pageSizeCheckPassed && (
          <div className="page-size-ok">
            ✓ All selected PDFs have consistent page sizes
          </div>
        )}

        {requiresTitleBlock && (
          <div className="form-group">
            <label>Define Title Block Region</label>
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
        )}

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

      <Dialog
        isOpen={errorDialog.show}
        title="Error"
        message={errorDialog.message}
        type="alert"
        onConfirm={() => setErrorDialog({ show: false, message: '' })}
      />
    </div>
  );
};

export default ExtractionModal;
