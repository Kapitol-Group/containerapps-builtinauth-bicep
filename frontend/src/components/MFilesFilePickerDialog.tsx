import React, { useEffect, useRef, useState } from 'react';
import { mfilesApi } from '../services/api';
import {
  MFilesDocumentClass,
  MFilesImportDocument,
  MFilesPropertyValue,
  MFilesSearchCriterion,
  MFilesSearchField,
  MFilesSearchModifier,
  MFilesSearchResult,
} from '../types';
import './MFilesFilePickerDialog.css';

const DEFAULT_DOC_CLASS = 'Drawing';
const RESERVED_FIELD_NAMES = new Set(['project', 'class', 'keyword']);

const MODIFIER_OPTIONS: Array<{ value: MFilesSearchModifier; label: string }> = [
  { value: '=', label: '= (equals)' },
  { value: 'contains', label: 'contains' },
  { value: 'startswith', label: 'startswith' },
  { value: 'wild', label: 'wild' },
  { value: '<', label: '<' },
  { value: 'lt', label: 'lt' },
  { value: 'lte', label: 'lte' },
  { value: '>', label: '>' },
  { value: 'gt', label: 'gt' },
  { value: 'gte', label: 'gte' },
  { value: 'equals', label: 'equals' },
  { value: 'quick', label: 'quick' },
];

interface FilterRow {
  id: number;
  name: string;
  modifier: MFilesSearchModifier;
  value: string;
}

interface MFilesFilePickerDialogProps {
  isOpen: boolean;
  tenderId: string;
  projectName: string;
  onClose: () => void;
  onImportSelected: (documents: MFilesImportDocument[]) => Promise<void>;
}

