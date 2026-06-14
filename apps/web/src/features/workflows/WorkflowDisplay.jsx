import { decodeText, displayFieldName, formatInlineStructuredValue, highlightParts, isBlank } from "./workflowUtils.js";

export function HighlightedText({ text, terms }) {
  return (
    <>
      {highlightParts(text, terms).map((part, index) => (
        typeof part === "string" ? part : <mark className="evidence-mark" key={index}>{part.mark}</mark>
      ))}
    </>
  );
}

export function StructuredValue({ value }) {
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
