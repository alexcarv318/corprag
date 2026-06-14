import { useCallback, useEffect, useRef, useState } from "react";

import { getTypeahead } from "../../api/workflows.js";
import { TYPEAHEAD_LIMITS } from "./workflowConstants.js";
import { typeaheadKind } from "./workflowUtils.js";

export default function TypeaheadInput({ parameter, value, label, subjectId, onChange }) {
  const kind = typeaheadKind(parameter);
  const [display, setDisplay] = useState(label || value || "");
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const cacheRef = useRef(new Map());
  const requestRef = useRef(0);

  useEffect(() => {
    setDisplay(label || value || "");
  }, [label, value]);

  const fetchItems = useCallback(
    async (query) => {
      if (!kind) return;
      const cacheKey = `${kind}:${subjectId || ""}:${query}`;
      if (cacheRef.current.has(cacheKey)) {
        setItems(cacheRef.current.get(cacheKey));
        setOpen(true);
        return;
      }
      const token = ++requestRef.current;
      setBusy(true);
      try {
        const payload = await getTypeahead({ kind, q: query, limit: TYPEAHEAD_LIMITS[kind] || 10, subjectId });
        if (token !== requestRef.current) return;
        const nextItems = dedupeTypeaheadItems(payload.items || []);
        cacheRef.current.set(cacheKey, nextItems);
        setItems(nextItems);
        setOpen(true);
      } catch (error) {
        if (token !== requestRef.current) return;
        setItems([{ id: "__error__", label: `× ${error.message}` }]);
        setOpen(true);
      } finally {
        if (token === requestRef.current) setBusy(false);
      }
    },
    [kind, subjectId]
  );

  if (!kind) return null;

  return (
    <div className="typeahead" data-typeahead-kind={kind} data-typeahead-limit={TYPEAHEAD_LIMITS[kind] || 10}>
      <input
        className="display"
        type="text"
        autoComplete="off"
        data-typeahead-kind={kind}
        placeholder={parameter.placeholder || `Search ${kind}…`}
        value={display}
        onFocus={() => fetchItems(display.trim())}
        onChange={(event) => {
          const next = event.target.value;
          setDisplay(next);
          onChange("");
          window.clearTimeout(TypeaheadInput.timer);
          TypeaheadInput.timer = window.setTimeout(() => fetchItems(next.trim()), 150);
        }}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
      />
      <div className="ta-spinner" hidden={!busy} />
      <input type="hidden" name={parameter.name} value={value || ""} readOnly />
      <ul className="dropdown" hidden={!open}>
        {items.length ? (
          items.map((item) => (
            <li
              key={item.id}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => {
                if (item.id === "__error__") return;
                onChange(item.id, item.label || item.id);
                setDisplay(item.label || item.id);
                setOpen(false);
              }}
            >
              <span className="ta-label">{item.label || item.id}</span>
              {item.hint ? <div className="ta-hint">{item.hint}</div> : null}
            </li>
          ))
        ) : (
          <li><span className="ta-label">No matches</span></li>
        )}
      </ul>
      <div className="selected-id">{value}</div>
    </div>
  );
}

function dedupeTypeaheadItems(items) {
  const seen = new Set();
  const result = [];
  for (const item of items) {
    const key = `${item.id || ""}::${String(item.label || "").trim().toLowerCase()}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(item);
  }
  return result;
}
