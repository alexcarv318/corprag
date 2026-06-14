import { useEffect, useRef } from "react";

import { HighlightedText } from "../workflows/WorkflowDisplay.jsx";
import { displayOptionValue, highlightParts } from "../workflows/workflowUtils.js";

export default function DocumentView({ payload, highlightChunkIds, highlightTerms }) {
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

