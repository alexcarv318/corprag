export function formatCell(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "—";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

export function compactNumber(value) {
  return new Intl.NumberFormat("en", { notation: "compact" }).format(value || 0);
}
