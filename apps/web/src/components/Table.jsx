import { formatCell } from "../utils/format.js";
import DocumentTitle from "../features/documents/DocumentTitle.jsx";

export default function Table({ columns = [], rows = [], documentTitles = {}, onEvidence, onSource }) {
  if (!rows.length) {
    return <div className="empty-state">No rows returned.</div>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.id || row.item_id || row.work_id || index}`}>
              {columns.map((column) => {
                const title = column === "file" ? documentTitles[row[column]]?.title : null;
                return (
                  <td key={column}>
                    {column === "file" && row[column] ? (
                      <DocumentTitle file={row[column]} title={title} />
                    ) : (
                      formatCell(row[column])
                    )}
                  </td>
                );
              })}
              <td className="row-actions">
                <button type="button" onClick={() => onEvidence(row)}>
                  Evidence
                </button>
                {row.file ? (
                  <button type="button" onClick={() => onSource(row.file)}>
                    Source
                  </button>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
