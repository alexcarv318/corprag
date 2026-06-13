import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getDocumentSource } from "./api/documents.js";
import { getCatalog, getDisclaimer, getEvidence, getTypeahead, getWorkflow, runWorkflow } from "./api/workflows.js";
import { workflowFromUrl, syncWorkflowToUrl } from "./utils/queryString.js";

const THEME_KEY = "corpner.theme.v2";
const SHARED_THEME_KEY = "theme";
const SIDEBAR_COLLAPSED_KEY = "corpner.sidebar_collapsed";
const GLOBAL_CANCEL_KEY = "corpner.show_cancelled";

const TYPEAHEAD_SUFFIX_MAP = [
  ["subject_id", "subject"],
  ["person_id", "person"],
  ["phase_id", "phase"],
  ["event_id", "event"],
  ["work_id", "work"],
  ["file", "file"],
  ["organization_id", "organization"],
  ["participant_id", "organization"],
  ["class_id", "class"],
  ["from_class_id", "class"],
  ["to_class_id", "class"],
  ["module", "module"]
];

const TYPEAHEAD_LIMITS = {
  subject: 12,
  person: 12,
  organization: 12,
  file: 12,
  event: 10,
  phase: 10,
  work: 10,
  class: 12,
  module: 12
};

const WORKFLOW_ICONS = {
  subject:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M6.70001 18H4.15002C2.72002 18 2 17.28 2 15.85V4.15002C2 2.72002 2.72002 2 4.15001 2H8.45001C9.88001 2 10.6 2.72002 10.6 4.15002V6" stroke="currentColor" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/><path d="M17.3699 8.41998V19.58C17.3699 21.19 16.57 22 14.96 22H9.11993C7.50993 22 6.69995 21.19 6.69995 19.58V8.41998C6.69995 6.80998 7.50993 6 9.11993 6H14.96C16.57 6 17.3699 6.80998 17.3699 8.41998Z" stroke="currentColor" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11H14M10 14H14M12 22V19" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  organization:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M7 10.74V13.94M12 9V15.68M17 10.74V13.94" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 22H15C20 22 22 20 22 15V9C22 4 20 2 15 2H9C4 2 2 4 2 9V15C2 20 4 22 9 22Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  person:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M17 21H7C3 21 2 20 2 16V8C2 4 3 3 7 3H17C21 3 22 4 22 8V16C22 20 21 21 17 21Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 8H19M15 12H19M17 16H19" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M8.49994 11.2899C9.49958 11.2899 10.3099 10.4796 10.3099 9.47992C10.3099 8.48029 9.49958 7.66992 8.49994 7.66992C7.50031 7.66992 6.68994 8.48029 6.68994 9.47992C6.68994 10.4796 7.50031 11.2899 8.49994 11.2899Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 16.33C11.86 14.88 10.71 13.74 9.26 13.61C8.76 13.56 8.25 13.56 7.74 13.61C6.29 13.75 5.14 14.88 5 16.33" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  document:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M22 10V15C22 20 20 22 15 22H9C4 22 2 20 2 15V9C2 4 4 2 9 2H14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M22 10H18C15 10 14 9 14 6V2L22 10Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M7 13H13M7 17H11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  capital:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M18.32 11.9999C20.92 11.9999 22 10.9999 21.04 7.71994C20.39 5.50994 18.49 3.60994 16.28 2.95994C13 1.99994 12 3.07994 12 5.67994V8.55994C12 10.9999 13 11.9999 15 11.9999H18.32Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M19.9999 14.7C19.0699 19.33 14.6299 22.69 9.57993 21.87C5.78993 21.26 2.73993 18.21 2.11993 14.42C1.30993 9.39001 4.64993 4.95001 9.25993 4.01001" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  poa:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M19 9C19 10.45 18.57 11.78 17.83 12.89C16.75 14.49 15.04 15.62 13.05 15.91C12.71 15.97 12.36 16 12 16C11.64 16 11.29 15.97 10.95 15.91C8.96 15.62 7.25 14.49 6.17 12.89C5.43 11.78 5 10.45 5 9C5 5.13 8.13 2 12 2C15.87 2 19 5.13 19 9Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M21.25 18.47L19.6 18.86C19.23 18.95 18.94 19.23 18.86 19.6L18.51 21.07C18.32 21.87 17.3 22.11 16.77 21.48L12 16L7.22996 21.49C6.69996 22.12 5.67996 21.88 5.48996 21.08L5.13996 19.61C5.04996 19.24 4.75996 18.95 4.39996 18.87L2.74996 18.48C1.98996 18.3 1.71996 17.35 2.26996 16.8L6.16996 12.9C7.24996 14.5 8.95996 15.63 10.95 15.92C11.29 15.98 11.64 16.01 12 16.01C12.36 16.01 12.71 15.98 13.05 15.92C15.04 15.63 16.75 14.5 17.83 12.9L21.73 16.8C22.28 17.34 22.01 18.29 21.25 18.47Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  event:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M15.24 2H8.76004C5.00004 2 4.71004 5.38 6.74004 7.22L17.26 16.78C19.29 18.62 19 22 15.24 22H8.76004C5.00004 22 4.71004 18.62 6.74004 16.78L17.26 7.22C19.29 5.38 19 2 15.24 2Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  data:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M13.01 2.92007L18.91 5.54007C20.61 6.29007 20.61 7.53007 18.91 8.28007L13.01 10.9001C12.34 11.2001 11.24 11.2001 10.57 10.9001L4.67 8.28007C2.97 7.53007 2.97 6.29007 4.67 5.54007L10.57 2.92007C11.24 2.62007 12.34 2.62007 13.01 2.92007Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 11C3 11.84 3.63 12.81 4.4 13.15L11.19 16.17C11.71 16.4 12.3 16.4 12.81 16.17L19.6 13.15C20.37 12.81 21 11.84 21 11M3 16C3 16.93 3.55 17.77 4.4 18.15L11.19 21.17C11.71 21.4 12.3 21.4 12.81 21.17L19.6 18.15C20.45 17.77 21 16.93 21 16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
};

