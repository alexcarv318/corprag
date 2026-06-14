import { useEffect, useRef, useState } from "react";

export default function FilterPopover({ anchorElement, anchorRect, column, filters, options, onApply, onClear, onClose }) {
  const popoverRef = useRef(null);
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState(() => new Set(filters[column] || options.map((option) => option.value)));

  useEffect(() => {
    setDraft(new Set(filters[column] || options.map((option) => option.value)));
    setQuery("");
  }, [column, filters, options]);

  useEffect(() => {
    function handlePointerDown(event) {
      if (popoverRef.current?.contains(event.target) || anchorElement?.contains(event.target)) return;
      onClose();
    }
    function handleKeyDown(event) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [anchorElement, onClose]);

  const filteredOptions = options.filter((option) => option.label.toLowerCase().includes(query.trim().toLowerCase()));
  const style = anchorRect
    ? {
        left: Math.min(anchorRect.left + window.scrollX, window.scrollX + window.innerWidth - 280),
        top: anchorRect.bottom + window.scrollY + 6
      }
    : undefined;

  function setAll(nextOptions, checked) {
    setDraft((current) => {
      const next = new Set(current);
      for (const option of nextOptions) {
        if (checked) next.add(option.value);
        else next.delete(option.value);
      }
      return next;
    });
  }

  return (
    <div className="filter-popover" ref={popoverRef} style={style}>
      <input
        autoFocus
        type="search"
        placeholder="Search values..."
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <div className="filter-actions">
        <button type="button" onClick={() => setAll(filteredOptions, true)}>All</button>
        <button type="button" onClick={() => setAll(filteredOptions, false)}>None</button>
      </div>
      <div className="filter-list">
        {filteredOptions.map((option) => (
          <label className="filter-row" key={option.value}>
            <input
              checked={draft.has(option.value)}
              type="checkbox"
              onChange={(event) => {
                setDraft((current) => {
                  const next = new Set(current);
                  if (event.target.checked) next.add(option.value);
                  else next.delete(option.value);
                  return next;
                });
              }}
            />
            <span className="filter-row-text" title={option.label}>{option.label}</span>
            <span className="filter-row-count">{option.count}</span>
          </label>
        ))}
      </div>
      <div className="filter-footer">
        <button type="button" onClick={onClose}>Cancel</button>
        <button type="button" onClick={() => onClear(column)}>Clear</button>
        <button className="primary" type="button" onClick={() => onApply(column, Array.from(draft), options.length)}>Apply</button>
      </div>
    </div>
  );
}

