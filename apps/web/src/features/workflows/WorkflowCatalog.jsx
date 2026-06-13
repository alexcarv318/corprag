import { Search } from "lucide-react";

import Tabs from "../../components/Tabs.jsx";

export default function WorkflowCatalog({
  categories,
  selectedCategory,
  onCategoryChange,
  workflows,
  selectedWorkflowId,
  onSelect,
  query,
  onQueryChange
}) {
  return (
    <aside className="catalog">
      <div className="catalog-search">
        <Search size={16} />
        <input
          aria-label="Search workflows"
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Search workflows"
          value={query}
        />
      </div>
      <Tabs tabs={["All", ...categories]} active={selectedCategory} onChange={onCategoryChange} />
      <div className="workflow-list">
        {workflows.map((workflow) => (
          <button
            className={workflow.workflow_id === selectedWorkflowId ? "workflow-item active" : "workflow-item"}
            key={workflow.workflow_id}
            onClick={() => onSelect(workflow.workflow_id)}
            type="button"
          >
            <span>{workflow.title}</span>
            <small>{workflow.category}</small>
          </button>
        ))}
      </div>
    </aside>
  );
}
