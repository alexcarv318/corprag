import ParameterRows from "./ParameterRows.jsx";

export default function WorkflowForm({ workflow, parameters, labels, setParameter, onRun, running, status }) {
  if (!workflow) return null;

  return (
    <div className="panel">
      <header><h2>Parameters</h2></header>
      <div className="body">
        <div className="params">
          <ParameterRows
            workflow={workflow}
            parameters={parameters}
            labels={labels}
            setParameter={setParameter}
          />
        </div>
        <div className="actions">
          <button type="button" disabled={running} onClick={onRun}>Run</button>
          <span className={`run-status ${status.tone || ""}`}>{running ? "Running…" : status.text}</span>
        </div>
      </div>
    </div>
  );
}
