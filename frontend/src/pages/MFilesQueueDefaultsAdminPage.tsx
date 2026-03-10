import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminApi, mfilesApi } from '../services/api';
import Dialog from '../components/Dialog';
import {
  MFilesDocumentClass,
  MFilesPropertyValue,
  MFilesQueueDefaultRule,
  MFilesQueueDefaultRuleType,
  MFilesSearchField,
} from '../types';
import './MFilesQueueDefaultsAdminPage.css';

const ALL_CLASSES_VALUE = '*';

interface EditableQueueDefaultRule extends MFilesQueueDefaultRule {
  local_id: string;
}

function createLocalRuleId(): string {
  return `rule-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function normalizeRule(rule: MFilesQueueDefaultRule): EditableQueueDefaultRule {
  return {
    ...rule,
    local_id: createLocalRuleId(),
    text_value: rule.text_value || '',
    lookup_value_id: rule.lookup_value_id || '',
    lookup_value_name: rule.lookup_value_name || '',
  };
}

function createEmptyRule(): EditableQueueDefaultRule {
  return {
    local_id: createLocalRuleId(),
    id: '',
    document_class: ALL_CLASSES_VALUE,
    property_name: '',
    rule_type: 'current_user',
    enabled: true,
    text_value: '',
    lookup_value_id: '',
    lookup_value_name: '',
  };
}

function normalizeValue(value: string): string {
  return value.trim().toLowerCase();
}

function isQueueRequiredField(field: MFilesSearchField): boolean {
  if (typeof field.queue_required === 'boolean') {
    return field.queue_required;
  }
  return Boolean(field.required && !field.system_auto_fill && !field.automation_managed);
}

function getMFilesDataType(field: MFilesSearchField): number {
  const parsed = Number(field.data_type);
  return Number.isFinite(parsed) ? parsed : -1;
}

function isLookupField(field: MFilesSearchField): boolean {
  const dataType = getMFilesDataType(field);
  return dataType === 9 || dataType === 10;
}

const MFilesQueueDefaultsAdminPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [rules, setRules] = useState<EditableQueueDefaultRule[]>([]);
  const [documentClasses, setDocumentClasses] = useState<MFilesDocumentClass[]>([]);
  const [fieldsByDocClass, setFieldsByDocClass] = useState<Record<string, MFilesSearchField[]>>({});
  const [fieldsLoadingByDocClass, setFieldsLoadingByDocClass] = useState<Record<string, boolean>>({});
  const [fieldsErrorByDocClass, setFieldsErrorByDocClass] = useState<Record<string, string>>({});
  const [propertyValuesByFieldId, setPropertyValuesByFieldId] = useState<Record<number, MFilesPropertyValue[]>>({});
  const [propertyValuesLoadingByFieldId, setPropertyValuesLoadingByFieldId] = useState<Record<number, boolean>>({});
  const [propertyValuesErrorByFieldId, setPropertyValuesErrorByFieldId] = useState<Record<number, string>>({});
  const [validationMessage, setValidationMessage] = useState('');
  const [saveMessage, setSaveMessage] = useState('');
  const [errorDialog, setErrorDialog] = useState<{ show: boolean; message: string }>({ show: false, message: '' });

  useEffect(() => {
    let cancelled = false;

    const loadPage = async () => {
      setLoading(true);
      try {
        const [loadedDefaultsResponse, loadedDocumentClasses] = await Promise.all([
          adminApi.getMFilesQueueDefaults(),
          mfilesApi.getDocumentClasses(),
        ]);
        if (cancelled) {
          return;
        }

        const normalizedClasses = loadedDocumentClasses.filter((item) => item?.name?.trim());
        setDocumentClasses(normalizedClasses);
        setRules((loadedDefaultsResponse.rules || []).map(normalizeRule));
      } catch (error: any) {
        if (!cancelled) {
          const message = error?.message || 'Failed to load M-Files queue defaults.';
          setErrorDialog({ show: true, message });
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadPage();

    return () => {
      cancelled = true;
    };
  }, []);

  const specificDocClasses = useMemo(
    () => Array.from(new Set(
      rules
        .map((rule) => rule.document_class.trim())
        .filter((docClass) => docClass && docClass !== ALL_CLASSES_VALUE)
    )),
    [rules]
  );

  useEffect(() => {
    specificDocClasses.forEach((docClass) => {
      if (fieldsByDocClass[docClass] || fieldsLoadingByDocClass[docClass]) {
        return;
      }

      setFieldsLoadingByDocClass((previous) => ({ ...previous, [docClass]: true }));
      setFieldsErrorByDocClass((previous) => ({ ...previous, [docClass]: '' }));

      mfilesApi.getSearchFields(docClass)
        .then((fields) => {
          setFieldsByDocClass((previous) => ({
            ...previous,
            [docClass]: fields.filter((field) => isQueueRequiredField(field)),
          }));
        })
        .catch((error: any) => {
          setFieldsErrorByDocClass((previous) => ({
            ...previous,
            [docClass]: error?.message || 'Failed to load document class properties.',
          }));
        })
        .finally(() => {
          setFieldsLoadingByDocClass((previous) => ({ ...previous, [docClass]: false }));
        });
    });
  }, [fieldsByDocClass, fieldsLoadingByDocClass, specificDocClasses]);

  const lookupPropertyIds = useMemo(() => {
    const ids = new Set<number>();
    rules.forEach((rule) => {
      if (rule.rule_type !== 'fixed_lookup' || rule.document_class === ALL_CLASSES_VALUE) {
        return;
      }

      const selectedField = (fieldsByDocClass[rule.document_class] || []).find(
        (field) => normalizeValue(field.name) === normalizeValue(rule.property_name)
      );
      if (!selectedField || !isLookupField(selectedField)) {
        return;
      }

      ids.add(selectedField.id);
    });
    return Array.from(ids);
  }, [fieldsByDocClass, rules]);

  useEffect(() => {
    lookupPropertyIds.forEach((propertyId) => {
      if (propertyValuesByFieldId[propertyId] || propertyValuesLoadingByFieldId[propertyId]) {
        return;
      }

      setPropertyValuesLoadingByFieldId((previous) => ({ ...previous, [propertyId]: true }));
      setPropertyValuesErrorByFieldId((previous) => ({ ...previous, [propertyId]: '' }));

      mfilesApi.getPropertyValues(propertyId)
        .then((values) => {
          setPropertyValuesByFieldId((previous) => ({ ...previous, [propertyId]: values }));
        })
        .catch((error: any) => {
          setPropertyValuesByFieldId((previous) => ({ ...previous, [propertyId]: [] }));
          setPropertyValuesErrorByFieldId((previous) => ({
            ...previous,
            [propertyId]: error?.message || 'Failed to load lookup values.',
          }));
        })
        .finally(() => {
          setPropertyValuesLoadingByFieldId((previous) => ({ ...previous, [propertyId]: false }));
        });
    });
  }, [lookupPropertyIds, propertyValuesByFieldId, propertyValuesLoadingByFieldId]);

  const updateRule = (localId: string, updates: Partial<EditableQueueDefaultRule>) => {
    setSaveMessage('');
    setValidationMessage('');
    setRules((previous) => previous.map((rule) => (
      rule.local_id === localId
        ? {
            ...rule,
            ...updates,
          }
        : rule
    )));
  };

  const removeRule = (localId: string) => {
    setSaveMessage('');
    setValidationMessage('');
    setRules((previous) => previous.filter((rule) => rule.local_id !== localId));
  };

  const addRule = () => {
    setSaveMessage('');
    setValidationMessage('');
    setRules((previous) => [...previous, createEmptyRule()]);
  };

  const validateRules = (): string | null => {
    const seen = new Set<string>();

    for (const rule of rules) {
      const docClass = rule.document_class.trim() || ALL_CLASSES_VALUE;
      const propertyName = rule.property_name.trim();
      if (!propertyName) {
        return 'Each rule must include a property name.';
      }

      const duplicateKey = `${normalizeValue(docClass)}::${normalizeValue(propertyName)}`;
      if (seen.has(duplicateKey)) {
        return `Duplicate rule detected for "${propertyName}" in "${docClass === ALL_CLASSES_VALUE ? 'All classes' : docClass}".`;
      }
      seen.add(duplicateKey);

      const selectedField = docClass === ALL_CLASSES_VALUE
        ? undefined
        : (fieldsByDocClass[docClass] || []).find(
            (field) => normalizeValue(field.name) === normalizeValue(propertyName)
          );

      if (docClass !== ALL_CLASSES_VALUE && !selectedField) {
        return `Property "${propertyName}" is not available for document class "${docClass}".`;
      }

      if (rule.rule_type === 'fixed_lookup') {
        if (docClass === ALL_CLASSES_VALUE) {
          return 'Fixed lookup rules require a specific document class.';
        }
        if (!selectedField || !isLookupField(selectedField)) {
          return `Property "${propertyName}" must be a lookup field to use a fixed lookup rule.`;
        }
        if (!rule.lookup_value_id?.trim() || !rule.lookup_value_name?.trim()) {
          return `Choose a lookup value for "${propertyName}".`;
        }
      }

      if (rule.rule_type === 'fixed_text') {
        if (selectedField && isLookupField(selectedField)) {
          return `Property "${propertyName}" cannot use a fixed text default because it is a lookup field.`;
        }
        if (!rule.text_value?.trim()) {
          return `Enter a default text value for "${propertyName}".`;
        }
      }
    }

    return null;
  };

  const handleSave = async () => {
    const validationError = validateRules();
    if (validationError) {
      setValidationMessage(validationError);
      return;
    }

    try {
      setSaving(true);
      setValidationMessage('');
      setSaveMessage('');

      const payload: MFilesQueueDefaultRule[] = rules.map((rule) => ({
        id: rule.id || rule.local_id,
        document_class: rule.document_class.trim() || ALL_CLASSES_VALUE,
        property_name: rule.property_name.trim(),
        rule_type: rule.rule_type,
        enabled: rule.enabled,
        text_value: rule.rule_type === 'fixed_text' ? rule.text_value?.trim() || '' : '',
        lookup_value_id: rule.rule_type === 'fixed_lookup' ? rule.lookup_value_id?.trim() || '' : '',
        lookup_value_name: rule.rule_type === 'fixed_lookup' ? rule.lookup_value_name?.trim() || '' : '',
      }));

      const savedDefaultsResponse = await adminApi.saveMFilesQueueDefaults(payload);
      setRules((savedDefaultsResponse.rules || []).map(normalizeRule));
      setSaveMessage('M-Files queue defaults saved.');
    } catch (error: any) {
      setErrorDialog({
        show: true,
        message: error?.message || 'Failed to save M-Files queue defaults.',
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mfiles-defaults-page">
      <header className="mfiles-defaults-header">
        <div className="mfiles-defaults-header-main">
          <button className="back-btn" onClick={() => navigate('/')}>
            ← Back
          </button>
          <div>
            <p className="mfiles-defaults-eyebrow">Admin</p>
            <h1>M-Files Queue Defaults</h1>
            <p className="mfiles-defaults-subtitle">
              Configure editable prefill rules for M-Files Queue Extraction fields.
            </p>
          </div>
        </div>
        <div className="mfiles-defaults-actions">
          <button className="btn-secondary" onClick={addRule} disabled={loading || saving}>
            + Add Rule
          </button>
          <button className="btn-primary" onClick={handleSave} disabled={loading || saving}>
            {saving ? 'Saving...' : 'Save Defaults'}
          </button>
        </div>
      </header>

      <main className="mfiles-defaults-content">
        <section className="mfiles-defaults-intro">
          <p>
            Specific document class rules override matching <strong>All classes</strong> rules. Fixed lookup rules
            must target a specific document class so the admin page can resolve allowed M-Files values.
          </p>
        </section>

        {validationMessage && <div className="mfiles-defaults-banner error">{validationMessage}</div>}
        {saveMessage && <div className="mfiles-defaults-banner success">{saveMessage}</div>}

        {loading ? (
          <div className="mfiles-defaults-empty">Loading M-Files queue defaults...</div>
        ) : rules.length === 0 ? (
          <div className="mfiles-defaults-empty">
            <p>No custom rules configured.</p>
            <button className="btn-primary" onClick={addRule}>Create Rule</button>
          </div>
        ) : (
          <div className="mfiles-defaults-rule-list">
            {rules.map((rule) => {
              const availableFields = rule.document_class === ALL_CLASSES_VALUE
                ? []
                : (fieldsByDocClass[rule.document_class] || []);
              const selectedField = availableFields.find(
                (field) => normalizeValue(field.name) === normalizeValue(rule.property_name)
              );
              const selectedFieldPropertyValues = selectedField
                ? propertyValuesByFieldId[selectedField.id] || []
                : [];
              const fieldLookupValuesLoading = selectedField
                ? Boolean(propertyValuesLoadingByFieldId[selectedField.id])
                : false;
              const fieldLookupValuesError = selectedField
                ? propertyValuesErrorByFieldId[selectedField.id]
                : '';

              return (
                <article key={rule.local_id} className="mfiles-defaults-rule-card">
                  <div className="mfiles-defaults-rule-header">
                    <h2>Rule</h2>
                    <button
                      type="button"
                      className="mfiles-defaults-remove"
                      onClick={() => removeRule(rule.local_id)}
                      aria-label="Remove rule"
                    >
                      ×
                    </button>
                  </div>

                  <div className="mfiles-defaults-grid">
                    <div className="mfiles-defaults-field">
                      <label htmlFor={`doc-class-${rule.local_id}`}>Document class</label>
                      <select
                        id={`doc-class-${rule.local_id}`}
                        value={rule.document_class}
                        onChange={(event) => {
                          const nextDocumentClass = event.target.value;
                          updateRule(rule.local_id, {
                            document_class: nextDocumentClass,
                            property_name: '',
                            lookup_value_id: '',
                            lookup_value_name: '',
                            text_value: rule.rule_type === 'fixed_text' ? rule.text_value : '',
                          });
                        }}
                      >
                        <option value={ALL_CLASSES_VALUE}>All classes</option>
                        {documentClasses.map((item) => (
                          <option key={item.id} value={item.name}>{item.name}</option>
                        ))}
                      </select>
                    </div>

                    <div className="mfiles-defaults-field">
                      <label htmlFor={`rule-type-${rule.local_id}`}>Rule type</label>
                      <select
                        id={`rule-type-${rule.local_id}`}
                        value={rule.rule_type}
                        onChange={(event) => {
                          const nextRuleType = event.target.value as MFilesQueueDefaultRuleType;
                          updateRule(rule.local_id, {
                            rule_type: nextRuleType,
                            text_value: nextRuleType === 'fixed_text' ? rule.text_value || '' : '',
                            lookup_value_id: nextRuleType === 'fixed_lookup' ? rule.lookup_value_id || '' : '',
                            lookup_value_name: nextRuleType === 'fixed_lookup' ? rule.lookup_value_name || '' : '',
                          });
                        }}
                      >
                        <option value="current_user">Current user</option>
                        <option value="fixed_text">Fixed text</option>
                        <option value="fixed_lookup">Fixed lookup</option>
                      </select>
                    </div>

                    <div className="mfiles-defaults-field mfiles-defaults-toggle">
                      <label htmlFor={`enabled-${rule.local_id}`}>Enabled</label>
                      <input
                        id={`enabled-${rule.local_id}`}
                        type="checkbox"
                        checked={rule.enabled}
                        onChange={(event) => updateRule(rule.local_id, { enabled: event.target.checked })}
                      />
                    </div>

                    <div className="mfiles-defaults-field mfiles-defaults-field-wide">
                      <label htmlFor={`property-${rule.local_id}`}>Property</label>
                      {rule.document_class === ALL_CLASSES_VALUE ? (
                        <input
                          id={`property-${rule.local_id}`}
                          type="text"
                          value={rule.property_name}
                          onChange={(event) => updateRule(rule.local_id, { property_name: event.target.value })}
                          placeholder="Enter the M-Files property name"
                        />
                      ) : (
                        <>
                          <select
                            id={`property-${rule.local_id}`}
                            value={rule.property_name}
                            onChange={(event) => {
                              updateRule(rule.local_id, {
                                property_name: event.target.value,
                                lookup_value_id: '',
                                lookup_value_name: '',
                              });
                            }}
                            disabled={Boolean(fieldsLoadingByDocClass[rule.document_class])}
                          >
                            <option value="">
                              {fieldsLoadingByDocClass[rule.document_class]
                                ? 'Loading properties...'
                                : 'Select property'}
                            </option>
                            {availableFields.map((field) => (
                              <option key={`${rule.local_id}-${field.id}`} value={field.name}>
                                {field.name}
                              </option>
                            ))}
                          </select>
                          {fieldsErrorByDocClass[rule.document_class] && (
                            <p className="mfiles-defaults-helper error-text">
                              {fieldsErrorByDocClass[rule.document_class]}
                            </p>
                          )}
                        </>
                      )}
                    </div>

                    {rule.rule_type === 'current_user' && (
                      <div className="mfiles-defaults-field mfiles-defaults-field-wide">
                        <label>Resolution</label>
                        <div className="mfiles-defaults-static">
                          Use the signed-in user&apos;s display name. Lookup fields will only prefill when an allowed
                          M-Files value exactly matches that name.
                        </div>
                      </div>
                    )}

                    {rule.rule_type === 'fixed_text' && (
                      <div className="mfiles-defaults-field mfiles-defaults-field-wide">
                        <label htmlFor={`fixed-text-${rule.local_id}`}>Default text value</label>
                        <input
                          id={`fixed-text-${rule.local_id}`}
                          type="text"
                          value={rule.text_value || ''}
                          onChange={(event) => updateRule(rule.local_id, { text_value: event.target.value })}
                          placeholder="Enter the default field value"
                        />
                      </div>
                    )}

                    {rule.rule_type === 'fixed_lookup' && (
                      <div className="mfiles-defaults-field mfiles-defaults-field-wide">
                        <label htmlFor={`fixed-lookup-${rule.local_id}`}>Lookup value</label>
                        {rule.document_class === ALL_CLASSES_VALUE ? (
                          <div className="mfiles-defaults-static error-text">
                            Fixed lookup rules require a specific document class.
                          </div>
                        ) : !rule.property_name ? (
                          <div className="mfiles-defaults-static">
                            Select a property first.
                          </div>
                        ) : !selectedField ? (
                          <div className="mfiles-defaults-static error-text">
                            The selected property is not available for this document class.
                          </div>
                        ) : !isLookupField(selectedField) ? (
                          <div className="mfiles-defaults-static error-text">
                            This property is not a lookup field.
                          </div>
                        ) : (
                          <>
                            <select
                              id={`fixed-lookup-${rule.local_id}`}
                              value={rule.lookup_value_id || ''}
                              onChange={(event) => {
                                const selectedValue = selectedFieldPropertyValues.find(
                                  (option) => option.id === event.target.value
                                );
                                updateRule(rule.local_id, {
                                  lookup_value_id: event.target.value,
                                  lookup_value_name: selectedValue?.name || '',
                                });
                              }}
                              disabled={fieldLookupValuesLoading}
                            >
                              <option value="">
                                {fieldLookupValuesLoading ? 'Loading lookup values...' : 'Select lookup value'}
                              </option>
                              {selectedFieldPropertyValues.map((option) => (
                                <option key={`${rule.local_id}-${option.id}`} value={option.id}>
                                  {option.name}
                                </option>
                              ))}
                            </select>
                            {fieldLookupValuesError && (
                              <p className="mfiles-defaults-helper error-text">{fieldLookupValuesError}</p>
                            )}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </main>

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

export default MFilesQueueDefaultsAdminPage;
