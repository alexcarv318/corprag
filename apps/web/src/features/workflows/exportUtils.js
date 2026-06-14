import { decodeText, displayOptionValue, formatInlineStructuredValue, isBlank, displayColumnName } from "./displayUtils.js";
import { cellKey } from "./tableUtils.js";

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
