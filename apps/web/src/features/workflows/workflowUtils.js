import { ALWAYS_HIDDEN_COLUMNS, DOCUMENT_TYPE_LABELS, EVIDENCE_DATE_COLUMNS, EVIDENCE_NUMBER_COLUMNS, EVIDENCE_TEXT_COLUMNS, TYPEAHEAD_SUFFIX_MAP } from "./workflowConstants.js";

export function typeaheadKind(parameter) {
  const name = parameter.name || "";
  for (const [suffix, kind] of TYPEAHEAD_SUFFIX_MAP) {
    if (name === suffix || name.endsWith("_" + suffix)) return kind;
  }
  return null;
}

export function workflowIconKey(workflow) {
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

export function defaultParameterValue(parameter, showCancelled) {
  if (parameter.name === "include_cancelled") return showCancelled || Boolean(parameter.default);
  if (parameter.default !== undefined && parameter.default !== null) return parameter.default;
  if (parameter.multiple) return [];
  if (parameter.kind === "boolean") return false;
  return "";
}

export function initialParameters(workflow, showCancelled) {
  return Object.fromEntries((workflow.parameters || []).map((parameter) => [parameter.name, defaultParameterValue(parameter, showCancelled)]));
}

export function displayOptionValue(value) {
  if (DOCUMENT_TYPE_LABELS[String(value)]) return DOCUMENT_TYPE_LABELS[String(value)];
  const text = String(value);
  const spaced = text.replace(/[_-]+/g, " ").trim();
  if (!spaced) return text;
  return spaced
    .split(/\s+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function isBlank(value) {
  return value === null || value === undefined || value === "";
}

export function collectRunParameters(parameters, workflow) {
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

export function resultTables(result) {
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

export function totalRows(result) {
  return resultTables(result).reduce((sum, table) => sum + (Number(table.row_count) || (table.rows || []).length), 0);
}

export function evidenceColumnKind(columnName) {
  const name = String(columnName || "").toLowerCase();
  if (EVIDENCE_DATE_COLUMNS.has(name)) return "date";
  if (EVIDENCE_NUMBER_COLUMNS.has(name)) return "number";
  if (EVIDENCE_TEXT_COLUMNS.has(name)) return "text";
  if (name.startsWith("date_") || name.includes("valid_") || name.endsWith("_date")) return "date";
  return null;
}

export function visibleColumns(columns) {
  return (columns || []).filter((column) => !ALWAYS_HIDDEN_COLUMNS.has(column) && !String(column).endsWith("_id"));
}

export function displayColumnName(column) {
  const key = String(column || "");
  if (key.endsWith("_id")) {
    const stem = key.slice(0, -3).replace(/[_]+/g, " ").trim();
    return stem ? `${stem.charAt(0).toUpperCase()}${stem.slice(1)} ID` : "ID";
  }
  return displayOptionValue(key);
}

export function cellKey(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

export function compareCellValues(left, right) {
  const leftBlank = isBlank(left);
  const rightBlank = isBlank(right);
  if (leftBlank && rightBlank) return 0;
  if (leftBlank) return 1;
  if (rightBlank) return -1;
  if (typeof left === "number" && typeof right === "number") return left - right;

  const leftNumber = Number(left);
  const rightNumber = Number(right);
  if (
    Number.isFinite(leftNumber)
    && Number.isFinite(rightNumber)
    && String(left).trim() !== ""
    && String(right).trim() !== ""
  ) {
    return leftNumber - rightNumber;
  }

  return cellKey(left).localeCompare(cellKey(right), undefined, { numeric: true, sensitivity: "base" });
}

export function filterValueLabel(value) {
  if (value === "") return "(blank)";
  try {
    const parsed = JSON.parse(value);
    if (Array.isArray(parsed)) {
      if (parsed.length === 1 && (typeof parsed[0] === "string" || typeof parsed[0] === "number" || typeof parsed[0] === "boolean")) {
        return decodeText(parsed[0]);
      }
      if (parsed.every((item) => typeof item === "string" || typeof item === "number" || typeof item === "boolean")) {
        return parsed.map(decodeText).join(", ");
      }
    }
  } catch {
    // Not a JSON-serialized structured filter value.
  }
  return decodeText(value);
}

function csvEscape(value) {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function csvCellText(column, value) {
  if (isBlank(value)) return "";
  if (column === "doc_type" || column === "supporting_doc_type" || column === "source_doc_type") {
    return displayOptionValue(value);
  }
  if ((column === "sources" || column === "source" || column === "mentions") && Array.isArray(value)) {
    return value
      .filter((entry) => entry && entry.file)
      .map((entry) => entry.title || entry.file)
      .join("; ");
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return decodeText(value);
  if (Array.isArray(value) && value.every((item) => typeof item === "string" || typeof item === "number")) {
    return value.map(decodeText).join(", ");
  }
  return formatInlineStructuredValue(value) || cellKey(value);
}

export function rowsToCsv(columns, rows) {
  const header = columns.map((column) => csvEscape(displayColumnName(column))).join(",");
  const body = rows.map((row) => columns.map((column) => csvEscape(csvCellText(column, row[column]))).join(","));
  return [header, ...body].join("\r\n");
}

export async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  try {
    document.execCommand("copy");
  } finally {
    textarea.remove();
  }
}

export function downloadText(text, filename) {
  const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function csvFilename(title) {
  const safe = String(title || "table")
    .replace(/[^\w\s-]+/g, "")
    .replace(/\s+/g, "_")
    .slice(0, 80);
  return `${safe || "table"}.csv`;
}

export function formatInlineStructuredValue(value) {
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

export function displayFieldName(key) {
  const aliases = { address_text: "Address", country_iso2: "Country code", kind: "Type", class: "Type" };
  if (aliases[key]) return aliases[key];
  const spaced = String(key).replace(/[_]+/g, " ").trim();
  return spaced ? spaced.charAt(0).toUpperCase() + spaced.slice(1) : String(key);
}

export function decodeText(value) {
  const text = String(value || "")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
  return text;
}

export function highlightParts(text, terms) {
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