const DOCUMENT_TYPE_LABELS = {
  incorporation_certificate: "Incorporation certificate",
  articles_of_association_or_bylaws: "Articles of association",
  continuation_certificate: "Continuation certificate",
  discontinuance_certificate: "Discontinuance certificate",
  dissolution_certificate: "Dissolution certificate",
  registry_extract_certificate: "Registry extract certificate",
  registry_filing: "Registry filing",
  administrative_certificate: "Administrative certificate",
  good_standing_certificate: "Good standing certificate",
  board_resolution: "Board resolution",
  board_meeting_minutes: "Board meeting minutes",
  shareholder_resolution: "Shareholder resolution",
  shareholder_meeting_minutes: "Shareholder meeting minutes",
  director_appointment: "Director appointment",
  director_resignation: "Director resignation",
  director_resolution: "Director resolution",
  share_certificate: "Share certificate",
  share_register: "Share register",
  share_transfer_agreement: "Share transfer agreement",
  share_contribution_agreement: "Share contribution agreement",
  power_of_attorney: "Power of attorney",
  proxy: "Proxy",
  intercompany_or_other_agreement: "Agreement",
  banking_payment_or_credit_record: "Banking or payment record",
  annual_accounts_financial_statements: "Annual accounts",
  tax_document: "Tax document",
  legal_declaration: "Legal declaration",
  legal_opinion: "Legal opinion",
  corporate_data_sheet: "Corporate data sheet",
  registry_extract: "Registry extract",
  correspondence: "Correspondence",
  other: "Other document"
};

const EVIDENCE_DATE_COLUMNS = new Set([
  "date_of_incorporation",
  "date_of_dissolution",
  "date_of_birth",
  "effective_date",
  "as_of",
  "term_start",
  "term_end",
  "from",
  "to",
  "valid_from",
  "valid_to",
  "valid_until",
  "phase_valid_from",
  "phase_valid_to"
]);
const EVIDENCE_NUMBER_COLUMNS = new Set(["amount", "shares", "share_count", "total_shares", "nominal_value", "capital"]);
const EVIDENCE_TEXT_COLUMNS = new Set([
  "registered_office",
  "registration_number",
  "address",
  "street",
  "passport",
  "residence",
  "nationality",
  "identifier"
]);
const ALWAYS_HIDDEN_COLUMNS = new Set([
  "phase_classes",
  "fibo_classes",
  "work_lifecycle_status",
  "expression_lifecycle_status",
  "item_lifecycle_status",
  "legal_name_canonical",
  "edge_count",
  "source_doc",
  "source_chunk",
  "supporting_files",
  "mention_count",
  "_dev"
]);

function storageBool(key, fallback = false) {
  try {
    const value = localStorage.getItem(key);
    return value === null ? fallback : value === "1" || value === "true";
  } catch {
    return fallback;
  }
}

function setStorageBool(key, value) {
  try {
    localStorage.setItem(key, value ? "1" : "0");
  } catch {
    // ignore unavailable storage
  }
}

function loadTheme() {
  try {
    return localStorage.getItem(SHARED_THEME_KEY) || localStorage.getItem(THEME_KEY) || "light";
  } catch {
    return "light";
  }
}

function saveTheme(theme) {
  try {
    localStorage.setItem(SHARED_THEME_KEY, theme);
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    // ignore unavailable storage
  }
}

function typeaheadKind(parameter) {
  const name = parameter.name || "";
  for (const [suffix, kind] of TYPEAHEAD_SUFFIX_MAP) {
    if (name === suffix || name.endsWith("_" + suffix)) return kind;
  }
  return null;
}

function workflowIconKey(workflow) {
  const text = `${workflow.workflow_id || ""} ${workflow.title || ""} ${workflow.category || ""}`.toLowerCase();
  if (text.includes("organization")) return "organization";
  if (text.includes("person")) return "person";
  if (text.includes("document")) return "document";
  if (text.includes("capital") || text.includes("share")) return "capital";
  if (text.includes("attorney") || text.includes("poa")) return "poa";
  if (text.includes("event") || text.includes("timeline")) return "event";
  if (text.includes("data_model") || text.includes("data model")) return "data";
  return "subject";
}

function WorkflowIcon({ workflow }) {
  return (
    <span
      className="workflow-icon"
      dangerouslySetInnerHTML={{ __html: WORKFLOW_ICONS[workflowIconKey(workflow)] || WORKFLOW_ICONS.data }}
    />
  );
}

function defaultParameterValue(parameter, showCancelled) {
  if (parameter.name === "include_cancelled") return showCancelled || Boolean(parameter.default);
  if (parameter.default !== undefined && parameter.default !== null) return parameter.default;
  if (parameter.multiple) return [];
  if (parameter.kind === "boolean") return false;
  return "";
}

function initialParameters(workflow, showCancelled) {
  return Object.fromEntries((workflow.parameters || []).map((parameter) => [parameter.name, defaultParameterValue(parameter, showCancelled)]));
}

