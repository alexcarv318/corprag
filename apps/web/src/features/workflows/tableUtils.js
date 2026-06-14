import { ALWAYS_HIDDEN_COLUMNS, EVIDENCE_DATE_COLUMNS, EVIDENCE_NUMBER_COLUMNS, EVIDENCE_TEXT_COLUMNS } from "./workflowConstants.js";
import { decodeText, isBlank } from "./displayUtils.js";

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
