import { Play } from "lucide-react";

import Button from "../../components/Button.jsx";
import { typeaheadKindForParameter } from "../../utils/workflows.js";
import FacetSelect from "./FacetSelect.jsx";
import TypeaheadInput from "./TypeaheadInput.jsx";

export default function WorkflowForm({ workflow, values, onChange, onSubmit, running }) {
  if (!workflow) {
    return null;
  }

  return (
    <form className="workflow-form" onSubmit={onSubmit}>
      {workflow.parameters.map((parameter) => (
        <label className="field" key={parameter.name} htmlFor={parameter.name}>
          <span>
            {parameter.label}
            {parameter.required ? <em>required</em> : null}
          </span>
          {parameter.kind === "select" ? (
            <FacetSelect
              parameter={parameter}
              parameters={values}
              value={values[parameter.name]}
              workflowId={workflow.workflow_id}
              onChange={(nextValue) => onChange(parameter.name, nextValue)}
            />
          ) : null}
          {parameter.kind === "boolean" ? (
            <input
              checked={Boolean(values[parameter.name])}
              id={parameter.name}
              onChange={(event) => onChange(parameter.name, event.target.checked)}
              type="checkbox"
            />
          ) : null}
          {parameter.kind === "number" ? (
            <input
              id={parameter.name}
              min="1"
              onChange={(event) => onChange(parameter.name, event.target.value)}
              type="number"
              value={values[parameter.name] ?? ""}
            />
          ) : null}
          {parameter.kind === "date" ? (
            <input
              id={parameter.name}
              onChange={(event) => onChange(parameter.name, event.target.value)}
              type="date"
              value={values[parameter.name] ?? ""}
            />
          ) : null}
          {parameter.kind === "string" && typeaheadKindForParameter(parameter) ? (
            <TypeaheadInput
              parameter={parameter}
              subjectId={values.subject_id}
              value={values[parameter.name]}
              onChange={(nextValue) => onChange(parameter.name, nextValue)}
            />
          ) : null}
          {parameter.kind === "string" && !typeaheadKindForParameter(parameter) ? (
            <input
              id={parameter.name}
              onChange={(event) => onChange(parameter.name, event.target.value)}
              placeholder={parameter.placeholder || ""}
              type="text"
              value={values[parameter.name] ?? ""}
            />
          ) : null}
          {parameter.description ? <small>{parameter.description}</small> : null}
        </label>
      ))}
      <Button className="run-button" disabled={running} type="submit">
        <Play size={16} />
        {running ? "Running..." : "Run workflow"}
      </Button>
    </form>
  );
}
