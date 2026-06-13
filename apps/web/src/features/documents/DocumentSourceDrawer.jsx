import Modal from "../../components/Modal.jsx";

export default function DocumentSourceDrawer({ source, loading, onClose }) {
  return (
    <Modal title="Document source" onClose={onClose}>
      {loading ? <p className="muted">Loading document source...</p> : null}
      {source ? (
        <>
          <div className="source-heading">
            <h3>{source.title || source.file}</h3>
            <span>{source.doc_type || "document"}</span>
          </div>
          {source.summary ? <p>{source.summary}</p> : null}
          {(source.chunks || []).map((chunk) => (
            <article className="source-chunk" key={chunk.chunk_id || chunk.sequence_index}>
              <strong>
                {chunk.structural_path || "Excerpt"} {chunk.page_first ? `p. ${chunk.page_first}` : ""}
              </strong>
              <p>{chunk.text || "No text available."}</p>
            </article>
          ))}
        </>
      ) : null}
    </Modal>
  );
}
