import { useEffect, useMemo, useState } from "react";

import { getTypeahead } from "../../api/workflows.js";
import { typeaheadKindForParameter } from "../../utils/workflows.js";

export default function TypeaheadInput({ parameter, value, subjectId, onChange }) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const kind = useMemo(() => typeaheadKindForParameter(parameter), [parameter]);

  useEffect(() => {
    if (!kind || query.trim().length < 2) {
      setItems([]);
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const payload = await getTypeahead({ kind, q: query, subjectId });
        if (!controller.signal.aborted) {
          setItems(payload.items || []);
          setOpen(true);
        }
      } catch {
        if (!controller.signal.aborted) {
          setItems([]);
        }
      }
    }, 180);

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [kind, query, subjectId]);

  return (
    <div className="typeahead">
      <input
        autoComplete="off"
        id={parameter.name}
        onBlur={() => window.setTimeout(() => setOpen(false), 120)}
        onChange={(event) => {
          setQuery(event.target.value);
          onChange(event.target.value);
        }}
        onFocus={() => setOpen(items.length > 0)}
        placeholder={parameter.placeholder || parameter.label}
        value={query || value || ""}
      />
      {open && items.length ? (
        <div className="typeahead-menu">
          {items.map((item) => (
            <button
              key={`${item.id}-${item.label}`}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => {
                onChange(item.id);
                setQuery(item.label);
                setOpen(false);
              }}
              type="button"
            >
              <span>{item.label}</span>
              {item.hint ? <small>{item.hint}</small> : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
