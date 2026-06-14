import { isBlank } from "./displayUtils.js";
import { resultTables, totalRows } from "./tableUtils.js";

export function isSourcesColumn(column) {
  return column === "sources" || column === "source" || column === "mentions";
}

export function sourceFiles(row) {
  const files = new Set();
  for (const value of Object.values(row || {})) {
    if (!Array.isArray(value)) continue;
    for (const entry of value) {
      if (entry && typeof entry === "object" && entry.file) files.add(entry.file);
    }
  }
  return Array.from(files);
}

export function evidenceEntityId(row) {
  for (const key of ["organization_id", "person_id", "phase_id", "subject_id", "address_id", "event_id"]) {
    if (typeof row?.[key] === "string" && row[key]) return row[key];
  }
  return null;
}

export function rowContext(row, columns) {
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

export function summarizeResult(result) {
  const tables = resultTables(result);
  const rows = totalRows(result);
  if (tables.length === 1) return `${rows} result${rows === 1 ? "" : "s"}`;
  return `${tables.length} tables · ${rows} total rows`;
}
