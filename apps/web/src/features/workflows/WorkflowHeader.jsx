import { WorkflowIcon } from "./WorkflowIcon.jsx";

export default function WorkflowHeader({ workflow }) {
  if (!workflow) {
    return (
      <div className="empty">
        <p>Select a workflow from the left.</p>
        <p className="hint">Every question is set up to answer "what is true today" by default. Set a date or turn on <em>Show inactive</em> to look further back.</p>
      </div>
    );
  }
  return (
    <div className="panel">
      <header>
        <WorkflowIcon workflow={workflow} />
        <h2>{workflow.title}</h2>
      </header>
      <div className="body">
        <p>{workflow.description}</p>
        {workflow.use_cases?.length ? (
          <div className="uses">
            <div className="uses-label">Use this when you want to ask:</div>
            <ul className="uses-list">
              {workflow.use_cases.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  );
}
