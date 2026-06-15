import { useMemo } from "react";

import { WorkflowIcon } from "../workflows/WorkflowIcon.jsx";
import SidebarToggleIcon from "./SidebarToggleIcon.jsx";

export default function Sidebar({ catalog, selected, onSelect, collapsed, onToggle }) {
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
          <h1 className="sidebar-title">Workflows</h1>
          <button
            id="sidebar-toggle"
            className="sidebar-toggle"
            type="button"
            title={collapsed ? "Show left panel" : "Hide left panel"}
            aria-label={collapsed ? "Show left panel" : "Hide left panel"}
            aria-expanded={!collapsed}
            onClick={onToggle}
          >
            <SidebarToggleIcon collapsed={collapsed} />
          </button>
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
