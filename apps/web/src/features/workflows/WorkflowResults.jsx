import Table from "../../components/Table.jsx";

export default function WorkflowResults({ documentTitles, result, onEvidence, onSource }) {
  if (!result) {
    return <div className="empty-state">Run a workflow to see results.</div>;
  }

  return (
    <div className="results-stack">
      <div className="result-meta">
        <span>{result.row_count} rows</span>
        <span>{Math.round(result.elapsed_ms || 0)} ms</span>
      </div>
      {(result.tables || []).map((table) => (
        <section className="result-table" key={table.table_id}>
          <h3>{table.title}</h3>
          <Table
            columns={table.columns}
            documentTitles={documentTitles}
            rows={table.rows}
            onEvidence={onEvidence}
            onSource={onSource}
          />
        </section>
      ))}
    </div>
  );
}
