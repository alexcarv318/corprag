import { useMemo } from "react";

import { WorkflowIcon } from "../workflows/WorkflowIcon.jsx";

export default function Sidebar({ catalog, selected, onSelect, collapsed, onToggle, status }) {
  const byCategory = useMemo(() => {
    const grouped = {};
    for (const workflow of catalog.workflows || []) {
      if (workflow.dev_only) continue;
      (grouped[workflow.category] = grouped[workflow.category] || []).push(workflow);
    }
    return grouped;
  }, [catalog.workflows]);

  return (
    <aside>
      <div className="sidebar-head">
        <div className="sidebar-head-row">
          <h1 className="sidebar-title">
            Workflows <span className="sub" id="catalog-stats">({(catalog.workflows || []).filter((workflow) => !workflow.dev_only).length})</span>
          </h1>
          <button
            id="sidebar-toggle"
            className="sidebar-toggle"
            type="button"
            title={collapsed ? "Show left panel" : "Hide left panel"}
            aria-label={collapsed ? "Show left panel" : "Hide left panel"}
            aria-expanded={!collapsed}
            onClick={onToggle}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
              <path d="M9 22H15C20 22 22 20 22 15V9C22 4 20 2 15 2H9C4 2 2 4 2 9V15C2 20 4 22 9 22Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M9 2V22" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
        <div className="sidebar-meta">
          <span className={`status ${status.tone || ""}`} id="server-status">{status.text}</span>
        </div>
      </div>
      <div id="sidebar" className="sidebar-body">
        {(catalog.categories || []).map((category) => {
          const workflows = byCategory[category] || [];
          if (!workflows.length) return null;
          return (
            <div className="group" key={category}>
              {workflows.map((workflow) => (
                <div
                  className={`item${selected === workflow.workflow_id ? " active" : ""}`}
                  key={workflow.workflow_id}
                  title={workflow.title}
                  onClick={() => onSelect(workflow.workflow_id)}
                >
                  <WorkflowIcon workflow={workflow} />
                  <span className="title">{workflow.title}</span>
                  <span className="id">{workflow.workflow_id}</span>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
