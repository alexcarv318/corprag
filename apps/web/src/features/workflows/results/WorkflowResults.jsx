import ResultTable from "./ResultTable.jsx";
import { resultTables, totalRows, visibleColumns } from "./tableUtils.js";

export default function WorkflowResults({ result, onSources, onEvidence }) {
  if (!result) return null;
  if (totalRows(result) === 0) {
    return (
      <div id="result-panel">
        <div className="panel"><div className="body"><p className="muted">No matches found.</p></div></div>
      </div>
    );
  }
  return (
    <div id="result-panel">
      {resultTables(result).map((table, index) => {
        const columns = visibleColumns(table.columns || []);
        const rows = table.rows || [];
        const rowCount = typeof table.row_count === "number" ? table.row_count : rows.length;
        return <ResultTable columns={columns} key={table.table_id || index} rowCount={rowCount} rows={rows} tableTitle={table.title || `Table ${index + 1}`} onSources={onSources} onEvidence={onEvidence} />;
      })}
    </div>
  );
}

