import { DOCUMENT_TYPE_LABELS } from "./documentLabels.js";

export function isBlank(value) {
  return value === null || value === undefined || value === "";
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

export function displayColumnName(column) {
  const key = String(column || "");
  if (key.endsWith("_id")) {
    const stem = key.slice(0, -3).replace(/[_]+/g, " ").trim();
    return stem ? `${stem.charAt(0).toUpperCase()}${stem.slice(1)} ID` : "ID";
  }
  return displayOptionValue(key);
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
