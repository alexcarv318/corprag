import DocumentView from "./DocumentView.jsx";
import { WORKFLOW_ICONS } from "../workflows/workflowConstants.js";

export default function DocumentSourceDrawer({ drawer, onClose, onBack, onOpenDocument }) {
  const open = Boolean(drawer);
  const title = drawer?.title || "Sources";
  return (
    <aside id="sources-drawer" className={`sources-drawer${open ? " open" : ""}`} hidden={!open} aria-hidden={!open}>
      <div className="drawer-head">
        <div className="drawer-title-wrap">
          <h2 id="sources-drawer-title">{title}</h2>
          <div id="sources-drawer-sub" className="drawer-sub">{drawer?.subtitle || ""}</div>
        </div>
        <button id="sources-drawer-back" type="button" className="drawer-back" hidden={!drawer?.document} aria-label="Back to sources" onClick={onBack}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
        </button>
        <button id="sources-drawer-close" type="button" className="drawer-close" title="Close (Esc)" aria-label="Close sources" onClick={onClose}>
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>
        </button>
      </div>
      <div id="sources-drawer-body" className="drawer-body">
        {drawer?.loading ? <div className="drawer-status">Loading…</div> : null}
        {drawer?.error ? <div className="drawer-status err">{drawer.error}</div> : null}
        {drawer?.document ? (
          <DocumentView
            payload={drawer.document}
            highlightChunkIds={drawer.highlightChunkIds || []}
            highlightTerms={drawer.highlightTerms || []}
          />
        ) : null}
        {!drawer?.document && drawer?.sources ? (
          <div className="source-list">
            <div className="source-list-hint">Open a source to inspect its extracted chunks.</div>
            {drawer.sources.map((source) => (
              <button className="source-list-item" key={`${source.file}-${source.chunk_id || ""}`} type="button" onClick={() => onOpenDocument(source)}>
                <span className="source-icon" dangerouslySetInnerHTML={{ __html: WORKFLOW_ICONS.document }} />
                <span className="source-copy">
                  <span className="source-meta"><span className="source-meta-item">{source.chunk_id || source.link_type || ""}</span></span>
                  <span className="source-name">{source.title || source.file}</span>
                  <span className="source-file">{source.file}</span>
                </span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </aside>
  );
}
