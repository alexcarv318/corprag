import MultiSelector from "./MultiSelector.jsx";
import TypeaheadInput from "./TypeaheadInput.jsx";
import { typeaheadKind } from "./parameterUtils.js";

export default function WorkflowForm({ workflow, parameters, labels, showCancelled, setParameter, onRun, running, status }) {
  if (!workflow) return null;
  const dateParams = new Map((workflow.parameters || []).filter((parameter) => parameter.kind === "date").map((parameter) => [parameter.name, parameter]));
  const handled = new Set();
  const hasDateRange = dateParams.has("since") && dateParams.has("until");

  function renderField(parameter) {
    const kind = typeaheadKind(parameter);
    if (kind) {
      return (
        <TypeaheadInput
          parameter={parameter}
          subjectId={parameter.name === "subject_id" ? null : parameters.subject_id}
          value={parameters[parameter.name] || ""}
          label={labels[parameter.name]}
          onChange={(nextValue, nextLabel) => setParameter(parameter.name, nextValue, nextLabel)}
        />
      );
    }
    if ((parameter.kind === "select" || parameter.options?.length) && parameter.options) {
      return <MultiSelector parameter={parameter} value={parameters[parameter.name]} onChange={(nextValue) => setParameter(parameter.name, nextValue)} />;
    }
    if (parameter.kind === "boolean") {
      return (
        <label className="bool">
          <input
            type="checkbox"
            name={parameter.name}
            checked={Boolean(parameters[parameter.name])}
            data-include-cancelled={parameter.name === "include_cancelled" ? "1" : undefined}
            onChange={(event) => setParameter(parameter.name, event.target.checked)}
          />
          <span>{parameter.label}</span>
        </label>
      );
    }
    return (
      <input
        type={parameter.kind === "number" ? "number" : parameter.kind === "date" ? "date" : "text"}
        name={parameter.name}
        placeholder={parameter.placeholder || ""}
        value={parameters[parameter.name] ?? ""}
        onChange={(event) => setParameter(parameter.name, event.target.value)}
      />
    );
  }

  function parameterRows() {
    const rows = [];
    if (hasDateRange) {
      handled.add("since");
      handled.add("until");
      const limit = (workflow.parameters || []).find((parameter) => parameter.name === "limit");
      if (limit) handled.add("limit");
      rows.push(
        <div className="date-range-row" key="date-range">
          <div className="date-range-main">
            <div className="date-range-label">Date range</div>
            <div className="date-range-controls">
              <label className="date-inline-field">
                <span>From</span>
                <span className="date-input-wrap">{renderField(dateParams.get("since"))}</span>
              </label>
              <label className="date-inline-field">
                <span>To</span>
                <span className="date-input-wrap">{renderField(dateParams.get("until"))}</span>
              </label>
            </div>
          </div>
          {limit ? (
            <label className="inline-limit-field">
              <span>{limit.label}</span>
              {renderField(limit)}
            </label>
          ) : null}
        </div>
      );
    }

    for (const parameter of workflow.parameters || []) {
      if (handled.has(parameter.name) || parameter.name === "event_domain") continue;
      if (parameter.kind === "boolean") {
        rows.push(
          <div className="field" style={{ gridColumn: "1 / -1" }} key={parameter.name}>
            {renderField(parameter)}
            {parameter.description ? <div className="desc">{parameter.description}</div> : null}
          </div>
        );
        continue;
      }
      if (parameter.name === "event_type") {
        rows.push(
          <div className="field" style={{ gridColumn: "1 / -1" }} key={parameter.name}>
            {renderField(parameter)}
          </div>
        );
        continue;
      }
      rows.push(
        <div className="param-label" key={`${parameter.name}-label`}>
          <div>
            {parameter.label}
            {parameter.required ? <span className="req-mark">*</span> : null}
          </div>
        </div>
      );
      rows.push(
        <div className="field" key={parameter.name}>
          {renderField(parameter)}
          {parameter.description ? <div className="desc">{parameter.description}</div> : null}
        </div>
      );
    }
    return rows;
  }

  return (
    <div className="panel">
      <header><h2>Parameters</h2></header>
      <div className="body">
        <div className="params">{parameterRows()}</div>
        <div className="actions">
          <button type="button" disabled={running} onClick={onRun}>Run</button>
          <span className={`run-status ${status.tone || ""}`}>{running ? "Running…" : status.text}</span>
          {showCancelled ? null : null}
        </div>
      </div>
    </div>
  );
}
