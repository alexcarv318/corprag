import { StructuredValue } from "../shared/StructuredValue.jsx";
import { decodeText, displayOptionValue, isBlank } from "../shared/displayUtils.js";
import { evidenceColumnKind } from "./tableUtils.js";
import { evidenceEntityId, isSourcesColumn, rowContext, sourceFiles } from "../shared/resultUtils.js";
import { cellWidthStyle } from "./resultTableLayout.js";

export default function ResultCell({ column, value, row, columns, columnWidth, onSources, onEvidence }) {
  const style = cellWidthStyle(columnWidth);
  if (isSourcesColumn(column) && Array.isArray(value)) {
    if (!value.length) return <td className="sources-empty" style={style}>—</td>;
    const sources = value.filter((entry) => entry && entry.file);
    if (!sources.length) return <td className="sources-empty" style={style}>—</td>;
    return (
      <td className="sources-cell-td" style={style}>
        <button className="sources-cell" type="button" title={sources.map((source) => source.file).join("\n")} onClick={(event) => { event.stopPropagation(); onSources(sources, rowContext(row, columns)); }}>
          {sources.length === 1 ? <span className="sources-single">{sources[0].file}</span> : <span className="sources-count">{sources.length} sources</span>}
        </button>
      </td>
    );
  }
  if (isBlank(value)) return <td className="json" style={style}>—</td>;
  if (column === "doc_type" || column === "supporting_doc_type" || column === "source_doc_type") return <td style={style}>{displayOptionValue(value)}</td>;
  if (evidenceColumnKind(column) && sourceFiles(row).length) {
    const values = Array.isArray(value) ? value : [value];
    return (
      <td className="evidence-cell" style={style}>
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
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return <td style={style}>{decodeText(value)}</td>;
  if (Array.isArray(value) && value.every((item) => typeof item === "string" || typeof item === "number")) return <td style={style}>{value.map(decodeText).join(", ")}</td>;
  return <td className="structured-cell" style={style}><StructuredValue value={value} /></td>;
}