function displayOptionValue(value) {
  if (DOCUMENT_TYPE_LABELS[String(value)]) return DOCUMENT_TYPE_LABELS[String(value)];
  const text = String(value);
  const spaced = text.replace(/[_-]+/g, " ").trim();
  if (!spaced) return text;
  return spaced
    .split(/\s+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function isBlank(value) {
  return value === null || value === undefined || value === "";
}

function collectRunParameters(parameters, workflow) {
  const payload = {};
  for (const parameter of workflow.parameters || []) {
    const value = parameters[parameter.name];
    if (Array.isArray(value)) {
      if (value.length) payload[parameter.name] = value;
      continue;
    }
    if (parameter.kind === "boolean") {
      payload[parameter.name] = Boolean(value);
      continue;
    }
    if (!isBlank(value)) payload[parameter.name] = value;
  }
  return payload;
}

function resultTables(result) {
  if (Array.isArray(result?.tables) && result.tables.length) return result.tables;
  if (!result) return [];
  return [
    {
      table_id: result.workflow_id || "results",
      title: "Results",
      rows: result.rows || [],
      columns: result.columns || [],
      row_count: result.row_count || 0
    }
  ];
}

function totalRows(result) {
  return resultTables(result).reduce((sum, table) => sum + (Number(table.row_count) || (table.rows || []).length), 0);
}

function evidenceColumnKind(columnName) {
  const name = String(columnName || "").toLowerCase();
  if (EVIDENCE_DATE_COLUMNS.has(name)) return "date";
  if (EVIDENCE_NUMBER_COLUMNS.has(name)) return "number";
  if (EVIDENCE_TEXT_COLUMNS.has(name)) return "text";
  if (name.startsWith("date_") || name.includes("valid_") || name.endsWith("_date")) return "date";
  return null;
}

function visibleColumns(columns) {
  return (columns || []).filter((column) => !ALWAYS_HIDDEN_COLUMNS.has(column) && !String(column).endsWith("_id"));
}

function formatInlineStructuredValue(value) {
  if (isBlank(value)) return "";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map(formatInlineStructuredValue).filter(Boolean).join(", ");
  if (typeof value === "object") {
    return Object.entries(value)
      .filter(([, item]) => !isBlank(item))
      .map(([key, item]) => `${displayFieldName(key)}: ${formatInlineStructuredValue(item)}`)
      .join(" · ");
  }
  return String(value);
}

function displayFieldName(key) {
  const aliases = { address_text: "Address", country_iso2: "Country code", kind: "Type", class: "Type" };
  if (aliases[key]) return aliases[key];
  const spaced = String(key).replace(/[_]+/g, " ").trim();
  return spaced ? spaced.charAt(0).toUpperCase() + spaced.slice(1) : String(key);
}

function decodeText(value) {
  const text = String(value || "")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
  return text;
}

function highlightParts(text, terms) {
  const cleanedText = decodeText(text);
  const cleanedTerms = (Array.isArray(terms) ? terms : [])
    .map((term) => decodeText(term).trim())
    .filter((term) => term.length >= 3)
    .sort((left, right) => right.length - left.length);
  if (!cleanedTerms.length) return [cleanedText];

  const lowered = cleanedText.toLowerCase();
  const ranges = [];
  let cursor = 0;
  while (cursor < cleanedText.length) {
    let bestIndex = -1;
    let bestTerm = "";
    for (const term of cleanedTerms) {
      const index = lowered.indexOf(term.toLowerCase(), cursor);
      if (index !== -1 && (bestIndex === -1 || index < bestIndex)) {
        bestIndex = index;
        bestTerm = term;
      }
    }
    if (bestIndex === -1) break;
    ranges.push([bestIndex, bestIndex + bestTerm.length]);
    cursor = bestIndex + Math.max(bestTerm.length, 1);
  }
  if (!ranges.length) return [cleanedText];

  const parts = [];
  let offset = 0;
  for (const [start, end] of ranges) {
    if (start > offset) parts.push(cleanedText.slice(offset, start));
    parts.push({ mark: cleanedText.slice(start, end) });
    offset = end;
  }
  if (offset < cleanedText.length) parts.push(cleanedText.slice(offset));
  return parts;
}

function HighlightedText({ text, terms }) {
  return (
    <>
      {highlightParts(text, terms).map((part, index) => (
        typeof part === "string" ? part : <mark className="evidence-mark" key={index}>{part.mark}</mark>
      ))}
    </>
  );
}

function StructuredValue({ value }) {
  if (isBlank(value)) return <span className="structured-meta">—</span>;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return decodeText(value);
  if (Array.isArray(value)) {
    if (!value.length) return <span className="structured-meta">—</span>;
    if (value.every((item) => typeof item === "string" || typeof item === "number")) {
      return value.map(decodeText).join(", ");
    }
    return (
      <div className="structured-list">
        {value.map((item, index) => (
          <div className="structured-item" key={index}>
            <StructuredValue value={item} />
          </div>
        ))}
      </div>
    );
  }
  if (typeof value === "object") {
    const entries = Object.entries(value).filter(([, item]) => !isBlank(item));
    const mainKey = ["label", "name", "title", "address_text", "address", "identifier", "value"].find((key) => !isBlank(value[key]));
    const detailEntries = entries.filter(([key]) => key !== mainKey);
    return (
      <div className="structured-item">
        {mainKey ? <div className="structured-main"><StructuredValue value={value[mainKey]} /></div> : null}
        {detailEntries.length ? (
          <div className="structured-meta">
            {detailEntries.map(([key, item]) => `${displayFieldName(key)}: ${formatInlineStructuredValue(item)}`).join(" · ")}
          </div>
        ) : null}
        {!mainKey && !detailEntries.length ? <div className="structured-main">{JSON.stringify(value)}</div> : null}
      </div>
    );
  }
  return String(value);
}

function isSourcesColumn(column) {
  return column === "sources" || column === "source" || column === "mentions";
}

function sourceFiles(row) {
  const files = new Set();
  for (const value of Object.values(row || {})) {
    if (!Array.isArray(value)) continue;
    for (const entry of value) {
      if (entry && typeof entry === "object" && entry.file) files.add(entry.file);
    }
  }
  return Array.from(files);
}

function evidenceEntityId(row) {
  for (const key of ["organization_id", "person_id", "phase_id", "subject_id", "address_id", "event_id"]) {
    if (typeof row?.[key] === "string" && row[key]) return row[key];
  }
  return null;
}

function rowContext(row, columns) {
  const keys = ["subject", "phase", "phase_label", "person", "label", "metric", "kind", "role", "as_of", "effective_date", "valid_from", "title", "event"];
  const parts = [];
  for (const key of keys) {
    if (!columns.includes(key)) continue;
    const value = row[key];
    if (isBlank(value) || Array.isArray(value) || typeof value === "object") continue;
    parts.push(String(value));
  }
  return parts.slice(0, 4).join(" — ");
}

function summarizeResult(result) {
  const tables = resultTables(result);
  const rows = totalRows(result);
  if (tables.length === 1) return `${rows} result${rows === 1 ? "" : "s"}`;
  return `${tables.length} tables · ${rows} total rows`;
}

function Sidebar({ catalog, selected, onSelect, collapsed, onToggle, status }) {
  const byCategory = useMemo(() => {
    const grouped = {};
    for (const workflow of catalog.workflows || []) {
      if (workflow.dev_only) continue;
      (grouped[workflow.category] = grouped[workflow.category] || []).push(workflow);
    }
    return grouped;
  }, [catalog.workflows]);

  return (
    <aside>
      <div className="sidebar-head">
        <div className="sidebar-head-row">
          <h1 className="sidebar-title">
            Workflows <span className="sub" id="catalog-stats">({(catalog.workflows || []).filter((workflow) => !workflow.dev_only).length})</span>
          </h1>
          <button
            id="sidebar-toggle"
            className="sidebar-toggle"
            type="button"
            title={collapsed ? "Show left panel" : "Hide left panel"}
            aria-label={collapsed ? "Show left panel" : "Hide left panel"}
            aria-expanded={!collapsed}
            onClick={onToggle}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
              <path d="M9 22H15C20 22 22 20 22 15V9C22 4 20 2 15 2H9C4 2 2 4 2 9V15C2 20 4 22 9 22Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M9 2V22" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
        <div className="sidebar-meta">
          <span className={`status ${status.tone || ""}`} id="server-status">{status.text}</span>
        </div>
      </div>
      <div id="sidebar" className="sidebar-body">
        {(catalog.categories || []).map((category) => {
          const workflows = byCategory[category] || [];
          if (!workflows.length) return null;
          return (
            <div className="group" key={category}>
              {workflows.map((workflow) => (
                <div
                  className={`item${selected === workflow.workflow_id ? " active" : ""}`}
                  key={workflow.workflow_id}
                  title={workflow.title}
                  onClick={() => onSelect(workflow.workflow_id)}
                >
                  <WorkflowIcon workflow={workflow} />
                  <span className="title">{workflow.title}</span>
                  <span className="id">{workflow.workflow_id}</span>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </aside>
  );
}

function TopActions({ theme, onThemeToggle, menuOpen, setMenuOpen, showCancelled, setShowCancelled, onOpenDisclaimer }) {
  return (
    <div className="top-actions" aria-label="Page actions">
      <a className="top-agent-link" href="/agent/" target="_self" rel="noopener noreferrer" title="Open the Corprag agent">
        Agent
      </a>
      <button id="theme-toggle" className="top-icon-btn" type="button" title={`Theme: ${theme}`} aria-label={`Theme: ${theme}`} onClick={onThemeToggle}>
        <svg className="theme-icon-sun" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" /></svg>
        <svg className="theme-icon-moon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401" /></svg>
        <span className="sr-only">Toggle theme</span>
      </button>
      <div className="avatar-menu-wrap">
        <button id="avatar-menu-btn" className="avatar-btn" type="button" aria-label="Open account menu" aria-controls="avatar-menu" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>
          A
        </button>
        <div id="avatar-menu" className="avatar-menu" hidden={!menuOpen}>
          <div className="menu-section">
            <label className="menu-switch" title="Also show items that are no longer in force across every workflow.">
              <span>Show inactive</span>
              <input id="global-show-cancelled" type="checkbox" checked={showCancelled} onChange={(event) => setShowCancelled(event.target.checked)} />
            </label>
            <label className="menu-switch" title="Show authority labels for row sources. Sorting still uses authority.">
              <span>Show source authority</span>
              <input id="global-show-source-authority" type="checkbox" defaultChecked />
            </label>
          </div>
          <div className="menu-section">
            <button id="disclaimer-open-btn" className="menu-item" type="button" onClick={onOpenDisclaimer}>
              About this console
            </button>
            <button id="logout-btn" className="menu-item" type="button" title="Sign out of workflows">
              Logout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function TypeaheadInput({ parameter, value, label, subjectId, onChange }) {
  const kind = typeaheadKind(parameter);
  const [display, setDisplay] = useState(label || value || "");
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const cacheRef = useRef(new Map());
  const requestRef = useRef(0);

  useEffect(() => {
    setDisplay(label || value || "");
  }, [label, value]);

  const fetchItems = useCallback(
    async (query) => {
      if (!kind) return;
      const cacheKey = `${kind}:${subjectId || ""}:${query}`;
      if (cacheRef.current.has(cacheKey)) {
        setItems(cacheRef.current.get(cacheKey));
        setOpen(true);
        return;
      }
      const token = ++requestRef.current;
      setBusy(true);
      try {
        const payload = await getTypeahead({ kind, q: query, limit: TYPEAHEAD_LIMITS[kind] || 10, subjectId });
        if (token !== requestRef.current) return;
        const nextItems = dedupeTypeaheadItems(payload.items || []);
        cacheRef.current.set(cacheKey, nextItems);
        setItems(nextItems);
        setOpen(true);
      } catch (error) {
        if (token !== requestRef.current) return;
        setItems([{ id: "__error__", label: `× ${error.message}` }]);
        setOpen(true);
      } finally {
        if (token === requestRef.current) setBusy(false);
      }
    },
    [kind, subjectId]
  );

  if (!kind) return null;

  return (
    <div className="typeahead" data-typeahead-kind={kind} data-typeahead-limit={TYPEAHEAD_LIMITS[kind] || 10}>
      <input
        className="display"
        type="text"
        autoComplete="off"
        data-typeahead-kind={kind}
        placeholder={parameter.placeholder || `Search ${kind}…`}
        value={display}
        onFocus={() => fetchItems(display.trim())}
        onChange={(event) => {
          const next = event.target.value;
          setDisplay(next);
          onChange("");
          window.clearTimeout(TypeaheadInput.timer);
          TypeaheadInput.timer = window.setTimeout(() => fetchItems(next.trim()), 150);
        }}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
      />
      <div className="ta-spinner" hidden={!busy} />
      <input type="hidden" name={parameter.name} value={value || ""} readOnly />
      <ul className="dropdown" hidden={!open}>
        {items.length ? (
          items.map((item) => (
            <li
              key={item.id}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => {
                if (item.id === "__error__") return;
                onChange(item.id, item.label || item.id);
                setDisplay(item.label || item.id);
                setOpen(false);
              }}
            >
              <span className="ta-label">{item.label || item.id}</span>
              {item.hint ? <div className="ta-hint">{item.hint}</div> : null}
            </li>
          ))
        ) : (
          <li><span className="ta-label">No matches</span></li>
        )}
      </ul>
      <div className="selected-id">{value}</div>
    </div>
  );
}

function dedupeTypeaheadItems(items) {
  const seen = new Set();
  const result = [];
  for (const item of items) {
    const key = `${item.id || ""}::${String(item.label || "").trim().toLowerCase()}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(item);
  }
  return result;
}

function MultiSelector({ parameter, value, onChange }) {
  const [open, setOpen] = useState(false);
  const selected = Array.isArray(value) ? value : value ? [String(value)] : [];
  const options = (parameter.options || []).map(String).filter((option) => option !== "" && option !== "all");
  const sentinel = (parameter.options || []).includes("all") ? "All" : "Any";
  const summary = selected.length === 0 ? `No boxes selected = ${sentinel}` : selected.length === 1 ? displayOptionValue(selected[0]) : `${selected.length} selected`;

  return (
    <div className="multi-select" data-enum-multi="1" data-name={parameter.name}>
      <button className="multi-trigger" type="button" aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen(!open)}>
        {summary}
      </button>
      <div className="multi-menu" hidden={!open}>
        <div className="multi-empty">No boxes selected = {sentinel}</div>
        {options.map((option) => (
          <label className="multi-option" key={option}>
            <input
              type="checkbox"
              value={option}
              checked={selected.includes(option)}
              onChange={(event) => {
                const next = event.target.checked ? [...selected, option] : selected.filter((item) => item !== option);
                onChange(parameter.multiple || parameter.name === "event_type" ? next : next[0] || "");
              }}
            />
            <span>{displayOptionValue(option)}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

function WorkflowParameters({ workflow, parameters, labels, showCancelled, setParameter, onRun, running, status }) {
  if (!workflow) return null;
  const dateParams = new Map((workflow.parameters || []).filter((parameter) => parameter.kind === "date").map((parameter) => [parameter.name, parameter]));
  const handled = new Set();
  const hasDateRange = dateParams.has("since") && dateParams.has("until");

  function renderField(parameter) {
    const kind = typeaheadKind(parameter);
    if (kind) {
      return (
        <TypeaheadInput
          parameter={parameter}
          subjectId={parameter.name === "subject_id" ? null : parameters.subject_id}
          value={parameters[parameter.name] || ""}
          label={labels[parameter.name]}
          onChange={(nextValue, nextLabel) => setParameter(parameter.name, nextValue, nextLabel)}
        />
      );
    }
    if ((parameter.kind === "select" || parameter.options?.length) && parameter.options) {
      return <MultiSelector parameter={parameter} value={parameters[parameter.name]} onChange={(nextValue) => setParameter(parameter.name, nextValue)} />;
    }
    if (parameter.kind === "boolean") {
      return (
        <label className="bool">
          <input
            type="checkbox"
            name={parameter.name}
            checked={Boolean(parameters[parameter.name])}
            data-include-cancelled={parameter.name === "include_cancelled" ? "1" : undefined}
            onChange={(event) => setParameter(parameter.name, event.target.checked)}
          />
          <span>{parameter.label}</span>
        </label>
      );
    }
    return (
      <input
        type={parameter.kind === "number" ? "number" : parameter.kind === "date" ? "date" : "text"}
        name={parameter.name}
        placeholder={parameter.placeholder || ""}
        value={parameters[parameter.name] ?? ""}
        onChange={(event) => setParameter(parameter.name, event.target.value)}
      />
    );
  }

  function parameterRows() {
    const rows = [];
    if (hasDateRange) {
      handled.add("since");
      handled.add("until");
      const limit = (workflow.parameters || []).find((parameter) => parameter.name === "limit");
      if (limit) handled.add("limit");
      rows.push(
        <div className="date-range-row" key="date-range">
          <div className="date-range-main">
            <div className="date-range-label">Date range</div>
            <div className="date-range-controls">
              <label className="date-inline-field">
                <span>From</span>
                <span className="date-input-wrap">{renderField(dateParams.get("since"))}</span>
              </label>
              <label className="date-inline-field">
                <span>To</span>
                <span className="date-input-wrap">{renderField(dateParams.get("until"))}</span>
              </label>
            </div>
          </div>
          {limit ? (
            <label className="inline-limit-field">
              <span>{limit.label}</span>
              {renderField(limit)}
            </label>
          ) : null}
        </div>
      );
    }

    for (const parameter of workflow.parameters || []) {
      if (handled.has(parameter.name) || parameter.name === "event_domain") continue;
      if (parameter.kind === "boolean") {
        rows.push(
          <div className="field" style={{ gridColumn: "1 / -1" }} key={parameter.name}>
            {renderField(parameter)}
            {parameter.description ? <div className="desc">{parameter.description}</div> : null}
          </div>
        );
        continue;
      }
      if (parameter.name === "event_type") {
        rows.push(
          <div className="field" style={{ gridColumn: "1 / -1" }} key={parameter.name}>
            {renderField(parameter)}
          </div>
        );
        continue;
      }
      rows.push(
        <div className="param-label" key={`${parameter.name}-label`}>
          <div>
            {parameter.label}
            {parameter.required ? <span className="req-mark">*</span> : null}
          </div>
        </div>
      );
      rows.push(
        <div className="field" key={parameter.name}>
          {renderField(parameter)}
          {parameter.description ? <div className="desc">{parameter.description}</div> : null}
        </div>
      );
    }
    return rows;
  }

  return (
    <div className="panel">
      <header><h2>Parameters</h2></header>
      <div className="body">
        <div className="params">{parameterRows()}</div>
        <div className="actions">
          <button type="button" disabled={running} onClick={onRun}>Run</button>
          <span className={`run-status ${status.tone || ""}`}>{running ? "Running…" : status.text}</span>
          {showCancelled ? null : null}
        </div>
      </div>
    </div>
  );
}

function WorkflowHeader({ workflow }) {
  if (!workflow) {
    return (
      <div className="empty">
        <p>Select a workflow from the left.</p>
        <p className="hint">Every question is set up to answer "what is true today" by default. Set a date or turn on <em>Show inactive</em> to look further back.</p>
      </div>
    );
  }
  return (
    <div className="panel">
      <header>
        <WorkflowIcon workflow={workflow} />
        <h2>{workflow.title}</h2>
      </header>
      <div className="body">
        <p>{workflow.description}</p>
        {workflow.use_cases?.length ? (
          <div className="uses">
            <div className="uses-label">Use this when you want to ask:</div>
            <ul className="uses-list">
              {workflow.use_cases.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ResultCell({ column, value, row, columns, onSources, onEvidence }) {
  if (isSourcesColumn(column) && Array.isArray(value)) {
    if (!value.length) return <td className="sources-empty">—</td>;
    const sources = value.filter((entry) => entry && entry.file);
    if (!sources.length) return <td className="sources-empty">—</td>;
    return (
      <td className="sources-cell-td">
        <button className="sources-cell" type="button" title={sources.map((source) => source.file).join("\n")} onClick={(event) => { event.stopPropagation(); onSources(sources, rowContext(row, columns)); }}>
          {sources.length === 1 ? <span className="sources-single">{sources[0].file}</span> : <span className="sources-count">{sources.length} sources</span>}
        </button>
      </td>
    );
  }
  if (isBlank(value)) return <td className="json">—</td>;
  if (column === "doc_type" || column === "supporting_doc_type" || column === "source_doc_type") return <td>{displayOptionValue(value)}</td>;
  if (evidenceColumnKind(column) && sourceFiles(row).length) {
    const values = Array.isArray(value) ? value : [value];
    return (
      <td className="evidence-cell">
        <div className="evidence-chips">
          {values.map((entry) => (
            <button
              className="evidence-value"
              key={String(entry)}
              type="button"
              title="Check the source evidence for this value"
              onClick={(event) => {
                event.stopPropagation();
                onEvidence({
                  value: String(entry),
                  column,
                  files: sourceFiles(row),
                  entity_id: evidenceEntityId(row),
                  context: rowContext(row, columns),
                  limit: 30
                });
              }}
            >
              {String(entry)}
              <span className="evidence-icon" dangerouslySetInnerHTML={{ __html: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="m21 21-4.3-4.3"></path></svg>' }} />
            </button>
          ))}
        </div>
      </td>
    );
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return <td>{decodeText(value)}</td>;
  if (Array.isArray(value) && value.every((item) => typeof item === "string" || typeof item === "number")) return <td>{value.map(decodeText).join(", ")}</td>;
  return <td className="structured-cell"><StructuredValue value={value} /></td>;
}

function Results({ result, onSources, onEvidence }) {
  if (!result) return null;
  if (totalRows(result) === 0) {
    return (
      <div id="result-panel">
        <div className="panel"><div className="body"><p className="muted">No matches found.</p></div></div>
      </div>
    );
  }
  return (
    <div id="result-panel">
      {resultTables(result).map((table, index) => {
        const columns = visibleColumns(table.columns || []);
        const rows = table.rows || [];
        const rowCount = typeof table.row_count === "number" ? table.row_count : rows.length;
        return (
          <div className="panel" key={table.table_id || index}>
            <header>
              <h3>{table.title || `Table ${index + 1}`}</h3>
              <span className="pill">{rowCount} row{rowCount === 1 ? "" : "s"}</span>
            </header>
            <div className="body">
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      {columns.map((column) => (
                        <th key={column}><div className="th-inner"><button className="th-label" type="button">{column}</button></div></th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, rowIndex) => (
                      <tr key={rowIndex}>
                        {columns.map((column) => (
                          <ResultCell column={column} columns={columns} key={column} row={row} value={row[column]} onSources={onSources} onEvidence={onEvidence} />
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function DisclaimerOverlay({ open, count, onClose }) {
  return (
    <div id="disclaimer-overlay" className="disclaimer-overlay" hidden={!open} role="dialog" aria-modal="true" aria-labelledby="disclaimer-title">
      <div className="disclaimer-card">
        <header>
          <h2 id="disclaimer-title">About this console</h2>
          <p className="lede">Please read before using the corporate knowledge graph workflows.</p>
        </header>
        <div className="disclaimer-body">
          <section>
            <h3>Scope</h3>
            <p>These workflows are built <strong>for corporate users</strong> to explore extracted facts directly.</p>
            <p>At present the knowledge graph contains <strong><span id="disclaimer-document-count" className="disclaimer-count">{count ?? "…"}</span> document works</strong> from that corpus.</p>
          </section>
          <section>
            <h3>Limitations</h3>
            <p>The graph is an analytical extraction surface, not a substitute for legal review of the underlying documents.</p>
          </section>
        </div>
        <footer className="disclaimer-foot">
          <label className="disclaimer-toggle">
            <input id="disclaimer-hide-forever" type="checkbox" />
            <span>Do not show automatically on this browser</span>
          </label>
          <span id="disclaimer-status" className="disclaimer-status" aria-live="polite" />
          <button id="disclaimer-ack-btn" type="button" onClick={onClose}>I have read and understand these limitations</button>
        </footer>
      </div>
    </div>
  );
}

function SourcesDrawer({ drawer, onClose, onBack, onOpenDocument }) {
  const open = Boolean(drawer);
  const title = drawer?.title || "Sources";
  return (
    <aside id="sources-drawer" className={`sources-drawer${open ? " open" : ""}`} hidden={!open} aria-hidden={!open}>
      <div className="drawer-head">
        <div className="drawer-title-wrap">
          <h2 id="sources-drawer-title">{title}</h2>
          <div id="sources-drawer-sub" className="drawer-sub">{drawer?.subtitle || ""}</div>
        </div>
        <button id="sources-drawer-back" type="button" className="drawer-back" hidden={!drawer?.document} aria-label="Back to sources" onClick={onBack}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
        </button>
        <button id="sources-drawer-close" type="button" className="drawer-close" title="Close (Esc)" aria-label="Close sources" onClick={onClose}>
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>
        </button>
      </div>
      <div id="sources-drawer-body" className="drawer-body">
        {drawer?.loading ? <div className="drawer-status">Loading…</div> : null}
        {drawer?.error ? <div className="drawer-status err">{drawer.error}</div> : null}
        {drawer?.document ? (
          <DocumentView
            payload={drawer.document}
            highlightChunkIds={drawer.highlightChunkIds || []}
            highlightTerms={drawer.highlightTerms || []}
          />
        ) : null}
        {!drawer?.document && drawer?.sources ? (
          <div className="source-list">
            <div className="source-list-hint">Open a source to inspect its extracted chunks.</div>
            {drawer.sources.map((source) => (
              <button className="source-list-item" key={`${source.file}-${source.chunk_id || ""}`} type="button" onClick={() => onOpenDocument(source)}>
                <span className="source-icon" dangerouslySetInnerHTML={{ __html: WORKFLOW_ICONS.document }} />
                <span className="source-copy">
                  <span className="source-meta"><span className="source-meta-item">{source.chunk_id || source.link_type || ""}</span></span>
                  <span className="source-name">{source.title || source.file}</span>
                  <span className="source-file">{source.file}</span>
                </span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </aside>
  );
}

function DocumentView({ payload, highlightChunkIds, highlightTerms }) {
  const chunks = payload.chunks || [];
  const bodyRef = useRef(null);
  const rows = chunks.map((chunk, index) => {
    const previous = index > 0 ? chunks[index - 1]?.page_first : null;
    return {
      chunk,
      pageBreak: chunk.page_first !== null && chunk.page_first !== undefined && chunk.page_first !== previous,
      highlighted: highlightChunkIds.includes(chunk.chunk_id)
        || highlightParts(chunk.text || "", highlightTerms).some((part) => typeof part !== "string")
    };
  });
  useEffect(() => {
    const target = bodyRef.current?.querySelector(".chunk.highlighted");
    if (target) target.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [payload, highlightChunkIds, highlightTerms]);

  return (
    <div className="doc-view" ref={bodyRef}>
      <div className="doc-head">
        <h3>{payload.title || payload.file || "Document"}</h3>
        <div className="doc-meta">
          {payload.doc_type ? <span className="source-type-badge">{displayOptionValue(payload.doc_type)}</span> : null}
          {payload.file ? <span className="doc-stat">{payload.file}</span> : null}
        </div>
      </div>
      {payload.summary ? <div className="doc-summary">{payload.summary}</div> : null}
      {rows.map(({ chunk, pageBreak, highlighted }) => {
        return (
          <div key={chunk.chunk_id || chunk.sequence_index}>
            {pageBreak ? <div className="doc-page-break">Page {chunk.page_first}</div> : null}
            <div className={`chunk chunk-${chunk.structural_role || "paragraph"}${highlighted ? " highlighted" : ""}`}>
              <span className="chunk-text">
                <HighlightedText text={chunk.text || "(no transcribed text; structural marker only)"} terms={highlightTerms} />
              </span>
              {chunk.structural_path ? <span className="chunk-anchor" title={chunk.structural_path}>{chunk.structural_path}</span> : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function App() {
  const [theme, setTheme] = useState(loadTheme);
  const [menuOpen, setMenuOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => storageBool(SIDEBAR_COLLAPSED_KEY));
  const [showCancelled, setShowCancelledState] = useState(() => storageBool(GLOBAL_CANCEL_KEY));
  const [catalog, setCatalog] = useState({ categories: [], workflows: [] });
  const [selectedId, setSelectedId] = useState(workflowFromUrl());
  const [workflow, setWorkflow] = useState(null);
  const [parameters, setParameters] = useState({});
  const [parameterLabels, setParameterLabels] = useState({});
  const [result, setResult] = useState(null);
  const [serverStatus, setServerStatus] = useState({ text: "Loading catalog…" });
  const [runStatus, setRunStatus] = useState({ text: "" });
  const [running, setRunning] = useState(false);
  const [documentCount, setDocumentCount] = useState(null);
  const [disclaimerOpen, setDisclaimerOpen] = useState(false);
  const [drawer, setDrawer] = useState(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    saveTheme(theme);
  }, [theme]);

  useEffect(() => {
    document.body.classList.toggle("sidebar-collapsed", collapsed);
    setStorageBool(SIDEBAR_COLLAPSED_KEY, collapsed);
  }, [collapsed]);

  useEffect(() => {
    setStorageBool(GLOBAL_CANCEL_KEY, showCancelled);
  }, [showCancelled]);

  useEffect(() => {
    let alive = true;
    getCatalog()
      .then((payload) => {
        if (!alive) return;
        setCatalog(payload);
        setServerStatus({ text: "Connected", tone: "ok" });
        setSelectedId((current) => current || payload.workflows?.find((item) => !item.dev_only)?.workflow_id || null);
      })
      .catch((error) => {
        if (alive) setServerStatus({ text: `× ${error.message}`, tone: "err" });
      });
    getDisclaimer()
      .then((payload) => alive && setDocumentCount(payload.document_count))
      .catch(() => alive && setDocumentCount(null));
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    let alive = true;
    syncWorkflowToUrl(selectedId);
    getWorkflow(selectedId)
      .then((payload) => {
        if (!alive) return;
        setWorkflow(payload);
        setParameters(initialParameters(payload, showCancelled));
        setParameterLabels({});
        setResult(null);
        setRunStatus({ text: "" });
      })
      .catch((error) => alive && setRunStatus({ text: `× ${error.message}`, tone: "err" }));
    return () => {
      alive = false;
    };
  }, [selectedId, showCancelled]);

  const setShowCancelled = (value) => {
    setShowCancelledState(value);
    setParameters((current) => (current.include_cancelled === undefined ? current : { ...current, include_cancelled: value }));
  };

  function setParameter(name, value, label) {
    setParameters((current) => ({ ...current, [name]: value }));
    if (label !== undefined) {
      setParameterLabels((current) => ({ ...current, [name]: label }));
    }
  }

  async function executeWorkflow() {
    if (!workflow) return;
    setRunning(true);
    setRunStatus({ text: "Running…" });
    try {
      const payload = await runWorkflow(workflow.workflow_id, collectRunParameters(parameters, workflow));
      setResult(payload);
      setRunStatus({ text: summarizeResult(payload), tone: "ok" });
    } catch (error) {
      setRunStatus({ text: `× ${error.message}`, tone: "err" });
    } finally {
      setRunning(false);
    }
  }

  async function openDocument(source) {
    setDrawer((current) => ({ ...current, loading: true, error: "" }));
    try {
      const payload = await getDocumentSource(source.file);
      setDrawer((current) => ({
        ...current,
        loading: false,
        document: payload,
        highlightChunkIds: source.chunk_id ? [source.chunk_id] : [],
        highlightTerms: current?.highlightTerms || []
      }));
    } catch (error) {
      setDrawer((current) => ({ ...current, loading: false, error: error.message }));
    }
  }

  async function openEvidence(payload) {
    setDrawer({ title: "Evidence", subtitle: payload.context || "", loading: true, sources: [] });
    try {
      const evidence = await getEvidence(payload);
      const sources = (evidence.chunks || []).map((chunk) => ({
        file: chunk.file || payload.files?.[0],
        chunk_id: chunk.chunk_id,
        title: chunk.title
      })).filter((source) => source.file);
      setDrawer({
        title: "Evidence",
        subtitle: payload.context || "",
        sources,
        loading: false,
        highlightTerms: evidence.highlight_terms || [],
        highlightChunkIds: sources.map((source) => source.chunk_id).filter(Boolean)
      });
    } catch (error) {
      setDrawer({ title: "Evidence", subtitle: payload.context || "", loading: false, error: error.message });
    }
  }

  return (
    <>
      <DisclaimerOverlay open={disclaimerOpen} count={documentCount} onClose={() => setDisclaimerOpen(false)} />
      <Sidebar
        catalog={catalog}
        collapsed={collapsed}
        selected={selectedId}
        status={serverStatus}
        onSelect={setSelectedId}
        onToggle={() => setCollapsed(!collapsed)}
      />
      <main>
        <TopActions
          menuOpen={menuOpen}
          setMenuOpen={setMenuOpen}
          showCancelled={showCancelled}
          theme={theme}
          setShowCancelled={setShowCancelled}
          onOpenDisclaimer={() => {
            setMenuOpen(false);
            setDisclaimerOpen(true);
          }}
          onThemeToggle={() => setTheme(theme === "dark" ? "light" : "dark")}
        />
        <div id="content">
          <WorkflowHeader workflow={workflow} />
          {workflow ? (
            <WorkflowParameters
              labels={parameterLabels}
              parameters={parameters}
              running={running}
              showCancelled={showCancelled}
              status={runStatus}
              workflow={workflow}
              setParameter={setParameter}
              onRun={executeWorkflow}
            />
          ) : null}
          <Results
            result={result}
            onEvidence={openEvidence}
            onSources={(sources, context) => setDrawer({ title: "Sources", subtitle: context, sources })}
          />
        </div>
      </main>
      <SourcesDrawer
        drawer={drawer}
        onBack={() => setDrawer((current) => current ? { ...current, document: null, error: "" } : null)}
        onClose={() => setDrawer(null)}
        onOpenDocument={openDocument}
      />
    </>
  );
}
