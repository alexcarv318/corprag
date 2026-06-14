import { useMemo, useState } from "react";

import FilterPopover from "./FilterPopover.jsx";
import ResultCell from "./ResultCell.jsx";
import { cellWidthStyle } from "./resultTableLayout.js";
import { displayColumnName } from "../shared/displayUtils.js";
import { copyText, csvFilename, downloadText, rowsToCsv } from "./exportUtils.js";
import { cellKey, compareCellValues, filterValueLabel } from "./tableUtils.js";

function filterOptionsForColumn(rows, filters, column) {
  const otherFilterKeys = Object.keys(filters).filter((key) => key !== column);
  const candidateRows = otherFilterKeys.length
    ? rows.filter((row) => otherFilterKeys.every((key) => filters[key].includes(cellKey(row[key]))))
    : rows;
  const counts = new Map();
  for (const row of candidateRows) {
    const key = cellKey(row[column]);
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([value, count]) => ({ value, count, label: filterValueLabel(value) }))
    .sort((left, right) => {
      if (left.value === right.value) return 0;
      if (left.value === "") return 1;
      if (right.value === "") return -1;
      return left.value.localeCompare(right.value, undefined, { numeric: true, sensitivity: "base" });
    });
}

export default function ResultTable({ columns, rows, rowCount, tableTitle, onSources, onEvidence }) {
  const [sort, setSort] = useState({ column: null, direction: 0 });
  const [filters, setFilters] = useState({});
  const [activeFilter, setActiveFilter] = useState(null);
  const [copyState, setCopyState] = useState("idle");
  const [columnWidths, setColumnWidths] = useState({});
  const [resizingColumn, setResizingColumn] = useState(null);

  const visibleRows = useMemo(() => {
    let view = rows;
    const filterKeys = Object.keys(filters);
    if (filterKeys.length) {
      view = view.filter((row) => filterKeys.every((column) => filters[column].includes(cellKey(row[column]))));
    }
    if (sort.column && sort.direction) {
      view = view.slice().sort((left, right) => sort.direction * compareCellValues(left[sort.column], right[sort.column]));
    }
    return view;
  }, [filters, rows, sort]);

  const activeOptions = useMemo(() => {
    if (!activeFilter) return [];
    return filterOptionsForColumn(rows, filters, activeFilter.column);
  }, [activeFilter, filters, rows]);

  const dirty = sort.column || Object.keys(filters).length > 0;
  const csvText = useMemo(() => rowsToCsv(columns, visibleRows), [columns, visibleRows]);

  function toggleSort(column) {
    setSort((current) => {
      if (current.column !== column) return { column, direction: 1 };
      if (current.direction === 1) return { column, direction: -1 };
      return { column: null, direction: 0 };
    });
  }

  function applyFilter(column, selectedValues, optionCount) {
    setFilters((current) => {
      const next = { ...current };
      if (selectedValues.length === optionCount) delete next[column];
      else next[column] = selectedValues;
      return next;
    });
    setActiveFilter(null);
  }

  function clearFilter(column) {
    setFilters((current) => {
      const next = { ...current };
      delete next[column];
      return next;
    });
    setActiveFilter(null);
  }

  function clearTableState() {
    setSort({ column: null, direction: 0 });
    setFilters({});
    setActiveFilter(null);
  }

  async function copyCsv() {
    try {
      await copyText(csvText);
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 1500);
    } catch {
      setCopyState("failed");
      window.setTimeout(() => setCopyState("idle"), 1500);
    }
  }

  function startColumnResize(event, column) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    const headerCell = event.currentTarget.closest("th");
    const startX = event.clientX;
    const startWidth = columnWidths[column] || headerCell?.getBoundingClientRect().width || 380;
    setActiveFilter(null);
    setResizingColumn(column);

    function onPointerMove(moveEvent) {
      const nextWidth = Math.max(96, Math.round(startWidth + moveEvent.clientX - startX));
      setColumnWidths((current) => ({ ...current, [column]: nextWidth }));
    }

    function finishResize() {
      setResizingColumn(null);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", finishResize);
      window.removeEventListener("pointercancel", finishResize);
    }

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", finishResize);
    window.addEventListener("pointercancel", finishResize);
  }

  return (
    <div className="panel">
      <header>
        <h3>{tableTitle}</h3>
        <span className="pill">{rowCount} row{rowCount === 1 ? "" : "s"}</span>
        <div className="csv-actions">
          <button className={`csv-copy-btn${copyState === "copied" ? " copied" : ""}`} type="button" onClick={copyCsv}>
            {copyState === "copied" ? "Copied ✓" : copyState === "failed" ? "Copy failed" : "Copy CSV"}
          </button>
          <button className="csv-download-btn" type="button" onClick={() => downloadText(csvText, csvFilename(tableTitle))}>
            Download CSV
          </button>
        </div>
      </header>
      <div className="body">
      <div className="table-meta">
        {Object.keys(filters).length ? <span className="pill">{visibleRows.length} of {rows.length} shown</span> : null}
        {dirty ? <button className="table-clear" type="button" onClick={clearTableState}>Clear filters & sort</button> : null}
      </div>
      <div className={`table-wrap${resizingColumn ? " resizing" : ""}`}>
        <table className="result-table">
          <colgroup>
            {columns.map((column) => (
              <col key={column} style={columnWidths[column] ? { width: `${columnWidths[column]}px` } : undefined} />
            ))}
          </colgroup>
          <thead>
            <tr>
              {columns.map((column) => (
                <th className={resizingColumn === column ? "is-resizing" : ""} key={column} style={cellWidthStyle(columnWidths[column])}>
                  <div className="th-inner">
                    <button className="th-label" type="button" onClick={() => toggleSort(column)}>
                      {displayColumnName(column)}
                      <span className="th-sort">{sort.column === column ? (sort.direction === 1 ? "▲" : "▼") : ""}</span>
                    </button>
                    <button
                      className={`th-filter${filters[column] ? " active" : ""}`}
                      title="Filter"
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        const anchorElement = event.currentTarget;
                        const anchorRect = anchorElement.getBoundingClientRect();
                        setActiveFilter((current) => (
                          current?.column === column
                            ? null
                            : {
                                column,
                                anchorElement,
                                anchorRect
                              }
                        ));
                      }}
                    >
                      ▾
                    </button>
                    <button
                      aria-label={`Resize ${displayColumnName(column)} column`}
                      className="th-resize"
                      title="Drag to resize column"
                      type="button"
                      onPointerDown={(event) => startColumnResize(event, column)}
                    />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, rowIndex) => (
              <tr key={row.id || row.item_id || row.work_id || rowIndex}>
                {columns.map((column) => (
                  <ResultCell
                    column={column}
                    columnWidth={columnWidths[column]}
                    columns={columns}
                    key={column}
                    row={row}
                    value={row[column]}
                    onSources={onSources}
                    onEvidence={onEvidence}
                  />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {activeFilter ? (
        <FilterPopover
          anchorElement={activeFilter.anchorElement}
          anchorRect={activeFilter.anchorRect}
          column={activeFilter.column}
          filters={filters}
          onApply={applyFilter}
          onClear={clearFilter}
          onClose={() => setActiveFilter(null)}
          options={activeOptions}
        />
      ) : null}
      </div>
    </div>
  );
}
