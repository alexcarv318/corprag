import { useEffect, useRef, useState } from "react";

import { displayOptionValue } from "../workflows/shared/displayUtils.js";
import DocumentView from "./DocumentView.jsx";

export default function DocumentSourceDrawer({ drawer, onClose, onBack, onOpenDocument, className = "" }) {
  const [visibleDrawer, setVisibleDrawer] = useState(drawer);
  const [renderedOpen, setRenderedOpen] = useState(Boolean(drawer));
  const mountedRef = useRef(Boolean(drawer));
  const open = renderedOpen;
  const title = visibleDrawer?.title || "Sources";

  useEffect(() => {
    if (drawer) {
      setVisibleDrawer(drawer);
      if (mountedRef.current) {
        setRenderedOpen(true);
        return undefined;
      }
      mountedRef.current = true;
      setRenderedOpen(false);
      const timeout = window.setTimeout(() => setRenderedOpen(true), 30);
      return () => window.clearTimeout(timeout);
    }

    setRenderedOpen(false);
    const timeout = window.setTimeout(() => {
      mountedRef.current = false;
      setVisibleDrawer(null);
    }, 240);
    return () => window.clearTimeout(timeout);
  }, [drawer]);

  if (!visibleDrawer) return null;

  return (
    <aside id="sources-drawer" className={`sources-drawer${open ? " open" : ""}${className ? ` ${className}` : ""}`} aria-hidden={!open}>
      <div className="source-drawer-header">
        <div className="source-drawer-heading">
          <h2 id="sources-drawer-title">{title}</h2>
          <div id="sources-drawer-sub" className="source-drawer-subtitle">{visibleDrawer?.subtitle || ""}</div>
        </div>
        <button id="sources-drawer-back" type="button" className="source-drawer-icon-button" hidden={!visibleDrawer?.document || !visibleDrawer?.sources?.length} aria-label="Back to sources" onClick={onBack}>
          <BackIcon />
        </button>
        <button id="sources-drawer-close" type="button" className="source-drawer-icon-button" title="Close (Esc)" aria-label="Close sources" onClick={onClose}>
          <CloseIcon />
        </button>
      </div>
      <div id="sources-drawer-body" className="source-drawer-body">
        {visibleDrawer?.loading ? <div className="source-drawer-status">Loading...</div> : null}
        {visibleDrawer?.error ? <div className="source-drawer-status error">{visibleDrawer.error}</div> : null}
        {visibleDrawer?.document ? (
          <DocumentView
            payload={visibleDrawer.document}
            highlightChunkIds={visibleDrawer.highlightChunkIds || []}
            highlightTerms={visibleDrawer.highlightTerms || []}
          />
        ) : null}
        {!visibleDrawer?.document && visibleDrawer?.sources ? (
          <div className="document-source-list">
            {visibleDrawer.sources.map((source) => (
              <button className="document-source-item" key={`${source.file}-${source.chunk_id || source.chunk_ids?.join(",") || ""}`} type="button" title={sourceTitle(source)} onClick={() => onOpenDocument(source)}>
                <span className="document-source-icon"><SourceDocumentIcon /></span>
                <div className="document-source-copy">
                  <div className="document-source-meta">
                    {sourceMetaLabel(source) ? <span className="document-source-meta-item">{sourceMetaLabel(source)}</span> : null}
                  </div>
                  <div className="document-source-name">{source.title || source.file}</div>
                  <div className="document-source-file">{source.file}</div>
                </div>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </aside>
  );
}

function sourceTitle(source) {
  return [source.title || source.file, source.file, sourceMetaLabel(source)].filter(Boolean).join(" · ");
}

function sourceMetaLabel(source) {
  return displayOptionValue(source.doc_type || source.source_type || source.link_type || "");
}

function SourceDocumentIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7z" />
      <path d="M14 2v5h5" />
      <path d="M9 13h6" />
      <path d="M9 17h4" />
    </svg>
  );
}

function BackIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M15 19L8 12L15 5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
