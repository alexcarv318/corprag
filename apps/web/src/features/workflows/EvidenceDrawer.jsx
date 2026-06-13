import Modal from "../../components/Modal.jsx";

export default function EvidenceDrawer({ evidence, loading, onClose }) {
  return (
    <Modal title="Evidence" onClose={onClose}>
      {loading ? <p className="muted">Loading evidence...</p> : null}
      {evidence ? (
        <>
          <div className="drawer-meta">
            {(evidence.highlight_terms || []).slice(0, 8).map((term) => (
              <span key={term}>{term}</span>
            ))}
          </div>
          {(evidence.chunks || []).map((chunk) => (
            <article className="source-chunk" key={chunk.chunk_id || chunk.sequence_index}>
              <strong>
                {chunk.file || chunk.title || "Source"} {chunk.page_first ? `p. ${chunk.page_first}` : ""}
              </strong>
              <p>{chunk.text || "No excerpt available."}</p>
            </article>
          ))}
          {!(evidence.chunks || []).length ? <p className="muted">No evidence chunks found.</p> : null}
        </>
      ) : null}
    </Modal>
  );
}