const MFilesFilePickerDialog: React.FC<MFilesFilePickerDialogProps> = ({
  isOpen,
  tenderId,
  projectName,
  onClose,
  onImportSelected,
}) => {
  const nextRowId = useRef(1);

  const [docClass, setDocClass] = useState('');
  const [docClasses, setDocClasses] = useState<MFilesDocumentClass[]>([]);
  const [loadingDocClasses, setLoadingDocClasses] = useState(false);
  const [docClassesError, setDocClassesError] = useState('');

  const [keyword, setKeyword] = useState('');
  const [filters, setFilters] = useState<FilterRow[]>([]);

  const [searchFields, setSearchFields] = useState<MFilesSearchField[]>([]);
  const [loadingSearchFields, setLoadingSearchFields] = useState(false);
  const [searchFieldsError, setSearchFieldsError] = useState('');
  const [propertyValuesByFieldId, setPropertyValuesByFieldId] = useState<Record<number, MFilesPropertyValue[]>>({});
  const [loadingPropertyValuesByFieldId, setLoadingPropertyValuesByFieldId] = useState<Record<number, boolean>>({});
  const [propertyValuesErrorByFieldId, setPropertyValuesErrorByFieldId] = useState<Record<number, string>>({});

  const [results, setResults] = useState<MFilesSearchResult[]>([]);
  const [selectedDisplayIds, setSelectedDisplayIds] = useState<Set<string>>(new Set());
  const [searching, setSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [importingSelection, setImportingSelection] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    setDocClass('');
    setDocClasses([]);
    setLoadingDocClasses(false);
    setDocClassesError('');
    setKeyword('');
    setFilters([]);
    setSearchFields([]);
    setSearchFieldsError('');
    setPropertyValuesByFieldId({});
    setLoadingPropertyValuesByFieldId({});
    setPropertyValuesErrorByFieldId({});
    setResults([]);
    setSelectedDisplayIds(new Set());
    setSearching(false);
    setHasSearched(false);
    setSearchError('');
    setImportingSelection(false);
    nextRowId.current = 1;
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    let cancelled = false;

    const loadDocumentClasses = async () => {
      setLoadingDocClasses(true);
      setDocClassesError('');

      try {
        const classes = await mfilesApi.getDocumentClasses();
        if (cancelled) {
          return;
        }

        const normalizedClasses = classes.filter((item) => item?.name?.trim());
        setDocClasses(normalizedClasses);

        const drawingClass = normalizedClasses.find(
          (item) => item.name.trim().toLowerCase() === DEFAULT_DOC_CLASS.toLowerCase()
        );
        const defaultClass = drawingClass?.name || normalizedClasses[0]?.name || DEFAULT_DOC_CLASS;
        setDocClass(defaultClass);
      } catch (error: any) {
        if (!cancelled) {
          setDocClasses([{ id: DEFAULT_DOC_CLASS, name: DEFAULT_DOC_CLASS }]);
          setDocClass(DEFAULT_DOC_CLASS);
          setDocClassesError(error?.message || 'Failed to load document classes');
        }
      } finally {
        if (!cancelled) {
          setLoadingDocClasses(false);
        }
      }
    };

    loadDocumentClasses();

    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || !docClass.trim()) {
      return;
    }

    let cancelled = false;
    const effectiveDocClass = docClass.trim();
    setPropertyValuesByFieldId({});
    setLoadingPropertyValuesByFieldId({});
    setPropertyValuesErrorByFieldId({});

    const timer = setTimeout(async () => {
      setLoadingSearchFields(true);
      setSearchFieldsError('');

      try {
        const fields = await mfilesApi.getSearchFields(effectiveDocClass);
        if (!cancelled) {
          setSearchFields(
            fields.filter((field) => !RESERVED_FIELD_NAMES.has(field.name.trim().toLowerCase()))
          );
        }
      } catch (error: any) {
        if (!cancelled) {
          setSearchFields([]);
          setSearchFieldsError(error?.message || 'Failed to load metadata fields');
        }
      } finally {
        if (!cancelled) {
          setLoadingSearchFields(false);
        }
      }
    }, 250);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [isOpen, docClass]);

  useEffect(() => {
    if (!isOpen || filters.length === 0 || searchFields.length === 0) {
      return;
    }

    let cancelled = false;
    const lookupFieldIds = Array.from(
      new Set(
        filters
          .map((row) => searchFields.find((field) => field.name === row.name))
          .filter((field): field is MFilesSearchField => Boolean(field))
          .filter((field) => {
            const dataType = Number(field.data_type);
            return dataType === 9 || dataType === 10;
          })
          .map((field) => field.id)
      )
    );

    lookupFieldIds.forEach((fieldId) => {
      if (propertyValuesByFieldId[fieldId] || loadingPropertyValuesByFieldId[fieldId]) {
        return;
      }

      setLoadingPropertyValuesByFieldId((previous) => ({ ...previous, [fieldId]: true }));
      setPropertyValuesErrorByFieldId((previous) => ({ ...previous, [fieldId]: '' }));

      mfilesApi.getPropertyValues(fieldId)
        .then((values) => {
          if (!cancelled) {
            setPropertyValuesByFieldId((previous) => ({ ...previous, [fieldId]: values }));
          }
        })
        .catch((error: any) => {
          if (!cancelled) {
            setPropertyValuesByFieldId((previous) => ({ ...previous, [fieldId]: [] }));
            setPropertyValuesErrorByFieldId((previous) => ({
              ...previous,
              [fieldId]: error?.message || 'Failed to load property values',
            }));
          }
        })
        .finally(() => {
          if (!cancelled) {
            setLoadingPropertyValuesByFieldId((previous) => ({ ...previous, [fieldId]: false }));
          }
        });
    });

    return () => {
      cancelled = true;
    };
  }, [isOpen, filters, searchFields, propertyValuesByFieldId, loadingPropertyValuesByFieldId]);

  if (!isOpen) {
    return null;
  }

  const addFilterRow = () => {
    setFilters((previous) => [
      ...previous,
      {
        id: nextRowId.current++,
        name: '',
        modifier: '=',
        value: '',
      },
    ]);
  };

  const removeFilterRow = (id: number) => {
    setFilters((previous) => previous.filter((row) => row.id !== id));
  };

  const updateFilterRow = (id: number, patch: Partial<FilterRow>) => {
    setFilters((previous) => previous.map((row) => (row.id === id ? { ...row, ...patch } : row)));
  };

  const handleSearch = async (event: React.FormEvent) => {
    event.preventDefault();

    setSearching(true);
    setSearchError('');
    setHasSearched(false);

    try {
      const criteria: MFilesSearchCriterion[] = filters
        .filter((row) => row.name.trim() && row.value.trim())
        .map((row) => ({
          name: row.name.trim(),
          modifier: row.modifier,
          value: row.value.trim(),
        }));

      const response = await mfilesApi.searchDocuments({
        tender_id: tenderId,
        doc_class: docClass.trim() || DEFAULT_DOC_CLASS,
        keyword: keyword.trim() || undefined,
        criteria,
      });

      setResults(response.results || []);
      setSelectedDisplayIds(new Set());
      setHasSearched(true);
    } catch (error: any) {
      setSearchError(error?.message || 'Failed to search M-Files');
      setResults([]);
      setSelectedDisplayIds(new Set());
      setHasSearched(true);
    } finally {
      setSearching(false);
    }
  };

  const isSelected = (displayId: string) => selectedDisplayIds.has(displayId);

  const toggleSelection = (displayId: string, checked: boolean) => {
    setSelectedDisplayIds((previous) => {
      const next = new Set(previous);
      if (checked) {
        next.add(displayId);
      } else {
        next.delete(displayId);
      }
      return next;
    });
  };

  const allResultsSelected = results.length > 0 && results.every((result) => selectedDisplayIds.has(result.display_id));

  const toggleSelectAll = () => {
    if (allResultsSelected) {
      setSelectedDisplayIds(new Set());
      return;
    }

    setSelectedDisplayIds(new Set(results.map((result) => result.display_id)));
  };

  const selectedCount = selectedDisplayIds.size;

  const handleImport = async () => {
    if (selectedCount === 0 || importingSelection) {
      return;
    }

    const selectedDocuments: MFilesImportDocument[] = results
      .filter((result) => selectedDisplayIds.has(result.display_id))
      .map((result) => ({
        display_id: result.display_id,
        title: result.title,
        filename: result.primary_filename || result.file_names?.[0] || undefined,
      }));

    setImportingSelection(true);
    setSearchError('');

    try {
      await onImportSelected(selectedDocuments);
      onClose();
    } catch (error: any) {
      setSearchError(error?.message || 'Failed to start M-Files import');
    } finally {
      setImportingSelection(false);
    }
  };

  const renderFileSummary = (result: MFilesSearchResult) => {
    if (!result.file_count) {
      return 'No file details';
    }

    const first = result.primary_filename || result.file_names?.[0] || 'Document';
    if (result.file_count === 1) {
      return first;
    }

    return `${first} (+${result.file_count - 1} more)`;
  };

  return (
    <div
      className="mfiles-picker-overlay"
      onClick={() => {
        if (!importingSelection) {
          onClose();
        }
      }}
    >
      <div className="mfiles-picker-dialog" onClick={(event) => event.stopPropagation()}>
        <div className="mfiles-picker-header">
          <h2>Browse M-Files</h2>
          <button
            type="button"
            className="mfiles-picker-close"
            onClick={onClose}
            aria-label="Close M-Files picker"
            disabled={importingSelection}
          >
            ×
          </button>
        </div>

        <form className="mfiles-search-panel" onSubmit={handleSearch}>
          <div className="mfiles-search-grid">
            <div className="mfiles-form-field">
              <label>Project (Locked)</label>
              <input type="text" value={projectName || 'Not configured'} readOnly />
            </div>

            <div className="mfiles-form-field">
              <label htmlFor="mfiles-doc-class">Class</label>
              <input
                id="mfiles-doc-class"
                type="text"
                list="mfiles-doc-class-options"
                value={docClass}
                onChange={(event) => setDocClass(event.target.value)}
                disabled={searching || importingSelection || loadingDocClasses}
                placeholder={loadingDocClasses ? 'Loading classes...' : 'Type to filter classes'}
              />
              <datalist id="mfiles-doc-class-options">
                {(docClasses.length > 0 ? docClasses : [{ id: DEFAULT_DOC_CLASS, name: docClass || DEFAULT_DOC_CLASS }]).map((item) => (
                  <option key={item.id} value={item.name} />
                ))}
              </datalist>
            </div>

            <div className="mfiles-form-field mfiles-form-field-keyword">
              <label htmlFor="mfiles-keyword">Keyword (Quick Search)</label>
              <input
                id="mfiles-keyword"
                type="text"
                value={keyword}
                onChange={(event) => setKeyword(event.target.value)}
                placeholder="Search any field (title, filename, etc.)"
                disabled={searching || importingSelection}
              />
            </div>
          </div>

          <div className="mfiles-filter-section">
            <div className="mfiles-filter-header">
              <h3>Additional Metadata Filters</h3>
              <button
                type="button"
                className="btn-secondary"
                onClick={addFilterRow}
                disabled={searching || importingSelection}
              >
                + Add Filter
              </button>
            </div>

            {filters.length === 0 ? (
              <p className="mfiles-filter-empty">No extra filters added.</p>
            ) : (
              <div className="mfiles-filter-rows">
                {filters.map((row) => (
                  (() => {
                    const selectedField = searchFields.find((field) => field.name === row.name);
                    const selectedFieldId = selectedField?.id;
                    const selectedFieldDataType = Number(selectedField?.data_type);
                    const isLookupField = selectedFieldDataType === 9 || selectedFieldDataType === 10;
                    const propertyValues = selectedFieldId ? (propertyValuesByFieldId[selectedFieldId] || []) : [];
                    const loadingPropertyValues = selectedFieldId ? Boolean(loadingPropertyValuesByFieldId[selectedFieldId]) : false;
                    const propertyValuesError = selectedFieldId ? propertyValuesErrorByFieldId[selectedFieldId] : '';

                    return (
                      <div key={row.id} className="mfiles-filter-row">
                        <select
                          value={row.name}
                          onChange={(event) => updateFilterRow(row.id, { name: event.target.value, value: '' })}
                          disabled={searching || importingSelection || loadingSearchFields}
                        >
                          <option value="">Select field</option>
                          {searchFields.map((field) => (
                            <option key={`${field.id}-${field.name}`} value={field.name}>
                              {field.name}
                            </option>
                          ))}
                        </select>

                        <select
                          value={row.modifier}
                          onChange={(event) => updateFilterRow(row.id, { modifier: event.target.value as MFilesSearchModifier })}
                          disabled={searching || importingSelection}
                        >
                          {MODIFIER_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>

                        {isLookupField ? (
                          <select
                            value={row.value}
                            onChange={(event) => updateFilterRow(row.id, { value: event.target.value })}
                            disabled={searching || importingSelection || loadingPropertyValues}
                          >
                            <option value="">
                              {loadingPropertyValues
                                ? 'Loading values...'
                                : propertyValuesError
                                  ? 'Failed to load values'
                                  : propertyValues.length > 0
                                    ? 'Select value'
                                    : 'No values available'}
                            </option>
                            {propertyValues.map((value) => (
                              <option key={`${value.id}-${value.name}`} value={value.name}>
                                {value.name}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            type="text"
                            value={row.value}
                            onChange={(event) => updateFilterRow(row.id, { value: event.target.value })}
                            placeholder="Value"
                            disabled={searching || importingSelection}
                          />
                        )}

                        <button
                          type="button"
                          className="mfiles-filter-remove"
                          onClick={() => removeFilterRow(row.id)}
                          disabled={searching || importingSelection}
                        >
                          Remove
                        </button>
                      </div>
                    );
                  })()
                ))}
              </div>
            )}

            {docClassesError && <p className="mfiles-error-text">{docClassesError}</p>}
            {loadingSearchFields && (
              <p className="mfiles-helper-text">Loading available fields for class "{docClass.trim() || DEFAULT_DOC_CLASS}"...</p>
            )}
            {searchFieldsError && <p className="mfiles-error-text">{searchFieldsError}</p>}
          </div>

          <div className="mfiles-search-actions">
            <button
              type="submit"
              className="btn-primary"
              disabled={searching || importingSelection || loadingDocClasses || !docClass.trim()}
            >
              {searching ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>

        <div className="mfiles-results-section">
          <div className="mfiles-results-header">
            <h3>Results</h3>
            {results.length > 0 && (
              <button type="button" className="btn-secondary" onClick={toggleSelectAll} disabled={importingSelection}>
                {allResultsSelected ? 'Deselect All' : 'Select All'}
              </button>
            )}
          </div>

          {searchError && <p className="mfiles-error-text">{searchError}</p>}

          <div className="mfiles-results-body">
            {searching ? (
              <p className="mfiles-empty-state">Searching M-Files...</p>
            ) : hasSearched && results.length === 0 ? (
              <p className="mfiles-empty-state">No documents matched your search.</p>
            ) : !hasSearched ? (
              <p className="mfiles-empty-state">Run a search to view M-Files documents.</p>
            ) : (
              <table className="mfiles-results-table">
                <thead>
                  <tr>
                    <th>
                      <input
                        type="checkbox"
                        checked={allResultsSelected}
                        onChange={(event) => {
                          if (event.target.checked) {
                            setSelectedDisplayIds(new Set(results.map((result) => result.display_id)));
                          } else {
                            setSelectedDisplayIds(new Set());
                          }
                        }}
                        aria-label="Select all results"
                      />
                    </th>
                    <th>Title</th>
                    <th>Display ID</th>
                    <th>Files</th>
                    <th>Last Modified</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((result) => (
                    <tr key={result.display_id}>
                      <td>
                        <input
                          type="checkbox"
                          checked={isSelected(result.display_id)}
                          onChange={(event) => toggleSelection(result.display_id, event.target.checked)}
                          aria-label={`Select document ${result.display_id}`}
                        />
                      </td>
                      <td>{result.title}</td>
                      <td>{result.display_id}</td>
                      <td title={result.file_names?.join(', ') || ''}>{renderFileSummary(result)}</td>
                      <td>{result.last_modified || '-'}</td>
                      <td>{result.score == null ? '-' : result.score.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="mfiles-picker-footer">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={importingSelection}>
            Cancel
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={handleImport}
            disabled={selectedCount === 0 || importingSelection}
          >
            {importingSelection ? 'Starting Import...' : `Import Selected (${selectedCount})`}
          </button>
        </div>
      </div>
    </div>
  );
};

export default MFilesFilePickerDialog;
