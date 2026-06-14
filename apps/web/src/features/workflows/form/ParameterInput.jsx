import DateInput from "./DateInput.jsx";
import EventTypeSelector from "./EventTypeSelector.jsx";
import MultiSelector from "./MultiSelector.jsx";
import TypeaheadInput from "./TypeaheadInput.jsx";
import { typeaheadKind } from "./parameterUtils.js";

export default function ParameterInput({ parameter, value, label, subjectId, onChange }) {
  const kind = typeaheadKind(parameter);
  if (kind) {
    return (
      <TypeaheadInput
        parameter={parameter}
        subjectId={parameter.name === "subject_id" ? null : subjectId}
        value={value || ""}
        label={label}
        onChange={onChange}
      />
    );
  }
  if (parameter.name === "event_type") {
    return (
      <EventTypeSelector
        parameter={parameter}
        value={value}
        onChange={onChange}
      />
    );
  }
  if ((parameter.kind === "select" || parameter.options?.length) && parameter.options) {
    return (
      <MultiSelector
        parameter={parameter}
        value={value}
        onChange={onChange}
      />
    );
  }
  if (parameter.kind === "boolean") {
    return (
      <label className="bool">
        <input
          type="checkbox"
          name={parameter.name}
          checked={Boolean(value)}
          data-include-cancelled={parameter.name === "include_cancelled" ? "1" : undefined}
          onChange={(event) => onChange(event.target.checked)}
        />
        <span>{parameter.label}</span>
      </label>
    );
  }
  if (parameter.kind === "date") {
    return (
      <DateInput
        parameter={parameter}
        value={value ?? ""}
        onChange={onChange}
      />
    );
  }
  return (
    <input
      type={parameter.kind === "number" ? "number" : "text"}
      name={parameter.name}
      placeholder={parameter.placeholder || ""}
      value={value ?? ""}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
