export default function DisclaimerOverlay({ open, count, onClose }) {
  return (
    <div id="disclaimer-overlay" className="disclaimer-overlay" hidden={!open} role="dialog" aria-modal="true" aria-labelledby="disclaimer-title">
      <div className="disclaimer-card">
        <header>
          <h2 id="disclaimer-title">About this console</h2>
          <p className="lede">Please read before using the corporate knowledge graph workflows.</p>
        </header>
        <div className="disclaimer-body">
          <section>
            <h3>Scope</h3>
            <p>These workflows are built <strong>for corporate users</strong> to explore extracted facts directly.</p>
            <p>At present the knowledge graph contains <strong><span id="disclaimer-document-count" className="disclaimer-count">{count ?? "…"}</span> document works</strong> from that corpus.</p>
          </section>
          <section>
            <h3>Limitations</h3>
            <p>The graph is an analytical extraction surface, not a substitute for legal review of the underlying documents.</p>
          </section>
        </div>
        <footer className="disclaimer-foot">
          <label className="disclaimer-toggle">
            <input id="disclaimer-hide-forever" type="checkbox" />
            <span>Do not show automatically on this browser</span>
          </label>
          <span id="disclaimer-status" className="disclaimer-status" aria-live="polite" />
          <button id="disclaimer-ack-btn" type="button" onClick={onClose}>I have read and understand these limitations</button>
        </footer>
      </div>
    </div>
  );
}
