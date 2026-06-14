import { useState } from "react";

import { displayOptionValue } from "./displayUtils.js";

export default function MultiSelector({ parameter, value, onChange }) {
  const [open, setOpen] = useState(false);
  const selected = Array.isArray(value) ? value : value ? [String(value)] : [];
  const options = (parameter.options || []).map(String).filter((option) => option !== "" && option !== "all");
  const sentinel = (parameter.options || []).includes("all") ? "All" : "Any";
  const summary = selected.length === 0 ? `No boxes selected = ${sentinel}` : selected.length === 1 ? displayOptionValue(selected[0]) : `${selected.length} selected`;

  return (
    <div className="multi-select" data-enum-multi="1" data-name={parameter.name}>
      <button className="multi-trigger" type="button" aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen(!open)}>
        {summary}
      </button>
      <div className="multi-menu" hidden={!open}>
        <div className="multi-empty">No boxes selected = {sentinel}</div>
        {options.map((option) => (
          <label className="multi-option" key={option}>
            <input
              type="checkbox"
              value={option}
              checked={selected.includes(option)}
              onChange={(event) => {
                const next = event.target.checked ? [...selected, option] : selected.filter((item) => item !== option);
                onChange(parameter.multiple || parameter.name === "event_type" ? next : next[0] || "");
              }}
            />
            <span>{displayOptionValue(option)}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
